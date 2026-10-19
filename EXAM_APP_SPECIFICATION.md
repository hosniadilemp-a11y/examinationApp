# Cahier des Charges & Spécifications Logicielles (SRS)
# Plateforme d'Examen et d'Entraînement Multi-Modules (LAN Distribué)

**Statut du Document :** Spécification Finale & Validée (Post-Interview / Zéro Ambiguïté)  
**Environnement Réseau :** Réseau Local Déconnecté / LAN Hors-ligne (Salles de TP isolées)  
**Modèle d'Architecture :** Serveurs de Salles Indépendants (Option B) avec Consolidation Master  
**Stack Technique :** Python FastAPI + PostgreSQL + Interface Web Moderne (Déploiement Docker Compose)  
**Langue de l'Interface :** 100% Français (Interface, notifications, alertes et rapports)

---

## 1. Résumé Exécutif & Objectif

L'objectif est de développer une plateforme web moderne et robuste d'examen et d'entraînement fonctionnant intégralement en réseau local (LAN). Le système répond aux besoins des établissements universitaires à travers différents modules et cours, avec gestion des rôles pour les Super Administrateurs, les Enseignants et les Étudiants.

L'application est conçue pour des **salles informatiques distribuées et autonomes (Option B)** : chaque salle physique dispose de son propre serveur local. Les examens sont préparés sur le Master ou localement, transférés aux serveurs de salle par import manuel (clé USB), et les résultats finaux sont exportés puis consolidés sur l'instance centrale Master.

---

## 2. Architecture Système & Topologie de Salles (Option B)

```
┌────────────────────────────────────────────────────────────────────────┐
│                        INSTANCE MASTER (Centrale)                      │
│  - Docker Compose: Backend FastAPI + PostgreSQL + Frontend Web         │
│  - Super Admin & Gestion Globale (Utilisateurs, Groupes, Modules)      │
│  - Génération & Téléchargement Web des Packages d'Examen (.exam.zip)   │
│  - Consolidation Master des Résultats (Par examen ou Global)           │
│  - Imports / Exports CSV Globaux & Rapports Institutionnels            │
└───────────────────▲───────────────────────────────▲────────────────────┘
                    │                               │
           Clé USB Manuelle                Clé USB Manuelle
     (Téléchargement / Dépôt Web)    (Téléchargement / Dépôt Web)
                    │                               │
                    ▼                               ▼
┌──────────────────────────────────────┐  ┌──────────────────────────────────────┐
│        SERVEUR SALLE A (Local)       │  │        SERVEUR SALLE B (Local)       │
│  - Déploiement Docker Compose        │  │  - Déploiement Docker Compose        │
│  - Serveur Web Local FastAPI         │  │  - Serveur Web Local FastAPI         │
│  - Base de Données Locale PostgreSQL │  │  - Base de Données Locale PostgreSQL │
│  - Monitoring Temps Réel WebSocket   │  │  - Monitoring Temps Réel WebSocket   │
│  - Roster Local & Authentification   │  │  - Roster Local & Authentification   │
└──────────────────▲───────────────────┘  └──────────────────▲───────────────────┘
                   │                                         │
       Sous-réseau Salle (Wi-Fi/LAN)             Sous-réseau Salle (Wi-Fi/LAN)
                   │                                         │
    ┌──────────────┴──────────────┐           ┌──────────────┴──────────────┐
    ▼                             ▼           ▼                             ▼
[Terminal Étudiant 1]   [Terminal Étudiant 2] [Terminal Étudiant 1] [Terminal Étudiant 2]
(Navigateur Web Client) (Navigateur Web Client) (Navigateur Web Client) (Navigateur Web Client)
```

### 2.1. Indépendance Totale des Salles
* Chaque salle fonctionne de manière 100% étanche sur son serveur local via `docker compose up`.
* Une coupure réseau ou panne matérielle dans une salle n'impacte jamais les autres.
* Aucune connexion Internet n'est requise pendant le déroulement des examens.

