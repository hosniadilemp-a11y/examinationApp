import os
import json
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.config import settings
from backend.app.database import engine, Base, SessionLocal
from backend.app.models import User, Module, Group, Exam, ExamSession, StudentAttempt, PracticeAttempt, Question
from backend.app.security import hash_password
from backend.app.routers import auth, users, groups, modules, csv_io, exams, practice, student_exam, proctor, sync_io, training_python, training_linux, admin

def _auto_migrate_schema(engine):
    """Vérifie et applique les colonnes manquantes pour SQLite local sans casser l'existant."""
    if engine.url.drivername.startswith("sqlite"):
        import sqlite3
        db_path = engine.url.database
        if db_path:
            try:
                conn = sqlite3.connect(db_path)
                cur = conn.cursor()
                cur.execute("PRAGMA table_info(users)")
                ucols = [r[1] for r in cur.fetchall()]
                if ucols:
                    if "plain_password" not in ucols:
                        cur.execute("ALTER TABLE users ADD COLUMN plain_password VARCHAR")
                    if "enrollment_year" not in ucols:
                        cur.execute("ALTER TABLE users ADD COLUMN enrollment_year VARCHAR")
                cur.execute("PRAGMA table_info(training_attempts)")
                cols = [r[1] for r in cur.fetchall()]
                if cols:
                    if "target_topic" not in cols:
                        cur.execute("ALTER TABLE training_attempts ADD COLUMN target_topic VARCHAR")
                    if "target_difficulty" not in cols:
                        cur.execute("ALTER TABLE training_attempts ADD COLUMN target_difficulty VARCHAR")
                    if "passed" not in cols:
                        cur.execute("ALTER TABLE training_attempts ADD COLUMN passed BOOLEAN DEFAULT 0")
                    if "hints_used" not in cols:
                        cur.execute("ALTER TABLE training_attempts ADD COLUMN hints_used INTEGER DEFAULT 0")
                cur.execute("PRAGMA table_info(practice_attempts)")
                pcols = [r[1] for r in cur.fetchall()]
                if pcols:
                    if "warnings_count" not in pcols:
                        cur.execute("ALTER TABLE practice_attempts ADD COLUMN warnings_count INTEGER DEFAULT 0")
                cur.execute("PRAGMA table_info(exams)")
                ecols = [r[1] for r in cur.fetchall()]
                if ecols:
                    if "exam_type" not in ecols:
                        cur.execute("ALTER TABLE exams ADD COLUMN exam_type VARCHAR DEFAULT 'theoretical'")
                    if "passing_score" not in ecols:
                        cur.execute("ALTER TABLE exams ADD COLUMN passing_score FLOAT DEFAULT 10.0")
                cur.execute("PRAGMA table_info(exams)")
                ecols = [r[1] for r in cur.fetchall()]
                if ecols:
                    if "exam_type" not in ecols:
                        cur.execute("ALTER TABLE exams ADD COLUMN exam_type VARCHAR DEFAULT 'theoretical'")
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"[SCHEMA AUTO-MIGRATE WARNING] {e}")

