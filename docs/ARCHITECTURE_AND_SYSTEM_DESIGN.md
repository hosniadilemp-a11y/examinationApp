# Architecture & Spécifications Détaillées du Système
# Plateforme d'Examen et d'Entraînement Multi-Modules (LAN Distribué)

**Version :** 1.0.0 — Document de Référence Complet  
**Statut :** Spécification Technique Consolidée  
**Langue UI :** Français uniquement  
**Capacité Cible :** Jusqu'à 30 étudiants simultanés par serveur de salle

---

## 1. Vue d'Ensemble & Principes Fondamentaux

Le système est une plateforme d'évaluation continue, d'examen officiel et d'entraînement pour les cursus informatiques universitaires, conçue pour opérer **intégralement hors-ligne sur réseau local (LAN)**.

### Principes Clés d'Ingénierie
1. **Autorité Serveur Absolue :** Le client web (navigateur étudiant) est considéré comme hostile et non fiable. Le serveur détient seul la vérité sur le chronomètre, l'état de suspension, l'enregistrement des réponses et le calcul des notes.
2. **Confidentialité Totale des Corrigés :** Aucune réponse correcte ni explication n'est jamais transmise au client étudiant durant un examen officiel.
3. **Indépendance des Salles (Option B) :** Chaque salle informatique dispose de son propre serveur autonome. Aucune panne réseau globale ou coupure de liaison centrale ne peut interrompre une session d'examen.
4. **Zéro Dépendance Internet :** Toutes les polices de caractères, scripts JavaScript, styles CSS et binaires d'exécution (notamment Pyodide) sont embarqués localement.
5. **Simplicité & Sobriété Frontend :** Vanilla JavaScript (modules ES), Web Components natifs et CSS moderne. Aucun bundler, aucun framework lourd, aucun build complexe.

---

## 2. Architecture Système & Flux de Données

```
                                  ┌─────────────────────────────────────────┐
                                  │       INSTANCE CENTRALE (MASTER)        │
                                  │   - Gestion Globale Utilisateurs/Groupes│
                                  │   - Auteur des Examens & Banques QCM    │
                                  │   - Export Packages (.exam.zip)         │
                                  │   - Import & Consolidation Notes        │
                                  └────────────────────▲────────────────────┘
                                                       │
                           Transfert Physique par Clé USB (Dépôt Web)
                       ┌───────────────────────────────┴───────────────────────────────┐
                       ▼                                                               ▼
        ┌──────────────────────────────┐                                ┌──────────────────────────────┐
        │    SERVEUR SALLE A (LAN)     │                                │    SERVEUR SALLE B (LAN)     │
        │ - FastAPI Backend (Port 8000)│                                │ - FastAPI Backend (Port 8000)│
        │ - Base SQLite (Mode WAL)     │                                │ - Base SQLite (Mode WAL)     │
        │ - Service WebSockets Live    │                                │ - Service WebSockets Live    │
        │ - UI Surveillance Enseignant │                                │ - UI Surveillance Enseignant │
        └──────────────▲───────────────┘                                └──────────────▲───────────────┘
                       │                                                               │
          Réseau Local Salle (Switch LAN)                                 Réseau Local Salle (Switch LAN)
          ┌────────────┴────────────┐                                     ┌────────────┴────────────┐
          ▼                         ▼                                     ▼                         ▼
   [Poste Étudiant 1]       [Poste Étudiant 30]                    [Poste Étudiant 1]       [Poste Étudiant 30]
   (Navigateur Web)         (Navigateur Web)                       (Navigateur Web)         (Navigateur Web)
```

### 2.1. Cycle de Vie d'un Examen
1. **Conception & Packaging (Master) :**
   * L'enseignant conçoit l'épreuve sur le Master (ou importe un fichier JSON structuré).
   * L'épreuve est exportée sous forme d'archive compressée `examen_<module>_<id>.exam.zip` contenant le sujet, les barèmes, les consignes et les éventuels médias.
2. **Déploiement en Salle :**
   * L'enseignant charge le fichier `.exam.zip` sur le serveur de salle via son interface d'administration Web juste avant la séance.
   * Le serveur extrait et intègre l'épreuve en base locale, puis supprime ou archive l'archive brute.
3. **Déroulement de l'Épreuve :**
   * Les étudiants se connectent et patientent dans la **Salle d'Attente**.
   * L'enseignant clique sur **"Lancer l'Épreuve"** : le décompte démarre simultanément pour tous.
   * Télémétrie en temps réel transmise via WebSocket (état des questions, focus, temps restant).
4. **Clôture & Exportation :**
   * À la fin du temps (ou soumission manuelle), l'étudiant visualise sa note finale.
   * L'enseignant télécharge l'archive `resultats_<salle>_<session>.zip` contenant les soumissions et le journal d'audit.
5. **Consolidation (Master) :**
   * L'administrateur ou l'enseignant injecte l'archive de résultats sur le Master, qui réconcilie les notes, calcule les moyennes de promotion et génère les exports CSV.

---

## 3. Modèle de Données Relationnel

Le schéma est conçu pour fonctionner de manière identique sous **SQLite (mode WAL)** sur les serveurs de salle et sous **PostgreSQL / SQLite** sur le Master.

