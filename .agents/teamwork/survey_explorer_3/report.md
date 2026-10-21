# Rapport d'Investigation Backend & Architecture : Centre d'Entraînement Linux

**Auteur** : `survey_explorer_3`  
**Date** : 2026-10-20  
**Statut** : Rapport d'exploration validé  
**Périmètre** : Architecture Backend FastAPI, Modèles SQLAlchemy / SQLite WAL, Piliers Diagnostiques & Découplage Bulletins, Endpoints d'Entraînement Linux et Suite de Tests Pytest (`tests/`).

---

## Résumé Exécutif

L'application **ExaminationQuiz APP** repose sur un backend **FastAPI 0.115+** avec ORM **SQLAlchemy** (moteur SQLite local en mode WAL avec bascule automatique PostgreSQL). Le système dispose d'une infrastructure complète d'évaluation avec :
1. Une distinction formelle entre épreuves officielles du semestre (`StudentAttempt` rattaché à `ExamSession`) et entraînements / tests diagnostiques 24/7 (`PracticeAttempt` et `TrainingAttempt`).
2. Un pilier diagnostique permanent existant (`LINUX_ADMIN`) basé sur 30 questions de positionnement (`seed_linux_30.json`), strictement découplé des moyennes académiques et bulletins semestriels.
3. Un modèle éprouvé de centre d'entraînement avec le Centre Python (`/api/training/python`, `training_service.py`, `curriculum.json`), offrant une structure idéale à reproduire pour le Centre d'Entraînement Linux.
4. Une suite de tests automatisés robuste comprenant **103 tests pytest** exécutés et validés à 100% de succès, isolés dans une base SQLite en mémoire (`tests/conftest.py`).

Ce rapport détaille la cartographie technique exacte, les garanties mathématiques de découplage, la spécification des nouveaux endpoints `/api/training/linux` et la couverture requise pour `tests/test_linux_training.py`.

---

## 1. Architecture Backend & Moteur de Données

### 1.1 Structure de l'Application FastAPI
- **Point d'entrée principal** : `backend/app/main.py`.
- **Cycle de vie (Lifespan)** :
  - La fonction `@asynccontextmanager async def lifespan(app: FastAPI)` gère le démarrage serveur en invoquant `init_db()`.
  - `init_db()` exécute `Base.metadata.create_all(bind=engine)`, puis appelle `_auto_migrate_schema(engine)` pour garantir la rétrocompatibilité des colonnes SQLite sans altérer les données existantes.
  - Initialise l'administrateur racine (`admin-root-01`), les 9 modules académiques initiaux (`ALGO`, `PYTHON_INIT`, `CRYPTO`, `LINUX_ADMIN`, `DEV_WEB`, `DATABASE_SQL`, `NETWORKS`, `AI_ML`, `DATA_STRUCT`), les spécialités (`DEV-IA`, `SYS-ADMIN`, `CYBER-SEC`), l'enseignant principal (`prof-01`), les groupes de TP (`GRP-1`, `GRP-2`) et 12 étudiants types si `AUTO_SEED_DEFAULT_USERS=True`.
- **Distribution statique** : Le frontend Vanilla JS/CSS est monté directement sur la racine `/` via `StaticFiles(directory=frontend_dir, html=True)`.
- **CORS** : Configuré avec `allow_origins=["*"]`, `allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]` pour un fonctionnement autonome en réseau local de salle de TP.

### 1.2 Moteur de Données & Configuration SQLAlchemy
- **Fichier de configuration** : `backend/app/config.py` (utilisation de `pydantic_settings.BaseSettings` avec chargement de `.env`).
- **Connexion à la base** : `backend/app/database.py` implémente `create_configured_engine()` :
  - **Priorité 1** : PostgreSQL si `DATABASE_URL` est accessible (pool size 10, max overflow 20, pre-ping activé).
  - **Repli automatique (Fallback)** : SQLite WAL local (`sqlite:///./exam_app.db`).
  - **Pragmas SQLite automatiques** :
    ```python
    @event.listens_for(Engine, "connect")
    def configure_sqlite_connection(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=10000")
        cursor.close()
    ```
- **Gestion de session** : `SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)` avec dépendance génératrice `get_db()`.

### 1.3 Schéma et Auto-Migration Dynamique
Dans `backend/app/main.py` (`_auto_migrate_schema`), un inspecteur PRAGMA SQLite vérifie et ajoute à la volée les colonnes requises si elles n'existent pas encore dans les tables SQLite physiques (ex: `users.plain_password`, `training_attempts.target_topic`, `exams.exam_type`, etc.).  
Cette méthode garantit une extension transparente sans nécessiter de script de migration externe lourd.

