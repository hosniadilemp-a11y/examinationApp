import pytest
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app, _seed_realistic_bulletin_data
from backend.app.models import User, Group, Module
from backend.app.security import hash_password

# Base de données de test en mémoire isolée
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    """Crée une nouvelle base de données propre pour chaque test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    # Données d'amorçage pour les tests
    admin = User(
        id="admin-01",
        username="admin",
        password_hash=hash_password("admin123"),
        plain_password="admin123",
        full_name="Admin Test",
        email="admin@test.com",
        role="admin",
        must_change_password=False,
        is_active=True
    )
    group1 = Group(id="GRP-1", name="Groupe 1", description="Groupe de test 1")
    group2 = Group(id="GRP-2", name="Groupe 2", description="Groupe de test 2")
    
    teacher = User(
        id="prof-01",
        username="prof_martin",
        password_hash=hash_password("prof123"),
        plain_password="prof123",
        full_name="Professeur Martin",
        email="martin@test.com",
        role="teacher",
        must_change_password=False,
        is_active=True
    )
    
    student = User(
        id="ETU-001",
        username="etudiant1",
        password_hash=hash_password("ETU-001"),
        plain_password="ETU-001",
        full_name="Alice Dupont",
        email="alice@test.com",
        role="student",
        group_id="GRP-1",
        must_change_password=True,
        is_active=True
    )
    
    mod1 = Module(code="PYTHON_INIT", title="Initiation à Python", description="Bases Python")
    mod2 = Module(code="CRYPTO", title="Cryptographie", description="Sécurité et chiffrement")
    
    # Spécialités REV-14
    g_dev = Group(id="DEV-IA", name="Développement & Intelligence Artificielle", description="Spécialité IA")
    g_sys = Group(id="SYS-ADMIN", name="Administration Systèmes & Réseaux", description="Spécialité Linux")
    g_sec = Group(id="CYBER-SEC", name="Cybersécurité & Données", description="Spécialité Sécurité")
    
    seeded_users = [admin, group1, group2, g_dev, g_sys, g_sec, teacher, student, mod1, mod2]
    
    # 4 étudiants par spécialité
    spec_students = [
        ("etu_dev1", "Alice Dev (IA-1)", "StudentDev1!", "alice.dev@exam.local", "DEV-IA"),
        ("etu_dev2", "Bob Dev (IA-2)", "StudentDev2!", "bob.dev@exam.local", "DEV-IA"),
        ("etu_dev3", "Clara Dev (IA-3)", "StudentDev3!", "clara.dev@exam.local", "DEV-IA"),
        ("etu_dev4", "David Dev (IA-4)", "StudentDev4!", "david.dev@exam.local", "DEV-IA"),
        ("etu_sys1", "Emma Sys (Linux-1)", "StudentSys1!", "emma.sys@exam.local", "SYS-ADMIN"),
        ("etu_sys2", "Fares Sys (Linux-2)", "StudentSys2!", "fares.sys@exam.local", "SYS-ADMIN"),
        ("etu_sys3", "Gilles Sys (Linux-3)", "StudentSys3!", "gilles.sys@exam.local", "SYS-ADMIN"),
        ("etu_sys4", "Hajar Sys (Linux-4)", "StudentSys4!", "hajar.sys@exam.local", "SYS-ADMIN"),
        ("etu_sec1", "Ines Sec (Crypto-1)", "StudentSec1!", "ines.sec@exam.local", "CYBER-SEC"),
        ("etu_sec2", "Jules Sec (Crypto-2)", "StudentSec2!", "jules.sec@exam.local", "CYBER-SEC"),
        ("etu_sec3", "Karim Sec (Crypto-3)", "StudentSec3!", "karim.sec@exam.local", "CYBER-SEC"),
        ("etu_sec4", "Lena Sec (Crypto-4)", "StudentSec4!", "lena.sec@exam.local", "CYBER-SEC"),
    ]
    for u_name, f_name, pwd, mail, gid in spec_students:
        seeded_users.append(User(
            id=f"ETU-{u_name.upper()}",
            username=u_name,
            password_hash=hash_password(pwd),
            plain_password=pwd,
            full_name=f_name,
            email=mail,
            role="student",
            group_id=gid,
            must_change_password=False,
            is_active=True
        ))
    
    # Affectation des modules au professeur (uniquement PYTHON_INIT, pas CRYPTO)
    teacher.assigned_modules.append(mod1)
    
    db.add_all(seeded_users)
    db.commit()
    
    yield db
    
    db.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db_session):
    """Client de test FastAPI avec injection de la base de données de test."""
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
            
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def admin_headers(client):
    res = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def teacher_headers(client):
    res = client.post("/api/auth/login", json={"username": "prof_martin", "password": "prof123"})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def student_headers(client):
    res = client.post("/api/auth/login", json={"username": "etudiant1", "password": "ETU-001"})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
