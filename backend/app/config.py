import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "ExaminationQuiz Platform"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    
    # Base de données : PostgreSQL prioritaire, avec bascule SQLite WAL locale
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://exam_user:exam_password@localhost:5432/exam_db")
    SQLITE_FALLBACK_URL: str = os.getenv("SQLITE_FALLBACK_URL", f"sqlite:///{os.getenv('SQLITE_DB_PATH', './exam_app.db')}")
    
    # Sécurité JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "exam_quiz_lan_insecure_default_secret_key_change_in_prod_998877")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 heures pour une session d'examen
    
    # Initialisation des identifiants (variables d'environnement, non hardcodés)
    INITIAL_ADMIN_USERNAME: str = os.getenv("ADMIN_USER", "admin")
    INITIAL_ADMIN_PASSWORD: str = os.getenv("ADMIN_PASS", "admin123")
    INITIAL_ADMIN_NAME: str = os.getenv("ADMIN_NAME", "Super Administrateur")
    INITIAL_ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "admin@exam.local")

    INITIAL_TEACHER_USERNAME: str = os.getenv("TEACHER_USER", "prof_martin")
    INITIAL_TEACHER_PASSWORD: str = os.getenv("TEACHER_PASS", "prof123")
    INITIAL_TEACHER_NAME: str = os.getenv("TEACHER_NAME", "Professeur Martin")

    INITIAL_STUDENT_USERNAME: str = os.getenv("STUDENT_USER", "etudiant1")
    INITIAL_STUDENT_PASSWORD: str = os.getenv("STUDENT_PASS", "etudiant123")
    INITIAL_STUDENT_NAME: str = os.getenv("STUDENT_NAME", "Alice Dupont")

    # Activation de l'amorçage automatique des comptes en base de données
    AUTO_SEED_DEFAULT_USERS: bool = os.getenv("AUTO_SEED_DEFAULT_USERS", "true").lower() in ("true", "1", "yes")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