```sql
-- Utilisateurs & Groupes
CREATE TABLE groups (
    id TEXT PRIMARY KEY,               -- ex: 'GRP-1', 'TD-A'
    name TEXT NOT NULL,
    description TEXT
);

CREATE TABLE users (
    id TEXT PRIMARY KEY,               -- Matricule ou identifiant unique
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,       -- Argon2id
    full_name TEXT NOT NULL,
    email TEXT,
    role TEXT NOT NULL CHECK (role IN ('admin', 'teacher', 'student')),
    group_id TEXT REFERENCES groups(id),
    must_change_password BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Modules & Attribution Enseignants
CREATE TABLE modules (
    code TEXT PRIMARY KEY,             -- ex: 'PYTHON_INIT', 'CRYPTO', 'LINUX_ADMIN'
    title TEXT NOT NULL,
    description TEXT
);

CREATE TABLE teacher_modules (
    teacher_id TEXT REFERENCES users(id),
    module_code TEXT REFERENCES modules(code),
    PRIMARY KEY (teacher_id, module_code)
);

-- Examens & Questions
CREATE TABLE exams (
    id TEXT PRIMARY KEY,
    module_code TEXT REFERENCES modules(code),
    title TEXT NOT NULL,
    instructions TEXT,
    duration_minutes INTEGER NOT NULL,
    global_points REAL NOT NULL DEFAULT 20.0,
    navigation_mode TEXT NOT NULL DEFAULT 'free', -- 'free'
    shuffle_questions BOOLEAN NOT NULL DEFAULT TRUE,
    shuffle_options BOOLEAN NOT NULL DEFAULT TRUE,
    partial_credit_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    default_negative_penalty REAL NOT NULL DEFAULT 0.5,
    created_by TEXT REFERENCES users(id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE exam_groups (
    exam_id TEXT REFERENCES exams(id),
    group_id TEXT REFERENCES groups(id),
    PRIMARY KEY (exam_id, group_id)
);

CREATE TABLE questions (
    id TEXT PRIMARY KEY,
    exam_id TEXT REFERENCES exams(id) ON DELETE CASCADE,
    ordering INTEGER NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('boolean', 'single_choice', 'multi_choice', 'fill_blank', 'matching')),
    prompt_markdown TEXT NOT NULL,
    points REAL NOT NULL DEFAULT 1.0,
    negative_penalty REAL NOT NULL DEFAULT 0.5,
    time_limit_seconds INTEGER,        -- Optionnel
    options_json TEXT NOT NULL,        -- Choix multiples ou paires d'appariement
    correct_answers_json TEXT NOT NULL -- Clefs correctes (chiffré / masqué aux étudiants)
);

-- Sessions d'Examen en Salle
CREATE TABLE exam_sessions (
    id TEXT PRIMARY KEY,
    exam_id TEXT REFERENCES exams(id),
    room_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'waiting', -- 'waiting', 'in_progress', 'completed', 'archived'
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    launched_by TEXT REFERENCES users(id)
);

-- Tentatives Étudiants & Télémétrie
CREATE TABLE student_attempts (
    id TEXT PRIMARY KEY,
    session_id TEXT REFERENCES exam_sessions(id),
    student_id TEXT REFERENCES users(id),
    status TEXT NOT NULL DEFAULT 'waiting', -- 'waiting', 'in_progress', 'suspended', 'submitted', 'timed_out'
    started_at TIMESTAMP,
    submitted_at TIMESTAMP,
    raw_score REAL,
    final_mark REAL,
    suspension_reason TEXT,
    suspension_count INTEGER NOT NULL DEFAULT 0,
    client_ip TEXT
);

CREATE TABLE student_answers (
    attempt_id TEXT REFERENCES student_attempts(id) ON DELETE CASCADE,
    question_id TEXT REFERENCES questions(id),
    answer_payload_json TEXT NOT NULL, -- Réponse fournie par l'étudiant
    is_correct BOOLEAN,
    awarded_points REAL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (attempt_id, question_id)
);

-- Journal d'Audit & Sécurité
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    student_id TEXT,
    event_type TEXT NOT NULL,          -- 'LOGIN', 'FULLSCREEN_EXIT', 'FOCUS_LOST', 'SUSPENDED', 'UNLOCKED', 'SUBMIT'
    details_json TEXT,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

---

## 4. Moteur d'Évaluation & Résolution des Cas Particuliers

### 4.1. Formules de Notation par Type de Question

| Type de Question | Règle d'Attribution des Points | Pénalité Faute | Note Minimale Question |
| :--- | :--- | :--- | :--- |
| **Vrai / Faux** | Réponse exacte : `+points` | Réponse fausse : `0` (ou `-penalty` si activé) | Plancher à `0` |
| **QCM Réponse Unique** | Bonne option choisie : `+points` | Mauvaise option : `0` (ou `-penalty` si activé) | Plancher à `0` |
| **QCM Réponses Multiples** | Chaque bonne réponse cochée : `points / N_bonnes` | Chaque mauvaise réponse cochée : `-penalty` | Plancher à `0` |
| **Texte à Trou** | Correspondance exacte ou normalisée : `+points` | Mauvaise saisie : `0` | `0` |
| **Appariement (Matching)** | Chaque paire correcte : `points / N_paires` | Paire incorrecte : `0` | `0` |

### 4.2. Résolution des Cas Limites (Section 12 des Spécifications)
1. **QCM sans aucune bonne réponse (cas rare / piège) :**
   * *Règle :* Si un enseignant configure une question où aucune option standard n'est valide, l'option explicite *"Aucune des réponses ci-dessus"* est automatiquement injectée par le moteur comme la seule bonne réponse, évitant ainsi toute division par zéro dans la formule `points / N_bonnes`.
2. **Pénalité sur questions binaires (Vrai/Faux) :**
   * *Règle :* Par défaut, une mauvaise réponse sur un Vrai/Faux rapporte `0` point. L'enseignant peut activer le mode strict TP (-1 ou -0.5) s'il souhaite sanctionner le hasard complet.
3. **Appariement partiel :**
   * Chaque association correcte rapporte une quote-part égale (`points / N`). Les mauvaises associations n'entraînent pas de pénalité négative (plancher à 0).
4. **Texte à trou :**
   * Normalisation automatique : suppression des espaces superflus (`trim()`), insensibilité à la casse par défaut, et tolérance paramétrable aux accents.

---

## 5. Moteur Anti-Triche & Sécurité Client

### 5.1. Matrice des Événements Surveillés

```
[Navigateur Étudiant]
   │
   ├── Événement `fullscreenchange` ──────────► Si Sortie de Plein Écran ──┐
   ├── Événement `window.blur` / `visibility` ─► Si Changement d'Onglet ────┤
   ├── Événement `copy` / `paste` / `contextmenu` ──► Bloqué Immédiatement  │
   │                                                                        ▼
   │                                                        Compteur d'Absence (>10s)
   │                                                                        │
   │                                                                  Si Dépassement
   │                                                                        ▼
   │                                                         VERROUILLAGE ÉCRAN SUSPENDU
   │                                                                        │
   └──────────────────────── Télémétrie WebSocket ──────────────────────────►
                                                                            ▼
                                                              [Tableau de Bord Enseignant]
                                                              (Alerte Rouge + Bouton "Débloquer")
