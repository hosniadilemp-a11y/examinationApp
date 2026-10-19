# Software Requirements Specification (SRS)
# Multi-Module Examination & Training Platform (LAN Distributed)

**Document Status:** Draft: decisions recorded, open items listed in Section 12  
**Target Environment:** Local Area Network (Offline-capable LAN / Subnet Rooms)  
**Architecture Pattern:** Distributed Room Servers (Option B) with Master Hub Aggregation  
**Primary Tech Stack:** Web-based (Python FastAPI/Flask backend + Vanilla JS / Web Components frontend), deployed with Docker Compose  
**UI Language:** French only  
**Capacity Target:** Up to 30 simultaneous students per room server

---

## 1. Executive Summary & Objective

The objective is to develop a robust, modern, web-based examination and training platform operating entirely within a Local Area Network (LAN). The system serves academic institutions across multiple courses and modules, supporting Super Administrators, Teachers, and Students. 

The application is structured for **distributed lab-room environments**, where each physical room runs an independent local instance. Exams are authored centrally or locally, distributed to room servers via LAN or USB sync, and the resulting student performance data is exported and aggregated back into the Master instance.

---

## 2. System Architecture & Distributed Room Topology (Option B)

```
┌────────────────────────────────────────────────────────────────────────┐
│                        MASTER INSTANCE (Central)                       │
│  - Super Admin & Global Management (Users, Groups, Courses, Modules)   │
│  - Exam Package Bundling & Export                                      │
│  - Master Results Aggregation (Single Exam or All Exams)               │
│  - Global CSV Import/Export & Institutional Reporting                  │
└───────────────────▲───────────────────────────────▲────────────────────┘
                    │                               │
        LAN Sync / USB Drive            LAN Sync / USB Drive
   (Exam Packages & Results Bundle) (Exam Packages & Results Bundle)
                    │                               │
                    ▼                               ▼
┌──────────────────────────────────────┐  ┌──────────────────────────────────────┐
│       ROOM SERVER A INSTANCE         │  │       ROOM SERVER B INSTANCE         │
│  - Local Web Server (FastAPI/Flask)  │  │  - Local Web Server (FastAPI/Flask)  │
│  - Local Database (SQLite / Postgres)│  │  - Local Database (SQLite / Postgres)│
│  - Live WebSocket Monitoring         │  │  - Live WebSocket Monitoring         │
│  - Local Student Roster & Auth       │  │  - Local Student Roster & Auth       │
└──────────────────▲───────────────────┘  └──────────────────▲───────────────────┘
                   │                                         │
        Local Room Subnet (Wi-Fi/LAN)             Local Room Subnet (Wi-Fi/LAN)
                   │                                         │
    ┌──────────────┴──────────────┐           ┌──────────────┴──────────────┐
    ▼                             ▼           ▼                             ▼
[Student Terminal 1]    [Student Terminal 2] [Student Terminal 1]   [Student Terminal 2]
(Web Browser Client)    (Web Browser Client) (Web Browser Client)   (Web Browser Client)
```

### 2.1. Room Server Independence
* Each examination room operates an isolated local server instance.
* Network disruptions or hardware resets in one room never affect other exam rooms.
* No continuous internet or external WAN connectivity is required during examination execution.

### 2.2. Synchronization & Data Interchange
* **Exam Distribution:** Completed exams (questions, assets, timer rules, scoring schemes) are packaged into gzip-compressed JSON archive bundles (`.exam` / `.json.gz`) from the Master instance and deployed to room instances via LAN upload or USB flash drive.
  * **Decision:** packages are **plain, with no encryption and no signature**. Anyone holding the file can read or modify the exam content. This is an accepted risk.
  * **Import timing:** because packages are readable, teachers import the `.exam` package on the room server **just before the exam session**, not days in advance. The server only sends question content to students after the session starts, and deletes or archives the package file after import. Packages must be kept off shared drives until then.
  * Each package carries a `schema_version` and a SHA-256 checksum used only to detect accidental corruption, not tampering.
* **Result Ingestion & Aggregation:** Upon exam completion, teachers/admins can export student submissions and scoring logs (either for a single exam or all exams in that room) as a portable bundle (`.results.zip` / `.csv`) and import them into the Master App instance for cross-room correlation and grade consolidation.

---

## 3. Technology Stack & Modern UI Standards

* **Backend:** Python (FastAPI or Flask) — lightweight, portable, fast local server execution, native JSON handling, and asynchronous WebSocket support for live monitoring.
* **Frontend:** Vanilla JavaScript (ES modules) with Web Components and modern CSS. No framework, no bundler, no build step. All assets (fonts, libraries, Pyodide) are vendored locally; nothing is loaded from the internet.
* **UI Language:** French only. No internationalization layer.
* **Deployment:** Docker Compose for both Master and Room Servers. Docker is a prerequisite on every machine that runs the platform. Images must be loadable offline.
* **Capacity:** Each room server supports up to 30 simultaneous students. SQLite runs in WAL mode with batched writes for autosave and telemetry.
* **Real-time Telemetry:** WebSockets / Server-Sent Events (SSE) for low-latency live proctoring feeds from student terminals to the teacher dashboard.
* **Storage:** Embedded relational database (SQLite for zero-config room instances, with optional PostgreSQL for Master deployment).
* **UI/UX Direction:**
  * Clean, state-of-the-art dashboard aesthetic (sleek typography, purposeful color tokens, dark/light accessibility).
  * 100% preservation of all functional workflows from legacy applications, modernized for superior responsiveness and ease of use.

