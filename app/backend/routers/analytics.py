from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..models import User, Exam, AnswerSheet, Evaluation, Subject
from ..auth import get_current_user

router = APIRouter()


@router.get("/dashboard")
def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    total_students = db.query(User).filter(User.role == "student").count()
    total_exams = db.query(Exam).count()
    total_evals = db.query(AnswerSheet).filter(AnswerSheet.status == "evaluated").count()
    pending = db.query(AnswerSheet).filter(AnswerSheet.status.in_(["pending", "processing"])).count()

    evaluated_sheets = db.query(AnswerSheet).filter(
        AnswerSheet.status == "evaluated",
        AnswerSheet.total_score.isnot(None),
        AnswerSheet.max_score.isnot(None),
    ).all()
    scores_pct = [
        s.total_score / s.max_score * 100
        for s in evaluated_sheets
        if s.max_score and s.max_score > 0
    ]
    avg_score = round(sum(scores_pct) / len(scores_pct), 1) if scores_pct else 0

    subjects = db.query(Subject).all()
    subject_stats = []
    for subj in subjects:
        exam_ids = [e.id for e in subj.exams]
        if not exam_ids:
            continue
        sheets = db.query(AnswerSheet).filter(
            AnswerSheet.exam_id.in_(exam_ids),
            AnswerSheet.status == "evaluated",
            AnswerSheet.total_score.isnot(None),
        ).all()
        if not sheets:
            continue
        pcts = [s.total_score / s.max_score * 100 for s in sheets if s.max_score]
        subject_stats.append({
            "subject": subj.name,
            "code": subj.code,
            "submissions": len(sheets),
            "avg_score": round(sum(pcts) / len(pcts), 1) if pcts else 0,
        })

    recent = db.query(AnswerSheet).order_by(
        AnswerSheet.submitted_at.desc()
    ).limit(10).all()

    return {
        "total_students": total_students,
        "total_exams": total_exams,
        "total_evaluations": total_evals,
        "avg_score_percent": avg_score,
        "pending_evaluations": pending,
        "subject_stats": subject_stats,
        "recent_activity": [
            {
                "student": s.student.name if s.student else "Unknown",
                "exam": s.exam.title if s.exam else "Unknown",
                "status": s.status,
                "score": f"{s.total_score}/{s.max_score}" if s.total_score else "—",
                "submitted_at": s.submitted_at.isoformat(),
            }
            for s in recent
        ],
        "score_distribution": _score_distribution(scores_pct),
    }


def _score_distribution(scores_pct: list) -> list:
    bands = {"0-40": 0, "41-60": 0, "61-75": 0, "76-90": 0, "91-100": 0}
    for s in scores_pct:
        if s <= 40:
            bands["0-40"] += 1
        elif s <= 60:
            bands["41-60"] += 1
        elif s <= 75:
            bands["61-75"] += 1
        elif s <= 90:
            bands["76-90"] += 1
        else:
            bands["91-100"] += 1
    return [{"range": k, "count": v} for k, v in bands.items()]


@router.get("/subject/{subject_id}")
def get_subject_analytics(
    subject_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        return {"error": "Subject not found"}

    exam_ids = [e.id for e in subject.exams]
    sheets = db.query(AnswerSheet).filter(
        AnswerSheet.exam_id.in_(exam_ids),
        AnswerSheet.status == "evaluated",
    ).all()

    evals = db.query(Evaluation).join(AnswerSheet).filter(
        AnswerSheet.exam_id.in_(exam_ids)
    ).all()

    concept_freq: dict = {}
    for ev in evals:
        for concept in (ev.missing_concepts or []):
            concept_freq[concept] = concept_freq.get(concept, 0) + 1

    top_missing = sorted(concept_freq.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "subject": subject.name,
        "total_submissions": len(sheets),
        "top_missing_concepts": [{"concept": k, "count": v} for k, v in top_missing],
    }
