import os
import shutil
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional
from ..database import SessionLocal, get_db
from ..models import User, Exam, AnswerSheet, Evaluation, Question, LearningPlan
from ..schemas import AnswerSheetResponse
from ..auth import get_current_user
from ..config import UPLOAD_DIR

router = APIRouter()


def run_evaluation(sheet_id: int):
    db = SessionLocal()
    try:
        sheet = db.query(AnswerSheet).filter(AnswerSheet.id == sheet_id).first()
        if not sheet:
            return

        from app.modules.ocr_processor import extract_text_from_file
        from app.modules.evaluator import evaluate_answer
        from app.modules.plagiarism import check_plagiarism

        if sheet.file_path and not sheet.extracted_text:
            extracted = extract_text_from_file(sheet.file_path)
            sheet.extracted_text = extracted
            db.commit()

        text = sheet.extracted_text or ""
        exam = db.query(Exam).filter(Exam.id == sheet.exam_id).first()
        if not exam:
            sheet.status = "failed"
            db.commit()
            return

        existing_answers = db.query(AnswerSheet).filter(
            AnswerSheet.exam_id == sheet.exam_id,
            AnswerSheet.id != sheet.id,
            AnswerSheet.extracted_text.isnot(None),
        ).all()
        plag_score = check_plagiarism(text, [s.extracted_text for s in existing_answers if s.extracted_text])
        sheet.plagiarism_score = plag_score

        total_score = 0.0
        total_max = 0
        for question in exam.questions:
            student_ans = extract_answer_for_question(text, question.question_number, question.question_text)
            eval_result = evaluate_answer(
                question_text=question.question_text,
                model_answer=question.model_answer,
                student_answer=student_ans,
                max_marks=question.marks,
                rubric=question.rubric,
                subject_area=question.subject_area,
            )
            ev = Evaluation(
                answer_sheet_id=sheet.id,
                question_id=question.id,
                student_answer=student_ans,
                score=eval_result["score"],
                max_score=question.marks,
                similarity_score=eval_result["similarity_score"],
                feedback=eval_result["feedback"],
                missing_concepts=eval_result["missing_concepts"],
                strengths=eval_result["strengths"],
            )
            db.add(ev)
            total_score += eval_result["score"]
            total_max += question.marks

        sheet.total_score = round(total_score, 2)
        sheet.max_score = total_max
        sheet.status = "evaluated"
        sheet.evaluated_at = datetime.utcnow()
        db.commit()

        generate_learning_plan(db, sheet.student_id, exam, sheet)

    except Exception as e:
        if sheet:
            sheet.status = "failed"
            db.commit()
        print(f"Evaluation error for sheet {sheet_id}: {e}")
    finally:
        db.close()