def init_db():
    """Initialise les tables et les données d'amorçage (Super Admin & Modules par défaut)."""
    Base.metadata.create_all(bind=engine)
    _auto_migrate_schema(engine)
    db = SessionLocal()
    try:
        # 1. Création de l'Administrateur Initial
        admin = db.query(User).filter(User.username == settings.INITIAL_ADMIN_USERNAME).first()
        if not admin:
            admin = User(
                id="admin-root-01",
                username=settings.INITIAL_ADMIN_USERNAME,
                password_hash=hash_password(settings.INITIAL_ADMIN_PASSWORD),
                plain_password=settings.INITIAL_ADMIN_PASSWORD,
                full_name=settings.INITIAL_ADMIN_NAME,
                email=settings.INITIAL_ADMIN_EMAIL,
                role="admin",
                must_change_password=False,
                is_active=True
            )
            db.add(admin)
        elif not admin.plain_password:
            admin.plain_password = settings.INITIAL_ADMIN_PASSWORD
            
        # 2. Création des Modules et Cours Académiques (3 modules de test + ALGO pour piliers bulletins)
        initial_modules = [
            ("ALGO", "Bases d'Algorithmique", "Variables, boucles, récursivité, tris et complexités fondamentales."),
            ("PYTHON_INIT", "Initiation à Python", "Apprentissage des bases du langage Python, structures de données et algorithmes fondamentaux."),
            ("CRYPTO", "Cryptographie & Sécurité", "Introduction à la sécurité de l'information, chiffrements symétriques/asymétriques, hachage et signatures numériques."),
            ("LINUX_ADMIN", "Administration des Systèmes Linux", "Gestion des serveurs Linux, arborescence système, droits utilisateurs, scripts bash et processus.")
        ]
        
        for code, title, desc in initial_modules:
            existing_mod = db.query(Module).filter(Module.code == code).first()
            if not existing_mod:
                db.add(Module(code=code, title=title, description=desc))

        # 3. Amorçage optionnel des comptes et des 4 Spécialités (configuré via .env)
        if settings.AUTO_SEED_DEFAULT_USERS:
            # Création des 4 Spécialités officielles (4 classes de 4 étudiants = 16 étudiants)
            specialties = [
                ("DEV-IA", "Classe 1 : Développement & IA", "Spécialité Génie Logiciel, Python & Intelligence Artificielle"),
                ("SYS-ADMIN", "Classe 2 : Systèmes & Réseaux Linux", "Spécialité Systèmes Linux, Réseaux & Cloud"),
                ("CYBER-SEC", "Classe 3 : Cybersécurité & Cryptographie", "Spécialité Sécurité de l'Information, Crypto & Audit"),
                ("GRP-1", "Classe 4 : Génie Logiciel & Systèmes (Groupe 1)", "Spécialité Ingénierie Logicielle & Systèmes")
            ]
            for grp_id, grp_name, grp_desc in specialties:
                g = db.query(Group).filter(Group.id == grp_id).first()
                if not g:
                    db.add(Group(id=grp_id, name=grp_name, description=grp_desc))
            db.flush()

            # Enseignant initial avec les modules assignés
            teacher = db.query(User).filter(User.username == settings.INITIAL_TEACHER_USERNAME).first()
            if not teacher:
                teacher = User(
                    id="prof-01",
                    username=settings.INITIAL_TEACHER_USERNAME,
                    password_hash=hash_password(settings.INITIAL_TEACHER_PASSWORD),
                    plain_password=settings.INITIAL_TEACHER_PASSWORD,
                    full_name=settings.INITIAL_TEACHER_NAME,
                    email="prof.martin@exam.local",
                    role="teacher",
                    must_change_password=False,
                    is_active=True
                )
                db.add(teacher)
                db.flush()
            elif not teacher.plain_password:
                teacher.plain_password = settings.INITIAL_TEACHER_PASSWORD

            for m_code in ["PYTHON_INIT", "ALGO", "CRYPTO", "LINUX_ADMIN"]:
                mod = db.query(Module).filter(Module.code == m_code).first()
                if mod and mod not in teacher.assigned_modules:
                    teacher.assigned_modules.append(mod)

            # Enseignants dédiés aux 3 modules de test (PYTHON_INIT, CRYPTO, LINUX_ADMIN)
            module_teachers = [
                ("TCH-PYTHON", "prof_python", "ProfPython1!", "Dr. Martin Laurent (Resp. Python)", "martin.python@ecole.fr", ["PYTHON_INIT"]),
                ("TCH-CRYPTO", "prof_crypto", "ProfCrypto1!", "Dr. Sophie Bernard (Resp. Crypto)", "sophie.crypto@ecole.fr", ["CRYPTO"]),
                ("TCH-LINUX", "prof_linux", "ProfLinux1!", "Dr. Karim Mansouri (Resp. Linux)", "karim.linux@ecole.fr", ["LINUX_ADMIN"]),
            ]
            for t_id, t_user, t_pwd, t_name, t_mail, t_mods in module_teachers:
                t_obj = db.query(User).filter(User.username == t_user).first()
                if not t_obj:
                    t_obj = User(
                        id=t_id,
                        username=t_user,
                        password_hash=hash_password(t_pwd),
                        plain_password=t_pwd,
                        full_name=t_name,
                        email=t_mail,
                        role="teacher",
                        must_change_password=False,
                        is_active=True
                    )
                    db.add(t_obj)
                    db.flush()
                for m_code in t_mods:
                    mod = db.query(Module).filter(Module.code == m_code).first()
                    if mod and mod not in t_obj.assigned_modules:
                        t_obj.assigned_modules.append(mod)

            # Étudiant initial par défaut (Classe GRP-1)
            student = db.query(User).filter(User.username == settings.INITIAL_STUDENT_USERNAME).first()
            if not student:
                student = User(
                    id="ETU-001",
                    username=settings.INITIAL_STUDENT_USERNAME,
                    password_hash=hash_password(settings.INITIAL_STUDENT_PASSWORD),
                    plain_password=settings.INITIAL_STUDENT_PASSWORD,
                    full_name="Alice Dupont (GL-1)",
                    email="etudiant1@exam.local",
                    role="student",
                    group_id="GRP-1",
                    enrollment_year="2025-2026",
                    must_change_password=False,
                    is_active=True
                )
                db.add(student)
            elif not student.plain_password:
                student.plain_password = settings.INITIAL_STUDENT_PASSWORD

            # 4 classes × 4 étudiants = 16 étudiants complets avec toutes leurs informations
            seeded_students = [
                # Classe 1 : DEV-IA (4 étudiants)
                ("etu_dev1", "Alice Dev (IA-1)", "StudentDev1!", "alice.dev@exam.local", "DEV-IA"),
                ("etu_dev2", "Bob Dev (IA-2)", "StudentDev2!", "bob.dev@exam.local", "DEV-IA"),
                ("etu_dev3", "Clara Dev (IA-3)", "StudentDev3!", "clara.dev@exam.local", "DEV-IA"),
                ("etu_dev4", "David Dev (IA-4)", "StudentDev4!", "david.dev@exam.local", "DEV-IA"),
                # Classe 2 : SYS-ADMIN (4 étudiants)
                ("etu_sys1", "Emma Sys (Linux-1)", "StudentSys1!", "emma.sys@exam.local", "SYS-ADMIN"),
                ("etu_sys2", "Fares Sys (Linux-2)", "StudentSys2!", "fares.sys@exam.local", "SYS-ADMIN"),
                ("etu_sys3", "Gilles Sys (Linux-3)", "StudentSys3!", "gilles.sys@exam.local", "SYS-ADMIN"),
                ("etu_sys4", "Hajar Sys (Linux-4)", "StudentSys4!", "hajar.sys@exam.local", "SYS-ADMIN"),
                # Classe 3 : CYBER-SEC (4 étudiants)
                ("etu_sec1", "Ines Sec (Crypto-1)", "StudentSec1!", "ines.sec@exam.local", "CYBER-SEC"),
                ("etu_sec2", "Jules Sec (Crypto-2)", "StudentSec2!", "jules.sec@exam.local", "CYBER-SEC"),
                ("etu_sec3", "Karim Sec (Crypto-3)", "StudentSec3!", "karim.sec@exam.local", "CYBER-SEC"),
                ("etu_sec4", "Lena Sec (Crypto-4)", "StudentSec4!", "lena.sec@exam.local", "CYBER-SEC"),
                # Classe 4 : GRP-1 (3 étudiants + etudiant1 = 4 étudiants)
                ("etu_log2", "Thomas Garnier (GL-2)", "StudentLog2!", "thomas.log@exam.local", "GRP-1"),
                ("etu_log3", "Camille Chevalier (GL-3)", "StudentLog3!", "camille.log@exam.local", "GRP-1"),
                ("etu_log4", "Maxime Lambert (GL-4)", "StudentLog4!", "maxime.log@exam.local", "GRP-1"),
            ]

            for u_name, f_name, pwd, mail, gid in seeded_students:
                existing_s = db.query(User).filter(User.username == u_name).first()
                if not existing_s:
                    db.add(User(
                        id=f"ETU-{u_name.upper()}",
                        username=u_name,
                        password_hash=hash_password(pwd),
                        plain_password=pwd,
                        full_name=f_name,
                        email=mail,
                        role="student",
                        group_id=gid,
                        enrollment_year="2025-2026",
                        must_change_password=False,
                        is_active=True
                    ))
                elif not existing_s.plain_password:
                    existing_s.plain_password = pwd

            # Amorçage des examens modèles pour les 3 modules si absents
            from scripts.reset_and_seed_exact_3_exams import reset_and_seed_3_exams
            e1 = db.query(Exam).filter(Exam.id == "EXAM-THEO-PYTHON").first()
            e2 = db.query(Exam).filter(Exam.id == "EXAM-PRAC-PYTHON").first()
            e3 = db.query(Exam).filter(Exam.id == "EXAM-THEO-CRYPTO").first()
            e4 = db.query(Exam).filter(Exam.id == "EXAM-THEO-LINUX").first()
            if not e1 or not e2 or not e3 or not e4:
                reset_and_seed_3_exams(db)

        db.commit()
    finally:
        db.close()

