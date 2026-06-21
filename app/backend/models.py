from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)
    department = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    answer_sheets = relationship("AnswerSheet", back_populates="student", foreign_keys="AnswerSheet.student_id")
    learning_plans = relationship("LearningPlan", back_populates="student")
    chat_messages = relationship("ChatMessage", back_populates="student")
    exams_created = relationship("Exam", back_populates="faculty")
    subjects_created = relationship("Subject", back_populates="creator")


class Subject(Base):
    __tablename__ = "subjects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    code = Column(String(50), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"))

    creator = relationship("User", back_populates="subjects_created")
    exams = relationship("Exam", back_populates="subject")
    learning_plans = relationship("LearningPlan", back_populates="subject")


class Exam(Base):
    __tablename__ = "exams"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    faculty_id = Column(Integer, ForeignKey("users.id"))
    total_marks = Column(Integer, default=100)
    duration_minutes = Column(Integer, default=180)
    instructions = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    subject = relationship("Subject", back_populates="exams")
    faculty = relationship("User", back_populates="exams_created")
    questions = relationship("Question", back_populates="exam", cascade="all, delete-orphan")
    answer_sheets = relationship("AnswerSheet", back_populates="exam")


class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id"))
    question_number = Column(Integer, nullable=False)
    question_text = Column(Text, nullable=False)
    model_answer = Column(Text, nullable=False)
    marks = Column(Integer, nullable=False)
    rubric = Column(JSON, nullable=True)
    subject_area = Column(String(100), nullable=True)

    exam = relationship("Exam", back_populates="questions")
    evaluations = relationship("Evaluation", back_populates="question")


class AnswerSheet(Base):
    __tablename__ = "answer_sheets"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"))
    exam_id = Column(Integer, ForeignKey("exams.id"))
    file_path = Column(String(500), nullable=True)
    extracted_text = Column(Text, nullable=True)
    status = Column(String(50), default="pending")
    total_score = Column(Float, nullable=True)
    max_score = Column(Integer, nullable=True)
    plagiarism_score = Column(Float, nullable=True)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    evaluated_at = Column(DateTime, nullable=True)

    student = relationship("User", back_populates="answer_sheets", foreign_keys=[student_id])
    exam = relationship("Exam", back_populates="answer_sheets")
    evaluations = relationship("Evaluation", back_populates="answer_sheet", cascade="all, delete-orphan")


class Evaluation(Base):
    __tablename__ = "evaluations"
    id = Column(Integer, primary_key=True, index=True)
    answer_sheet_id = Column(Integer, ForeignKey("answer_sheets.id"))
    question_id = Column(Integer, ForeignKey("questions.id"))
    student_answer = Column(Text, nullable=True)
    score = Column(Float, nullable=True)
    max_score = Column(Integer, nullable=True)
    similarity_score = Column(Float, nullable=True)
    feedback = Column(Text, nullable=True)
    missing_concepts = Column(JSON, nullable=True)
    strengths = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    answer_sheet = relationship("AnswerSheet", back_populates="evaluations")
    question = relationship("Question", back_populates="evaluations")


class LearningPlan(Base):
    __tablename__ = "learning_plans"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"))
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    recommendations = Column(JSON, nullable=True)
    weak_areas = Column(JSON, nullable=True)
    resources = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("User", back_populates="learning_plans")
    subject = relationship("Subject", back_populates="learning_plans")


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"))
    session_id = Column(String(100), nullable=True)
    message = Column(Text, nullable=False)
    response = Column(Text, nullable=True)
    subject = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("User", back_populates="chat_messages")
