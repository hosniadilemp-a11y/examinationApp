# Plan de Développement & Feuilles de Route par Phases
# Plateforme d'Examen et d'Entraînement Multi-Modules (LAN Distribué)

**Statut :** Document Cadre d'Exécution  
**Règle d'Or du Projet :** Développement séquentiel rigoureux par phases. **Chaque phase doit être validée et testée avant de passer à la suivante.**

---

## Vue d'Ensemble des Phases de Développement

```
┌────────────────────────────────────────────────────────────────────────┐
│  PHASE 1 : Socle Backend, Modèles de Données & Authentification        │
│  FastAPI, Base SQLite WAL, Modèles Pydantic, Auth Argon2, Groupes, CSV │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ [Validation Gate 1]
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  PHASE 2 : Moteur de Questions & Notation Granulaire                   │
│  5 Types de questions, Calcul des pénalités, 120 questions des tests   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ [Validation Gate 2]
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  PHASE 3 : Interface Étudiant d'Examen & Dispositif Anti-Triche        │
│  Plein écran, Blocage copie, Règle 10s, Navigation libre, Alerte 60s   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ [Validation Gate 3]
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  PHASE 4 : Dashboard Enseignant de Surveillance en Temps Réel          │
│  Télémétrie WebSocket (AlgoExam), Déblocage 1-clic, Lancement groupé   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ [Validation Gate 4]
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  PHASE 5 : Synchronisation Manuelle USB & Consolidation Master         │
│  Export/Import .exam.zip, Export .results.zip, Consolidation Master    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ [Validation Gate 5]
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  PHASE 6 : Module d'Entraînement Évolutif Python (Pyodide Sandboxed)   │
│  Intégration QuizApp, Web Worker Pyodide hors-ligne, Mode Évolution    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ [Validation Gate 6]
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  PHASE 7 : Conteneurisation Docker Turnkey & Tests de Charge           │
│  Docker Compose, Simulation 30 postes simultanés, Recette Finale       │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 📌 Phase 1 : Socle Backend, Modèles de Données & Authentification

### 1.1. Objectifs & Livrables
* Mise en place de l'arborescence du projet Python (FastAPI).
* Configuration de la base de données SQLite en mode **WAL (Write-Ahead Logging)** avec migrations automatisées.
* Implémentation du système d'authentification robuste (hachage Argon2id, tokens de session sécurisés).
* Gestion des utilisateurs, attribution des rôles (`admin`, `teacher`, `student`) et organisation par **Groupes**.
* Modules d'importation et d'exportation en masse via fichiers CSV (`students.csv`, `teachers.csv`, `groups.csv`, `modules.csv`).
* Changement de mot de passe obligatoire à la première connexion (mot de passe initial = identifiant étudiant).

### 1.2. Critères de Validation (Validation Gate 1)
- [x] Le serveur FastAPI démarre sans erreur et expose la documentation OpenAPI sur `/docs`.
- [x] Un script d'import CSV injecte correctement 100 étudiants répartis sur 4 groupes.
- [x] L'authentification rejette les mots de passe erronés et limite les tentatives abusives (rate-limiting).
- [x] La base SQLite gère des écritures concurrentes en mode WAL sans verrouillage intempestif (`database is locked`).
- [x] Tests unitaires automatisés réussis (`pytest tests/test_phase1.py`).

---

## 📌 Phase 2 : Moteur de Questions, Rendu Markdown & Notation Granulaire

### 2.1. Objectifs & Livrables
* Implémentation de la logique de validation et de notation pour les **5 types de questions** :
  1. Vrai / Faux (Binaire).
  2. QCM à réponse unique.
  3. QCM à réponses multiples (avec crédit partiel et pénalité paramétrable).
  4. Texte à trou (Fill-in-the-blank avec normalisation automatique).
  5. Appariement / Correspondance (Matching en deux colonnes).
* Parser Markdown avec coloration syntaxique de code informatique (Python, Bash, C, SQL).
* Création et injection des **120 questions initiales** pour les 4 tests d'entraînement permanent :
  * 30 questions *Bases d'Algorithmique*.
  * 30 questions *Bases de Python*.
  * 30 questions *Bases de Cryptographie*.
  * 30 questions *Bases d'Administration Linux*.
* API REST de création manuelle de questions et d'import/export de questionnaires au format JSON.

### 2.2. Critères de Validation (Validation Gate 2)
- [x] Les 5 types de questions sont évalués conformément aux formules mathématiques (incluant le plancher à 0).
- [x] La formule de pénalité négative sur les QCM multiples attribue un score exact au centième près.
- [x] Les 120 questions de test libre sont chargées et testables via les routes d'entraînement.
- [x] Les extraits de code s'affichent avec une indentation propre et une coloration syntaxique fidèle.
- [x] Suite de tests unitaires validée (`pytest tests/test_phase2.py`).

---

## 📌 Phase 3 : Interface Étudiant d'Examen & Dispositif Anti-Triche

### 3.1. Objectifs & Livrables
* Interface web du terminal étudiant en **Vanilla JS / Web Components** (100% en Français, zéro dépendance externe).
* Palette de navigation libre : grille de questions, marquage pour relecture, indicateurs d'état en direct.
* Système d'auto-sauvegarde instantanée des réponses (avec mise en cache locale en cas de coupure réseau).
* **Dispositif Anti-Triche côté client :**
  * Verrouillage du mode plein écran HTML5 dès le début de l'épreuve.
  * Blocage absolu du copier/coller (`Ctrl+C`, `Ctrl+V`), du clic droit et de la sélection de texte.
  * **Règle des 10 secondes d'absence :** Compteur automatique si sortie de plein écran ou changement d'onglet ; verrouillage immédiat sur écran rouge de suspension si $>10$ secondes.
* Affichage du compte à rebours global avec **alerte rouge de grâce de 60 secondes** à l'approche de la fin.
* Écran de fin d'examen avec affichage immédiat de la note finale obtenue (sans révélation du corrigé).

### 3.2. Critères de Validation (Validation Gate 3)
- [x] Le passage en plein écran est immédiat et ergonomique.
- [x] Si l'étudiant quitte le plein écran pendant 11 secondes, l'écran de suspension apparaît et bloque toute interaction.
- [x] Si le câble réseau est débranché pendant 15 secondes mais que l'étudiant reste en plein écran, l'épreuve continue normalement et les réponses se synchronisent dès le rebranchement.
- [x] Le redémarrage de la machine ou le rafraîchissement du navigateur restaure immédiatement la session avec les réponses sauvegardées.

---

## 📌 Phase 4 : Dashboard Enseignant de Surveillance en Temps Réel

### 4.1. Objectifs & Livrables
* Tableau de bord de proctoring en direct inspiré de `oldapps/AlgoCompilerv2/AlgoCompilerv2/AlgoExamination` :
  * Grille visuelle des postes étudiants connectés dans la salle.
  * Télémétrie en direct via WebSockets : statut de connexion, question active, barre de progression, état de sécurité (🟢 Normal, 🟡 Focus Warning, 🔴 **Suspendu**).
* **Système de Lancement Synchronisé :**
  * Salle d'attente pour les étudiants.
  * Bouton enseignant *"Lancer l'Épreuve"* démarrant simultanément l'examen pour toute la salle.
* **Barre d'Actions Administrateur / Surveillant :**
  * Bouton **"Débloquer" en 1 clic** pour réactiver instantanément un étudiant suspendu.
  * Bouton d'ajout de temps additionnel (+5 min, +10 min, sur-mesure) individuel ou collectif.
  * Soumission forcée et mise en pause d'une tentative.
* Journal d'audit chronologique infalsifiable des alertes et actions du surveillant.

### 4.2. Critères de Validation (Validation Gate 4)
- [x] La latence de transmission des événements entre le poste étudiant et le dashboard enseignant est inférieure à 300 ms en réseau local.
- [x] Le clic sur "Lancer l'Épreuve" débloque tous les postes étudiants connectés de manière synchrone.
- [x] Le clic sur "Débloquer" réactive immédiatement le terminal d'un étudiant suspendu.
- [x] L'attribution de +5 minutes met à jour le chronomètre de l'étudiant en direct.

---

## 📌 Phase 5 : Synchronisation Manuelle par Clé USB & Consolidation Master

### 5.1. Objectifs & Livrables
* **Moteur d'Export / Import de Sujets (Option B) :**
  * Génération de l'archive compressée `.exam.zip` sur le Master (questions, options, consignes, médias).
  * Interface d'import web sur le serveur de salle permettant le chargement de l'examen via clé USB.
* **Moteur d'Export / Import de Résultats :**
  * Génération de l'archive `.results.zip` et du tableur `.csv` sur le serveur de salle après l'examen.
  * Module de téléversement et de fusion sur le Master : importation idempotente (aucun doublon en cas de ré-import).
* **Consolidation & Statistiques :**
  * Synthèse globale des notes par groupe et par module (`notes_consolidees.csv`).
  * Calcul des métriques statistiques : moyenne, médiane, écart-type, taux de réussite par question, détection des anomalies de temps de réponse.

### 5.2. Critères de Validation (Validation Gate 5)
- [x] Un examen exporté du Master sous `.exam.zip` s'importe en moins de 5 secondes sur un serveur de salle vierge.
- [x] Les résultats de 2 salles distinctes sont importés et réconciliés sur le Master sans conflit d'identifiants.
- [x] Ré-importer le même fichier de résultats n'altère pas les données (idempotence vérifiée).

---

## 📌 Phase 6 : Module d'Entraînement Évolutif Python (Pyodide Sandboxed)

### 6.1. Objectifs & Livrables
* Récupération et intégration du contenu pédagogique et des chapitres de `oldapps/QuizApp`.
* Intégration de l'interpréteur Python dans le navigateur via **Pyodide (WebAssembly)** :
  * Fichiers Pyodide embarqués localement pour fonctionnement 100% hors-ligne.
  * Exécution au sein d'un **Web Worker** isolé pour ne jamais bloquer l'interface utilisateur.
  * Minuteur de sécurité (Watchdog 5 secondes) pour interrompre les boucles infinies de code étudiant.
* **Mode Évolution :** Calcul dynamique du niveau de l'étudiant et proposition d'exercices adaptés en fonction de ses réussites précédentes.

### 6.2. Critères de Validation (Validation Gate 6)
- [x] L'étudiant peut exécuter du code Python dans son navigateur sans aucune connexion Internet.
- [x] Un script contenant une boucle infinie (`while True: pass`) est stoppé proprement après 5 secondes sans figer le navigateur.
- [x] Le serveur backend ne subit aucune charge processeur lors des exécutions de code étudiant.
- [x] La progression par chapitre enregistre correctement les jalons franchis.

---

## 📌 Phase 7 : Conteneurisation Docker Turnkey & Tests de Charge

### 7.1. Objectifs & Livrables
* Création du fichier `docker-compose.yml` tout-en-un pour le déploiement immédiat :
  * Conteneur Backend FastAPI.
  * Conteneur Base de Données (PostgreSQL ou volume SQLite WAL monté).
  * Serveur statique de distribution du Frontend.
* Script de démarrage simplifié (`lancer_serveur_salle.bat` / `.sh`).
* **Test de Charge Réaliste :**
  * Simulation de 30 clients simultanés envoyant des requêtes de télémétrie WebSocket et d'auto-sauvegarde toutes les 5 secondes.
  * Vérification de l'empreinte mémoire et CPU sur une machine standard de salle de TP.
* Rédaction du guide d'exploitation pour les enseignants et les surveillants.

### 7.2. Critères de Validation (Validation Gate 7)
- [x] La commande `docker compose up -d` démarre l'ensemble de la pile applicative en moins de 30 secondes.
- [x] 30 connexions simultanées n'entraînent aucun ralentissement, ni latence WebSocket perceptible.
- [x] Recette fonctionnelle de bout en bout validée par l'utilisateur.

---

## 📌 Phase 8 : Révisions Spécialités, Mots de Passe & Gestion des Bulletins (REV-41 à REV-47)

### 8.1. Objectifs & Livrables
* Épuration du Centre d'Entraînement Python (retrait badges / XP / gamification).
* Remplacement complet de la terminologie « Groupe » par « Spécialité » (`DEV-IA`, `SYS-ADMIN`, `CYBER-SEC`).
* Mots de passe en clair (`plain_password`) dans le CRUD Admin et import CSV avec auto-détection de délimiteur.
* Cursus académique structuré avec Algorithmique (`ALGO`) en tronc commun et modules de spécialité.
* Gestion des Bulletins Académiques : synthèse des 4 piliers + 2 examens, moyenne générale /20 et verdict d'admission.
* Amorçage de données réalistes pour 12 étudiants types et validation sous forte charge.
* Exportation multiformat des bulletins : PDF officiel, Word DOCX, archive groupée ZIP et palmarès de promotion trié par module.

### 8.2. Critères de Validation (Validation Gate 8)
- [x] La gestion des bulletins calcule la moyenne et le verdict jury avec exactitude.
- [x] L'export individuel et collectif fonctionne en PDF, Word (.docx) et archive ZIP.
- [x] Le palmarès par spécialité trie fidèlement les promotions selon n'importe quel module choisi.
- [x] Suite de tests automatisés validée (`pytest tests/test_phase8_revisions.py`).

---

## 📌 Phase 9 : Analyse Psychométrique, Synchronisation USB & Gestionnaire Web de Questions (REV-48 à REV-50)

### 9.1. Objectifs & Livrables
* **Analyse Psychométrique des Épreuves (Item Analysis) :**
  * Calcul de la moyenne, médiane, écart-type $\sigma$ et taux d'admission.
  * Calcul de l'Indice de Discrimination $D = P_U - P_L$ (règle des 27% de Kelley) et qualification psychométrique.
  * Détection automatique des questions anormales ($D < 0$ ou $P = 0\%$) avec bannière d'alerte et export CSV UTF-8 BOM.
* **Synchronisation Manuelle Hors-Ligne par Clé USB (Option B) :**
  * Export de sujet `.exam.zip` (manifeste JSON + empreinte SHA-256) et import sécurisé sur serveur de salle.
  * Export des résultats de session `.results.zip` (soumissions, réponses, logs d'audit) et import idempotent consolidé sur l'instance Master.
* **Gestionnaire Web de Questions & Banques d'Épreuves :**
  * Modale interactive `#modal-manage-questions` listant les questions d'une épreuve avec prévisualisation Markdown.
  * Éditeur visuel `#modal-edit-question` supportant les 5 types (`boolean`, `single_choice`, `multi_choice`, `fill_blank`, `matching`) avec options dynamiques, barèmes et pénalités.
  * Importation et exportation massives de questionnaires au format JSON.

### 9.2. Critères de Validation (Validation Gate 9)
- [x] L'analyse psychométrique calcule des indices $D$ exacts et qualifie fidèlement le pouvoir discriminant de chaque question.
- [x] Le flux complet d'export/import de package `.exam.zip` et `.results.zip` est 100% idempotent et vérifie l'empreinte SHA-256.
- [x] La création, modification et suppression de questions via l'éditeur web s'exécute sans rechargement de page.
- [x] Suite complète de 78 tests automatisés validée sans aucune régression (`pytest tests/test_phase9_features.py`).

