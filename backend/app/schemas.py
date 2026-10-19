from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field, ConfigDict

# --- Authentification & Jetons ---
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"
    must_change_password: bool

class TokenPayload(BaseModel):
    sub: str  # user.id
    username: str
    role: str
    must_change_password: bool
    exp: Optional[int] = None

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)

class PasswordChangeRequest(BaseModel):
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=4)

class PasswordResetRequest(BaseModel):
    user_id: str
    new_password: Optional[str] = None  # Si None, réinitialise avec l'ID étudiant

# --- Groupes ---
class GroupBase(BaseModel):
    id: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None

class GroupCreate(GroupBase):
    pass

class GroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class GroupResponse(GroupBase):
    created_at: datetime
    student_count: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)

# --- Modules ---
class ModuleBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None

class ModuleCreate(ModuleBase):
    pass

class ModuleUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None

class ModuleResponse(ModuleBase):
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- Utilisateurs ---
class UserBase(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    full_name: str = Field(..., min_length=1, max_length=200)
    email: Optional[str] = None
    role: str = Field(default="student", pattern="^(admin|teacher|student)$")
    group_id: Optional[str] = None

class UserCreate(UserBase):
    id: Optional[str] = None  # Si absent, utilise username
    password: Optional[str] = None  # Si absent pour étudiant, initialisé avec l'id
    must_change_password: Optional[bool] = True

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = Field(None, pattern="^(admin|teacher|student)$")
    group_id: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None

class UserBrief(BaseModel):
    id: str
    username: str
    full_name: str
    role: str

    model_config = ConfigDict(from_attributes=True)

class UserResponse(BaseModel):
    id: str
    username: str
    full_name: str
    email: Optional[str]
    role: str
    group_id: Optional[str]
    must_change_password: bool
    is_active: bool
    created_at: datetime
    plain_password: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class TeacherModuleAssign(BaseModel):
    teacher_id: str
    module_code: str

# --- Imports / Exports CSV ---
class CSVImportResponse(BaseModel):
    success: bool
    imported_count: int
    updated_count: int
    errors: List[str] = []
    message: str

# --- Questions & Examens ---
class QuestionBase(BaseModel):
    ordering: int = 1
    type: str = Field(..., pattern="^(boolean|single_choice|multi_choice|fill_blank|matching)$")
    prompt_markdown: str
    points: float = 1.0
    negative_penalty: float = 0.5
    time_limit_seconds: Optional[int] = None
    options_json: str = "[]"

class QuestionCreate(QuestionBase):
    correct_answers_json: str  # JSON list, dict or bool

class QuestionUpdate(BaseModel):
    ordering: Optional[int] = None
    type: Optional[str] = Field(None, pattern="^(boolean|single_choice|multi_choice|fill_blank|matching)$")
    prompt_markdown: Optional[str] = None
    points: Optional[float] = None
    negative_penalty: Optional[float] = None
    time_limit_seconds: Optional[int] = None
    options_json: Optional[str] = None
    correct_answers_json: Optional[str] = None

class QuestionResponse(QuestionBase):
    id: str
    exam_id: str
    correct_answers_json: str

    model_config = ConfigDict(from_attributes=True)

class QuestionStudentView(QuestionBase):
    id: str
    exam_id: str
    # correct_answers_json est MASQUÉ aux étudiants pour garantir le secret absolu des épreuves !

    model_config = ConfigDict(from_attributes=True)

class ExamBase(BaseModel):
    module_code: str
    title: str = Field(..., min_length=1, max_length=200)
    instructions: Optional[str] = None
    duration_minutes: int = Field(default=60, ge=1, le=360)
    global_points: float = Field(default=20.0, ge=1.0)
    navigation_mode: str = "free"
    shuffle_questions: bool = True
    shuffle_options: bool = True
    partial_credit_enabled: bool = True
    default_negative_penalty: float = 0.5

class ExamCreate(ExamBase):
    group_ids: List[str] = []
    room_id: Optional[str] = None

class ExamUpdate(BaseModel):
    title: Optional[str] = None
    instructions: Optional[str] = None
    duration_minutes: Optional[int] = None
    global_points: Optional[float] = None
    shuffle_questions: Optional[bool] = None
    shuffle_options: Optional[bool] = None
    partial_credit_enabled: Optional[bool] = None
    default_negative_penalty: Optional[float] = None
    group_ids: Optional[List[str]] = None

class ExamResponse(ExamBase):
    id: str
    created_by: Optional[str]
    created_at: datetime
    question_count: Optional[int] = 0
    assigned_groups: Optional[List[str]] = []

    model_config = ConfigDict(from_attributes=True)

class ExamDetailResponse(ExamResponse):
    questions: List[QuestionResponse] = []

# --- Tests de Niveau ---
class PracticeSubmitPayload(BaseModel):
    answers: dict  # {question_id: user_answer}
    question_ids: Optional[List[str]] = None
    warnings_count: Optional[int] = 0

class PracticeQuestionResult(BaseModel):
    question_id: str
    prompt_markdown: str
    type: str
    user_answer: Any
    correct_answer: Any
    awarded_points: float
    max_points: float
    is_correct: bool
    explanation: str

class PracticeExamResult(BaseModel):
    attempt_id: Optional[str] = None
    module_code: str
    module_title: str
    total_awarded: float
    max_possible: float
    grade_20: float
    percentage: float
    warnings_count: Optional[int] = 0
    detailed_results: List[PracticeQuestionResult]

# Rebuild pour les références circulaires
Token.model_rebuild()

