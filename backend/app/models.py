import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Boolean, DateTime, ForeignKey, 
    Text, Integer, Float, Table
)
from sqlalchemy.orm import relationship
from backend.app.database import Base

# Table d'association Many-to-Many Enseignants <-> Modules
teacher_modules = Table(
    "teacher_modules",
    Base.metadata,
    Column("teacher_id", String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("module_code", String, ForeignKey("modules.code", ondelete="CASCADE"), primary_key=True)
)

# Table d'association Many-to-Many Examens <-> Groupes
exam_groups = Table(
    "exam_groups",
    Base.metadata,
    Column("exam_id", String, ForeignKey("exams.id", ondelete="CASCADE"), primary_key=True),
    Column("group_id", String, ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True)
)

class Group(Base):
    __tablename__ = "groups"
    
    id = Column(String, primary_key=True, index=True)  # ex: "GRP-1", "TD-A"
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relations
    users = relationship("User", back_populates="group", cascade="all, delete-orphan")
    exams = relationship("Exam", secondary=exam_groups, back_populates="groups")

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, index=True)  # Matricule ou UUID
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    plain_password = Column(String, nullable=True)  # Mot de passe en clair pour consultation/mise à jour admin
    full_name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    role = Column(String, nullable=False, default="student")  # 'admin', 'teacher', 'student'
    group_id = Column(String, ForeignKey("groups.id", ondelete="SET NULL"), nullable=True)
    must_change_password = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relations
    group = relationship("Group", back_populates="users")
    assigned_modules = relationship("Module", secondary=teacher_modules, back_populates="teachers")
    attempts = relationship("StudentAttempt", back_populates="student", cascade="all, delete-orphan")
    training_attempts = relationship("TrainingAttempt", back_populates="user", cascade="all, delete-orphan")
    chapter_progress = relationship("ChapterProgress", back_populates="user", cascade="all, delete-orphan")
    practice_attempts = relationship("PracticeAttempt", back_populates="user", cascade="all, delete-orphan")

class Module(Base):
    __tablename__ = "modules"
    
    code = Column(String, primary_key=True, index=True)  # ex: 'PYTHON_INIT', 'CRYPTO', 'LINUX_ADMIN'
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relations
    teachers = relationship("User", secondary=teacher_modules, back_populates="assigned_modules")
    exams = relationship("Exam", back_populates="module", cascade="all, delete-orphan")