### 2.2. Synchronisation Manuelle par Clé USB
* **Distribution des Examens :** Les épreuves finalisées sont packagées sous forme d'archives compressées (`.exam.zip`) depuis l'interface web Master, puis importées sur les serveurs de salle via l'interface web d'administration à partir d'une clé USB.
* **Consolidation des Résultats :** À la fin de la séance, les enseignants exportent les résultats (soit pour un examen spécifique, soit pour l'ensemble des examens de la salle) sous forme de bundle (`.results.zip` / `.csv`) via l'interface web, puis les injectent dans le Master pour centralisation des notes.

---

## 3. Stack Technique & Déploiement

* **Backend :** **Python FastAPI** — framework asynchrone haute performance, typage strict Pydantic, gestion native des WebSockets pour le monitoring en direct, et documentation OpenAPI interactive.
* **Base de Données :** **PostgreSQL** standardisé sur tous les nœuds (Master et serveurs de salle), conteneurisé sous Docker.
* **Frontend :** Application Web monopage moderne (HTML5, Vanilla CSS / composants modulaires, JavaScript dynamique) intégrant le rendu Markdown et la coloration syntaxique de code.
* **Conteneurisation :** Fichier `docker-compose.yml` prêt à l'emploi regroupant FastAPI, PostgreSQL et le serveur Web statique/Vite.
* **Langue :** Interface utilisateur, boutons, consignes, alertes et rapports d'évaluation **100% en Français**.

---

## 4. Gestion des Utilisateurs & Organisation Pédagogique

### 4.1. Authentification
* **Identifiants Complets :** Connexion par **Nom d'utilisateur & Mot de passe** pour tous les profils (Admins, Enseignants, Étudiants).
* **Import Initial :** Intégration en masse des comptes étudiants et enseignants via fichiers CSV par le Super Administrateur.

### 4.2. Organisation des Étudiants par Groupes
* Les étudiants sont rattachés à des **Groupes** (ex: *Groupe 1*, *Groupe 2*, *TD-A*, *TP-B*).
* La planification et l'affectation des examens s'effectuent directement par Groupe.

### 4.3. Matrice des Droits

| Fonctionnalité | Super Administrateur | Enseignant | Étudiant |
| :--- | :---: | :---: | :---: |
| Gestion Globale Utilisateurs & Groupes | ✅ Total | ❌ Aucun | ❌ Aucun |
| Gestion des Cours & Modules | ✅ Total | ❌ Affectés uniq. | ❌ Consultation |
| Création & Édition de Questions (JSON / Interface) | ✅ Total | ✅ Modules affectés | ❌ Aucun |
| Planification & Lancement par Groupe | ✅ Total | ✅ Modules affectés | ❌ Aucun |
| Dashboard de Surveillance en Temps Réel | ✅ Total | ✅ Ses sessions | ❌ Aucun |
| Déblocage à Distance des Étudiants Suspendus | ✅ Total | ✅ 1-Clic Dashboard | ❌ Aucun |
| Consultation des Notes & Analyses Statistiques | ✅ Total | ✅ Ses sessions | ❌ Sa note uniq. |
| Import / Export CSV (Utilisateurs, Groupes, Notes) | ✅ Total | ✅ Export résultats | ❌ Aucun |
| Import / Export Packages Synchronisation USB | ✅ Total | ✅ Niveau salle | ❌ Aucun |
| Mode Entraînement Évolutif Python | ✅ Total | ✅ Total | ✅ Accès libre |
| 4 Tests d'Entraînement Libres (24h/24) | ✅ Total | ✅ Total | ✅ Accès libre |
| Interface de Passage d'Examen Officiel | ❌ Non | ❌ Non | ✅ Selon Groupe |

---

## 5. Moteur de Questions, Navigation & Évaluation

### 5.1. Typologie des Questions
1. **Vrai / Faux (Oui/Non) :** Choix binaire.
2. **QCM à Réponse Unique :** 1 seule bonne réponse parmi $N$ options.
3. **QCM à Réponses Multiples :** Plusieurs bonnes réponses (ou aucune bonne réponse).
4. **Texte à Trou (Fill-in-the-Blank) :** Saisie directe avec normalisation des espaces et insensibilité optionnelle à la casse.
5. **Appariement / Correspondance (Matching) :** Association interactive entre deux colonnes d'éléments.
6. **Support du Code Informatique :** Rendu Markdown enrichi avec **coloration syntaxique** pour les blocs de code (Python, C, Bash, SQL, etc.).

### 5.2. Déroulement de l'Examen : Lancement Synchronisé & Navigation Libre
* **Lancement Synchronisé par l'Enseignant :**
  * Les étudiants se connectent et patientent dans une **Salle d'Attente ("En attente du lancement par l'enseignant")**.
  * Sur son écran de monitoring, l'enseignant visualise la liste des étudiants connectés prêts dans la salle.
  * L'enseignant clique sur **"Lancer l'Épreuve"** pour démarrer le chronomètre simultanément pour toute la salle.
* **Palette de Navigation Libre :**
  * Les étudiants disposent d'une grille interactive des questions (accès direct à n'importe quelle question, aller-retour libre).
  * Possibilité de marquer une question pour relecture ultérieure.
  * Indicateurs visuels d'état : *Répondue*, *Marquée pour relecture*, *Non visitée*.
