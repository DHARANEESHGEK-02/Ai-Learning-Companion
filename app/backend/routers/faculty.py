from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import User, Subject, Exam, Question, AnswerSheet, Evaluation
from ..schemas import (
    SubjectCreate, SubjectResponse,
    ExamCreate, ExamResponse,
    QuestionCreate, QuestionResponse,
)
from ..auth import require_faculty

router = APIRouter()


@router.post("/subjects", response_model=SubjectResponse)
def create_subject(
    data: SubjectCreate,
    current_user: User = Depends(require_faculty),
    db: Session = Depends(get_db),
):
    existing = db.query(Subject).filter(Subject.code == data.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Subject code already exists")
    subject = Subject(**data.model_dump(), created_by=current_user.id)
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject


@router.get("/subjects", response_model=List[SubjectResponse])
def list_subjects(
    current_user: User = Depends(require_faculty),
    db: Session = Depends(get_db),
):
    return db.query(Subject).all()


@router.post("/exams", response_model=ExamResponse)
def create_exam(
    data: ExamCreate,
    current_user: User = Depends(require_faculty),
    db: Session = Depends(get_db),
):
    subject = db.query(Subject).filter(Subject.id == data.subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    exam = Exam(**data.model_dump(), faculty_id=current_user.id)
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return exam


@router.get("/exams")
def list_exams(
    current_user: User = Depends(require_faculty),
    db: Session = Depends(get_db),
):
    exams = db.query(Exam).filter(Exam.faculty_id == current_user.id).all()
    return [
        {
            "id": e.id,
            "title": e.title,
            "subject": e.subject.name if e.subject else "N/A",
            "total_marks": e.total_marks,
            "question_count": len(e.questions),
            "submission_count": len(e.answer_sheets),
            "evaluated_count": len([s for s in e.answer_sheets if s.status == "evaluated"]),
            "created_at": e.created_at.isoformat(),
        }
        for e in exams
    ]


@router.post("/exams/{exam_id}/questions", response_model=QuestionResponse)
def add_question(
    exam_id: int,
    data: QuestionCreate,
    current_user: User = Depends(require_faculty),
    db: Session = Depends(get_db),
):
    exam = db.query(Exam).filter(Exam.id == exam_id, Exam.faculty_id == current_user.id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    question = Question(**data.model_dump(), exam_id=exam_id)
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


@router.get("/exams/{exam_id}/questions", response_model=List[QuestionResponse])
def get_questions(
    exam_id: int,
    current_user: User = Depends(require_faculty),
    db: Session = Depends(get_db),
):
    exam = db.query(Exam).filter(Exam.id == exam_id, Exam.faculty_id == current_user.id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    return exam.questions


@router.get("/submissions")
def list_submissions(
    current_user: User = Depends(require_faculty),
    db: Session = Depends(get_db),
):
    exams = db.query(Exam).filter(Exam.faculty_id == current_user.id).all()
    exam_ids = [e.id for e in exams]
    sheets = db.query(AnswerSheet).filter(AnswerSheet.exam_id.in_(exam_ids)).all()
    return [
        {
            "id": s.id,
            "student_name": s.student.name if s.student else "Unknown",
            "student_email": s.student.email if s.student else "",
            "exam_title": s.exam.title if s.exam else "Unknown",
            "status": s.status,
            "total_score": s.total_score,
            "max_score": s.max_score or (s.exam.total_marks if s.exam else 100),
            "plagiarism_score": s.plagiarism_score,
            "submitted_at": s.submitted_at.isoformat(),
            "evaluated_at": s.evaluated_at.isoformat() if s.evaluated_at else None,
        }
        for s in sheets
    ]


@router.post("/batch-evaluate")
def batch_evaluate(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_faculty),
    db: Session = Depends(get_db),
):
    exams = db.query(Exam).filter(Exam.faculty_id == current_user.id).all()
    exam_ids = [e.id for e in exams]
    pending = db.query(AnswerSheet).filter(
        AnswerSheet.exam_id.in_(exam_ids),
        AnswerSheet.status == "pending",
    ).all()

    from ..routers.evaluations import run_evaluation
    for sheet in pending:
        sheet.status = "processing"
        db.commit()
        background_tasks.add_task(run_evaluation, sheet.id)

    return {"message": f"Queued {len(pending)} answer sheets for evaluation"}


@router.get("/dashboard-stats")
def faculty_dashboard(
    current_user: User = Depends(require_faculty),
    db: Session = Depends(get_db),
):
    exams = db.query(Exam).filter(Exam.faculty_id == current_user.id).all()
    exam_ids = [e.id for e in exams]
    sheets = db.query(AnswerSheet).filter(AnswerSheet.exam_id.in_(exam_ids)).all()
    evaluated = [s for s in sheets if s.status == "evaluated"]
    scores = [s.total_score for s in evaluated if s.total_score is not None]
    max_scores = [s.max_score or 100 for s in evaluated if s.total_score is not None]
    percentages = [s / m * 100 for s, m in zip(scores, max_scores)]

    return {
        "total_exams": len(exams),
        "total_submissions": len(sheets),
        "pending_evaluations": len([s for s in sheets if s.status in ("pending", "processing")]),
        "evaluated": len(evaluated),
        "avg_score_percent": round(sum(percentages) / len(percentages), 1) if percentages else 0,
        "exam_stats": [
            {
                "exam": e.title,
                "submissions": len(e.answer_sheets),
                "evaluated": len([s for s in e.answer_sheets if s.status == "evaluated"]),
                "avg_score": round(
                    sum(s.total_score for s in e.answer_sheets if s.total_score) /
                    max(1, len([s for s in e.answer_sheets if s.total_score])), 1
                ),
            }
            for e in exams
        ],
    }
