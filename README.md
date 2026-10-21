# 🎓 Plateforme d'Examen et d'Entraînement Multi-Modules (LAN Distribué & 100% Hors-Ligne)

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![SQLite WAL / PostgreSQL](https://img.shields.io/badge/Database-SQLite%20WAL%20%7C%20Postgres-336791.svg)](https://www.sqlite.org/)
[![Vanilla JS](https://img.shields.io/badge/Frontend-Vanilla%20ES%20Modules-F7DF1E.svg)](https://developer.mozilla.org/)
[![Pyodide WebAssembly](https://img.shields.io/badge/Python%20Engine-Pyodide%20v0.26-E44D26.svg)](https://pyodide.org/)
[![Tests Status](https://img.shields.io/badge/Tests-85%2F85%20Passing%20(100%25)-brightgreen.svg)](https://docs.pytest.org/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)]()

> Plateforme web institutionnelle complète d'évaluation continue, d'examen officiel surveillé et d'entraînement en programmation informatique, conçue pour opérer **strictement en réseau local autonome (LAN)** sans aucune dépendance à Internet ni recours à des CDN externes.

---

## 📑 Sommaire
1. [Vue d'Ensemble & Architecture Réseau](#-vue-densemble--architecture-réseau)
2. [Fonctionnalités Clés](#-fonctionnalités-clés)
3. [Guide d'Installation Pas à Pas](#-guide-dinstallation-pas-à-pas)
   - [Prérequis Système](#1-prérequis-système)
   - [Méthode 1 : Démarrage Clé en Main (Recommandé)](#2-méthode-1--démarrage-clé-en-main-turnkey)
   - [Méthode 2 : Installation Manuelle Détaillée](#3-méthode-2--installation-manuelle-détaillée)
   - [Méthode 3 : Déploiement avec Docker Compose](#4-méthode-3--déploiement-avec-docker-compose)
4. [Identifiants de Test & Rôles par Défaut](#-identifiants-de-test--rôles-par-défaut)
5. [Dispositifs de Sécurité & Anti-Triche](#-dispositifs-de-sécurité--anti-triche)
6. [Moteur Psychométrique & Item Analysis](#-moteur-psychométrique--item-analysis)
7. [Synchronisation Hors-Ligne par Clé USB (Option B)](#-synchronisation-hors-ligne-par-clé-usb-option-b)
8. [Gestion des Bulletins & Exports Multiformats](#-gestion-des-bulletins--exports-multiformats)
9. [Suivi des Tests Automatisés](#-suivi-des-tests-automatisés)
10. [Structure du Projet](#-structure-du-projet)

---

## 🏛 Vue d'Ensemble & Architecture Réseau

L'application repose sur le modèle architectural **Option B (Serveurs de Salles Distribués avec Hub Central Master)** :

```
┌────────────────────────────────────────────────────────────────────────┐
│                        INSTANCE CENTRALE (MASTER)                      │
│  - Super Administration & Gestion Globale (Étudiants, Groupes, Cours)  │
│  - Édition Web des Épreuves & Banques de Questions JSON               │
│  - Export des Packages d'Examens (.exam.zip avec empreinte SHA-256)    │
│  - Ingestion Idempotente des Résultats & Consolidation Académique      │
└───────────────────▲───────────────────────────────▲────────────────────┘
                    │                               │
        Synchronisation USB / LAN       Synchronisation USB / LAN
    (Packages .exam.zip & .results.zip) (Packages .exam.zip & .results.zip)
                    │                               │
                    ▼                               ▼
┌──────────────────────────────────────┐  ┌──────────────────────────────────────┐
│       SERVEUR SALLE A (LAN)          │  │       SERVEUR SALLE B (LAN)          │
│  - Serveur FastAPI Autonome          │  │  - Serveur FastAPI Autonome          │
│  - Base SQLite locale (Mode WAL)     │  │  - Base SQLite locale (Mode WAL)     │
│  - Télémétrie WebSocket temps réel   │  │  - Télémétrie WebSocket temps réel   │
│  - Surveillance Enseignant en direct │  │  - Surveillance Enseignant en direct │
└──────────────────▲───────────────────┘  └──────────────────▲───────────────────┘
                   │                                         │
        Switch LAN / Wi-Fi de Salle               Switch LAN / Wi-Fi de Salle
                   │                                         │
    ┌──────────────┴──────────────┐           ┌──────────────┴──────────────┐
    ▼                             ▼           ▼                             ▼
[Poste Candidat 1]      [Poste Candidat 30] [Poste Candidat 1]      [Poste Candidat 30]
 (Navigateur Web)        (Navigateur Web)    (Navigateur Web)        (Navigateur Web)
```

* **100% Hors-Ligne :** Aucune requête externe. Toutes les bibliothèques frontend (Web Components, CodeMirror, Pyodide WebAssembly, feuilles de style, polices) sont embarquées en local dans `frontend/vendor/`.
* **Autorité Serveur Stricte :** Le serveur détient la seule vérité chronométrique, applique la validation des réponses et gère les suspensions. Les corrigés restent confidentiels et ne transitent jamais sur le réseau étudiant pendant une épreuve officielle.

---

## 🚀 Fonctionnalités Clés

### 1. Contrôle d'Accès & Espaces Dédiés (RBAC)
* **Super Administrateur (`admin`) :** Gestion CRUD complète des Étudiants, Enseignants, Spécialités (`DEV-IA`, `SYS-ADMIN`, `CYBER-SEC`) et Unités d'Enseignement. Tableau de bord multi-salles, import/export CSV et consolidation globale.
* **Enseignant Surveillant (`teacher`) :** Création d'examens sur-mesure ou chargement depuis templates officiels, éditeur web de questions, console de surveillance télémétrique en direct, déblocage des postes et analyses psychométriques.
* **Étudiant / Candidat (`student`) :** Espace personnel avec indicateurs académiques, salle d'attente synchronisée, interface d'épreuve sécurisée, tests d'entraînement 24/7 et Centre d'Entraînement Python.

### 2. Moteur d'Évaluation Universel à 6 Types d'Épreuves
1. **Vrai / Faux (`boolean`) :** Choix binaire avec tolérance de typage serveur.
2. **QCM Choix Unique (`single_choice`) :** 1 réponse correcte parmi $N$ options.
3. **QCM Choix Multiples (`multi_choice`) :** Crédit partiel au prorata des bonnes réponses et pénalité configurable pour les fausses sélections (avec plancher automatique à zéro).
4. **Texte à Trou (`fill_blank`) :** Normalisation insensible à la casse et aux espaces superflus.
5. **Appariement / Correspondance (`matching`) :** Association 1-à-1 dynamique en deux colonnes avec exclusion mutuelle des choix déjà retenus.
6. **Programmation Python Pratique (`coding`) :** Défis d'algorithmique et de code inspirés d'AlgoCompiler / HackerRank, avec double panneau ajustable, CodeMirror Dracula, console I/O, onglet de validation des tests publics, et évaluation serveur stricte avec tests cachés masqués (`[Protégé]`).

### 3. Centre d'Entraînement & Défis d'Algorithmique (230 Problèmes)
* **Double Moteur Python :** Pyodide WebAssembly isolé pour l'entraînement instantané hors-ligne et Sandbox Python Subprocess sécurisé côté serveur avec watchdog de 5 secondes.
* **Formules Mathématiques Hors-Ligne :** Rendu KaTeX local (`frontend/vendor/katex/`) sans recours à Internet ($O(N)$, complexité, sommes et équations).
* **Règle Stricte des Tests :** 100% des 230 problèmes comportent obligatoirement $\ge 2$ tests publics et $\ge 1$ test caché.
* **Isolation Pédagogique des 4 Tests de Niveau :** Les 4 épreuves de niveau sont diagnostiques et disponibles 24h/24 en self-service ; elles n'impactent pas les moyennes officielles des modules de cours.
* **Éditeur CodeMirror Professionnel :** Coloration syntaxique Python, indentation automatique, numéros de ligne et diagnostic d'exceptions précis (`traceback` complet avec numéro de ligne).
* 10 chapitres d'entraînement progressif, défis AlgoCompiler avancés et mode adaptatif personnalisé.

---

## 📦 Guide d'Installation Pas à Pas

### 1. Prérequis Système

* **Système d'Exploitation :** Windows 10/11, Linux (Ubuntu, Debian, CentOS) ou macOS.
* **Python :** Version **3.11 ou supérieure** ([Télécharger Python](https://www.python.org/downloads/)).
  > ⚠️ Lors de l'installation sous Windows, veillez à cocher la case **« Add python.exe to PATH »**.
* **Git :** Recommandé pour cloner et mettre à jour le projet.

---

### 2. Méthode 1 : Démarrage Clé en Main (Turnkey)

Cette méthode est la plus simple et la plus rapide pour déployer un serveur de salle.

#### Sous Windows :
1. Téléchargez ou clonez le dépôt :
   ```bash
   git clone https://github.com/hosniadilemp-a11y/examinationApp.git
   cd examinationApp
   ```
2. Double-cliquez directement sur :
   ```cmd
   lancer_serveur_salle.bat
   ```
3. Le script détecte votre adresse IP locale, démarre le serveur FastAPI (Uvicorn) sur le port `8000` et ouvre automatiquement le navigateur sur `http://localhost:8000`.

#### Sous Linux / macOS :
1. Accordez les droits d'exécution au script :
   ```bash
   chmod +x lancer_serveur_salle.sh
   ```
2. Exécutez le script :
   ```bash
   ./lancer_serveur_salle.sh
   ```

---

### 3. Méthode 2 : Installation Manuelle Détaillée

Pour un contrôle total de l'environnement virtuel et des paramètres.

#### Étape 1 : Cloner le Répertoire
```bash
git clone https://github.com/hosniadilemp-a11y/examinationApp.git
cd examinationApp
```

#### Étape 2 : Créer et Activer un Environnement Virtuel Python
* **Sous Windows (PowerShell / CMD) :**
  ```powershell
  python -m venv .venv
  .venv\Scripts\activate
  ```
* **Sous Linux / macOS :**
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```

#### Étape 3 : Installer les Dépendances
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> **Contenu des dépendances principales :**
> `fastapi`, `uvicorn`, `sqlalchemy`, `pydantic`, `argon2-cffi`, `PyJWT`, `reportlab` (génération PDF), `python-docx` (génération Word), `pytest`, `httpx`, `websockets`.

#### Étape 4 : Configurer le Fichier d'Environnement
Copiez le fichier `.env.example` en `.env` :
* **Sous Windows :**
  ```cmd
  copy .env.example .env
  ```
* **Sous Linux / macOS :**
  ```bash
  cp .env.example .env
  ```
*(Par défaut, si PostgreSQL n'est pas actif, le serveur bascule automatiquement sur la base locale embarquée `exam_app.db` en mode SQLite WAL).*

#### Étape 5 : Lancer le Serveur Web FastAPI
```bash
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Étape 6 : Accéder à la Plateforme
* **Sur le poste serveur (Enseignant / Admin) :** `http://localhost:8000`
* **Depuis les postes candidats sur le même réseau LAN :** `http://<IP_DU_SERVEUR>:8000`
* **Documentation interactive API Swagger :** `http://localhost:8000/docs`

---

### 4. Méthode 3 : Déploiement Conteneurisé Clé en Main (Dossier `deployment/`)

Pour une exploitation simplifiée en production ou en salle d'examen, un ensemble complet de scripts de cycle de vie est fourni dans le dossier `deployment/` :

| Script Windows | Script Linux / macOS | Description & Action |
| :--- | :--- | :--- |
| `deployment\start_app.bat` | `deployment/start_app.sh` | Démarre la pile Docker et vérifie l'état de santé du serveur (`healthcheck`). |
| `deployment\stop_app.bat` | `deployment/stop_app.sh` | Arrête proprement les conteneurs tout en **préservant les données**. |
| `deployment\update_app.bat` | `deployment/update_app.sh` | Reconstruit l'image avec les nouvelles mises à jour et applique les auto-migrations sans perte de données. |
| `deployment\export_offline_image.bat` | — | Exporte l'image Docker sous archive `examination-quiz-server.tar` pour déploiement USB en milieu isolé (Air-gap). |
| `deployment\load_offline_image.bat` | — | Charge l'image Docker depuis l'archive locale `.tar`. |

Pour consulter le guide complet de persistance et de configuration autonome (SQLite WAL ou PostgreSQL) :
👉 Voir [deployment/DEPLOYMENT_AND_PERSISTENCE_GUIDE.md](file:///c:/Users/adel/Documents/ExaminationQuiz%20APP/deployment/DEPLOYMENT_AND_PERSISTENCE_GUIDE.md).

---

## 🔑 Identifiants de Test & Rôles par Défaut

Les comptes suivants sont automatiquement injectés en base de données lors du premier lancement (`AUTO_SEED_DEFAULT_USERS=true`) :

| Rôle | Identifiant (`username`) | Mot de passe | Description & Affectation |
| :--- | :--- | :--- | :--- |
| **Super Administrateur** | `admin` | `admin123` | Console de direction, gestion des comptes, multi-salles |
| **Enseignant Référent** | `prof_martin` | `prof123` | Responsable pédagogique (`ALGO`, `PYTHON_INIT`, `CRYPTO`, `LINUX_ADMIN`) |
| **Étudiant (Dev IA)** | `etu_dev1` à `etu_dev4` | `StudentDev1!` à `StudentDev4!` | Filière `DEV-IA` (4 étudiants pré-amorcés avec notes) |
| **Étudiant (SysAdmin)** | `etu_sys1` à `etu_sys4` | `StudentSys1!` à `StudentSys4!` | Filière `SYS-ADMIN` (4 étudiants pré-amorcés avec notes) |
| **Étudiant (CyberSec)** | `etu_sec1` à `etu_sec4` | `StudentSec1!` à `StudentSec4!` | Filière `CYBER-SEC` (4 étudiants pré-amorcés avec notes) |
| **Étudiant (Générique)** | `etudiant1` | `etudiant123` | Candidat standard pour tests rapides |

---

## 🛡 Dispositifs de Sécurité & Anti-Triche

1. **Mode Plein Écran Forcé & Floutage d'Obstruction :**
   - L'épreuve et la salle d'attente s'exécutent en mode plein écran HTML5 strict.
   - Dès la perte du plein écran ou de la fenêtre, l'écran devient immédiatement opaque via un filtre flou haute densité (`filter: blur(16px)`) et une boîte modale bloquante `#overlay-fullscreen-required` empêche toute lecture.
2. **Verrouillage du Presse-Papier & Clic Droit :**
   - Blocage natif des raccourcis de copie/collage (`Ctrl+C`, `Ctrl+X`, `Ctrl+V`), interdiction de la sélection de texte hors zones autorisées et neutralisation du menu contextuel.
3. **Règle des 10 Secondes d'Absence :**
   - Toute sortie de l'application (changement d'onglet, réduction de fenêtre) supérieure à 10 secondes consécutives provoque le **verrouillage automatique et la suspension de l'épreuve**.
4. **Règle des 4 Avertissements :**
   - Au bout de 4 incidents anti-triche détectés, le poste est suspendu avec notification immédiate au surveillant.
5. **Console de Surveillance & Déblocage 1-Clic :**
   - Le professeur surveille en direct l'avancement de chaque candidat (statut réseau, progression en %, temps restant, alertes).
   - Un bouton `🔓 Débloquer` permet de réactiver un poste suspendu tout en remettant le compteur d'avertissements à zéro.
   - Commande `🛑 Clôturer l'Épreuve` forçant la soumission et la notation synchrone de toutes les copies.

---

## 📊 Moteur Psychométrique & Item Analysis

Accessible via la modale `#modal-item-analysis` depuis les dashboards Enseignant, Proctor et Admin :
* **Statistiques Globales :** Moyenne générale, médiane, écart-type $\sigma$, note min/max et taux de réussite ($\ge 10.0/20$).
* **Indice de Discrimination de Kelley ($D$) :**
  $$D = P_U - P_L$$
  - $P_U$ : Taux de réussite du tiers supérieur de la promotion ($27\%$ des meilleurs scores).
  - $P_L$ : Taux de réussite du tiers inférieur de la promotion ($27\%$ des scores les plus faibles).
* **Qualification Automatique de la Question :**
  - $D \ge 0.40$ : *Excellente discrimination*
  - $0.30 \le D < 0.40$ : *Bonne discrimination*
  - $0.20 \le D < 0.30$ : *Discrimination acceptable*
  - $0.00 \le D < 0.20$ : *Faible discrimination*
  - $D < 0.00$ : *Anomalie critique inversée* (les étudiants faibles ont mieux réussi que les étudiants forts).
* **Détection d'Anomalies :** Signalement visuel instantané des questions aberrantes ($D < 0$ ou $P = 0\%$) et export des résultats d'analyse au format CSV UTF-8 BOM.

---

## 💾 Synchronisation Hors-Ligne par Clé USB (Option B)

1. **Export de l'Épreuve depuis le Master :**
   - Bouton `📦 Package (.exam.zip)` téléchargeant l'archive contenant `exam_manifest.json` et son empreinte cryptographique `checksum.sha256`.
2. **Import sur le Serveur de Salle TP :**
   - Bouton `📦 Importer Package (.exam.zip)` vérifiant l'intégrité SHA-256 et déployant l'examen instantanément.
3. **Export des Résultats Post-Épreuve :**
   - Bouton `📦 Exporter Résultats (.results.zip)` consolidant `session_metadata.json`, `student_submissions.csv`, `question_answers.csv` et `audit_logs.json`.
4. **Réconciliation Master :**
   - Ingestion idempotente sur le serveur central Master sans risque de duplication des notes ni altération d'identifiants.

---

## 📜 Gestion des Bulletins & Exports Multiformats

Accessible dans la section **Gestion des Bulletins** pour les administrateurs et enseignants :
* **Moteur d'Évaluation Unifié :** Synthèse automatique des 4 piliers diagnostiques (`ALGO`, `PYTHON_INIT`, `CRYPTO`, `LINUX_ADMIN`) et des examens officiels (Théorique et Machine).
* **Moyenne Générale & Admission :** Calcul pondéré /20 avec attribution automatique du statut `ADMIS` ($\ge 10.0$) ou `AJOURNÉ`.
* **Exportations Disponibles :**
  - **Impression A4 / PDF Direct :** Modale haute définition stylisée avec déclenchement de la boîte d'impression navigateur.
  - **Bulletin Officiel PDF :** Document institutionnel généré par `reportlab` avec filigrane, tableaux soignés et signatures officielles.
  - **Bulletin Word (.docx) :** Document modifiable natif généré via `python-docx`.
  - **Archive Groupée (.zip) :** Téléchargement en 1 clic de l'ensemble des bulletins de la promotion (PDF + Word + CSV récapitulatif).
  - **Palmarès Officiel par Spécialité :** Classement complet trié par note de n'importe quel module choisi, exportable en PDF Paysage ou Word Paysage.

---

## ✅ Suivi des Tests Automatisés

Le projet intègre une suite de tests unitaires et d'intégration validant chaque couche fonctionnelle.

### Lancer la suite de tests complète :
```bash
pytest
```

### Résultat de la suite de tests :
```text
collected 78 items

tests/test_phase1.py ............. (13 tests) [Socle Backend, Auth Argon2, CSV IO, Groupes]
tests/test_phase2.py .................. (18 tests) [Moteur de Notation, Pénalités, Questions]
tests/test_phase3.py ....... (7 tests) [Terminal Étudiant, Anti-Triche, Sauvegarde, Score]
tests/test_phase4.py ...... (6 tests) [Proctoring Temps Réel, WebSocket, Déblocage 1-Clic]
tests/test_phase5.py ... (3 tests) [Export/Import USB, SHA-256, Réconciliation Master]
tests/test_phase6.py ......... (9 tests) [Sandbox Pyodide WebAssembly, Mode Évolution]
tests/test_phase7.py ... (3 tests) [Conteneurisation Docker, Test de Charge 30 Postes]
tests/test_phase8_revisions.py ............... (15 tests) [Spécialités, Bulletins, Exports DOCX/PDF/ZIP]
tests/test_phase9_features.py .... (4 tests) [Item Analysis Psychométrie, Package USB, Éditeur Web]

============================== 78 passed in 158s (100%) ==============================
```

---

## 📁 Structure du Projet

```text
ExaminationQuiz APP/
├── backend/
│   ├── app/
│   │   ├── config.py                  # Paramètres et variables d'environnement
│   │   ├── database.py                # Moteur SQLAlchemy (PostgreSQL / SQLite WAL)
│   │   ├── dependencies.py            # Injection de dépendances et sécurité
│   │   ├── main.py                    # Point d'entrée FastAPI & initialisation de la base
│   │   ├── models.py                  # Modèles relationnels SQLAlchemy
│   │   ├── schemas.py                 # Schémas Pydantic de validation
│   │   ├── security.py                # Hachage Argon2id et JWT
│   │   ├── data/                      # Données de formation Python
│   │   ├── routers/                   # Contrôleurs API REST & WebSockets
│   │   │   ├── admin.py               # Console d'administration et bulletins
│   │   │   ├── auth.py                # Authentification et gestion de mot de passe
│   │   │   ├── csv_io.py              # Imports/exports CSV
│   │   │   ├── exams.py               # Gestion et templates d'examens
│   │   │   ├── practice.py            # Tests de niveau libres 24/7
│   │   │   ├── proctor.py             # Surveillance en direct et télémétrie
│   │   │   ├── student_exam.py        # Déroulement d'épreuve et anti-triche
│   │   │   ├── sync_io.py             # Synchronisation USB (.exam.zip, .results.zip)
│   │   │   └── training_python.py     # Centre d'entraînement Python
│   │   ├── seeds/                     # Banques de 120 questions & templates JSON
│   │   └── services/                  # Logique métier avancée
│   │       ├── document_export.py     # Générateur PDF (ReportLab) et Word (python-docx)
│   │       ├── grading.py             # Moteur de calcul des notes et pénalités
│   │       ├── item_analysis.py       # Analyse psychométrique & discrimination D
│   │       ├── training_service.py    # Algorithmes d'adaptation du niveau
│   │       └── websocket_manager.py   # Gestionnaire de télémétrie WebSocket
├── frontend/
│   ├── css/
│   │   ├── main.css                   # Styles généraux, dark mode, typographie
│   │   └── proctor.css                # Styles du dashboard de surveillance
│   ├── js/
│   │   ├── api.js                     # Client API REST et WebSocket
│   │   ├── anti-cheat.js              # Gestionnaire plein écran, floutage et 10s rule
│   │   ├── app.js                     # Contrôleur principal de l'application
│   │   ├── exam-runner.js             # Moteur de rendu et d'interaction des épreuves
│   │   ├── pyodide-runner.js          # Interface Web Worker Pyodide
│   │   └── pyodide-worker.js          # Web Worker WebAssembly local isolé
│   ├── vendor/                        # Dépendances embarquées 100% hors-ligne (CodeMirror, Pyodide)
│   └── index.html                     # Application Web monopage (SPA Vanilla)
├── docs/                              # Spécifications, architecture et feuilles de route
│   ├── spec.md                        # Cahier des charges officiel v2.0
│   ├── ARCHITECTURE_AND_SYSTEM_DESIGN.md # Architecture détaillée et révisions REV-01 à REV-50
│   └── IMPLEMENTATION_PHASES_ROADMAP.md  # Roadmap séquentielle par phases
├── scripts/                           # Outils de maintenance et tests de charge
├── tests/                             # Suite complète de tests unitaires et d'intégration
├── docker-compose.yml                 # Déploiement multi-conteneurs
├── Dockerfile                         # Image de production du serveur
├── lancer_serveur_salle.bat           # Lanceur automatique Windows en 1 clic
├── lancer_serveur_salle.sh            # Lanceur automatique Linux / macOS
├── logins.txt                         # Récapitulatif des identifiants par défaut
├── pytest.ini                         # Configuration des tests pytest
├── requirements.txt                   # Liste complète des bibliothèques Python
└── update.txt                         # Journal d'audit chronologique de toutes les révisions
```

---

## 👥 Auteur & Support

* **Dépôt Officiel GitHub :** [https://github.com/hosniadilemp-a11y/examinationApp.git](https://github.com/hosniadilemp-a11y/examinationApp.git)
* **Conception & Développement :** Équipe d'Ingénierie Pédagogique et Systèmes d'Évaluation.
* **Support & Maintenance :** Voir documentation technique dans [`docs/spec.md`](file:///c:/Users/adel/Documents/ExaminationQuiz%20APP/docs/spec.md).