class Exam(Base):
    __tablename__ = "exams"
    
    id = Column(String, primary_key=True, index=True)
    module_code = Column(String, ForeignKey("modules.code", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    instructions = Column(Text, nullable=True)
    duration_minutes = Column(Integer, nullable=False, default=60)
    global_points = Column(Float, nullable=False, default=20.0)
    navigation_mode = Column(String, nullable=False, default="free")
    shuffle_questions = Column(Boolean, nullable=False, default=True)
    shuffle_options = Column(Boolean, nullable=False, default=True)
    partial_credit_enabled = Column(Boolean, nullable=False, default=True)
    default_negative_penalty = Column(Float, nullable=False, default=0.5)
    created_by = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relations
    module = relationship("Module", back_populates="exams")
    groups = relationship("Group", secondary=exam_groups, back_populates="exams")
    questions = relationship("Question", back_populates="exam", cascade="all, delete-orphan", order_by="Question.ordering")
    sessions = relationship("ExamSession", back_populates="exam", cascade="all, delete-orphan")

class Question(Base):
    __tablename__ = "questions"
    
    id = Column(String, primary_key=True, index=True)
    exam_id = Column(String, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    ordering = Column(Integer, nullable=False, default=1)
    type = Column(String, nullable=False)  # 'boolean', 'single_choice', 'multi_choice', 'fill_blank', 'matching'
    prompt_markdown = Column(Text, nullable=False)
    points = Column(Float, nullable=False, default=1.0)
    negative_penalty = Column(Float, nullable=False, default=0.5)
    time_limit_seconds = Column(Integer, nullable=True)
    options_json = Column(Text, nullable=False, default="[]")
    correct_answers_json = Column(Text, nullable=False, default="[]")
    
    # Relations
    exam = relationship("Exam", back_populates="questions")

class ExamSession(Base):
    __tablename__ = "exam_sessions"
    
    id = Column(String, primary_key=True, index=True)
    exam_id = Column(String, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    room_id = Column(String, nullable=False)  # ex: "SALLE-TP-1"
    status = Column(String, nullable=False, default="waiting")  # 'waiting', 'in_progress', 'completed', 'archived'
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    launched_by = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Relations
    exam = relationship("Exam", back_populates="sessions")
    attempts = relationship("StudentAttempt", back_populates="session", cascade="all, delete-orphan")

class StudentAttempt(Base):
    __tablename__ = "student_attempts"
    
    id = Column(String, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("exam_sessions.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, nullable=False, default="waiting")  # 'waiting', 'in_progress', 'suspended', 'submitted', 'timed_out'
    started_at = Column(DateTime, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    raw_score = Column(Float, nullable=True)
    final_mark = Column(Float, nullable=True)
    suspension_reason = Column(String, nullable=True)
    suspension_count = Column(Integer, nullable=False, default=0)
    client_ip = Column(String, nullable=True)
    
    # Relations
    session = relationship("ExamSession", back_populates="attempts")
    student = relationship("User", back_populates="attempts")
    answers = relationship("StudentAnswer", back_populates="attempt", cascade="all, delete-orphan")

class StudentAnswer(Base):
    __tablename__ = "student_answers"
    
    attempt_id = Column(String, ForeignKey("student_attempts.id", ondelete="CASCADE"), primary_key=True)
    question_id = Column(String, ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True)
    answer_payload_json = Column(Text, nullable=False, default="{}")
    is_correct = Column(Boolean, nullable=True)
    awarded_points = Column(Float, nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relations
    attempt = relationship("StudentAttempt", back_populates="answers")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, nullable=True, index=True)
    student_id = Column(String, nullable=True, index=True)
    event_type = Column(String, nullable=False)  # 'LOGIN', 'FULLSCREEN_EXIT', 'FOCUS_LOST', 'SUSPENDED', 'UNLOCKED', 'SUBMIT'
    details_json = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

class TrainingAttempt(Base):
    __tablename__ = "training_attempts"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    assessment_type = Column(String, nullable=False, default="training")  # 'theoretical', 'practical', 'training', 'evolution'
    selected_topics_json = Column(Text, nullable=False, default="[]")
    selected_difficulties_json = Column(Text, nullable=False, default="[]")
    target_topic = Column(String, nullable=True)
    target_difficulty = Column(String, nullable=True)
    passed = Column(Boolean, nullable=True)  # True if final_mark >= 14.0
    final_mark = Column(Float, nullable=False)  # Note sur 20
    percentage = Column(Float, nullable=False)
    total_questions = Column(Integer, nullable=False)
    correct_count = Column(Integer, nullable=False)
    hints_used = Column(Integer, nullable=False, default=0)
    topic_marks_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    user = relationship("User", back_populates="training_attempts")

class ChapterProgress(Base):
    __tablename__ = "chapter_progress"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    chapter_id = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="in_progress")  # 'not_started', 'in_progress', 'completed'
    best_mark = Column(Float, nullable=False, default=0.0)
    completed_exercises = Column(Integer, nullable=False, default=0)
    total_exercises = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    user = relationship("User", back_populates="chapter_progress")

class PracticeAttempt(Base):
    __tablename__ = "practice_attempts"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    module_code = Column(String, nullable=False, index=True)  # ALGO, PYTHON_INIT, CRYPTO, LINUX_ADMIN
    module_title = Column(String, nullable=False)
    grade_20 = Column(Float, nullable=False)
    percentage = Column(Float, nullable=False)
    total_awarded = Column(Float, nullable=False)
    max_possible = Column(Float, nullable=False)
    answers_json = Column(Text, nullable=False, default="{}")
    detailed_results_json = Column(Text, nullable=True)
    warnings_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    user = relationship("User", back_populates="practice_attempts")