---

## 4. User Roles & Academic Organization

### 4.1. Student Organizational Structure: Groups
* **Student Classification:** Students are organized strictly by **Groups** (e.g., *Group 1*, *Group 2*, *TD-A*, *TP-B*) rather than broad specialties.
* **Targeted Scheduling:** Teachers and Admins assign exams and access permissions directly to one or multiple Groups.

### 4.2. Authentication
* All users (students, teachers, administrators) sign in with **user ID + password**.
* Passwords are stored only as salted hashes (argon2, or bcrypt as fallback). Login attempts are rate-limited.
* Permissions in 4.3 are enforced on the server for every request, not only in the UI.
* **Initial password = the student ID.** The first login forces the user to choose a new password before continuing. Teachers (for their students) and administrators can reset a password back to the student ID, which again forces a change.
* **Accepted risk:** until a student changes the initial password, anyone who knows that student's ID can log in as them. Student IDs should therefore be changed at first login before any official exam, ideally during a supervised session.

### 4.3. Permission Matrix

| Feature / Capability | Super Administrator | Teacher | Student |
| :--- | :---: | :---: | :---: |
| Global User & Group Management (CRUD) | ✅ Full | ❌ None | ❌ None |
| Course & Module Management | ✅ Full | ❌ Assigned only | ❌ View assigned |
| Question Authoring (JSON Import & Web Editor) | ✅ Full | ✅ Assigned modules | ❌ None |
| Exam Scheduling & Launching by Group | ✅ Full | ✅ Assigned modules | ❌ None |
| Live Proctoring & Monitoring Dashboard | ✅ Full | ✅ Own sessions | ❌ None |
| Anti-Cheating Telemetry & Suspension Control | ✅ Full | ✅ Unlock/Pause | ❌ Monitored |
| Student Gradebook & Statistical Item Analysis | ✅ Full | ✅ Own sessions | ❌ Own score only |
| Bulk CSV Import / Export (Users, Groups, Results)| ✅ Full | ✅ Results export | ❌ None |
| Room Synchronization Package Export/Import | ✅ Full | ✅ Room level | ❌ None |
| Python Evolution & Chapter Training Mode | ✅ Full | ✅ Full | ✅ Full access |
| Free Practice Tests (Self-paced, anytime) | ✅ Full | ✅ Full | ✅ Unrestricted |
| Official Examination Taking Interface | ❌ None | ❌ None | ✅ Assigned by Group |

---

## 5. Question Engine & Granular Grading Model

### 5.1. Supported Question Types
1. **Yes / No (True/False):** Binary choice verification.
2. **Single-Choice Multiple Choice (MCQ):** 1 of $N$ options is correct.
3. **Multi-Choice Multiple Choice (MCMCQ):** Several correct choices, or cases where no options apply.
4. **Fill-in-the-Blank:** Open-ended token input with whitespace normalization and optional case-insensitivity.
5. **Matching / Pairing (Patching):** Two-column interactive association engine.

### 5.2. Granular Scoring & Penalty Engine
* **Partial Credit & Negative Penalties:**
  * For multi-choice questions with multiple answers, the engine calculates positive fractional points for correct selections and applies customizable negative penalties for incorrect selections.
  * **Formula (multi-choice):** each correct selection earns `points / number_of_correct_options`. Each incorrect selection subtracts `negative_penalty` (an absolute number of points, e.g. 0.5). Unselected options score nothing. The question score is the sum, then floored.
  * **Example:** 4 points, 3 correct options, penalty 0.5. Two correct picks and one wrong pick give `2 x 4/3 - 0.5 = 2.17` (rounded to 2 decimals).
  * Score floor limit: Minimum score per question defaults to `0` (or configurable negative floor).
* **Customization Hierarchy:**
  * **Global Preset:** Teacher defines a default scoring policy for the entire exam (e.g., standard partial credit with $-0.5$ penalty for false picks).
  * **Per-Question Override:** Teacher can override scoring weights, penalty values, and time allowances on a granular question-by-question basis.

---

## 6. Anti-Cheating & Strict Exam Integrity Controls

### 6.1. Client-Side Lockout Controls
* **Full-Screen Enforcement:**
  * The student examination interface enforces strict HTML5 Fullscreen mode upon starting the exam.
  * Attempting to minimize, restore down, or exit fullscreen immediately triggers a visual security countdown and alert log.
* **Clipboard Lockout (Copy/Paste Block):**
  * Copy, cut, and paste shortcuts (`Ctrl+C`, `Ctrl+X`, `Ctrl+V`, `Cmd+C`, `Cmd+V`) are completely blocked.
  * Right-click context menus and text highlighting/selection outside designated text inputs are disabled.
* **Unauthorized Click Detection:**
  * Clicks outside active answer widgets or interface navigation zones are intercepted, prevented, and logged as suspicious behavior.