```

### 5.2. Gestion Précise des Coupures Réseau vs Départs d'Écran
* **Déconnexion Réseau (Câble débranché / Wi-Fi instable) :**
  * L'application web bascule en mode cache local (IndexedDB / localStorage).
  * L'étudiant conserve son plein écran et continue de répondre normalement.
  * Le chronomètre serveur continue de tourner.
  * Dès le retour du réseau, toutes les réponses accumulées sont transmises en rafale.
  * **Aucune suspension** n'est déclenchée pour une coupure réseau pure.
* **Départ d'Écran (> 10 secondes) :**
  * Si l'étudiant quitte le plein écran ou minimise la fenêtre pendant plus de 10 secondes, le verrouillage de sécurité s'active.
  * Le statut passe à `suspended`.
  * Seul l'enseignant peut lever la suspension d'un clic depuis son poste.

---

## 6. Moteur d'Entraînement Python (Exécution Sécurisée Pyodide)

* **Architecture Client-Side Sandboxée :**
  * Le code Python saisi par l'étudiant est exécuté **directement dans le navigateur** via **Pyodide** (WebAssembly) au sein d'un **Web Worker** dédié.
  * **Sécurité totale du serveur :** Aucun code étudiant n'est jamais exécuté sur le serveur backend.
  * **Protection Anti-Boucle Infinie :** Un minuteur de sécurité dans le Web Worker interrompt automatiquement l'exécution si elle excède 5 secondes.
  * **Fonctionnement 100% Hors-Ligne :** Les fichiers Pyodide (.wasm, .js) sont stockés localement sur le serveur et mis en cache par le navigateur.

---

## 7. Spécification des Banques de Questions d'Entraînement Libre

Les **4 tests d'entraînement libre** (30 questions chacun, soit 120 questions au total) sont intégrés dès l'installation initiale sous forme de fichiers JSON :
1. `seed_algo_30.json` : Notions fondamentales d'algorithmique (boucles, conditions, récursivité, complexité élémentaire).
2. `seed_python_30.json` : Syntaxe Python, structures de données (listes, tuples, dictionnaires), fonctions, gestion d'erreurs (30 questions uniques certifiées sans répétition).
3. `seed_crypto_30.json` : Chiffrement historique (César, Vigenère), chiffrement moderne symétrique/asymétrique, fonctions de hachage, clés publiques/privées.
4. `seed_linux_30.json` : Commandes de base, hiérarchie `/`, droits (`chmod`/`chown`), redirection de flux, gestion des processus.

---

## 8. Évolution Architecturale & Révisions Système (REV-01 à REV-12)

### 8.1. Sandbox Pyodide Web Worker (REV-01)
* **Détection du mode Worker :** Pyodide v0.26+ exécute un test `isClassicWorker()` lors de son initialisation en tentant `globalThis.importScripts(...)`. Dans un environnement Web Worker standard avec scripts dynamiques, cette fonction est neutralisée via `globalThis.importScripts = undefined` avant l'importation de `pyodide.mjs`.
* **Exécution 100% Hors-Ligne :** Instanciation directe du module ES depuis les assets locaux vendored (`/vendor/pyodide/`).

### 8.2. Moteur de Rendu Markdown Sécurisé (REV-02)
* Parseur Vanilla performant sans dépendance externe (`_formatMarkdown`) pour convertir de façon sécurisée les blocs de code préformatés (fenced code blocks), l'inline code, la hiérarchie de titres (`#`, `##`, `###`), le gras/italique, et générer une typographie aérée avec gestion sémantique des paragraphes `<p>`.

### 8.3. Double Brassage & Échantillonnage Déterministe (REV-03 & REV-10)
* **Double Brassage :** À chaque appel de l'API des tests de niveau, la liste des questions et les choix de réponses associés sont permutés aléatoirement. Chaque choix conserve son `id` logique d'origine pour garantir une notation serveur inviolable.
* **Échantillonnage :** Prise en charge du paramètre `count=20` permettant de sélectionner aléatoirement 20 questions parmi les 30 du réservoir `seed_python_30.json`.
* **Traçabilité de Soumission :** L'endpoint de soumission accepte `question_ids` pour scorer précisément l'échantillon exact administré à l'étudiant.

### 8.4. Environnement de Développement Intégré CodeMirror (REV-04)
* Pour les épreuves de programmation (`type: "coding"`), attachement automatique d'une instance CodeMirror locale avec coloration syntaxique Python, numéros de ligne, gestion de l'indentation à 4 espaces et réactivité temps réel avec l'état de l'épreuve.

### 8.5. Tolérance de Typage & Normalisation de Notation (REV-05, REV-06, REV-09)
* **Booléens :** Normalisation universelle des représentations (`true`/`false`, `"true"`/`"false"`, `"Vrai"`/`"Faux"`, `1`/`0`).
* **Sérialisation des Réponses :** Remplacement de la chaîne placeholder par la valeur effective de la réponse utilisateur pour un retour pédagogique transparent.
* **Association (Matching) :** Comparaison insensible à l'ordre des clés dans l'objet d'association et attribution systématique de 100% des points dès que le total des paires exactes égale le nombre de paires requises.