* **Avertissement de Fin d'Épreuve (Grace Warning de 60 secondes) :**
  * Lorsque le compte à rebours global atteint `00:01:00`, le bandeau passe en rouge d'alerte.
  * À `00:00:00`, un compte à rebours de grâce de **60 secondes** permet une dernière relecture avant le verrouillage et la soumission automatique définitive.

### 5.3. Double Brassage Anti-Triche (Dual Shuffling)
* **Ordre des questions aléatoire :** Chaque étudiant reçoit les questions dans un ordre différent.
* **Ordre des options aléatoire :** Les propositions de réponse (A, B, C, D) sont mélangées aléatoirement pour chaque étudiant afin d'empêcher la copie visuelle sur les écrans voisins.

### 5.4. Barème Granulaire & Pénalités Personnalisables
* **Crédit Partiel avec Pénalité Négative :**
  * Pour les questions à choix multiples complexes, chaque bonne réponse cochée apporte des points positifs, tandis que chaque mauvaise réponse cochée retranche une pénalité paramétrable.
  * Plancher de note par défaut à `0` (évite les scores négatifs sur une question).
* **Personnalisation par l'Enseignant :**
  * Définition d'un barème par défaut au niveau de l'examen.
  * Surcharge possible question par question (points, pénalité négative, temps indicatif).