### 6.2. The 10-Second Away Rule: Automatic Student Suspension
* **Absence Detection:** If a student exits fullscreen, switches tabs, minimizes the window, or leaves the active exam view for **more than 10 consecutive seconds**:
  * The student’s exam terminal is **instantly locked and Suspended**.
  * An intrusive lockout screen appears: *"Exam Suspended: Unauthorized window exit detected (>10s). Contact your proctor."*
  * Answers entered up to the moment of suspension are safely preserved.
  * **Proctor Re-authorization:** Only the supervising teacher or administrator can lift the suspension from their live monitoring dashboard after verifying the incident.
* **Network Disconnects:** A lost connection is **not** treated as leaving the exam. The student card shows *Disconnected* or *Reconnecting*, the server-side exam timer keeps running, and the 10-second rule does not apply to offline time. On reconnect the client resyncs and the session continues. The 10-second rule applies to window/fullscreen/tab events recorded while the student is connected, or reported by the client once it reconnects.

### 6.3. Monitoring Interface (Reference: `oldapps/AlgoCompilerv2/AlgoCompilerv2/AlgoExamination`)
The teacher's live monitoring view adopts the comprehensive telemetry layout from `AlgoExamination`:
* **Real-time Student Grid:** Visual cards for each student displaying:
  * Network connectivity status (Online, Disconnected, Reconnecting).
  * Security State: 🟢 Normal, 🟡 Focus Warning, 🔴 **Suspended (>10s Absence / Exit)**.
  * Current question index and progress bar (e.g., Question 14/30).
  * Real-time submission state (Answered, Unanswered, Marked for Review).
  * Elapsed time vs. remaining exam time.
* **Proctor Action Bar:** Ability to:
  * **Unlock Suspended Student** (lifts the 10-second penalty lockout).
  * Grant extra time (per student or room-wide).
  * Pause/resume an individual student exam.
  * Force-submit an active exam.

---

## 7. Free Practice Tests & Question Banks (Self-Paced)

In addition to scheduled official examinations, the platform provides **4 Free Diagnostic & Practice Tests** available to **all students at all times** without requiring teacher scheduling:

| Practice Test Module | Question Bank Size | Focus & Topics | Availability |
| :--- | :---: | :--- | :---: |
| **1. Algorithmique Basics** | **30 Questions** | Variables, control structures, loops, recursion, basic complexity, sorting/searching fundamentals. | Anytime (24/7) |
| **2. Python Basics** | **30 Questions** | Syntax, lists, dicts, tuples, functions, string manipulation, file I/O, exceptions. | Anytime (24/7) |
| **3. Cryptographie Basics** | **30 Questions** | Symmetric/asymmetric ciphers, hashing, Caesar & Vigenère, RSA basics, public/private keys, signatures. | Anytime (24/7) |
| **4. Administration Linux Basics** | **30 Questions** | Filesystem hierarchy, permissions (`chmod`/`chown`), process management, basic shell commands (`grep`, `find`, `awk`), package management. | Anytime (24/7) |

* **Self-Assessment Feedback:** Students receive instant scoring, detailed explanations for correct/incorrect answers, and question-level breakdowns upon completing any free test.

---

## 8. Python Training & Chapter Evolution Subsystem

* **Reference Asset:** Replicates the training architecture from `oldapps/QuizApp`. The legacy code is available in the repository under `oldapps/` as read-only reference.
* **Code Execution:** Student Python code runs **in the browser using Pyodide** inside a Web Worker, with an execution timeout and the ability to interrupt infinite loops. Pyodide files are bundled locally so training works offline. Student code is never executed on the server.
* **Modes:**
  * **Chapter-by-Chapter Training:** Progressive exercises aligned with curriculum units.
  * **Evolution Mode:** Dynamic difficulty adjustment based on student performance in previous chapter attempts.
* **Curriculum Roadmap:**
  * Primary Launch Module: **Initiation à Python** (training + examination).
  * Secondary Launch Modules (Examination Only for initial release):
    * **Cryptographie**
    * **Administration des Systèmes Linux**

---

## 9. Legacy Codebase Mapping & Asset Reuse

| Legacy Source | Target Module in New System | Reused Logic & Assets |
| :--- | :--- | :--- |
| `oldapps/AlgoCompilerv2/AlgoCompilerv2/AlgoExamination` | `core/monitoring/` & `client/teacher_monitor/` | Live examination proctoring UI, WebSocket telemetry schema, suspension controls, and real-time student state tracking. |
| `oldapps/QuizApp/QuizApp/` | `core/training/` & `data/curriculum/python/` | Python curriculum datasets, chapter definitions, quiz formats (`.quiz`), and evolution scoring algorithms. |
| `oldapps/TP_DM/` | `client/student_exam/` & `core/exam_engine/` | Student examination workflow, question rendering patterns, countdown timers, and answer auto-save routines. |

---

## 10. Data Ingestion & Export Specifications

### 10.1. CSV Ingestion (Admin)
* `students.csv`: `student_id, full_name, email, group_id, group_name` *(replacing specialty)*
* `teachers.csv`: `teacher_id, full_name, email, assigned_modules`
* `groups.csv`: `group_id, group_name, description`
* `modules.csv`: `module_code, module_name, description`