### 8.6. Isolation Étanche des Statistiques Cursus (REV-08)
* Cloisonnement strict des domaines d'évaluation :
  - `StudentAttempt` : Examens officiels sous surveillance.
  - `PracticeAttempt` : Tests de niveau 24h/24 des 4 modules fondamentaux.
  - `TrainingAttempt` & `ChapterProgress` : Parcours progressif, XP (10 niveaux) et 68 badges du Centre Python.

### 8.7. Échelle Officielle à 6 Paliers (REV-11)
* Grille standardisée adoptée :
  1. *Insuffisant* (0.00 à < 7.00 / 20)
  2. *Sous la moyenne* (7.00 à < 10.00 / 20)
  3. *Limite* (10.00 à < 12.00 / 20)
  4. *Moyen* (12.00 à < 14.00 / 20)
  5. *Bon* (14.00 à < 16.00 / 20)
  6. *Excellent* (16.00 à 20.00 / 20)

### 8.8. Cycle de Vie Anti-Triche et Nettoyage d'Événements (REV-12)
* Arrêt immédiat et libération de tous les écouteurs du gestionnaire `AntiCheatManager` lors de la soumission de l'examen ou de la navigation vers un écran hors-épreuve.

### 8.9. Modèles d'Examens JSON & Importation Dynamique (REV-13)
* **Templates Prêts à l'Emploi :** Stockage de 3 modèles normalisés (`template_exam_python.json`, `template_exam_linux.json`, `template_exam_crypto.json`) intégrant chacun 8 questions panachées couvrant les 6 types supportés, notés sur 20 points avec durées prédéfinies.
* **API Dédiée :** Exposition des routes `GET /api/exams/templates`, `POST /api/exams/templates/{template_id}/load` et `POST /api/exams/import-template`.
* **Interface Enseignant :** Modale de chargement instantané d'un modèle et sélecteur de fichier JSON local (`input[type="file"]`) avec parsing et rafraîchissement immédiat de la vue enseignant.

### 8.10. Jeu de Données de Test & Segmentation des Spécialités (REV-14)
* **Groupes Cibles :** Définition de 3 spécialités représentatives : `DEV-IA` (Développement & IA), `SYS-ADMIN` (Systèmes & Réseaux), et `CYBER-SEC` (Sécurité & Cryptographie).
* **Population Étudiante :** Initialisation de 4 étudiants par groupe (12 étudiants : `dev1..4`, `sys1..4`, `sec1..4`) dotés de mots de passe hachés Argon2id (`StudentDev1..4!`, etc.) pour tester le ciblage par groupe et la surveillance multi-postes.

### 8.11. Découplage de la Création et du Lancement d'Examen (REV-15)
* **Persistance Isolée :** La création ou l'import d'un examen initialise l'enregistrement `Exam` en base avec ses questions associées et ses groupes cibles, sans instancier d'entité `ExamSession`.
* **Statut Visuel :** L'examen est catalogué sous l'état `🟢 Prêt` dans la liste de l'enseignant, permettant une préparation en amont sans déclenchement prématuré de l'épreuve.

### 8.12. Salle de Surveillance & Monitoring Interactif en Direct (REV-16)
* **Architecture Télémetrique :** Inspirée d'AlgoExamination, la vue `#view-proctor-live` établit un canal WebSocket bidirectionnel `/ws/proctor/{session_id}`.
* **Grille Dynamique des Postes :** Visualisation matricielle de l'ensemble des candidats inscrits au groupe avec carte individuelle : nom, identifiant, groupe, statut coloré (*Non entré*, *En cours*, *Suspendu*, *Terminé*), question active, pourcentage de complétion et compteur d'avertissements.
* **Pilotage Collectif :** Commandes de démarrage synchronisé de l'épreuve pour tous les candidats connectés et prolongation collective du temps (+5 minutes).
* **Contrôles Individuels :** Action de déblocage immédiat d'un poste suspendu (`POST /api/proctor/sessions/{session_id}/attempts/{attempt_id}/unlock`) et journal d'audit interactif alimenté en temps réel par les alertes anti-triche et événements de télémétrie.

### 8.13. Formatage Élargi des Réponses de Programmation dans les Corrigés (REV-17)
* **Présentation Multi-lignes :** Utilisation de conteneurs `<pre><code class="python-code-block">` préservant scrupuleusement l'indentation, les sauts de lignes et la coloration pour le code soumis par l'étudiant et la solution de référence.
* **Conteneur Pleine Largeur :** Élargissement de `#view-score` à 1000px pour éviter tout tassement horizontal.

### 8.14. Grille de Badges pour les Questions d'Association (REV-18)
* **Rendu Modulaire :** Remplacement de la sérialisation textuelle brute par une grille `.matching-badges-grid` de cartes `.matching-badge-card`.
* **Diagnostic Visuel Immédiat :** Encadrement vert ✅ pour les appariements exacts et rouge ❌ pour les associations erronées avec indication explicite de la cible attendue.

### 8.15. Support Stdin et Prise en Charge de `input()` dans Pyodide (REV-19)
* **Interception du Flux d'Entrée :** Encapsulation de `builtins.input` via `_safe_input_mock` et d'une classe `SafeStdin` dans le Web Worker Pyodide, prévenant toute levée d'`EOFError` lors de l'exécution de scripts lisant l'entrée standard.
* **Champ Interactif :** Mise à disposition d'une entrée `stdin-input` modifiable par l'étudiant directement au-dessus du terminal d'exécution.

### 8.16. Navigation Cohérente & Origine de Session (REV-20)
* **Traçabilité de Contexte :** Mémorisation de l'origine d'appel (`activeOriginView`) garantissant qu'une session issue du Centre d'Entraînement Python redirige fidèlement vers `view-python` lors de l'abandon ou de la consultation des résultats.

