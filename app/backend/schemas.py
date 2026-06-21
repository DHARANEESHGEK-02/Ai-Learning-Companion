from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class UserCreate(BaseModel):
    email: str
    name: str
    password: str
    role: str
    department: Optional[str] = None


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    role: str
    department: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


class SubjectCreate(BaseModel):
    name: str
    code: str
    description: Optional[str] = None


class SubjectResponse(BaseModel):
    id: int
    name: str
    code: str
    description: Optional[str] = None

    model_config = {"from_attributes": True}


class StudentQuestionResponse(BaseModel):
    id: int
    question_number: int
    question_text: str
    marks: int
    subject_area: Optional[str] = None

    model_config = {"from_attributes": True}


class QuestionCreate(BaseModel):
    question_number: int
    question_text: str
    model_answer: str
    marks: int
    rubric: Optional[List[Dict[str, Any]]] = None
    subject_area: Optional[str] = None


class QuestionResponse(BaseModel):
    id: int
    question_number: int
    question_text: str
    model_answer: str
    marks: int
    rubric: Optional[List[Dict[str, Any]]] = None
    subject_area: Optional[str] = None

    model_config = {"from_attributes": True}


class ExamCreate(BaseModel):
    title: str
    subject_id: int
    total_marks: int = 100
    duration_minutes: int = 180
    instructions: Optional[str] = None


class ExamResponse(BaseModel):
    id: int
    title: str
    subject_id: int
    faculty_id: int
    total_marks: int
    duration_minutes: int
    instructions: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AnswerSheetResponse(BaseModel):
    id: int
    student_id: int
    exam_id: int
    status: str
    total_score: Optional[float] = None
    max_score: Optional[int] = None
    plagiarism_score: Optional[float] = None
    submitted_at: datetime
    evaluated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class EvaluationResponse(BaseModel):
    id: int
    answer_sheet_id: int
    question_id: int
    student_answer: Optional[str] = None
    score: Optional[float] = None
    max_score: Optional[int] = None
    similarity_score: Optional[float] = None
    feedback: Optional[str] = None
    missing_concepts: Optional[List[str]] = None
    strengths: Optional[List[str]] = None

    model_config = {"from_attributes": True}


class LearningPlanResponse(BaseModel):
    id: int
    student_id: int
    subject_id: Optional[int] = None
    recommendations: Optional[List[str]] = None
    weak_areas: Optional[List[str]] = None
    resources: Optional[List[Dict[str, str]]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    message: str
    subject: Optional[str] = None
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str


class AnalyticsDashboard(BaseModel):
    total_students: int
    total_exams: int
    total_evaluations: int
    avg_score: float
    pending_evaluations: int
    subject_stats: List[Dict[str, Any]]
    recent_activity: List[Dict[str, Any]]