### 10.2. JSON Exam Authoring Format
* Structured schema allowing questions with:
  * `type` (`boolean`, `single_choice`, `multi_choice`, `fill_blank`, `matching`)
  * `prompt` (supports Markdown and code snippets)
  * `options` and `correct_keys`
  * `scoring` (`points`, `negative_penalty`, `partial_credit_enabled`)
  * `time_limit_seconds` (optional per question)

### 10.3. Reporting & Result Aggregation
* Single-exam export and all-exams batch export per room server.
* Master Aggregator reconciles room reports into a unified spreadsheet (`master_grades.csv`) and generates PDF/CSV statistical summaries (mean, standard deviation, question discrimination index, flagged anomalies, suspension logs).

---

## 11. Non-Functional Requirements

* **Offline:** No runtime dependency on the internet, a CDN, or external fonts.
* **Server authority:** Exam timers, scores, suspension state, and answer correctness are decided and stored on the server. The browser is untrusted.
* **Answer secrecy:** Correct answers and explanations are never sent to a student client during an official exam.
* **Durability:** A browser crash or reboot loses at most a few seconds of entered answers (autosave).
* **Audit:** Every proctor action and security event is recorded in an append-only log.
* **Idempotent import:** Re-importing the same result bundle never duplicates results on the Master.
* **Practice vs. official:** Free practice test results are stored separately and never enter Master grade aggregation.

---

## 12. Open Items (to be decided before implementation)

1. **Scoring edge cases:** how partial credit applies to matching, what boolean and single-choice questions score on a wrong answer (penalty or just 0), and how multi-choice scores when a question has no correct option (the formula divides by zero).
2. **Question content:** who writes the 120 practice questions and the Python curriculum, and in what format.
3. **Teacher ownership:** meaning of "own sessions" when several teachers share a module.
4. **Backup and recovery:** policy for room databases and behavior if a room server fails mid-exam.
5. **Master hosting:** where it runs, who administers it, how result bundles are transported.
6. **Browser support:** supported browsers and versions on student terminals (fullscreen and Pyodide behavior).
7. **Testing:** end-to-end test tooling and CI environment.
8. **Media assets:** whether questions need images or other media, and size limits.
9. **Data retention:** retention of audit logs and student data.
10. **Docker prerequisite:** confirm Docker can be installed on every room server and on the master.

---

## 13. Spécifications de l'Interface Étudiant & Bilan Académique (Mise à Jour v2.0)

### 13.1. Tableau de Bord Étudiant Enrichi
* **Bannière Profil & Niveau Global :**
  * Affichage immédiat du nom complet et du groupe de l'étudiant.
  * Badge de niveau hiérarchique : **Niveau 1 à 8** (*Grand Débutant* à *Expert Python*) avec code couleur dynamique (bleu, vert émeraude, magenta expert).
  * Indicateur textuel de la moyenne sur les 4 modules fondamentaux.
  * Barre de progression visuelle indiquant la complétion vers le niveau supérieur.
* **Cartes d'Indicateurs Clés (KPI Cards) :**
  1. **Moyenne Piliers :** Note moyenne (/20) sur les 4 modules fondamentaux.
  2. **Moyenne Globale :** Moyenne générale (/20) incluant toutes les épreuves et entraînements.
  3. **Taux de Réussite :** Pourcentage d'évaluations obtenues avec une note ≥ 10.0 / 20.
  4. **Modules Validés :** Ratio de modules validés par rapport au total du cursus (ex: `4/4`).

### 13.2. Calcul du Niveau Académique sur les 4 Examens Fondamentaux
Le niveau global de l'étudiant est déterminé par la moyenne arithmétique de ses meilleures notes sur les 4 modules piliers :
* `ALGO` : Algorithmique & Structures de Données
* `PYTHON_INIT` : Python & Programmation Fondamentale
* `CRYPTO` : Cryptographie & Sécurité des Données
* `LINUX_ADMIN` : Administration Systèmes & Réseaux Linux

**Grille Officielle des Niveaux (Échelle à 6 Paliers - REV-11) :**
* **Niveau 6 — Excellent (`excellent`) :** Moyenne de 16.00 à 20.00 / 20 (Maîtrise complète du contenu)
* **Niveau 5 — Bon (`good`) :** 14.00 ≤ Moyenne < 16.00 / 20 (Acquis solides, lacunes mineures)
* **Niveau 4 — Moyen (`average`) :** 12.00 ≤ Moyenne < 14.00 / 20 (Acquis acceptables, des lacunes subsistent)
* **Niveau 3 — Limite (`borderline`) :** 10.00 ≤ Moyenne < 12.00 / 20 (Moyenne atteinte de justesse)
* **Niveau 2 — Sous la moyenne (`below_average`) :** 7.00 ≤ Moyenne < 10.00 / 20 (En dessous de la moyenne)
* **Niveau 1 — Insuffisant (`insufficient`) :** 0.00 ≤ Moyenne < 7.00 / 20 (Très loin du niveau requis)

### 13.3. Vue Complète des Performances & Statistiques (`#view-stats`)
* **Fiches Piliers Fondamentaux :**
  * Carte dédiée pour chaque module fondamental affichant la note maximale, la note moyenne, le nombre d'essais et un badge de maîtrise (*Non commencé*, *En découverte*, *En progression*, *Compétence acquise*, *Niveau Avancé*, *Maîtrise Experte*).
  * Bouton d'action directe pour lancer un entraînement immédiat sur le module.