### 8.17. En-têtes Épurés & Capsules de Métadonnées (REV-21)
* **Épuration des Prompts :** Nettoyage systématique des balises de chapitres ou difficultés préfixées dans le Markdown brut.
* **Barre de Métadonnées :** Rendu unifié sous forme de capsules stylisées : dossier thématique, pill de difficulté colorée (Vert / Jaune / Orange / Rouge), type de question et points.

### 8.18. Sélection Exclusive 1-to-1 en Appariement (REV-22)
* **Intégrité de Choix :** Implémentation d'une exclusion mutuelle dynamique (`updateMutualExclusion`) désactivant toute option déjà sélectionnée dans les autres sélecteurs de la question.
* **Option Neutre :** Prise en charge de la valeur vide `"— Choisir une correspondance —"` permettant la désélection ou l'assignation partielle.

### 8.19. Confinement du Bouton Retour au Centre Python (REV-23)
* **Cloisonnement Fonctionnel :** L'écran de score et de restitution du Centre d'Entraînement Python masque strictement les boutons de redirection vers le tableau de bord général et les statistiques globales du cursus.
* **Navigation Étudiant Immersive :** Présentation d'un bouton unique `⬅️ Retourner au Centre d'Entraînement Python`, préservant la continuité du parcours d'apprentissage guidé et de la progression par chapitres sans rupture de contexte.

### 8.20. Diagnostic d'Erreur & Traceback Complet dans le Sandbox Pyodide (REV-24)
* **Extraction Déterministe des Exceptions :** Exécution du code étudiant dans le Web Worker Pyodide encapsulée dans `compile(code, "<script.py>", "exec")` et interprétée au moyen de `traceback.format_exc()`.
* **Clarté Pédagogique :** Éradication des erreurs génériques opaques (`PythonError: ...`) au profit d'un diagnostic direct restituant le type d'exception réel (`TypeError`, `IndexError`, `SyntaxError`, etc.) et le numéro de ligne précis de l'incident, facilitant l'apprentissage en autonomie.

### 8.21. Salle d'Attente Interactive & Démarrage Synchronisé Sécurisé (REV-25)
* **Confidentialité Totale Pré-Épreuve :** Lorsqu'un étudiant rejoint une session en statut `waiting`, le serveur crée la tentative en état `waiting` et renvoie uniquement les métadonnées (titre, durée, barème) sans transmettre la moindre question.
* **Écran d'Attente Dynamique :** Affichage de `#view-waiting-room` avec indicateur pulsant et consignes officielles, interdisant toute interaction non autorisée.
* **Transition Synchrone :** Boucle de rafraîchissement d'état (`GET /api/student/exam/{exam_id}/status`) détectant immédiatement le passage de la session à `in_progress` par l'enseignant, entraînant le basculement automatique et simultané de tous les candidats vers l'interface d'épreuve `#view-exam`.

### 8.22. Surveillance Structurée en Tableau Télémétrique (REV-26)
* **Visualisation Compacte Haute Densité :** Remplacement de la grille de cartes par un tableau interactif dense `table#proctor-candidates-table` (`tbody#proctor-students-table-body`), capable d'afficher simultanément 30 candidats sans encombrement visuel.
* **Métriques par Candidat :** Identifiant, nom de l'étudiant, spécialité/groupe, statut d'épreuve coloré, jauge de progression (ex: `5/8 (62%)`), temps restant synchronisé, compteur d'avertissements de sécurité et actions contextuelles d'intervention immédiate (`🔓 Débloquer`, `🛑 Forcer`, `+5m`).

### 8.23. Anti-Triche Haute Sécurité avec Floutage Immédiat (REV-27)
* **Obstruction Visuelle Instantanée :** Toute rupture du mode plein écran (`fullscreenchange`) déclenche l'application synchrone de la classe CSS `.exam-fullscreen-lost-blurred` (`filter: blur(16px); user-select: none; pointer-events: none;`) sur l'ensemble de l'interface d'examen.
* **Modale d'Interception Inviolable :** Affichage de l'overlay `#overlay-fullscreen-required` avec avertissement rouge et bouton d'action `Repasser en plein écran`. L'accès au sujet et la saisie de réponses restent physiquement impossibles tant que l'intégrité du plein écran n'est pas restaurée.

### 8.24. Horloge Authoritaire Serveur & Synchronisation Continue (REV-28)
* **Anti-Dérive d'Horloge Client :** Le serveur calcule avec précision les secondes restantes effectives (`remaining_seconds = max(0, duration_seconds - elapsed)`) lors de chaque enregistrement de réponse (`POST /api/student/exam/{exam_id}/save-answer`) et de vérification périodique d'état (`GET /api/student/exam/{exam_id}/status`).
* **Calibrage Automatique du Chronomètre :** Le gestionnaire de compte à rebours client réaligne sa valeur locale sur l'autorité serveur (`syncServerRemainingSeconds`), garantissant une fin d'épreuve parfaitement synchronisée pour tous les candidats quel que soit le décalage de l'horloge système locale.

### 8.25. Règle des 4 Avertissements et Suspension Officielle (REV-29)
* **Tolérance Zéro Anti-Triche :** Lors des examens officiels sous surveillance, l'accumulation de 4 avertissements (pertes de focus, sorties du mode plein écran) entraîne la suspension immédiate du poste d'examen (`status = 'suspended'`).
* **Protocole de Déblocage Surveillant :** L'enseignant surveillant peut lever la suspension depuis son tableau de bord (`POST /api/proctor/sessions/{session_id}/attempts/{attempt_id}/unlock`). L'action réinitialise le compteur d'avertissements à 0 côté serveur et client, lève les filtres d'obstruction visuelle et permet à l'étudiant de poursuivre son épreuve.