def _seed_realistic_bulletin_data(db):
    """Amorce exactement les 3 examens officiels et les résultats (piliers + examens) pour simuler la charge et valider les bulletins."""
    from scripts.reset_and_seed_exact_3_exams import reset_and_seed_3_exams
    
    e1 = db.query(Exam).filter(Exam.id == "EXAM-THEO-PYTHON").first()
    e2 = db.query(Exam).filter(Exam.id == "EXAM-PRAC-PYTHON").first()
    e3 = db.query(Exam).filter(Exam.id == "EXAM-THEO-CRYPTO").first()
    if not e1 or not e2 or not e3:
        reset_and_seed_3_exams(db)

    for ex_id in ["EXAM-THEO-PYTHON", "EXAM-PRAC-PYTHON", "EXAM-THEO-CRYPTO"]:
        sess_id = f"SESS-{ex_id}"
        sess = db.query(ExamSession).filter(ExamSession.id == sess_id).first()
        if not sess:
            db.add(ExamSession(
                id=sess_id,
                exam_id=ex_id,
                room_id="SALLE-CENTRAL-01",
                status="completed",
                started_at=datetime.now(timezone.utc),
                ended_at=datetime.now(timezone.utc),
                launched_by=None
            ))
            db.flush()

    student_simulation = {
        # DEV-IA
        "etu_dev1": ({"ALGO": 16.5, "PYTHON_INIT": 18.0, "CRYPTO": 14.0, "LINUX_ADMIN": 15.0}, 17.5, 18.0, "EXAM-THEO-PYTHON", "EXAM-PRAC-PYTHON"),
        "etu_dev2": ({"ALGO": 12.0, "PYTHON_INIT": 14.0, "CRYPTO": 11.5, "LINUX_ADMIN": 12.0}, 13.0, 13.5, "EXAM-THEO-PYTHON", "EXAM-PRAC-PYTHON"),
        "etu_dev3": ({"ALGO": 10.5, "PYTHON_INIT": 12.0, "CRYPTO": 9.5, "LINUX_ADMIN": 10.0}, 11.0, 10.5, "EXAM-THEO-PYTHON", "EXAM-PRAC-PYTHON"),
        "etu_dev4": ({"ALGO": 8.0, "PYTHON_INIT": 9.0, "CRYPTO": 7.5, "LINUX_ADMIN": 8.5}, 8.0, 7.0, "EXAM-THEO-PYTHON", "EXAM-PRAC-PYTHON"),
        # SYS-ADMIN
        "etu_sys1": ({"ALGO": 15.0, "PYTHON_INIT": 14.5, "CRYPTO": 16.0, "LINUX_ADMIN": 19.0}, 17.0, 18.5, "EXAM-THEO-PYTHON", "EXAM-PRAC-PYTHON"),
        "etu_sys2": ({"ALGO": 11.5, "PYTHON_INIT": 12.0, "CRYPTO": 13.0, "LINUX_ADMIN": 15.0}, 14.0, 13.0, "EXAM-THEO-PYTHON", "EXAM-PRAC-PYTHON"),
        "etu_sys3": ({"ALGO": 10.0, "PYTHON_INIT": 9.5, "CRYPTO": 10.5, "LINUX_ADMIN": 12.0}, 10.5, 10.0, "EXAM-THEO-PYTHON", "EXAM-PRAC-PYTHON"),
        "etu_sys4": ({"ALGO": 7.0, "PYTHON_INIT": 8.0, "CRYPTO": 9.0, "LINUX_ADMIN": 10.0}, 8.5, 7.5, "EXAM-THEO-PYTHON", "EXAM-PRAC-PYTHON"),
        # CYBER-SEC
        "etu_sec1": ({"ALGO": 16.0, "PYTHON_INIT": 15.0, "CRYPTO": 18.5, "LINUX_ADMIN": 16.0}, 18.0, 17.5, "EXAM-THEO-CRYPTO", "EXAM-PRAC-PYTHON"),
        "etu_sec2": ({"ALGO": 13.0, "PYTHON_INIT": 12.5, "CRYPTO": 15.0, "LINUX_ADMIN": 13.5}, 14.0, 13.5, "EXAM-THEO-CRYPTO", "EXAM-PRAC-PYTHON"),
        "etu_sec3": ({"ALGO": 10.0, "PYTHON_INIT": 10.5, "CRYPTO": 12.0, "LINUX_ADMIN": 11.0}, 10.5, 10.0, "EXAM-THEO-CRYPTO", "EXAM-PRAC-PYTHON"),
        "etu_sec4": ({"ALGO": 8.5, "PYTHON_INIT": 7.5, "CRYPTO": 9.0, "LINUX_ADMIN": 8.0}, 8.0, 7.0, "EXAM-THEO-CRYPTO", "EXAM-PRAC-PYTHON"),
        # Étudiant initial par défaut
        "etudiant1": ({"ALGO": 14.0, "PYTHON_INIT": 15.5, "CRYPTO": 13.0, "LINUX_ADMIN": 14.5}, 15.0, 16.0, "EXAM-THEO-PYTHON", "EXAM-PRAC-PYTHON"),
    }

    pillar_titles = {
        "ALGO": "Bases d'Algorithmique",
        "PYTHON_INIT": "Initiation à Python",
        "CRYPTO": "Cryptographie Fondamentale",
        "LINUX_ADMIN": "Administration Système Linux"
    }

    for username, (fund_dict, score_theo, score_prac, theo_exam_id, prac_exam_id) in student_simulation.items():
        st = db.query(User).filter(User.username == username).first()
        if not st:
            continue
            
        for m_code, score in fund_dict.items():
            p_existing = db.query(PracticeAttempt).filter(
                PracticeAttempt.user_id == st.id,
                PracticeAttempt.module_code == m_code
            ).first()
            if not p_existing:
                db.add(PracticeAttempt(
                    id=f"P-{st.id}-{m_code}",
                    user_id=st.id,
                    module_code=m_code,
                    module_title=pillar_titles.get(m_code, m_code),
                    grade_20=score,
                    percentage=round((score / 20.0) * 100, 1),
                    total_awarded=score,
                    max_possible=20.0
                ))

        sess_theo_id = f"SESS-{theo_exam_id}"
        att_theo = db.query(StudentAttempt).filter(
            StudentAttempt.student_id == st.id,
            StudentAttempt.session_id == sess_theo_id
        ).first()
        if not att_theo:
            db.add(StudentAttempt(
                id=f"ATT-{st.id}-THEO",
                session_id=sess_theo_id,
                student_id=st.id,
                status="submitted",
                started_at=datetime.now(timezone.utc),
                submitted_at=datetime.now(timezone.utc),
                raw_score=score_theo,
                final_mark=score_theo
            ))

        sess_prac_id = f"SESS-{prac_exam_id}"
        att_prac = db.query(StudentAttempt).filter(
            StudentAttempt.student_id == st.id,
            StudentAttempt.session_id == sess_prac_id
        ).first()
        if not att_prac:
            db.add(StudentAttempt(
                id=f"ATT-{st.id}-PRAC",
                session_id=sess_prac_id,
                student_id=st.id,
                status="submitted",
                started_at=datetime.now(timezone.utc),
                submitted_at=datetime.now(timezone.utc),
                raw_score=score_prac,
                final_mark=score_prac
            ))

    db.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Démarrage
    init_db()
    yield
    # Arrêt
    pass

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Plateforme web d'examen et d'entraînement pour salles de TP en réseau local autonome.",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan
)

# Configuration CORS pour réseau local LAN
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Empêcher la mise en cache agressive des scripts JS et fichiers HTML côté client
@app.middleware("http")
async def add_no_cache_headers(request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path.endswith(".js") or path.endswith(".html") or path == "/":
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# Inclusion des routeurs
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(groups.router)
app.include_router(modules.router)
app.include_router(csv_io.router)
app.include_router(exams.router)
app.include_router(practice.router)
app.include_router(student_exam.router)
app.include_router(proctor.router)
app.include_router(sync_io.router)
app.include_router(training_python.router)
app.include_router(training_linux.router)
app.include_router(admin.router)

@app.get("/api/health", tags=["Système"])
def health_check():
    """Point de contrôle de santé du serveur."""
    return {
        "status": "online",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }

# Distribution de l'Interface Web Statique (Vanilla Frontend)
import os
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "frontend")
if os.path.exists(frontend_dir):
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