def extract_answer_for_question(full_text: str, q_num: int, q_text: str) -> str:
    import re
    patterns = [
        rf"(?:Q\.?|Question)\s*{q_num}[:\.\)]\s*(.*?)(?=(?:Q\.?|Question)\s*\d+[:\.\)]|$)",
        rf"\b{q_num}[:\.\)]\s*(.*?)(?=\b\d+[:\.\)]|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, full_text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()[:2000]

    lines = full_text.split("\n")
    for i, line in enumerate(lines):
        if str(q_num) in line[:10]:
            snippet = "\n".join(lines[i:i+20])
            return snippet.strip()[:2000]

    chunk_size = max(200, len(full_text) // max(1, 5))
    start = (q_num - 1) * chunk_size
    return full_text[start:start + chunk_size].strip()


def generate_learning_plan(db, student_id: int, exam, sheet):
    try:
        evaluations = db.query(Evaluation).filter(
            Evaluation.answer_sheet_id == sheet.id
        ).all()
        weak_areas = []
        all_missing = []
        for ev in evaluations:
            if ev.score is not None and ev.max_score and ev.score / ev.max_score < 0.6:
                q = db.query(Question).filter(Question.id == ev.question_id).first()
                if q:
                    weak_areas.append(q.subject_area or q.question_text[:60])
            if ev.missing_concepts:
                all_missing.extend(ev.missing_concepts)

        import google.generativeai as genai
        from app.backend.config import GEMINI_API_KEY
        if GEMINI_API_KEY:
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel("gemini-1.5-flash")
            prompt = f"""Create a personalized learning plan for a student.
Exam: {exam.title}
Weak areas: {', '.join(weak_areas[:5]) if weak_areas else 'None identified'}
Missing concepts: {', '.join(all_missing[:10]) if all_missing else 'None'}

Return JSON with:
{{
  "recommendations": ["list of 5 actionable study recommendations"],
  "resources": [{{"title": "resource name", "type": "book/video/website", "url": ""}}],
  "study_schedule": "brief schedule suggestion"
}}"""
            try:
                response = model.generate_content(prompt)
                import json, re
                text = response.text
                json_match = re.search(r'\{.*\}', text, re.DOTALL)
                if json_match:
                    plan_data = json.loads(json_match.group())
                else:
                    plan_data = {"recommendations": ["Review weak areas", "Practice more problems"], "resources": []}
            except Exception:
                plan_data = {"recommendations": weak_areas[:3] or ["Continue practicing"], "resources": []}
        else:
            plan_data = {"recommendations": ["Review weak areas: " + ", ".join(weak_areas[:3])], "resources": []}

        plan = LearningPlan(
            student_id=student_id,
            subject_id=exam.subject_id,
            recommendations=plan_data.get("recommendations", []),
            weak_areas=weak_areas,
            resources=plan_data.get("resources", []),
        )
        db.add(plan)
        db.commit()
    except Exception as e:
        print(f"Learning plan generation error: {e}")


@router.post("/upload")
async def upload_answer_sheet(
    background_tasks: BackgroundTasks,
    exam_id: int = Form(...),
    file: Optional[UploadFile] = File(None),
    text_answer: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    existing = db.query(AnswerSheet).filter(
        AnswerSheet.student_id == current_user.id,
        AnswerSheet.exam_id == exam_id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already submitted for this exam")

    file_path = None
    if file:
        ext = os.path.splitext(file.filename)[1] if file.filename else ".bin"
        filename = f"{uuid.uuid4()}{ext}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

    sheet = AnswerSheet(
        student_id=current_user.id,
        exam_id=exam_id,
        file_path=file_path,
        extracted_text=text_answer,
        status="processing",
        max_score=exam.total_marks,
    )
    db.add(sheet)
    db.commit()
    db.refresh(sheet)

    background_tasks.add_task(run_evaluation, sheet.id)

    return {"message": "Submitted successfully", "sheet_id": sheet.id, "status": "processing"}


@router.get("/{sheet_id}")
def get_evaluation_result(
    sheet_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sheet = db.query(AnswerSheet).filter(AnswerSheet.id == sheet_id).first()
    if not sheet:
        raise HTTPException(status_code=404, detail="Not found")
    if sheet.student_id != current_user.id and current_user.role != "faculty":
        raise HTTPException(status_code=403, detail="Access denied")

    evaluations = db.query(Evaluation).filter(Evaluation.answer_sheet_id == sheet_id).all()
    return {
        "sheet_id": sheet.id,
        "status": sheet.status,
        "total_score": sheet.total_score,
        "max_score": sheet.max_score,
        "percentage": round(sheet.total_score / sheet.max_score * 100, 1) if sheet.total_score and sheet.max_score else None,
        "plagiarism_score": sheet.plagiarism_score,
        "evaluations": [
            {
                "question_number": e.question.question_number if e.question else "?",
                "question_text": e.question.question_text if e.question else "",
                "student_answer": e.student_answer,
                "score": e.score,
                "max_score": e.max_score,
                "similarity_score": e.similarity_score,
                "feedback": e.feedback,
                "missing_concepts": e.missing_concepts or [],
                "strengths": e.strengths or [],
            }
            for e in evaluations
        ],
    }