### 1.4 Enregistrement des Routeurs
Tous les routeurs REST sont regroupés dans `backend/app/routers/` et enregistrés dans `app` :
- `auth.py` : `/api/auth` (authentification JWT, gestion de session).
- `users.py` : `/api/users` (gestion des comptes, filtres de spécialité, mots de passe).
- `groups.py` : `/api/groups` (gestion des groupes et promotions).
- `modules.py` : `/api/modules` (gestion des modules académiques et affectation des enseignants).
- `csv_io.py` : `/api/csv` (imports/exports CSV utilisateurs, groupes, résultats).
- `exams.py` : `/api/exams` (création d'examens, templates, questions théoriques & pratiques).
- `practice.py` : `/api/practice` (tests de niveau 24h/24 des 4 piliers).
- `student_exam.py` : `/api/student` (salle d'attente, passage d'examen, autosave, bulletin étudiant).
- `proctor.py` : `/api/proctor` (surveillance en temps réel, prolongation, déverrouillage).
- `sync_io.py` : `/api/sync` (export/import USB de paquets d'examen maîtres et résultats de salle).
- `training_python.py` : `/api/training/python` (centre d'entraînement Python, chapitres, progression, sandbox).
- `admin.py` : `/api/admin` (statistiques consolidées, génération de bulletins PDF/DOCX/ZIP).

---

## 2. Suivi de Progression, Piliers Diagnostiques & Découplage Académique

### 2.1 Les Quatre Piliers Diagnostiques & `LINUX_ADMIN`
Le routeur `backend/app/routers/practice.py` gère les 4 tests de niveau permanents disponibles 24h/24 :
1. **ALGO** : Bases d'Algorithmique (`seed_algo_30.json`).
2. **PYTHON_INIT** : Bases de Python (`seed_python_30.json`).
3. **CRYPTO** : Bases de Cryptographie (`seed_crypto_30.json`).
4. **LINUX_ADMIN** : Bases d'Administration Linux (`seed_linux_30.json`).

Pour chaque module, le système :
- Tire 20 à 30 questions parmi les seeds avec double brassage (ordre des questions + ordre des options).
- Masque les réponses correctes dans la vue étudiant (`QuestionStudentView`).
- Calcule la note instantanée sur 20 via `backend/app/services/grading.py`.
- Enregistre une tentative dans la table `practice_attempts`.
- Calcule les métriques officielles : nombre de tentatives, moyenne des 4 dernières notes (`last_4_average`), note maximale (`best_grade`), niveau (1 à 6) et titre de niveau selon l'échelle officielle :
  - Niveau 1 : Insuffisant (< 7,00)
  - Niveau 2 : Sous la moyenne (7,00 à < 10,00)
  - Niveau 3 : Limite (10,00 à < 12,00)
  - Niveau 4 : Moyen (12,00 à < 14,00)
  - Niveau 5 : Bon (14,00 à < 16,00)
  - Niveau 6 : Excellent (16,00 à 20,00)

### 2.2 Modèle de Données `PracticeAttempt`
Table `practice_attempts` dans `backend/app/models.py` :
```python
class PracticeAttempt(Base):
    __tablename__ = "practice_attempts"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    module_code = Column(String, nullable=False, index=True)  # 'ALGO', 'PYTHON_INIT', 'CRYPTO', 'LINUX_ADMIN'
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
```

### 2.3 Découplage Strict Garanti dans `_build_student_bulletin` (`admin.py`)
L'architecture garantit un **découplage strict et hermétique** entre les entraînements / tests diagnostiques et les notes d'examens officiels du semestre.  
Preuve par le code dans `backend/app/routers/admin.py` (lignes 334-405) :

```python
# 1. Les 4 piliers de niveau sont extraits de PracticeAttempt UNIQUEMENT pour la section "fundamentals"
p_attempts = db.query(PracticeAttempt).filter(PracticeAttempt.user_id == st.id).all()
for code, title in pillar_configs:
    matching = [p.grade_20 for p in p_attempts if p.module_code == code]
    best_score = round(max(matching), 2) if matching else None
    fundamentals[code] = { "score": best_score, ... }

# 2. Les notes officielles sont extraites STRICTEMENT de StudentAttempt rattaché à une ExamSession
s_attempts = db.query(StudentAttempt).filter(
    StudentAttempt.student_id == st.id,
    StudentAttempt.status.in_(["submitted", "completed", "timed_out"]),
    StudentAttempt.final_mark.isnot(None)
).all()

# 3. La moyenne générale et les verdicts académiques sont calculés EXCLUSIVEMENT à partir des épreuves officielles
official_scores = exam_scores  # [theo_score, prac_score]
general_avg = round(sum(official_scores) / len(official_scores), 2) if official_scores else None

if general_avg is not None:
    is_pass = general_avg >= 10.0
    verdict = "ADMIS" if is_pass else "AJOURNÉ"
```

**Conséquence fondamentale** :
Aucune tentative d'entraînement, aucun test de positionnement et aucun exercice pratique Linux ne modifie la moyenne générale du semestre (`general_average`), la moyenne des examens (`exams_average`), ni la décision du jury (`verdict`: ADMIS/AJOURNÉ). Le bulletin affiche les piliers diagnostiques dans une section distincte d'évaluation de niveau préalable, sans impact sur le calcul d'admissibilité semestrielle.

### 2.4 Liaison du Centre d'Entraînement Linux avec le Pilier `LINUX_ADMIN`
Lorsque l'étudiant s'entraîne dans le Centre Linux :
- Ses tentatives d'entraînement ou validations de défis sont enregistrées avec `module_code="LINUX_ADMIN"`.
- Ces scores alimentent les statistiques du pilier `LINUX_ADMIN` accessibles via `GET /api/practice/modules` et `GET /api/practice/history`.
- Le bulletin académique (`GET /api/student/bulletin`) affiche instantanément la meilleure performance obtenue sous le pilier `fundamentals["LINUX_ADMIN"]`.
- Le découplage reste rigoureusement préservé.

---

## 3. Spécification des Endpoints & Architecture du Service d'Entraînement Linux

### 3.1 Modèle de Conception : Réplication du Centre Python
Le Centre d'Entraînement Python existant dans `backend/app/routers/training_python.py` et `backend/app/services/training_service.py` fournit l'architecture de référence :
- Séparation données de cursus (`data/`) / logique métier (`services/`) / API REST (`routers/`).
- Masquage systématique des tests cachés (`hidden_tests`) et solutions de référence lors de l'accès étudiant.
- Évaluation granulaire avec scoring partiel et rapport de rétroaction détaillé.

### 3.2 Fichiers de Données Cursus Linux (`backend/app/data/linux_training/`)
Création du dossier `backend/app/data/linux_training/` contenant :
1. `curriculum.json` : Cursus complet structuré en 4 niveaux progressifs :
   - **Niveau 1 : Navigation & Fichiers de Base** (`pwd`, `cd`, `ls -la`, `touch`, `mkdir -p`, `cat`, `head`, `tail`, `wc`, `cp`, `mv`, `rm -r`).
   - **Niveau 2 : Permissions, Utilisateurs & Filtrage** (`chmod` octal/symbolique, `chown`, `grep`, `sort`, `uniq`, `find`, visualisation `ls -l`).
   - **Niveau 3 : Scripts Bash, Tubes & Redirections** (`|`, `>`, `>>`, `<`, enchaînements `&&`, `;`, variables, `$?`, scripts `.sh`).
   - **Niveau 4 : Administration Système, Processus & Diagnostic** (`ps`, `top`, `kill`, `uptime`, `whoami`, `uname`, `env`, `export`, gestion des démons).
2. `challenges.json` (ou intégré dans `curriculum.json`) :
   - Chaque défi practical comporte :
     - `id` : identifiant unique (ex: `"LINUX-101"`).
     - `level` : 1, 2, 3 ou 4.
     - `title` : Titre explicite (ex: *"Sécurisation des permissions d'un script"*).
     - `description` : Contexte opérationnel et consignes.
     - `initial_fs` : Arborescence et fichiers pré-générés dans le VFS client.
     - `starter_cmd` : Commande de départ optionnelle.
     - `public_tests` : **Au moins 2 cas de test publics** visibles de l'étudiant.
     - `hidden_tests` : **Au moins 5 cas de test cachés** évaluant le résultat sans fuite de solution.
     - `points` : Barème (ex: 2.0 à 5.0).
     - `hints` : Indices progressifs.

### 3.3 Service Linux (`backend/app/services/linux_training_service.py`)
Fonctions clés à implémenter :
- `load_linux_curriculum() -> dict` : Charge et met en cache `curriculum.json`.
- `get_safe_challenges_list(level: Optional[int] = None) -> list` : Retourne la liste des défis sans divulguer `hidden_tests` ni `solution`.
- `get_challenge_detail_student(challenge_id: str) -> dict` : Détail complet d'un défi pour l'espace de travail avec `initial_fs` et tests publics uniquement.
- `evaluate_linux_challenge(challenge_id: str, student_command: str, vfs_dump: dict) -> dict` : Évalue la conformité des fichiers et sorties d'exécution par rapport aux critères de validation.
- `sync_student_linux_pillar(user_id: str, score: float, db: Session) -> PracticeAttempt` : Met à jour ou insère la tentative dans `practice_attempts` pour le pilier `LINUX_ADMIN`.

### 3.4 Spécification des Endpoints de l'API (`/api/training/linux`)
Nouveau routeur : `backend/app/routers/training_linux.py` enregistré dans `main.py` avec le préfixe `/api/training/linux` :

| Méthode | Endpoint | Rôle | RBAC |
|---|---|---|---|
| `GET` | `/api/training/linux/curriculum` | Retourne la structure du cursus (niveaux, objectifs, comptages de défis et QCM). | Étudiant / Tous |
| `GET` | `/api/training/linux/challenges` | Liste les défis pratiques par niveau avec le statut étudiant (non résolu, en cours, résolu). | Étudiant |
| `GET` | `/api/training/linux/challenges/{challenge_id}` | Récupère la consigne d'un défi, l'état initial VFS et les cas publics (tests cachés strictement masqués). | Étudiant |
| `GET` | `/api/training/linux/theory/quizzes` | Retourne les questions théoriques du volet concepts système (FHS, signaux, permissions). | Étudiant |
| `POST` | `/api/training/linux/generate-session` | Génère une série d'exercices personnalisée selon le niveau ou sujet ciblé. | Étudiant |
| `POST` | `/api/training/linux/submit-challenge` | Soumet la solution d'un défi pratique (commande + état VFS). Valide les tests publics et cachés. Met à jour la progression et synchronise le pilier `LINUX_ADMIN`. | Étudiant |
| `POST` | `/api/training/linux/submit-session` | Soumet une session complète (théorie + pratique), calcule la note sur 20 et met à jour `PracticeAttempt`. | Étudiant |
| `GET` | `/api/training/linux/progress` | Retourne la progression globale de l'étudiant (défis réussis, niveau courant, XP). | Étudiant |
| `GET` | `/api/training/linux/history` | Historique détaillé des soumissions avec dates et scores. | Étudiant |

### 3.5 Protocole de Confidentialité Étudiante & Tests Cachés
Pour empêcher toute tentative de tricherie via les outils de développement du navigateur (`F12` / Network / Console) :
- Le backend filtre systématiquement le champ `hidden_tests` avant sérialisation vers le client lors des requêtes `GET`.
- Lors de la soumission (`POST /submit-challenge`), le résultat retourné affiche le statut des tests cachés sous forme agrégée (ex: `passed_count: 5, total_count: 5, is_public: false, expected_output: "[Protégé]"`), sans jamais exposer la chaîne exacte de contrôle ou le fichier témoin secret.

---

## 4. Cadre de Tests Automatisés & Spécification de `tests/test_linux_training.py`

### 4.1 État des Lieux de la Suite de Tests (`tests/`)
La plateforme dispose d'un framework de test unifié piloté par `pytest`.
- **Exécution réelle constatée** : **103 tests passés avec succès à 100%** (durée : ~2m30s en raison des tests de charge concurrente et sandbox).
- **Configuration** : `pytest.ini` configure `testpaths = tests`, `python_files = test_*.py`, niveau de verbosité `-v`, et ignore les alertes de dépréciation.
- **Isolation des tests** (`tests/conftest.py`) :
  - Chaque test s'exécute dans une base SQLite en mémoire volatile (`sqlite:///:memory:`) avec `StaticPool`.
  - La fixture `db_session` amorce à neuf les rôles clés (`admin-01`, `prof-01`, `ETU-001`), les groupes de TP, les 3 spécialités (`DEV-IA`, `SYS-ADMIN`, `CYBER-SEC`) et 12 étudiants spécialisés.
  - La fixture `client` substitue la dépendance `get_db` de FastAPI via `app.dependency_overrides[get_db]`.
  - Des fixtures d'en-tête prêtes à l'emploi sont fournies : `admin_headers`, `teacher_headers`, `student_headers`.

### 4.2 Spécification Détaillée du Nouveau Fichier `tests/test_linux_training.py`
Le fichier de test à créer (`tests/test_linux_training.py`) doit comporter **au minimum 10 tests unitaires et d'intégration** :

```python
# Architecture recommandée pour tests/test_linux_training.py :

def test_linux_curriculum_structure_and_levels():
    """Vérifie la présence des 4 niveaux de formation et la validité du schéma curriculum.json."""
    # - Cursus charge 4 niveaux (Navigation, Permissions, Scripts/Pipes, Sysadmin).
    # - Tous les défis possèdent id, title, description, initial_fs, points >= 1.

def test_linux_challenges_public_and_hidden_tests_counts():
    """Vérifie que chaque défi practical respecte la règle R3 : >= 2 tests publics et >= 5 tests cachés."""
    # - Pour chaque défi : len(public_tests) >= 2 et len(hidden_tests) >= 5.

def test_linux_curriculum_endpoint_student_view_secrecy(client, student_headers):
    """Vérifie que l'endpoint GET /api/training/linux/challenges masque les tests cachés et solutions."""
    # - Réponse 200 OK.
    # - 'hidden_tests' et 'solution' absents des données retournées.

def test_linux_challenge_detail_endpoint(client, student_headers):
    """Vérifie la consultation d'un défi individuel avec son initial_fs."""
    # - GET /api/training/linux/challenges/{id} retourne initial_fs et public_tests.

def test_linux_generate_session_with_level_filters(client, student_headers):
    """Vérifie la génération d'une session personnalisée par niveau ou modalité (théorique vs pratique)."""
    # - POST /api/training/linux/generate-session avec filter level=2.
    # - Les exercices retournés correspondent au niveau demandé.

def test_linux_submit_challenge_success_evaluation(client, student_headers):
    """Vérifie la validation d'un défi réussi et le calcul des points."""
    # - POST /api/training/linux/submit-challenge avec solution valide.
    # - all_passed == True, note attribuée conforme au barème.

def test_linux_submit_challenge_hidden_tests_masking(client, student_headers):
    """Vérifie que le rapport de soumission masque le contenu sensible des tests cachés."""
    # - Dans les résultats détaillés : expected_output == "[Protégé]" pour les tests cachés.

def test_linux_progress_and_history_persistence(client, student_headers):
    """Vérifie l'enregistrement persistant de la progression et de l'historique."""
    # - GET /api/training/linux/progress reflète le défi résolu.
    # - GET /api/training/linux/history contient la tentative avec timestamp.

def test_linux_training_links_to_diagnostic_placement_pillar(client, student_headers, db_session):
    """Vérifie la synchronisation automatique avec le pilier LINUX_ADMIN dans practice_attempts."""
    # - Après soumission, une ligne PracticeAttempt(module_code='LINUX_ADMIN') est présente.
    # - GET /api/practice/history et GET /api/practice/modules affichent les statistiques mises à jour.

def test_linux_training_strict_decoupling_from_semester_gpa(client, student_headers, db_session):
    """Vérifie rigoureusement que les exercices Linux n'impactent pas les moyennes officielles d'examens."""
    # - Consultation de GET /api/student/bulletin avant et après soumission Linux.
    # - general_average et verdict (ADMIS/AJOURNÉ) demeurent strictement inchangés.

def test_linux_training_rbac_unauthenticated_forbidden(client):
    """Vérifie que les endpoints protégés rejettent les accès anonymes avec un code 401."""
    # - Requête sans Authorization header -> 401 Unauthorized.
```

---

## 5. Synthèse & Feuille de Route d'Intégration Backend

Pour l'équipe de mise en œuvre (implementers), la feuille de route backend se découpe en 4 étapes modulaires sans risque de régression :

1. **Jalon Données** :
   - Créer `backend/app/data/linux_training/curriculum.json` et `challenges.json` avec les 4 niveaux, les états VFS initiaux et la règle stricte : $\ge 2$ tests publics et $\ge 5$ tests cachés par défi.
2. **Jalon Service** :
   - Créer `backend/app/services/linux_training_service.py` pour le parsing du cursus, la projection sécurisée (masquage des secrets) et la fonction de synchronisation `sync_student_linux_pillar`.
3. **Jalon Router & API** :
   - Créer `backend/app/routers/training_linux.py` exposant les 9 endpoints décrits au point 3.4.
   - Enregistrer `training_linux` dans `backend/app/main.py`.
4. **Jalon Tests Automatisés** :
   - Créer `tests/test_linux_training.py` couvrant les 11 cas d'usage.
   - Exécuter `pytest tests/` pour s'assurer que les 103 tests existants + les nouveaux tests Linux passent tous avec un taux de succès de **100%**.

---
*Rapport rédigé par survey_explorer_3. Disponible dans `.agents/teamwork/survey_explorer_3/report.md`.*