### 8.26. Clôture Collective d'Épreuve et Notation Automatique (REV-30)
* **Commande Centralisée de Fin d'Épreuve :** Mise à disposition du bouton `🛑 Clôturer l'Épreuve` sur le tableau de bord de surveillance, appelant l'endpoint `POST /api/proctor/sessions/{session_id}/close`.
* **Scellement Massif Instantané :** Le serveur force la soumission de toutes les copies en cours de la session, calcule leurs notes définitives sur 20 selon le barème, passe les tentatives à `completed`, clôture la session et diffuse un signal WebSocket `SESSION_CLOSED` provoquant le verrouillage immédiat des postes étudiants.

### 8.27. Modale de Création d'Examen Personnalisé avec Double Brassage (REV-31)
* **Interface Enseignant Ergonomique :** Modale dédiée `#modal-create-custom-exam` permettant de paramétrer le titre de l'épreuve, le module cible (`ALGO`, `CRYPTO`, `LINUX_ADMIN`, `PYTHON_INIT`), la durée en minutes, la note maximale, la salle de lancement (ex: `SALLE-TP-1`), les groupes autorisés (`DEV-IA`, `SYS-ADMIN`, `CYBER-SEC`, `GRP-1`) et les options de randomisation.
* **Auto-Population et Session Découplée :** Lorsque l'enseignant spécifie une salle, le serveur extrait et peuple automatiquement les questions issues du modèle de référence du module, configure le double brassage des questions et des options, et instancie la session au statut `waiting` prête pour le déploiement en salle.

### 8.28. Robustesse de la Soumission et Écran de Score Officiel (REV-32)
* **Résolution de Régression :** Élimination de l'erreur d'exécution `TypeError: this.renderScoreScreen is not a function` lors de la soumission d'une tentative officielle.
* **Restitution Standardisée :** Implémentation complète de la fonction `renderScoreScreen` affichant la note obtenue /20, le barème total, l'appréciation académique et le scellement définitif de la copie.

### 8.29. Verrouillage Immuable des Cartes d'Épreuves Soumises (REV-33)
* **Protection Post-Examen :** Dès qu'une tentative est soumise (`submitted`, `completed`, `timed_out`), la carte de l'examen dans le tableau de bord étudiant remplace les boutons de lancement (`Commencer l'examen`, `Reprendre`) par un badge immuable `✅ Épreuve Soumise & Scellée (Note : XX.XX / 20)`.
* **Intégrité Académique :** Toute tentative de réouverture ou de re-soumission de l'épreuve est physiquement neutralisée tant dans le DOM de l'interface client que par l'autorité du serveur.

### 8.30. Sécurisation Plein Écran de la Salle d'Attente (REV-34)
* **Confinement Pré-Épreuve :** Dès que le candidat rejoint une épreuve en attente de départ (`status === 'waiting'`), l'interface bascule en plein écran (`this.requestFullscreen()`).
* **Obstruction Visuelle Synchrone :** L'écouteur global `fullscreenchange` et le sous-système anti-triche surveillent `#view-waiting-room`. Si le plein écran est perdu avant le début officiel, le flou `.exam-fullscreen-lost-blurred` (`filter: blur(16px)`) est immédiatement appliqué et l'overlay `#overlay-fullscreen-required` interdit toute manipulation tant que le mode plein écran n'est pas rétabli.

### 8.31. Protocole d'Abandon Contrôlé de la Salle d'Attente (REV-35)
* **Avertissement Pédagogique :** Le clic sur `✕ Quitter la Salle d'Attente` déclenche un dialogue d'interception confirmant l'imminence de l'examen.
* **Gestion d'État Bilatérale :**
  - En cas d'annulation, le candidat demeure dans la salle d'attente et son affichage plein écran est réaffirmé (`this.requestFullscreen()`).
  - En cas de confirmation, le cycle d'attente s'interrompt de manière propre (`clearInterval(this.waitingRoomInterval)`), les classes de flou sont réinitialisées, le plein écran du navigateur est relâché (`exitFullscreen()`), et la redirection s'opère vers le tableau de bord sans résidu d'écouteurs.

### 8.32. Fiabilisation du Routage Étudiant & Résolution de Régression (REV-36)
* **Intégrité de l'API Interne du Contrôleur :** Fourniture de la méthode explicite `renderStudentDashboard()` sur l'instance de `AppController`, servant de passerelle normalisée vers `this.renderDashboard(this.currentUser)`.
* **Suppression des Exceptions Bloquantes :** Éradication totale des erreurs `TypeError: this.renderStudentDashboard is not a function` identifiées lors des interactions avec le bouton d'abandon de la salle d'attente et certains boutons de retour des corrigés.

### 8.33. Chronomètre Authoritaire en Temps Réel dans la Console de Surveillance (REV-37)
* **Authoritative Clock Synchronization :** L'endpoint `GET /api/proctor/sessions/{session_id}/overview` calcule dynamiquement le temps restant de la session (`session_remaining_seconds`) à partir de l'horodatage UTC certifié serveur `session.started_at` et de `exam.duration_minutes`, évitant toute manipulation ou dérive locale sur les machines clientes.
* **Composant Proctoring Timer :** Ajout du conteneur visuel `#proctor-session-timer` dans l'en-tête de `#view-proctor-live`. Un ticker asynchrone 1s décrémente la valeur en direct avec transitions chromatiques automatiques (bleu standard, ambre en dessous de 5 minutes, rouge d'alerte en dessous de 60 secondes).

### 8.34. Épuration Ergonomique de l'UI & Retrait du Bouton "Voir Statistiques" (REV-38)
* **Simplification du Parcours Candidat :** Suppression physique et logique du bouton `#btn-open-full-stats` (Dashboard étudiant), `#btn-score-view-stats` (vue de restitution des scores) et de l'onglet `nav-stats` (barre de navigation supérieure).
* **Concentration sur les Piliers Pédagogiques :** Le candidat conserve une vue directe sur ses progrès via les cartes de compétences et son tableau de bord épuré sans dispersion inutile.

