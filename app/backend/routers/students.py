from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import User, Exam, Question, AnswerSheet, Evaluation, LearningPlan, ChatMessage
from ..schemas import (
    AnswerSheetResponse, EvaluationResponse, LearningPlanResponse, ChatRequest, ChatResponse,
    StudentQuestionResponse,
)
from ..auth import require_student
import uuid
import google.generativeai as genai
from ..config import GEMINI_API_KEY

router = APIRouter()

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


@router.get("/exams")
def get_available_exams(
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    exams = db.query(Exam).all()
    result = []
    for exam in exams:
        sheet = db.query(AnswerSheet).filter(
            AnswerSheet.student_id == current_user.id,
            AnswerSheet.exam_id == exam.id,
        ).first()
        result.append({
            "id": exam.id,
            "title": exam.title,
            "subject": exam.subject.name if exam.subject else "N/A",
            "total_marks": exam.total_marks,
            "duration_minutes": exam.duration_minutes,
            "submitted": sheet is not None,
            "status": sheet.status if sheet else "not_submitted",
            "score": sheet.total_score if sheet else None,
        })
    return result


@router.get("/exams/{exam_id}/questions", response_model=List[StudentQuestionResponse])
def get_exam_questions(
    exam_id: int,
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    questions = (
        db.query(Question)
        .filter(Question.exam_id == exam_id)
        .order_by(Question.question_number)
        .all()
    )
    return questions


@router.get("/my-submissions", response_model=List[AnswerSheetResponse])
def get_my_submissions(
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    return db.query(AnswerSheet).filter(AnswerSheet.student_id == current_user.id).all()


@router.get("/submissions/{sheet_id}/evaluations")
def get_submission_evaluations(
    sheet_id: int,
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    sheet = db.query(AnswerSheet).filter(
        AnswerSheet.id == sheet_id,
        AnswerSheet.student_id == current_user.id,
    ).first()
    if not sheet:
        raise HTTPException(status_code=404, detail="Submission not found")

    evals = db.query(Evaluation).filter(Evaluation.answer_sheet_id == sheet_id).all()
    result = []
    for e in evals:
        result.append({
            "id": e.id,
            "question_number": e.question.question_number if e.question else "?",
            "question_text": e.question.question_text[:100] + "..." if e.question and len(e.question.question_text) > 100 else (e.question.question_text if e.question else ""),
            "student_answer": e.student_answer,
            "score": e.score,
            "max_score": e.max_score,
            "similarity_score": e.similarity_score,
            "feedback": e.feedback,
            "missing_concepts": e.missing_concepts or [],
            "strengths": e.strengths or [],
        })
    return result


@router.get("/learning-plan")
def get_learning_plan(
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    plans = db.query(LearningPlan).filter(
        LearningPlan.student_id == current_user.id
    ).order_by(LearningPlan.created_at.desc()).all()
    return [
        {
            "id": p.id,
            "subject": p.subject.name if p.subject else "General",
            "recommendations": p.recommendations or [],
            "weak_areas": p.weak_areas or [],
            "resources": p.resources or [],
            "created_at": p.created_at.isoformat(),
        }
        for p in plans
    ]


@router.post("/chat", response_model=ChatResponse)
def ai_tutor_chat(
    request: ChatRequest,
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    session_id = request.session_id or str(uuid.uuid4())

    history = db.query(ChatMessage).filter(
        ChatMessage.student_id == current_user.id,
        ChatMessage.session_id == session_id,
    ).order_by(ChatMessage.created_at).limit(10).all()

    context = "\n".join([f"Student: {m.message}\nTutor: {m.response}" for m in history])
    subject_ctx = f"Subject: {request.subject}" if request.subject else ""

    prompt = f"""You are an expert AI tutor for university students. Be encouraging, clear, and educational.
{subject_ctx}

Conversation history:
{context}

Student: {request.message}

Provide a helpful, detailed educational response. Include examples where appropriate."""

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        ai_response = response.text
    except Exception as e:
        ai_response = f"I'm having trouble connecting right now. Please try again. (Error: {str(e)[:100]})"

    msg = ChatMessage(
        student_id=current_user.id,
        session_id=session_id,
        message=request.message,
        response=ai_response,
        subject=request.subject,
    )
    db.add(msg)
    db.commit()

    return ChatResponse(response=ai_response, session_id=session_id)


@router.get("/dashboard-stats")
def get_student_dashboard(
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    sheets = db.query(AnswerSheet).filter(AnswerSheet.student_id == current_user.id).all()
    evaluated = [s for s in sheets if s.status == "evaluated"]
    scores = [s.total_score for s in evaluated if s.total_score is not None]

    return {
        "total_submissions": len(sheets),
        "evaluated": len(evaluated),
        "pending": len([s for s in sheets if s.status in ("pending", "processing")]),
        "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
        "best_score": max(scores) if scores else 0,
        "score_history": [
            {
                "exam": s.exam.title if s.exam else "Unknown",
                "score": s.total_score,
                "max": s.max_score or s.exam.total_marks if s.exam else 100,
                "date": s.submitted_at.isoformat(),
            }
            for s in evaluated
        ],
    }
