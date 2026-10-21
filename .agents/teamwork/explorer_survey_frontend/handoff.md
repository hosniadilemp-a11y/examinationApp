# Rapport de Synthèse & Recommandations : Architecture Frontend & Intégration AlgoCompiler

**Auteur** : Frontend & AlgoCompiler Explorer  
**Date** : 2026-10-20  
**Emplacement** : `c:\Users\adel\Documents\ExaminationQuiz APP\.agents\teamwork\explorer_survey_frontend\handoff.md`  
**Projet** : ExaminationQuiz APP (Plateforme d'Examen et Tests de Niveau LAN)  
**Référence Externe Analysée** : `oldapps/AlgoCompilerv2` (`challenge.html`, `challenge.css`, `algo-hints.js`, `script.js`)

---

## 1. Observations

### 1.1 Organisation Actuelle du Codebase Frontend
L'application frontend est une Single Page Application (SPA) en JavaScript ES6 vanilla sans framework lourd (ni React, ni Vue), structurée autour de fichiers statiques montés à la racine `/` par FastAPI (`backend/app/main.py:456`) :

- **HTML Principal** : `frontend/index.html` (1 824 lignes, 107 Ko).
  - Déclare 10 vues principales `<main id="view-...">` commutées par `classList.toggle('active')` :
    1. `#view-login` (l. 92) : Écran de connexion avec conteneur d'erreur `#login-error`.
    2. `#view-dashboard` (l. 120) : Tableau de bord étudiant (KPIs, 4 piliers, examens officiels, tests de niveau).
    3. `#view-stats` (l. 227) : Statistiques détaillées de l'étudiant.
    4. `#view-python` (l. 312) : Centre d'entraînement Python (cursus par chapitres, 68 badges, historique).
    5. `#view-exam` (l. 525) : Déroulement d'épreuve (chronomètre, palette latérale, conteneur question).
    6. `#view-waiting-room` (l. 600) : Salle d'attente interactive avant synchronisation du surveillant.
    7. `#view-score` (l. 627) : Affichage des résultats post-épreuve et corrigé pédagogique.
    8. `#view-teacher` (l. 646) : Espace enseignant et gestion des épreuves.
    9. `#view-proctor-live` (l. 685) : Salle de surveillance et monitoring télémétrique en direct.
    10. `#view-admin` (l. 778) : Espace super-administrateur (statistiques, étudiants, enseignants, modules, examens, bulletins).
  - Déclare 15 modales d'interaction (`.modal-overlay`) :
    `#modal-exam-template-picker` (l. 1143), `#modal-python-config` (l. 1159), `#modal-practice-history` (l. 1198), `#modal-badges-gallery` (l. 1231), `#modal-python-history` (l. 1259), `#modal-submit-confirmation` (l. 1292), `#modal-create-custom-exam` (l. 1329), `#modal-admin-student` (l. 1425), `#modal-admin-teacher` (l. 1472), `#modal-admin-module` (l. 1509), `#modal-admin-assign-module` (l. 1538), `#modal-admin-bulletin` (l. 1569), `#modal-item-analysis` (l. 1600), `#modal-manage-questions` (l. 1683), `#modal-edit-question` (l. 1737).
  - Déclare un conteneur dédié aux toasts modernes (l. 89) :
    `<div id="app-toast-container" class="app-toast-container"></div>`.
  - Importe KaTeX (`katex.min.js`, `auto-render.min.js`) et CodeMirror 5 (`codemirror.min.js`, `python.min.js`, `closebrackets.min.js`, `matchbrackets.min.js`, `show-hint.js`, `python-hint.js`).

- **Feuille de Style** : `frontend/css/style.css` (2 948 lignes, 62 Ko).
  - Contient les styles de base, thèmes, cartes d'examens, badges, grilles et tables.
  - Définit les classes du système de toast moderne aux lignes 2763-2843 (`.app-toast-container`, `.app-toast`, `.toast-success`, `.toast-danger`, `.toast-warning`, `.toast-info`, `@keyframes slideToastIn`).
  - Définit les styles de la mise en page deux colonnes aux lignes 2330-2560 (`.challenge-layout`, `.problem-pane`, `.split-pane-divider`, `.editor-pane`, `.editor-toolbar`, `.editor-status-bar`, `.h-splitter`, `.bottom-pane`, `.tabs-header`, `.tab-content`).
  - Définit les règles adaptatives du mode programmation aux lignes 338-353 (`.exam-layout.coding-mode`).

- **Scripts Clients** :
  - `frontend/js/api.js` (652 lignes) : Client HTTP singleton (`ApiClient`), gestion des jetons JWT, requêtes REST, gestion du mode hors ligne et des événements d'authentification (`auth:expired`).
  - `frontend/js/app.js` (4 930 lignes) : Contrôleur frontal central (`AppController`), routage, gestionnaires d'événements, rendu des vues enseignant/étudiant/admin.
  - `frontend/js/exam-runner.js` (1 306 lignes) : Moteur d'exécution des examens et entraînements (`ExamRunner`), affichage des questions par type, palette, intégration CodeMirror, console E/S, et exécution de tests.
  - `frontend/js/anticheat.js` (343 lignes) : Gestionnaire de sécurité anti-triche (`AntiCheatManager`), détection de perte de focus (`blur`), changement d'onglet (`visibilitychange`), sortie plein écran, compte à rebours 10 secondes avec suspension `AWAY_10S`, blocage copier-coller et raccourcis.
  - `frontend/js/pyodide-runner.js` & `pyodide-worker.js` : Exécution Python in-browser via WebAssembly / Web Worker pour le mode entraînement local.
  - `frontend/vendor/codemirror/addon/hint/python-hint.js` (248 lignes) : Fournisseur de complétion automatique Python (mots-clés, builtins, bibliothèques scientifiques, snippets).

---

### 1.2 Analyse Approfondie de la Référence `oldapps/AlgoCompilerv2`
L'inspection des fichiers sources de la référence `oldapps/AlgoCompilerv2/AlgoCompilerv2/AlgoCompiler/src/web/` (`templates/challenge.html`, `static/css/challenge.css`, `static/algo-hints.js`, `static/script.js`) révèle les mécanismes clés suivants :

1. **Agencement Two-Pane Homogène** :
   - Structure flexbox `challenge-layout` divisée en deux panneaux (`problem-pane` et `editor-pane`) séparés par un séparateur vertical draggable (`#vertical-splitter`, classe `.split-pane-divider`).
   - Le panneau droit est sous-divisé en hauteur par un séparateur horizontal draggable (`#horizontal-splitter`, classe `.h-splitter`) séparant l'éditeur supérieur (`editor-wrapper`, min 30%, max 85%) et les onglets inférieurs (`bottom-pane`).
   - Les redimensionnements mettent à jour la géométrie des panneaux en pourcentages et appellent immédiatement `window.editor.refresh()` pour recalculer la mise en page CodeMirror sans scintillement.
2. **Rendu Mathématique KaTeX** :
   - Fonction `window.renderMathInElement(descEl, { delimiters: [{left: '$$', right: '$$', display: true}, {left: '$', right: '$', display: false}, {left: '\\(', right: '\\)', display: false}, {left: '\\[', right: '\\]', display: true}], throwOnError: false })`.
   - Boucle de résilience vérifiant la disponibilité de `window.renderMathInElement` avant déclenchement.
3. **Barre d'Outils et Barre d'État Éditeur** (`script.js:1479-1520`) :
   - Outils : Annuler (`undo`), Refaire (`redo`), Bascule de commentaire (`toggleComment`), Recherche (`find`), Remplacement (`replace`), Formatage (`formatAlgoCode`), Réinitialisation au modèle (`reset-template-btn`), Indicateur de modèle protégé (`template-lock-indicator`), Chronomètre.
   - Barre d'état en bas de l'éditeur : Position curseur (`Ln X, Col Y`), décompte de caractères et de lignes, bascule retour à la ligne (`Wrap`), ajustement dynamique de la taille de police (`A-`, `A+`, réinitialisation).
4. **Moteur d'Autocomplétion & Dictionnaires IntelliSense** (`algo-hints.js:1-622`) :
   - Enregistrement du helper CodeMirror via `CodeMirror.registerHelper("hint", "algo", function(cm, options) { ... })`.
   - Rendu visuel soigné des suggestions avec étiquettes badges distinctes :
     - `hint-badge-snippet` (`SNIP` : snippets de blocs d'instructions)
     - `hint-badge-keyword` (`KW` : mots-clés de contrôle)
     - `hint-badge-builtin` (`FN` : fonctions intégrées)
     - `hint-badge-variable` (`VAR` : variables déclarées)
     - `hint-badge-module` (`MODULE` : modules scientifiques importés)
   - Filtrage et tri par pertinence : correspondance exacte d'abord, priorité de type (variable > snippet > mot-clé > fonction > opérateur), puis ordre alphabétique.
   - Déclencheur automatique : écouteur `inputRead` sur frappe de caractères alphanumériques ou de point `.`, avec temporisation anti-rebond (300 ms), combiné au raccourci clavier standard `Ctrl-Space`.
5. **Rendu des Graphiques Scientifiques Headless** :
   - Côté backend (`backend/app/services/sandbox_runner.py:12-34`), injection automatique d'un hook `FIGURE_HOOK` interceptant les figures Matplotlib actives (`plt.get_fignums()`), encodage PNG en mémoire via `io.BytesIO()`, conversion base64 et émission encapsulée `__ALGO_FIGURES_JSON__:[...]`.
   - Extraction côté serveur et transmission dans le champ `figures: ["data:image/png;base64,..."]` de la réponse JSON.
   - Côté frontend (`exam-runner.js:656, 1002-1019`), conteneur `#console-figures` injectant des blocs d'images clairs sans rechargement.

---

### 1.3 Écarts Identifiés par Rapport aux Exigences R1-R7

| Réf. | Exigence du Cahier des Charges | État Observé dans le Code Actuel | Écart / Lacune Détectée |
| :--- | :----------------------------- | :-------------------------------- | :---------------------- |
| **R1** | **Two-Pane Coding & CodeMirror Autocomplete**<br>- Mise en page homogène sans double ascenseur<br>- Autocomplete Python natif (`Ctrl-Space` & auto-frappe)<br>- Rendu des graphiques headless base64<br>- Bouton retour pratique verbatim "Retourner au Centre d'Entraînement Python ➔" vers `#view-python` | - `.challenge-layout.fused-workspace` fixé avec `height: calc(100vh - 165px)` combiné aux marges externes de `.exam-main` (`height: calc(100vh - 64px)`), créant un risque de double scrollbar.<br>- `python-hint.js` implémente les dictionnaires mais les classes CSS `.hint-badge*` manquent dans `style.css`.<br>- Le bouton de retour affiche `⬅️ Retourner au Centre d'Entraînement Python` (`app.js:2114, 2276`) au lieu du texte exact demandé avec flèche droite. | **Écart de style & libellé** :<br>1. Hauteur flexbox du conteneur fused à calibrer avec `height: 100%` et `overflow: hidden`.<br>2. Manque de styles CSS pour `.hint-badge` et `.CodeMirror-hints`.<br>3. Uniformisation du libellé exact du bouton retour. |
| **R3** | **Distinction Théorique vs Pratique**<br>- Épreuve Théorique : questions non-code uniquement.<br>- Épreuve Pratique : défis de code Python uniquement.<br>- Interface de création s'adaptant dynamiquement au type sélectionné. | - Le modèle de données et le formulaire actuel (`#modal-edit-question`, l. 1750) proposent les 6 types indistinctement dans un menu déroulant unique.<br>- Aucun verrouillage n'empêche l'ajout de questions de code dans un examen théorique, ni l'inverse. | **Écart structurel** :<br>Le formulaire de création de questions doit filtrer les types admissibles selon la nature de l'épreuve (`exam.exam_type`). |
| **R4** | **Expérience Enseignant & Builder Dédié**<br>- Redesign `#view-teacher` : tableau responsive avec colonnes structurées (Titre, Module, Type, Durée, Questions, Points, Groupes, Actions directes).<br>- Page dédiée en 2 étapes : Étape 1 (Configuration générale), Étape 2 (Builder de questions intégré, total points en direct, réordonnancement). | - `#view-teacher` (l. 677) affiche une grille de cartes (`<div class="card-grid">`).<br>- La création d'examen se fait via une modale courte (`#modal-create-custom-exam`), tandis que les questions sont gérées dans une seconde modale séparée (`#modal-manage-questions`). | **Écart majeur d'ergonomie** :<br>1. Remplacer la grille de cartes par un tableau responsive complet à 8 colonnes.<br>2. Créer une interface d'édition/création d'examen pas-à-pas (Étape 1 : Métadonnées & type, Étape 2 : Questions intégrées avec validation immédiate). |
| **R5** | **États Cartes Étudiants & Anti-Triche**<br>- Épreuve en cours : "🔄 Rejoindre l'épreuve en cours ➔" (vert émeraude).<br>- Salle d'attente : "⏳ Rejoindre la salle d'attente ➔" (ambre).<br>- Non démarré : "Commencer l'épreuve ➔" (primaire).<br>- Verrouillage plein écran, détection de flou, suspension 10s et 403. | - `_loadOfficialExams` (`app.js:786-788`) génère uniquement "Reprendre mon épreuve ➔" ou "Commencer l'épreuve ➔", sans distinction de style pour la salle d'attente ni badge émeraude/ambre.<br>- `anticheat.js` gère déjà la suspension 10s et le backend renvoie bien 403 (`student_exam.py:267, 417`). | **Écart UI d'état** :<br>Mettre à niveau le rendu des boutons d'actions sur les cartes d'examens selon l'état `attempt_status` / `session_status`. |
| **R6** | **Toasts Modernes, Touche Échap & Connexion**<br>- Toasts modernes remplaçant les 45 `alert()` natifs.<br>- Fermeture immédiate de toutes les modales par touche `Escape` ou clic sur backdrop.<br>- Formulaire de connexion propre sans alerte navigateur.<br>- Correction du bug multi-enseignants `[object Object]`. | - Exactement 45 appels natifs `alert()` disséminés dans `app.js` et `exam-runner.js`.<br>- Le conteneur `#app-toast-container` et le CSS existent, mais la méthode `showToast()` n'a jamais été codée sur `AppController` !<br>- Aucun écouteur `keydown` sur `Escape` n'est enregistré pour fermer les modales actives.<br>- L'événement `auth:expired` déclenche un `alert()` natif au lieu d'une redirection fluide.<br>- `ModuleResponse` dans `backend/app/schemas.py:63` omet la sérialisation de la liste des enseignants, et `app.js:3637` tente d'accéder directement aux objets sans extraction de secours. | **Écart d'interactivité & robustesse** :<br>1. Implémenter `AppController.showToast(message, type, duration)`.<br>2. Remplacer tous les `alert(...)` par `this.showToast(...)`.<br>3. Ajouter l'écouteur universel de touche `Escape` et de clic sur backdrop pour toutes les modales.<br>4. Supprimer l'alerte sur `auth:expired`.<br>5. Corriger l'affichage des enseignants multi-affectés. |
| **R7** | **Tableau de Bord de Surveillance Proctor**<br>- Télémétrie temps réel des postes (connexion, battement de cœur, progression, temps restant).<br>- Journal des violations anti-triche.<br>- Actions individuelles et groupées (+5m, déblocage, clôture). | - `#view-proctor-live` (l. 685-775) et `_renderProctorOverviewData` (`app.js:2663-2850`) sont déjà très complets avec barre de progression, alertes et WebSocket.<br>- Seuls les retours d'actions surveillant utilisent encore des `alert()` natifs (l. 2543, 2557, 2559, 2808, 2823, 2837). | **Écart mineur** :<br>Remplacer les `alert()` de surveillance par des toasts de confirmation. |

---

## 2. Chaîne Logique (Logic Chain)

1. **Intégration Two-Pane sans Double Ascenseur (R1)** :
   - *Observation* : `frontend/css/style.css:2930` définit `.challenge-layout.fused-workspace` avec une hauteur fixe `calc(100vh - 165px)`. Or, le conteneur parent `.exam-main` dispose déjà de sa propre hauteur et d'un en-tête d'épreuve (`#exam-active-title`) et pied de page (`exam-runner.js:550`).
   - *Déduction* : Si la hauteur totale des enfants dépasse l'espace viewport, `.exam-main` déclenche une barre de défilement verticale globale alors que `.problem-pane` et `.editor-pane` possèdent déjà leurs barres de défilement internes, créant ainsi deux barres de défilement imbriquées.
   - *Conclusion* : Définir `.exam-layout.coding-mode #exam-question-container` avec `flex: 1; min-height: 0; display: flex; flex-direction: column;` et `.challenge-layout.fused-workspace` avec `height: 100%; flex: 1; min-height: 0; overflow: hidden;`. De cette manière, l'espace restant est exactement consommé sans jamais déborder du conteneur principal.

2. **Système de Notification Toast & Remplacement des `alert()` (R6)** :
   - *Observation* : `frontend/index.html:89` contient `<div id="app-toast-container" class="app-toast-container"></div>` et `frontend/css/style.css:2763-2843` fournit les styles CSS complets pour `.app-toast.toast-success`, `.toast-danger`, `.toast-warning`, `.toast-info`. Pourtant, `frontend/js/app.js` comporte 45 appels directs à `alert(...)`, et un appel à `this.showToast(...)` à la ligne 75 qui lève une exception d'exécution car la méthode n'existe pas.
   - *Déduction* : L'architecture de toasts a été préparée visuellement mais jamais raccordée dans la logique JavaScript.
   - *Conclusion* : Implémenter une méthode robuste `showToast(message, type = 'info', duration = 4000)` sur `AppController` et l'exporter globalement (par exemple sur `window.showToast`) afin qu'`exam-runner.js` et toutes les fonctions puissent notifier l'utilisateur de manière non-bloquante avec des icônes SVG/émojis et des animations fluides. Remplacer chaque appel à `alert()` par `showToast()`.

3. **Fermeture des Modales par la Touche Échap et Clic Backdrop (R6)** :
   - *Observation* : Dans `app.js:424-429`, la fermeture des modales n'est déclenchée que par le clic sur les éléments portant la classe `.modal-close-btn`. Aucun écouteur `document.addEventListener('keydown', ...)` ne vérifie `e.key === 'Escape'`, et aucun écouteur de clic sur `.modal-overlay` n'est en place.
   - *Déduction* : L'utilisateur ne peut fermer une modale qu'en ciblant précisément la petite croix "✕" ou le bouton "Annuler", ce qui contrevient aux standards d'accessibilité et à l'exigence R6.
   - *Conclusion* : Attacher au niveau global un écouteur `keydown` qui recherche `.modal-overlay.active` et retire la classe `.active` sur pression de la touche `Escape` (ou `Esc`). De même, pour chaque `.modal-overlay`, attacher un écouteur `click` fermant la modale si `e.target === modalOverlay`.

4. **Correction du Bug d'Affichage Multi-Enseignants `[object Object]` (R6)** :
   - *Observation* : Dans `app.js:3636-3638`, l'affichage des enseignants d'un module fait :
     `const teachersBadges = (m.teachers && m.teachers.length > 0) ? m.teachers.map(t => ... ${this._escapeHtml(t.full_name)} ...).join('') : ...`
     Or, dans `backend/app/schemas.py:63`, `ModuleResponse` ne possède pas le champ `teachers: Optional[List[UserResponse]] = []`. Si le backend renvoie un tableau d'identifiants bruts, d'objets sans `full_name`, ou si `m.teachers` est converti en chaîne dans d'autres contextes, l'évaluation JavaScript produit `[object Object]`.
   - *Déduction* : La chaîne de données est rompue à la fois côté sérialisation du backend et côté tolérance du frontend.
   - *Conclusion* : Sécuriser le gabarit d'affichage côté frontend pour gérer aussi bien les objets enseignant (`t.full_name || t.username || t.id`) que les identifiants simples, et veiller à ce que le schéma Pydantic `ModuleResponse` expose explicitement la liste des enseignants affectés.

5. **Refonte de la Vue Enseignant & Builder Pas-à-Pas (R3 & R4)** :
   - *Observation* : Actuellement, `#view-teacher` présente une simple grille de cartes (`card-grid`) ne permettant pas de visualiser d'un coup d'œil les 8 caractéristiques requises (Titre, Module, Type, Durée, Nombre de questions, Barème total, Groupes autorisés, Actions). De plus, la création d'épreuve est cloisonnée dans une modale sans éditeur de questions intégré.
   - *Déduction* : Pour respecter le cahier des charges R4 et R3, l'enseignant doit disposer d'un tableau synthétique ordonnable et d'une page dédiée d'édition d'épreuve guidée en deux étapes (Étape 1 : Paramétrage général dont le choix du type ; Étape 2 : Concepteur de questions qui exclut le type "coding" si l'épreuve est Théorique, ou qui force les défis de programmation avec tests publics/cachés si l'épreuve est Pratique).
   - *Conclusion* : Remplacer le conteneur `#teacher-exams-list` par une table de données responsive (`.table-responsive > table.data-table`), et créer la vue dédiée d'édition `#view-exam-builder` (ou étendre `#view-teacher` avec une sous-vue plein écran) orchestrant les Étapes 1 et 2 avec calcul dynamique du total des points.

6. **Distinction des Boutons d'Action sur les Cartes d'Examens Étudiants (R5)** :
   - *Observation* : Dans `app.js:784-789`, un examen non rendu génère un bouton bleu générique avec le texte `"Reprendre mon épreuve ➔"` ou `"Commencer l'épreuve ➔"`.
   - *Déduction* : L'étudiant ne perçoit pas visuellement la différence entre une épreuve déjà entamée (tentative active), une épreuve pour laquelle il est en salle d'attente (en attente du feu vert du surveillant), et une épreuve vierge.
   - *Conclusion* : Conditionner le style et le texte du bouton :
     - Si `ex.attempt_status === 'in_progress'` : Bouton vert émeraude (`background: #10b981; border-color: #059669;`) avec le texte `"🔄 Rejoindre l'épreuve en cours ➔"`.
     - Si `ex.session_status === 'waiting'` ou `ex.attempt_status === 'waiting'` : Bouton ambre (`background: #f59e0b; border-color: #d97706;`) avec le texte `"⏳ Rejoindre la salle d'attente ➔"`.
     - Sinon : Bouton primaire classique (`background: #2563eb;`) avec le texte `"Commencer l'épreuve ➔"`.

---

## 3. Caveats & Hypothèses

- **Mode d'Exécution Python Sandbox vs Pyodide** :
  Le backend dispose d'un exécuteur sandbox sous Linux/Windows (`backend/app/services/sandbox_runner.py`), tandis que le client intègre également Pyodide WebAssembly pour les entraînements locaux. Pour les examens officiels et les vérifications de tests cachés, l'évaluation doit impérativement s'exécuter côté serveur via l'API sécurisée (`/api/student/exams/{id}/save` et `/api/training/python/run-tests` avec `run_all=True`), sans jamais communiquer les sorties attendues des tests cachés au navigateur de l'étudiant.
- **Support des Terminaux Étroits (Tablettes/Mobiles)** :
  L'agencement Two-Pane à 50%/50% est optimal sur écran d'ordinateur (résolution >= 1024px). Sur les largeurs d'écran inférieures à 768px, la feuille de style doit basculer en disposition verticale empilée (`flex-direction: column`) pour préserver la lisibilité de l'énoncé et de l'éditeur.
- **Règles Anti-Triche en Entraînement vs Examen Officiel** :
  En mode test de niveau ou entraînement libre, la consultation de documentation externe est autorisée (pas de flou bloquant ni de pénalité sur perte de focus), alors qu'en examen officiel, le plein écran strict et la règle des 10 secondes d'absence avec suspension surveillant s'appliquent rigoureusement.

---

## 4. Conclusion & Plan d'Action Recommandé

L'analyse démontre que l'architecture technique existante est saine, riche et cohérente, mais souffre de plusieurs déconnexions ponctuelles entre les composants d'interface et les spécifications R1-R7.

### Plan de Mise en Œuvre Frontend Détaillé

#### Étape 1 : Système Global de Notifications Toast & Gestion des Modales (R6)
1. **Dans `frontend/js/app.js`** :
   - Ajouter la méthode `showToast(message, type = 'info', duration = 4000)` à la classe `AppController`.
   - Créer dynamiquement un élément `.app-toast.toast-${type}` avec son icône (succès `✅`, erreur `❌`, avertissement `⚠️`, info `ℹ️`), son texte échappé et son bouton de fermeture.
   - Remplacer l'ensemble des 45 occurrences de `alert(...)` par `this.showToast(...)` (ou `window.showToast(...)`).
   - Supprimer l'alerte bloquante sur l'événement `auth:expired` (l. 580) et la remplacer par un toast d'information discret suivi de `this.renderLogin()`.
   - Ajouter un écouteur global `keydown` sur la touche `Escape` pour fermer toute modale active `.modal-overlay.active`.
   - Ajouter un écouteur `click` sur chaque `.modal-overlay` fermant la modale si l'utilisateur clique sur l'arrière-plan semi-transparent.
2. **Dans `frontend/css/style.css`** :
   - Ajouter les styles complémentaires pour `.hint-badge` et `.CodeMirror-hints` importés d'AlgoCompilerv2.

#### Étape 2 : Deux Panneaux Fused & Autocomplétion CodeMirror (R1)
1. **Dans `frontend/css/style.css`** :
   - Ajuster `.challenge-layout.fused-workspace` : remplacer `height: calc(100vh - 165px)` par `height: 100%; flex: 1; min-height: 0; overflow: hidden;`.
   - Intégrer les styles d'autocomplétion `.hint-badge`, `.hint-badge-snippet`, `.hint-badge-keyword`, `.hint-badge-builtin`, `.hint-badge-module`, `.hint-badge-variable`, `.CodeMirror-hints`, et `.CodeMirror-hint-active`.
2. **Dans `frontend/js/exam-runner.js`** :
   - Calibrer les options CodeMirror `hintOptions` pour cibler explicitement le helper `python` enregistré par `python-hint.js`.
   - Renommer les boutons d'exécution du panneau inférieur pour correspondre au standard AlgoCompiler :
     - Bouton 1 : `"▶️ Exécuter avec Entrée"` (au lieu de `"Exécuter (stdin)"`).
     - Bouton 2 : `"⚡ Exécuter sur les Tests"` (au lieu de `"Tester ma Solution"`).
     - Bouton 3 : `"🚀 Soumettre la Solution"` (au lieu de `"Enregistrer"`).
   - Corriger l'appel à `api.runPythonTests` pour passer `exercise_id` et non la chaîne de code comme premier argument.
3. **Dans `frontend/js/app.js`** :
   - Mettre à jour les libellés de retour de session d'entraînement aux lignes 2114 et 2276 pour afficher verbatim :
     `"Retourner au Centre d'Entraînement Python ➔"`.

#### Étape 3 : Refonte de la Gestion Enseignant & Concepteur d'Épreuve (R3 & R4)
1. **Dans `frontend/index.html`** :
   - Remplacer `<div id="teacher-exams-list" class="card-grid"></div>` dans `#view-teacher` par une structure de table responsive :
     ```html
     <div class="table-responsive" style="margin-top:14px; background:var(--bg-surface); border:1px solid var(--card-border); border-radius:var(--radius-md); overflow-x:auto;">
       <table class="data-table" id="teacher-exams-table" style="width:100%; border-collapse:separate; border-spacing:0; text-align:left;">
         <thead>
           <tr>
             <th>Titre de l'Épreuve</th>
             <th>Module</th>
             <th>Type</th>
             <th>Durée</th>
             <th>Questions</th>
             <th>Barème</th>
             <th>Groupes Cibles</th>
             <th style="text-align:right;">Actions Directes</th>
           </tr>
         </thead>
         <tbody id="teacher-exams-table-body"></tbody>
       </table>
     </div>
     ```
   - Ajouter une vue ou un panneau dédié plein écran `#view-exam-builder` (ou intégrer un sous-module pas-à-pas) avec :
     - **Étape 1** : Titre, Module, Type d'épreuve (Théorique vs Pratique), Durée, Seuil de validation, Groupes autorisés, Options d'aléa et anti-triche.
     - **Étape 2** : Concepteur de questions intégré. Si "Théorique" : options QCM unique, QCM multiple, Vrai/Faux, Texte à trou, Appariement (type coding désactivé). Si "Pratique" : défis de programmation Python avec starter code, >= 2 tests publics et >= 10 tests cachés.
2. **Dans `frontend/js/app.js`** :
   - Mettre à jour `renderTeacherView()` pour peupler le tableau à 8 colonnes avec les boutons d'action : `Modifier Questions`, `Surveiller & Lancer`, `Exporter (.exam.zip)`, `Supprimer`.
   - Assurer la synchronisation dynamique du total des points et de la validation instantanée.

#### Étape 4 : États Visuels des Cartes Étudiants & Durcissement Anti-Triche (R5)
1. **Dans `frontend/js/app.js` (`_loadOfficialExams`)** :
   - Détecter si `ex.attempt_status === 'in_progress'` : bouton vert émeraude `"🔄 Rejoindre l'épreuve en cours ➔"`.
   - Détecter si `ex.session_status === 'waiting'` ou `ex.attempt_status === 'waiting'` : bouton ambre `"⏳ Rejoindre la salle d'attente ➔"`.
   - Détecter si non démarré : bouton primaire bleu `"Commencer l'épreuve ➔"`.
2. **Tolérance aux Reconnexions** :
   - Vérifier que l'état local (`localStorage` de l'examen courant) et le timer serveur synchronisé (`syncServerRemainingSeconds`) restaurent immédiatement la question active et les réponses saisies lors d'un rafraîchissement (`F5`).

#### Étape 5 : Correction du Bug Multi-Enseignants `[object Object]` (R6)
1. **Dans `backend/app/schemas.py`** :
   - Compléter `ModuleResponse` avec `teachers: Optional[List[UserResponse]] = []`.
2. **Dans `frontend/js/app.js` (`loadAdminModules` et modal d'affectation)** :
   - Extraire avec résilience le nom de l'enseignant :
     `const name = typeof t === 'object' ? (t.full_name || t.username || t.id) : String(t);`.

---

## 5. Méthode de Vérification Indépendante

Pour vérifier de façon reproductible et rigoureuse la conformité de l'interface :

1. **Exécution de la Suite de Tests Automatisée** :
   ```bash
   pytest tests/
   ```
   *Critère de succès* : 100% de passage sur l'ensemble des 85+ suites de test (notamment `test_sandbox_and_challenges.py`, `test_anticheat_telemetry.py`, `test_exams.py`, `test_modules_rbac.py`).

2. **Simulation Multi-Scénarios Bout-en-Bout** :
   ```bash
   python scripts/simulate_all_exam_scenarios.py
   ```
   *Critère de succès* : Exécution sans erreur des 10 scénarios complets d'évaluation (étudiant, enseignant, surveillant, administrateur).

3. **Inspection Visuelle et Validation des Éléments d'Interface (Navigateur)** :
   - Lancer l'application :
     ```bash
     uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
     ```
   - Ouvrir `http://127.0.0.1:8000/`.
   - **Vérification R1 & Autocomplete** : Ouvrir un défi Python dans le centre d'entraînement ou en examen. Vérifier la complétion `Ctrl-Space` et à la frappe (mots-clés, builtins, bibliothèques scientifiques) avec affichage des badges colorés. Exécuter un script avec `matplotlib.pyplot` et vérifier l'apparition immédiate de l'image PNG dans `#console-figures`. Vérifier que le bouton de fin d'entraînement porte le texte `"Retourner au Centre d'Entraînement Python ➔"` et ramène à `#view-python`.
   - **Vérification R3 & R4** : Se connecter en tant qu'enseignant (`prof.dupont` / `ProfPass123!`). Vérifier que `#view-teacher` affiche le tableau à 8 colonnes. Créer un examen théorique et vérifier l'inaccessibilité du type de question "coding" ; créer un examen pratique et vérifier la saisie obligatoire de >= 2 tests publics et >= 10 tests cachés.
   - **Vérification R5** : Se connecter en tant qu'étudiant (`etudiant.dev1` / `DevPass123!`). Vérifier les couleurs des boutons selon l'état (émeraude pour reprise, ambre pour salle d'attente, bleu pour débuter). Déclencher une sortie plein écran et vérifier le compte à rebours de 10 secondes et la suspension.
   - **Vérification R6** : Provoquer une action (sauvegarde, suppression, erreur de connexion) et vérifier qu'aucun popup `alert()` natif n'apparaît, mais qu'un toast élégant s'affiche en haut à droite. Ouvrir n'importe quelle modale et appuyer sur `Échap` : la modale doit se fermer immédiatement.
   - **Vérification R7** : Ouvrir la vue surveillant (`#view-proctor-live`) pendant qu'un étudiant est connecté : vérifier la mise à jour des jauges de progression, l'affichage du temps restant et le bon fonctionnement des actions surveillant (+5m, déblocage).

4. **Conditions d'Invalidation** :
   - Présence d'un appel natif `alert()` restant lors des interactions courantes.
   - Apparition de `[object Object]` dans la gestion des modules.
   - Double barre de défilement verticale visible dans l'environnement de code deux colonnes.
   - Impossibilité de fermer une modale avec la touche `Escape`.
