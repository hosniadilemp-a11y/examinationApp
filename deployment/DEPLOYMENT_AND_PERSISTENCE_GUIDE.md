# 🚀 Guide Complet de Déploiement Docker, Persistance des Données & Sécurité

Ce guide détaille l'architecture de déploiement en conteneur Docker, les garanties de persistance des bases de données lors des mises à jour, la gestion des promotions/années d'inscription, ainsi que l'audit de sécurité et d'inviolabilité de la plateforme.

---

## 1. Démarrage, Arrêt et Mise à Jour de l'Application

Tous les scripts d'exploitation sont centralisés dans le répertoire `deployment/` :

| Script Windows | Script Linux/macOS | Action Réalisée |
| :--- | :--- | :--- |
| `start_app.bat` | `start_app.sh` | Lance l'application et la base de données en arrière-plan via Docker Compose. Vérifie le contrôle de santé (`/api/health`). |
| `stop_app.bat` | `stop_app.sh` | Arrête proprement les conteneurs sans aucune perte de données. |
| `update_app.bat` | `update_app.sh` | **Reconstruit la nouvelle image Docker** avec le code mis à jour, applique les migrations de schéma et redémarre les services sans toucher aux données. |
| `export_offline_image.bat` | — | Compile et exporte l'image dans `examination-quiz-server.tar` pour déploiement hors-ligne sur clé USB. |
| `load_offline_image.bat` | — | Charge l'image depuis `examination-quiz-server.tar` sur une machine isolée sans accès internet. |

---

## 2. Persistance des Données : Que se passe-t-il lors d'une mise à jour ?

### 🔒 Garantie d'Immuabilité des Données
Lorsqu'une mise à jour de l'application est déployée (via `update_app.bat` ou `docker compose build`) :
1. **Les volumes Docker sont conservés :**
   * Le volume PostgreSQL `postgres_data` ou le volume SQLite WAL `room_data` / `standalone_data` sont gérés par le moteur Docker indépendamment des conteneurs.
   * La destruction et le remplacement du conteneur ne détruisent **JAMAIS** le volume attaché.
2. **Migrations de Schéma Automatiques et Non-Destructives :**
   * Au démarrage, le serveur exécute une vérification du schéma (`backend/app/main.py`).
   * Si une nouvelle fonctionnalité nécessite de nouvelles colonnes (comme `enrollment_year` ou `exam_type`), le système exécute un `ALTER TABLE ... ADD COLUMN ...` uniquement si la colonne n'existe pas déjà.
   * **Aucune table n'est écrasée ou réinitialisée.**
   * Tous les comptes utilisateurs, mots de passe, épreuves créées, copies d'examen soumises et notes attribuées restent intacts.

---

## 3. Gestion des Promotions et Années d'Inscription des Étudiants

Pour éviter que les étudiants de différentes promotions ne soient intervertis ou mélangés :
1. **Attribut `enrollment_year` (ex: `2024-2025`, `2025-2026`) :**
   * Chaque étudiant est rattaché à une année d'inscription.
   * Cet attribut est modifiable dans la modale d'édition étudiant (`modal-admin-student`).
2. **Filtres Administrateurs et Enseignants :**
   * Dans l'espace d'administration des étudiants, un sélecteur déroulant `Toutes les Années` permet de filtrer instantanément les étudiants par promotion.
   * L'API `GET /api/users/enrollment-years` fournit dynamiquement la liste de toutes les promotions enregistrées.
3. **Import / Export CSV avec Promotion :**
   * Le fichier CSV d'import accepte les colonnes `annee`, `année`, `promotion` ou `enrollment_year`.
   * L'export CSV inclut la colonne `enrollment_year`.

---

## 4. Audit de Sécurité : Un étudiant peut-il falsifier sa note ou accéder aux panneaux Enseignant/Admin ?

### 🛡️ Réponse formelle : NON, aucune brèche ne le permet.

Voici l'analyse technique des couches de protection inviolables implémentées :

#### 1. Inviolabilité de la Notation (Calcul Strictement Côté Serveur)
* **Aucun score n'est transmis par le client :**
  Lors de la soumission d'une copie (`POST /api/student/exams/{attempt_id}/submit`), le corps de la requête contient uniquement les réponses de l'étudiant :
  ```json
  {
    "answers": {
      "q1": "B",
      "q2": "def solution(): return 42"
    }
  }
  ```
  Le champ `score`, `points` ou `final_mark` n'existe pas dans le schéma de requête client. Si un étudiant tente d'injecter un faux score via DevTools, **FastAPI l'ignore totalement**.
* **Évaluation Sandbox Côté Serveur :**
  Pour les défis Python, le code de l'étudiant est exécuté sur le serveur dans un sous-processus sécurisé (`sandbox_runner.py`) avec isolation mémoire et timeout strict.
* **Secret des Tests Cachés :**
  Les tests cachés ($\ge 10$) sont stockés en base sur le serveur. Le serveur teste le code contre ces tests secrets, calcule la note serveur de manière autonome et enregistre la note directement dans la table `exam_attempts`. L'étudiant ne reçoit que la note finale scellée.

#### 2. Contrôle d'Accès Basé sur les Rôles (RBAC) & Tokens JWT Signés
* **Vérification cryptographique à chaque requête :**
  Chaque requête vers l'API nécessite un en-tête `Authorization: Bearer <token_jwt>`.
  Le token est chiffré et signé avec `HMAC-SHA256` en utilisant une clé secrète serveur `SECRET_KEY`.
* **Privilèges Enseignant et Administrateur :**
  Tous les endpoints d'administration (`/api/admin/*`, `/api/users/*`) et de gestion des examens (`/api/exams/*`, `/api/proctor/*`) vérifient formellement :
  ```python
  if current_user.role not in ["admin", "super_admin"]:
      raise HTTPException(status_code=403, detail="Privilèges insuffisants")
  ```
  Un token étudiant tentant d'accéder à l'interface enseignant ou à l'API admin reçoit immédiatement une erreur **`HTTP 403 Forbidden`**.
* **Impossibilité d'élévation de privilèges :**
  L'étudiant ne peut pas modifier son propre rôle dans le token, car toute modification altère la signature cryptographique du JWT et déclenche une erreur `HTTP 401 Unauthorized (Signature verification failed)`.

#### 3. Accès Réseau à la Base de Données
* **Base SQLite locale :**
  La base de données est un fichier local sur le disque du serveur (`/app/data/exam_app.db`). SQLite ne dispose d'aucun port réseau et n'écoute aucune connexion externe. Aucun étudiant sur le réseau local LAN ne peut se connecter au fichier SQLite.
* **Base PostgreSQL (Docker) :**
  Dans le réseau virtuel Docker, PostgreSQL est cloisonné sur le réseau interne `exam_network`. Seul le conteneur FastAPI communique avec la base de données.