### 5.5. Restitution Immédiate de la Note
* Dès la soumission (ou à l'expiration du temps), la **note finale** (ex: `15.5 / 20`) s'affiche immédiatement à l'écran de l'étudiant.
* Le corrigé détaillé et les réponses exactes demeurent masqués pour préserver l'étanchéité des sujets entre les différentes vagues d'examen.

---

## 6. Dispositif Anti-Triche & Intégrité de l'Épreuve

### 6.1. Verrouillage du Poste Client
* **Plein Écran Obligatoire :** L'interface bascule en mode plein écran HTML5 dès le démarrage. Toute sortie de plein écran déclenche une alerte immédiate.
* **Bloquage du Presse-papier :** Désactivation complète des raccourcis de copie/collage (`Ctrl+C`, `Ctrl+V`, `Cmd+C`, `Cmd+V`), du clic droit contextuel et de la sélection de texte hors zones de saisie prévues.
* **Interception des Clics Non Autorisés :** Les clics en dehors des zones interactives d'examen sont bloqués et tracés.

### 6.2. Règle des 10 Secondes d'Absence : Suspension Automatique
* **Détection de Sortie :** Si un étudiant quitte le plein écran, réduit la fenêtre ou change d'onglet pendant **plus de 10 secondes consécutives** :
  * Le terminal d'examen est **instantanément bloqué et Suspendu**.
  * Un écran rouge de sécurité s'affiche : *"Épreuve Suspendue : Sortie d'écran non autorisée détectée (>10s). Veuillez contacter votre surveillant."*
  * Les réponses saisies jusqu'à cet instant sont conservées en base de données.
* **Déblocage à Distance par l'Enseignant :**
  * L'enseignant voit apparaître une alerte rouge clignotante **Suspendu** sur la carte de l'étudiant dans son dashboard de monitoring.
  * L'enseignant clique sur le bouton **"Débloquer"** directement depuis son interface web : l'écran de l'étudiant se réactive instantanément via WebSocket sans déplacement physique nécessaire.

### 6.3. Tolérance aux Coupures Réseau & Reconnexion Transparente
* **Cache Local & Tolérance aux Micro-coupures Réseau :** Si une perte de liaison réseau survient mais que l'étudiant reste dans l'application en plein écran, le test n'est **pas suspendu**. Les réponses sont stockées localement en cache navigateur et synchronisées automatiquement dès le rétablissement de la liaison.
* **Reprise Après Crash / Reboot / Rafraîchissement :** Si la machine plante ou redémarre, l'étudiant se reconnecte simplement avec son nom d'utilisateur et son mot de passe : l'épreuve reprend exactement là où elle en était avec les réponses sauvegardées et le temps restant exact.
* **Exclusion Explicite :** **Aucune empreinte matérielle intrusive (machine footprint)** n'est collectée.

### 6.4. Interface de Surveillance en Direct (Référence : `AlgoExamination`)
Reprise de la mise en page éprouvée de `oldapps/AlgoCompilerv2/AlgoCompilerv2/AlgoExamination` :
* **Grille de Cartes Étudiants en Direct :**
  * État de connexion (En ligne, Déconnecté, En attente).
  * Statut de Sécurité : 🟢 Normal, 🟡 Alerte Focus, 🔴 **Suspendu (>10s d'absence)**.
  * Progression en temps réel (ex: 18/30 questions traitées, pourcentage).
  * Temps écoulé et temps restant.
* **Barre d'Actions Surveillant :**
  * **Déblocage 1-Clic** des étudiants suspendus.
  * Ajout de temps supplémentaire (+5 min, +10 min, sur-mesure) individuel ou collectif.
  * Mise en pause / reprise d'un étudiant.
  * Soumission forcée en fin d'épreuve.

---

## 7. Tests d'Entraînement Libres (Accès Permanent 24h/24)

En complément des examens planifiés, la plateforme met à disposition **4 Tests Diagnostiques Gratuits** accessibles à **tous les étudiants à tout moment** en auto-formation :

| Module d'Entraînement | Volume de Questions | Thèmes Abordés | Disponibilité |
| :--- | :---: | :--- | :---: |
| **1. Bases d'Algorithmique** | **30 Questions** | Variables, conditions, boucles, fonctions récursives, complexité de base, tris et recherches. | Permanent (24h/24) |
| **2. Bases de Python** | **30 Questions** | Syntaxe, listes, dictionnaires, tuples, découpage de chaînes, fichiers, exceptions. | Permanent (24h/24) |
| **3. Bases de Cryptographie** | **30 Questions** | Chiffrement symétrique/asymétrique, hachage, César/Vigenère, clés publiques/privées, RSA, signatures. | Permanent (24h/24) |
| **4. Bases d'Administration Linux** | **30 Questions** | Arborescence de fichiers, permissions (`chmod`/`chown`), gestion des processus, filtres shell (`grep`, `find`), paquets. | Permanent (24h/24) |

* **Retour Pédagogique Immédiat :** Sur ces 4 tests libres, les étudiants bénéficient de la note immédiate, du corrigé complet avec explications pédagogiques pour chaque question.

---

## 8. Module Spécifique d'Entraînement Évolutif Python

* **Référence Logicielle :** Réplication de l'architecture d'entraînement de `oldapps/QuizApp`.
* **Fonctionnalités :**
  * **Entraînement par Chapitre :** Progression séquentielle sur les chapitres du cours de Python.
  * **Mode Évolution :** Adaptation de la difficulté en fonction du taux de réussite sur les exercices précédents.
* **Feuille de Route Pédagogique :**
  * Module Pilote Complet : **Initiation à Python** (Entraînement évolutif + Examens).
  * Modules Secondaires (Examens seuls au lancement initial) :
    * **Cryptographie**
    * **Administration des Systèmes Linux**

---

## 9. Répertoire des Composants Hérités à Réutiliser

| Source Héritée | Emplacement Cible | Éléments & Logique Réutilisés |
| :--- | :--- | :--- |
| `oldapps/AlgoCompilerv2/AlgoCompilerv2/AlgoExamination` | `core/monitoring/` & `client/teacher_monitor/` | Architecture UI de surveillance, télémétrie WebSocket, contrôles de suspension et d'ajout de temps, grille des cartes étudiants. |
| `oldapps/QuizApp/QuizApp/` | `core/training/` & `data/curriculum/python/` | Banque de données Python, chapitres, parseur de formats `.quiz`, algorithmes d'évolution de niveau. |
| `oldapps/TP_DM/` | `client/student_exam/` & `core/exam_engine/` | Formats d'évaluation continue, calcul des scores, dispositions ergonomiques pour étudiants, auto-sauvegarde. |

---

## 10. Spécifications des Données d'Entrée & de Sortie

### 10.1. Schéma d'Import CSV (Administration)
* `students.csv` : `student_id, username, password_hash, full_name, email, group_id, group_name`
* `teachers.csv` : `teacher_id, username, password_hash, full_name, email, assigned_modules`
* `groups.csv` : `group_id, group_name, description`
* `modules.csv` : `module_code, module_name, description`

### 10.2. Schéma JSON de Création d'Examen
Format JSON standardisé supportant :
* `type` (`boolean`, `single_choice`, `multi_choice`, `fill_blank`, `matching`)
* `prompt` (rendu Markdown et blocs de code)
* `options` et `correct_keys`
* `scoring` (`points`, `negative_penalty`, `partial_credit_enabled`)
* `time_limit_seconds` (temps indicatif optionnel par question)

### 10.3. Formats d'Exportation & Consolidation
* Export individuel d'un examen ou export global de l'ensemble des examens d'une salle sous archive `.results.zip` et tableur `.csv`.
* Le module Master reconcilie les fichiers de salle dans une feuille unifiée (`notes_consolidees.csv`) et génère les statistiques détaillées (moyennes de salle, écarts-types, indice de discrimination des questions, journal des suspensions pour tentative de triche).