* **Échelle Interactive des Niveaux :**
  * Grille visuelle des 8 paliers mettant en exergue le palier actuel atteint par l'étudiant (`★ Votre Niveau Actuel`).
* **Tableau Exhaustif des Modules :**
  * Liste détaillée de tous les modules du cursus avec statut de validation (Validé / Non validé), barème, notes et boutons d'entraînement.
* **Historique Chronologique des Évaluations :**
  * Journal de toutes les épreuves passées (examens officiels scellés et tests d'entraînement) avec date, intitulé, note obtenue et statut.

### 13.4. Centre d'Entraînement Python Évolutif & Hors-Ligne
* **10 Chapitres Fondamentaux Accessibles 24h/24 :**
  1. Variables, Types & Opérateurs
  2. Conditions & Logique Booléenne
  3. Boucles & Itérations
  4. Fonctions & Portée
  5. Listes & Tuples
  6. Dictionnaires & Ensembles
  7. Manipulation de Fichiers & I/O
  8. Gestion des Exceptions
  9. Algorithmes Classiques
  10. Notions Orientées Objet (POO)
* **Mode Évolutif Personnalisable :** Modal permettant de configurer le volume (5, 10 ou 15 exercices) et les niveaux de difficulté (Facile, Intermédiaire, Avancé).
* **Moteur d'Exécution Pyodide Local :** Exécution du code dans un Web Worker WebAssembly local sans accès internet avec Watchdog de sécurité (5 secondes) pour interrompre les boucles infinies.

### 13.5. Déroulement Unifié des Épreuves & Navigation Clavier
* **Format 1 Question par Page :**
  * Les tests d'entraînement libre adoptent exactement la même ergonomie que les examens officiels.
  * Palette latérale interactive indiquant l'état de chaque question (Active, Répondue, Marquée avec drapeau 🚩).
* **Navigation Clavier au Flèches :**
  * `ArrowLeft` : Navigation vers la question précédente.
  * `ArrowRight` : Navigation vers la question suivante.
  * Protection automatique : Les touches fléchées ne sont pas interceptées lorsque le curseur est actif dans un champ de saisie (`input`, `textarea`, `select`).
* **Résolution des Interactions Multi-Choix (`multi_choice`) :**
  * Gestion synchrone et réactive de la sélection multiple (cocher/décocher).
  * Harmonisation des identifiants numériques et chaînes de caractères.
  * Mise à jour en temps réel de la palette et sauvegarde automatique.

### 13.6. Dédoublement Strict des Interfaces par Rôle
* **Étudiant (`student`) :** Espace personnel orienté apprentissage et évaluation (Tableau de bord, statistiques détaillées, centre Python, entraînements libres, examens officiels). Aucune commande d'administration n'est exposée.
* **Enseignant (`teacher`) :** Espace de surveillance de salle en direct avec tableau télémétrique, état des étudiants connectés, temps restant et déblocage des postes suspendus.
* **Super Administrateur (`admin`) :** Console centrale de gestion de la base de données (PostgreSQL ou SQLite WAL), import/export CSV des promotions et journaux d'audit de sécurité.

---

## 14. Historique des Révisions et Mises à Niveau du Système (REV-01 à REV-40)

Les révisions suivantes ont été intégrées et validées selon les règles de gouvernance `.agent/rules.md` :

1. **REV-01 (Pyodide Worker ES Module) :** Résolution de l'exception `Classic web workers are not supported` par neutralisation de `globalThis.importScripts = undefined` avant l'import dynamique de Pyodide v0.26+ en mode module WebAssembly local.
2. **REV-02 (Typographie & Parseur Markdown) :** Rendu riche et aéré des énoncés de questions (`_formatMarkdown`) prenant en charge les blocs de code, l'inline code, les titres `###`/`##`/`#`, gras, italique et paragraphes sans balises brutes apparentes.
3. **REV-03 (Double Brassage Aléatoire) :** Randomisation indépendante de l'ordre des questions et des options de réponses dans les tests de niveau, avec mapping d'identifiants garanti et support de `question_ids` lors de la notation serveur.
4. **REV-04 (Éditeur de Code Python CodeMirror) :** Intégration de l'éditeur CodeMirror en mode Python avec numérotation de ligne, coloration syntaxique, indentation automatique à 4 espaces et auto-fermeture des parenthèses/crochets (100% hors-ligne).
5. **REV-05 (Normalisation Vrai/Faux Booléens) :** Prise en charge unifiée des questions booléennes (`boolean` / `yesno`) avec binding strict sur `true` / `false` natifs et évaluation tolérante côté serveur.
6. **REV-06 (Capture des Réponses Utilisateur) :** Élimination de la chaîne temporaire `"Réponse soumise"` en faveur de la sérialisation des véritables réponses fournies par l'étudiant pour un corrigé pédagogique exact.
7. **REV-07 (Support Universel des 6 Types de Questions en Cursus Python) :** Prise en charge native de `boolean`, `single_choice`, `multi_choice`, `fill_blank`, `matching` et `coding` dans toutes les sessions du Centre d'Entraînement Python.
8. **REV-08 (Isolation Étanche des Statistiques Cursus Python) :** Découplage strict des statistiques du Centre Python (`TrainingAttempt`, `ChapterProgress`, progression des 10 chapitres, 68 badges de compétences) par rapport aux évaluations officielles et transversales.
9. **REV-09 (Notation Fiabilisée des Questions d'Association) :** Normalisation rigoureuse des paires clé/valeur pour les questions de type `matching`, garantissant qu'une association 4/4 attribue 100% des points avec validation verte `is_correct = True`.
10. **REV-10 (Banque de Questions Python Certifiée & Tirage de 20 Questions) :** Enrichissement du fichier `seed_python_30.json` avec 30 questions de programmation uniques (suppression des répétitions) et tirage aléatoire de 20 questions par test.
11. **REV-11 (Échelle Officielle des 6 Paliers Académiques) :** Déploiement de l'échelle à 6 niveaux : *Excellent* (16-20), *Bon* (14-<16), *Moyen* (12-<14), *Limite* (10-<12), *Sous la moyenne* (7-<10), *Insuffisant* (0-<7).
12. **REV-12 (Arrêt Systématique de l'Anti-Triche Hors Épreuve) :** Désactivation immédiate des écouteurs de plein écran et de floutage (`AntiCheatManager.stop()`) dès la sortie d'un examen ou l'affichage de l'écran des résultats.
13. **REV-13 (Templates d'Examens JSON & Import Enseignant) :** 3 modèles d'examens complets pré-packagés (Python, Linux, Cryptographie) avec panachage équilibré des 6 types de questions sur 20 points, et endpoints `/api/exams/templates`, `/load`, `/import-template`.
14. **REV-14 (Données de Test : 3 Spécialités avec 4 Étudiants) :** Configuration et initialisation en base de données de 3 groupes (`DEV-IA`, `SYS-ADMIN`, `CYBER-SEC`) comptant chacun 4 étudiants (`dev1..4`, `sys1..4`, `sec1..4`) avec authentification Argon2id.
15. **REV-15 (Découplage Création / Lancement d'Examen) :** Création d'examen enregistrée au statut `🟢 Prêt` sans génération anticipée de session ni démarrage prématuré du chronomètre.
16. **REV-16 (Interface Interactive de Surveillance & Monitoring en Direct) :** Salle de proctoring `#view-proctor-live` (style AlgoExamination) avec grille temps réel des postes étudiants, télémétrie WebSocket `/ws/proctor/{session_id}`, lancement synchronisé, prolongation collective de temps (+5m), déblocage à distance des suspensions anti-triche et journal d'audit interactif.
17. **REV-17 (Mise en Page Aérée & Code Multi-Lignes dans les Corrigés) :** Présentation du code Python soumis et de la solution de référence dans des blocs `<pre><code class="python-code-block">` préservant l'indentation, au sein d'une vue de restitution élargie à 1000px.
18. **REV-18 (Grille Élégante de Badges pour les Questions d'Association) :** Remplacement des chaînes concaténées brutes par une grille de cartes/badges `.matching-badges-grid` avec bordures colorées vertes ✅ et rouges ❌ indiquant précisément les correspondances validées et attendues.
19. **REV-19 (Support de `input()` et `sys.stdin` dans le Sandbox Pyodide) :** Emulation sécurisée du flux d'entrée standard via `SafeStdin` / `_safe_input_mock` dans le Web Worker Pyodide évitant toute exception `EOFError`, complétée par un champ de saisie dynamique `stdin-input` pour les tests interactifs de scripts Python.
20. **REV-20 (Navigation et Retour Systématique au Centre Python) :** Préservation de l'origine de navigation (`activeOriginView = 'view-python'`) garantissant que la fin ou l'abandon d'un quiz ramène l'étudiant directement dans le Centre Python.
21. **REV-21 (En-têtes Épurés & Badges Typés de Métadonnées) :** Suppression des balises brutes markdown des énoncés et affichage au-dessus de chaque question d'une rangée de capsules élégantes (Thème, Pill de difficulté colorée, Type de question, Barème).
22. **REV-22 (Exclusion Mutuelle 1-to-1 & Désélection Libre en Association) :** Désactivation dynamique des options de droite déjà sélectionnées dans les autres menus déroulants d'une question d'association, avec possibilité de sélection neutre par défaut via `— Choisir une correspondance —`.
23. **REV-23 (Score Centre Python — Bouton Unique de Retour au Centre) :** Masquage systématique des boutons de retour dashboard et statistiques globales sur l'écran des scores du Centre Python, au profit d'un bouton unique `⬅️ Retourner au Centre d'Entraînement Python`.
24. **REV-24 (Pyodide Sandbox — Diagnostic d'Erreur & Traceback Complet) :** Refonte du bac à sable WebAssembly avec exécution via `compile(code, "<script.py>", "exec")` et `traceback.format_exc()` pour afficher explicitement les types d'erreurs Python réels et leurs numéros de lignes (ex. `TypeError: 'int' object is not iterable on line 3`).
25. **REV-25 (Examen Officiel & Synchronisation — Salle d'Attente Interactive Étudiant) :** Vue d'attente interactive `#view-waiting-room` bloquant l'accès aux questions et préservant le secret absolu des énoncés tant que le surveillant n'a pas validé le lancement pour la salle. Démarrage instantané et synchronisé dès l'impulsion de l'enseignant.
26. **REV-26 (Surveillance & Proctoring — Tableau Structuré des Candidats) :** Remplacement de la grille de cartes par un tableau interactif `table#proctor-candidates-table` dense et structuré (Poste, Statut temps réel, Progression, Chronomètre, Alertes anti-triche, Télémétrie en direct et Actions).
27. **REV-27 (Anti-Triche — Flou d'Obstruction Immédiat & Modal de Plein Écran) :** Application instantanée de la classe `.exam-fullscreen-lost-blurred` (`filter: blur(16px)`) et de l'overlay `#overlay-fullscreen-required` dès la perte du mode plein écran, empêchant toute lecture non autorisée.
28. **REV-28 (Minuteur & Synchronisation — Alignement Authoritaire Serveur) :** Calcul et synchronisation continue du temps restant côté serveur dans `save_student_answer` et `check_attempt_status`, éliminant les dérives d'horloge entre clients et serveur.
29. **REV-29 (Anti-Triche — Suspension aux 4 Avertissements et Remise à Zéro) :** Suspension automatique du poste d'examen officiel dès 4 avertissements anti-triche (sorties plein écran ou perte de focus), avec remise à 0 du compteur lors du déblocage par le surveillant.
30. **REV-30 (Surveillance & Proctoring — Clôture Collective de l'Épreuve) :** Bouton `🛑 Clôturer l'Épreuve` et endpoint `POST /api/proctor/sessions/{session_id}/close` permettant à l'enseignant de sceller et soumettre d'un seul clic toutes les copies actives de la salle.
31. **REV-31 (Enseignant — Modale Complète de Création d'Examen Sur-Mesure) :** Interface interactive `#modal-create-custom-exam` permettant de paramétrer module, durée, barème, salle d'attente, ciblage de groupes (`DEV-IA`, `SYS-ADMIN`, `CYBER-SEC`, `GRP-1`), options de brassage et anti-triche strict.
32. **REV-32 (Examen Officiel — Résolution du Bug 'renderScoreScreen is not a function') :** Implémentation complète de la méthode `renderScoreScreen` dans `app.js`, supprimant le plantage lors de la soumission officielle et affichant le score scellé et la note /20.
33. **REV-33 (Dashboard Étudiant — Affichage Immuable du Statut 'Soumis & Scellé') :** Remplacement des boutons d'action sur la carte de cours par un encart définitif `✅ Épreuve Soumise & Scellée (Note / 20)` interdisant toute réouverture d'examen une fois rendu.
34. **REV-34 (Salle d'Attente — Mode Plein Écran Forcé & Flou d'Obstruction) :** Passage automatique en plein écran dès l'accès à `#view-waiting-room`. En cas de sortie non autorisée, application immédiate de la classe `.exam-fullscreen-lost-blurred` (`filter: blur(16px)`) et de la modale bloquante `#overlay-fullscreen-required` avec bouton de réengagement immédiat.
35. **REV-35 (Salle d'Attente — Confirmation d'Abandon & Déconnexion Propre du Plein Écran) :** Dialogue de confirmation lors du clic sur `✕ Quitter la Salle d'Attente` prévenant l'étudiant du départ imminent de l'épreuve. En cas d'annulation, maintien du plein écran. En cas d'accord, arrêt du rafraîchissement d'état, libération propre du plein écran navigateur et retour au tableau de bord.
36. **REV-36 (Dashboard Étudiant — Correction Régression 'renderStudentDashboard is not a function') :** Définition de la méthode `renderStudentDashboard` sur la classe `AppController` dans `app.js` et ajout des méthodes d'aide `requestFullscreen()` et `exitFullscreen()`, éliminant l'exception JavaScript et sécurisant toute la navigation retour vers le tableau de bord.
37. **REV-37 (Surveillance / Proctoring — Chronomètre Temps Réel de Session Salle) :** Ajout du widget chronomètre live `#proctor-session-timer` dans le bandeau de surveillance `#view-proctor-live` synchronisé sur l'attribut faisant autorité côté serveur `session_remaining_seconds` retourné par `GET /api/proctor/sessions/{session_id}/overview`, avec décompte actif à la seconde, coloration dynamique d'alerte et gestion des statuts en attente/clôturé.
38. **REV-38 (UI / Épuration — Suppression Définitive du Bouton 'Voir Statistiques' Partout) :** Épuration complète de l'interface par suppression définitive du bouton `#btn-open-full-stats` (Dashboard), `#btn-score-view-stats` (Score d'examen et test de niveau) et du lien `nav-stats` (Barre de navigation étudiante), conformément aux exigences utilisateur.
39. **REV-39 (Administration / CRUD Global — Console Super Administrateur Complète) :** Console Super Admin intégrée dans `#view-admin` articulée en 5 onglets dynamiques : Multi-Salles & Statistiques, Étudiants (recherche, filtre promotion, CRUD complet et réinitialisation de mot de passe), Enseignants (CRUD complet et historique des modules), Modules Académiques (CRUD complet et affectation/désaffectation de responsables pédagogiques), et Examens & Épreuves (surveillance directe en 1 clic et suppression).
40. **REV-40 (Administration / Multi-Salles — Ingestion CSV des Résultats & Consolidation Académique) :** Module d'ingestion et réconciliation `POST /api/admin/csv/import/results` traitant les fichiers de résultats de salles distantes (`student_submissions.csv`), routeur `backend/app/routers/admin.py` avec KPIs académiques consolidés (`GET /api/admin/statistics/overview`), filtrage fin des copies soumises (`GET /api/admin/results`) et export global officiel en CSV UTF-8 BOM (`GET /api/admin/csv/export/exam-results`).
41. **REV-41 (UI / Centre d'Entraînement Python — Suppression du Bandeau Badges et Gamification) :** Suppression intégrale du bandeau de badges/XP (`🎖️ Niveau 1 — Débutant, XP accumulée, Badges débloqués, Galerie des 68 Badges, Historique des Entraînements Python`) dans `#view-python` afin de dédier l'espace visuel directement au catalogue de programmation.
42. **REV-42 (Terminologie Académique — Remplacement Global de 'Groupe' par 'Spécialité') :** Harmonisation de toute l'application en substituant "Groupe" par "Spécialité" (`DEV-IA`, `SYS-ADMIN`, `CYBER-SEC`) dans tous les composants de l'interface (en-têtes, filtres, modales, tableaux), tout en maintenant la rétrocompatibilité complète des modèles de données et parseurs CSV.
43. **REV-43 (Gestion des Étudiants — Mots de Passe en Clair & Importation CSV Enrichie) :** Stockage du mot de passe en clair (`plain_password`) sur le modèle `User` pour les besoins de supervision en environnement LAN d'examen hors-ligne, affichage et modification directe dans le CRUD administrateur, générateur de mot de passe `🎲 Générer`, et support de l'import CSV avec détection automatique de délimiteur (`,` ou `;`).
44. **REV-44 (Architecture Pédagogique — Spécialités d'Enseignement et Tronc Commun) :** Alignement du cursus avec Algorithmique (`ALGO`) en tronc commun pour toutes les filières, `PYTHON_INIT` pour `DEV-IA`, `LINUX_ADMIN` pour `SYS-ADMIN`, et `CRYPTO` pour `CYBER-SEC`, avec affectation des épreuves et des enseignants par spécialité.
45. **REV-45 (Gestion des Bulletins Académiques — Synthèse, Impression PDF & Export Consolidé) :** Création du moteur d'évaluation académique unifié (`_build_student_bulletin`) synthétisant les 4 piliers diagnostiques et les 2 examens officiels (théorique et pratique machine), calcul de la moyenne générale (/20), décision d'admission (`ADMIS` si >= 10.0 ou `AJOURNÉ`), modale imprimable haute définition avec styles `@media print` A4/PDF direct, et export CSV consolidé sans redondance.
46. **REV-46 (Simulation & Amorçage Réaliste — Validation de la Charge et des Données de Test) :** Amorçage de sessions d'examen réelles et de tentatives pour 12 étudiants représentatifs (4 par spécialité `DEV-IA`, `SYS-ADMIN`, `CYBER-SEC`) avec 4 notes fondamentales et 2 notes d'épreuves officielles chacun, validant le chargement, les filtres et l'exportation des bulletins sous forte charge.
47. **REV-47 (Exportation Multiformat des Bulletins & Palmarès Trié par Module) :** Service centralisé `backend/app/services/document_export.py` exploitant `reportlab` et `python-docx` pour la génération de bulletins individuels en PDF officiel et Word (.docx), le téléchargement groupé sous archive ZIP (avec CSV récapitulatif), et la production du palmarès officiel par spécialité ordonné selon les notes de n'importe quel module choisi (`ALGO`, `PYTHON_INIT`, `CRYPTO`, `LINUX_ADMIN`, `THEO`, `PRAC`, `AVG`) en formats PDF et Word Paysage.
48. **REV-48 (Moteur d'Analyse Statistique & Psychométrique des Questions) :** Service `backend/app/services/item_analysis.py` calculant les métriques statistiques de promotion (moyenne, médiane, écart-type $\sigma$, taux d'admission), l'Indice de Discrimination $D = P_U - P_L$ (règle de Kelley top/bottom 27%), la qualification psychométrique automatique et la détection d'anomalies ($D < 0$ ou $P = 0\%$), avec modale dédiée `#modal-item-analysis` et export CSV UTF-8 BOM.
49. **REV-49 (Synchronisation Manuelle USB & Déploiement Hors-Ligne) :** Intégration frontend/backend complète du protocole USB Option B : exportation du package d'examen `.exam.zip` (manifeste + empreinte SHA-256), importation locale sur serveur de salle, exportation post-examen de l'archive de résultats `.results.zip` (soumissions, réponses, logs d'audit) et réconciliation idempotente sur l'instance Master avec tableur consolidé multi-salles.
50. **REV-50 (Gestionnaire & Éditeur Web de Questions d'Épreuves) :** Interface interactive `#modal-manage-questions` et `#modal-edit-question` permettant la création, modification, suppression et importation/exportation JSON de questions pour les 5 types d'épreuves (`boolean`, `single_choice`, `multi_choice`, `fill_blank`, `matching`) avec barèmes et pénalités personnalisables.