### 8.35. Console Super Administrateur & Architecture CRUD Modulaire (REV-39)
* **Refonte Complète de `#view-admin` :** Transformation de la vue administrateur en une console à 5 onglets découplés :
  - **Multi-Salles & Résultats :** KPIs consolidés temps réel, outils d'ingestion/exportation CSV et filtrage des copies.
  - **Gestion des Étudiants :** Table complète, recherche temps réel, filtre par groupe de TP/spécialité (`DEV-IA`, `SYS-ADMIN`, `CYBER-SEC`, `GRP-1`), modale d'ajout/modification (`#modal-admin-student`), réinitialisation de mot de passe et suppression sécurisée.
  - **Gestion des Enseignants :** Table des professeurs, modale d'ajout/édition (`#modal-admin-teacher`), suppression et consultation de l'affectation aux modules.
  - **Gestion des Modules Académiques :** CRUD complet des unités d'enseignement (`#modal-admin-module`) et modale d'affectation/désaffectation dynamique des enseignants responsables (`#modal-admin-assign-module`).
  - **Gestion des Examens :** Listing global de toutes les épreuves, accès en un clic à la surveillance de salle et suppression sécurisée avec nettoyage en cascade.

### 8.36. Consolidation Multi-Salles & Ingestion CSV Idempotente (REV-40)
* **Architecture d'Ingestion Multi-Salles :** Module `backend/app/routers/admin.py` exposant l'endpoint `POST /api/admin/csv/import/results`. Il analyse les exports CSV de serveurs autonomes de salles distantes (`student_submissions.csv`), crée les étudiants et groupes manquants à la volée, génère si nécessaire une session d'examen rattachée et consolide les notes (`final_mark`, `raw_score`).
* **Reporting et Export Consolidé :** Endpoint `GET /api/admin/csv/export/exam-results` produisant un fichier CSV UTF-8 BOM regroupant l'intégralité des copies et métadonnées de toutes les salles pour l'archivage ou l'import dans les progiciels universitaires.

### 8.37. Épuration du Centre d'Entraînement Python (REV-41)
* **Retrait des Éléments de Gamification :** Suppression intégrale du bandeau de badges/XP (`🎖️ Niveau 1 — Débutant`, `XP accumulée`, `Badges débloqués`, galerie de badges, historique des entraînements) dans `#view-python`.
* **Focalisation Pédagogique :** L'espace visuel est désormais réservé sans distraction au catalogue des chapitres fondamentaux et au mode évolutif.

### 8.38. Refonte Terminologique Globale vers les Spécialités Académiques (REV-42)
* **Cohérence Institutionnelle :** Remplacement de toute mention de « Groupe » par « Spécialité » (`DEV-IA`, `SYS-ADMIN`, `CYBER-SEC`) dans l'ensemble des écrans (en-têtes, filtres, tables, modales de création d'examen et d'étudiants).
* **Rétrocompatibilité Totale :** Maintien transparent du champ technique `group_id` dans la base relationnelle et compatibilité bi-directionnelle avec les imports CSV anciens.

### 8.39. Transparence des Mots de Passe & Importation CSV Avancée (REV-43)
* **Mots de Passe en Clair :** Ajout de la colonne `plain_password` sur le modèle `User` pour faciliter la gestion d'urgence en salle d'examen fermée sans accès internet.
* **Générateur Intégré & CSV Détecteur Automatique :** Bouton `🎲 Générer` dans le formulaire étudiant et reconnaissance automatique des délimiteurs virgule (`,`) ou point-virgule (`;`) lors de l'import CSV.

### 8.40. Cursus Académique Pédagogique par Spécialité & Tronc Commun (REV-44)
* **Structure Pédagogique :** Algorithmique (`ALGO`) en tronc commun pour toutes les spécialités. `PYTHON_INIT` pour `DEV-IA`, `LINUX_ADMIN` pour `SYS-ADMIN`, `CRYPTO` pour `CYBER-SEC`.
* **Attribution des Rôles :** Enseignants affectés à leurs modules et examens filtrés selon la spécialité de l'étudiant.

### 8.41. Gestion Centralisée des Bulletins Académiques (REV-45)
* **Synthèse Globale :** Moteur d'évaluation (`_build_student_bulletin`) combinant les 4 piliers fondamentaux et les 2 examens officiels (théorique et machine).
* **Admission & Impression A4 :** Calcul de la moyenne générale (/20), statut `ADMIS` ($\ge 10.0$) ou `AJOURNÉ`, et fenêtre d'impression haute définition conforme au format officiel.

### 8.42. Amorçage et Qualification de Charge Haute Densité (REV-46)
* **Jeux de Données Réalistes :** Amorçage de 12 étudiants types (4 par spécialité) avec notes initiales et tentatives officielles scellées.
* **Validation Haute Charge :** Vérification de l'absence de redondance et de la robustesse des requêtes consolidées.

### 8.43. Moteur d'Exportation Multiformat & Palmarès Officiel (REV-47)
* **Formats Pris en Charge :** Export de bulletins individuels et collectifs en PDF haute fidélité (`reportlab`) et Microsoft Word DOCX (`python-docx`).
* **Archive ZIP & Palmarès Trié :** Téléchargement groupé de tous les bulletins dans une archive `.zip` et palmarès académique classé par note de module sélectionné.

### 8.44. Moteur d'Analyse Psychométrique & Indice de Discrimination (REV-48)
* **Indice de Discrimination de Kelley :** Calcul automatique de $D = P_U - P_L$ (comparaison du tiers supérieur 27% et inférieur 27%).
* **Détection d'Anomalies :** Identification immédiate des questions à discrimination inversée ($D < 0$) ou à taux d'échec total ($P = 0\%$) avec affichage dédié et export CSV.

### 8.45. Protocole de Synchronisation Hors-Ligne par Clé USB (REV-49)
* **Export / Import de Sujets d'Examen :** Génération de bundles `.exam.zip` avec empreinte SHA-256 pour transfert hors-ligne sur les serveurs de salle sans connexion internet.
* **Réconciliation Idempotente :** Exportation post-épreuve de l'archive `.results.zip` et fusion sécurisée sur le serveur Master sans duplication de notes.

### 8.46. Gestionnaire & Éditeur Web de Questions Universel (REV-50)
* **Éditeur Visuel Multi-Types :** Création et modification en ligne des 5 types de questions (`boolean`, `single_choice`, `multi_choice`, `fill_blank`, `matching`) avec barèmes, pénalités et temps alloué.
* **Import/Export JSON :** Transfert fluide des banques de questions entre modules et instances.

### 8.47. Moteur d'Évaluation de Code Python & Interface Défi AlgoCompiler (REV-51)
* **Interface Inspirée d'AlgoCompiler / HackerRank :** Disposition responsive en double panneau avec redimensionnement interactif :
  - *Panneau Gauche :* Énoncé riche du problème avec intégration complète de KaTeX hors-ligne (`frontend/vendor/katex/`) pour le rendu des notations mathématiques ($O(N)$, formules de complexité, équations), capsules de difficulté, temps d'exécution limite et spécifications d'entrées/sorties.
  - *Panneau Droit :* Éditeur CodeMirror Python avec thème Dracula, barre d'outils complète (Annuler/Rétablir, Commenter le code, Réinitialiser au starter code, Gestion de taille de police) et barre d'état dynamique (Position curseur, Longueur).
  - *Volet Inférieur Réglable (Splitter Horizontal) :* Navigation par onglets interactifs entre la *Console d'Exécution* (entrée personnalisée `stdin` et flux de sortie `stdout`/`stderr`) et les *Résultats des Tests* (affichage des tests publics validés ou échoués avec vue différentielle attendu vs obtenu).
* **Moteur d'Exécution Hybride (`sandbox_runner.py`) :** Service Python backend exécutant le code utilisateur dans un sous-processus isolé avec garde-fou temporel (timeout de 5 secondes), capture sécurisée des flux standards et capture exhaustive des exceptions et tracebacks.
* **Règle Stricte des Cas de Test & Catalogue Étendu :**
  - Exigence architecturale absolue : chaque problème de programmation dispose obligatoirement d'au moins 2 tests publics et d'au moins 1 test caché.
  - Rééquilibrage intégral des 183 exercices du curriculum (`curriculum.json`) et intégration des 47 problèmes d'algorithmique avancée d'AlgoCompiler (`coding_challenges.json`), portant le référentiel à **230 défis de programmation**.

### 8.48. Confidentialité Absolue des Corrigés & Protection Inviolable des Tests Cachés (REV-52)
* **Secret des Corrigés en Examen Officiel :** Aucune réponse attendue, explication pédagogique ni code de référence n'est transmis au client web de l'étudiant tant que l'épreuve n'est pas définitivement scellée.
* **Masquage Authoritaire des Tests Cachés :** Dans `sandbox_runner.py`, tout test marqué `is_public=False` voit ses métadonnées et résultats sensibles remplacés par `[Protégé]` pour la sortie attendue et `[Test Caché]` pour les paramètres d'entrée.
* **Évaluation Côté Serveur :** L'attribution de la note partielle proportionnelle au taux de réussite des tests est calculée de manière étanche par le service `grading.py` sans exposition du jeu d'évaluation au client.

### 8.49. Studio Enseignant de Conception d'Examens & Auteur de Questions de Programmation (REV-53)
* **Sélecteur Dynamique de Modules :** La modale de création d'examen `#modal-create-custom-exam` charge dynamiquement l'ensemble des modules d'enseignement de l'établissement (`DEV_WEB`, `DATABASE_SQL`, `NETWORKS`, `AI_ML`, `DATA_STRUCT`, etc.) ou les modules affectés à l'enseignant connecté.
* **Auteur de Questions de Programmation (`coding`) :** Extension du formulaire de création de questions pour prendre en charge le type `coding`, incluant la saisie du code squelette (`starter_code`), l'ajout libre de tests publics et la définition obligatoire d'au moins 1 test caché d'évaluation, avec validation bloquante côté interface.

### 8.50. Isolation Pédagogique des 4 Tests Diagnostiques de Niveau (REV-54)
* **Positionnement 24/7 en Libre-Service :** Les 4 épreuves diagnostiques (Python Niveaux 1 à 4) sont formellement isolées des cursus d'enseignement académique. Elles permettent aux étudiants d'auto-évaluer leur progression à tout moment sans incidence sur leurs notes semestrielles.
* **Indépendance des Bulletins Officiels :** Le moteur d'évaluation académique et de génération de bulletins A4/PDF exclut totalement les tentatives de ces tests diagnostiques des moyennes générales de spécialité.

### 8.51. Télémétrie Proctoring Temps Réel & Persistance Authoritaire des Extensions (REV-55)
* **Suivi de Connexion en Direct :** `WebSocketManager` suit activement l'état des connexions sockets par étudiant (`is_student_connected`). La vue de surveillance proctor affiche instantanément les statuts `En ligne`, `Hors-ligne`, `Focus Perdu` ou `Suspendu`.
* **Persistance en Base de Données des Prolongations :** L'endpoint `POST /api/proctor/sessions/{session_id}/extend-time` modifie directement l'attribut `exam_attempts.started_at` en base SQLite. L'extension de temps (+5 min, +10 min) reste ainsi pérenne et fait autorité lors de tout rechargement de page ou reprise de session après incident réseau.
* **Résilience Haute Densité :** L'architecture gère les variations de charge jusqu'à 30+ étudiants en simultané avec mise en mémoire tampon des réponses et synchronisation idempotente.







