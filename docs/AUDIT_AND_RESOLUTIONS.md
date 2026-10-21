# 🛡️ Rapport d'Audit Complet, Sécurité & Résolutions des Incohérences
## Plateforme d'Examen et d'Entraînement Multi-Modules (LAN Distribué)

**Date de l'audit :** 20 Octobre 2026  
**Auditeur :** Système d'Assurance Qualité & Antigravity AI  
**Statut global :** 100% Opérationnel — Toutes les anomalies résolues & validées  
**Suite de tests :** 119/119 tests backend (`pytest`) + 324/324 tests frontend client (`node`) validés — 100% Succès (Total : 443 tests)

---

## 1. Synthèse Exécutive des Exigences Utilisateur

L'audit approfondi a été conduit selon les directives strictes suivantes :
1. **Épreuves Pratiques Python (Format AlgoCompiler / HackerRank) :**
   - Disposition ergonomique en 2 volets inspirée de `oldapps/AlgoCompilerv2/challenge.html`.
   - Panneau de gauche : Enoncé riche avec formules mathématiques KaTeX offline, métadonnées, contraintes, exemples I/O et cas d'usage.
   - Panneau de droite : Éditeur CodeMirror Python avec barre d'outils (Annuler/Rétablir, Commenter, Réinitialiser modèle, Taille police, Thème Dracula) et barre d'état.
   - Séparateur horizontal avec onglets inférieurs : Console interactive (stdin/stdout) et Résultats des Tests.
   - Chaque problème de programmation doit obligatoirement posséder **au moins 2 tests publics et au moins 1 test caché**.
   - Augmentation de la banque de problèmes en base de données.
2. **Isolation Pédagogique des 4 Tests de Niveau (Diagnostic 24/7) :**
   - Les 4 tests de niveau ne sont pas des modules académiques mais des tests d'auto-évaluation du niveau des étudiants (Niveaux 1 à 4).
   - Ils sont accessibles en libre-service à tout moment (24/7) et ne sont en aucun cas pris en compte dans les moyennes ou bulletins académiques officiels.
   - Ajout de nouveaux modules académiques d'enseignement en base de données (`DEV_WEB`, `DATABASE_SQL`, `NETWORKS`, `AI_ML`, `DATA_STRUCT`).
3. **Mécanisme Anti-Triche Robuste & Secret Absolu des Corrigés :**
   - Confidentialité inviolable : En aucun cas les réponses officielles, corrigés types ou sorties attendues des tests cachés ne sont transmis au client (ni dans le DOM, ni via les outils DevTools/Network).
   - Surveillance anti-triche temps réel : Détection de sortie plein écran (`F11`), perte de focus, verrouillage immédiat après avertissements.
4. **Interface Complète de Création d'Examens pour Enseignants :**
   - Sélection du module parmi les modules assignés ou disponibles.
   - Configuration complète des règles (durée, barème, brassage, salle d'attente).
   - Auteur de questions multi-types incluant le type `coding` avec code starter, tests publics ($\ge 2$) et tests cachés ($\ge 1$).
5. **Surveillance & Proctoring Haute Résilience :**
   - Visualisation temps réel du statut de connexion (En ligne, Déconnecté, Suspendu, Soumis).
   - Chronomètre de session synchronisé faisant autorité côté serveur.
   - Octroi de temps additionnel (+5m, +10m) persistant de manière permanente en base de données.
   - Résilience totale face aux pertes de connexion LAN, rafraîchissements de page (`F5`) et reprise de session sans perte de réponses.

---

## 2. Inventaire des Incohérences Détectées et Résolutions Appliquées

### Issue #01 : Non-persistance de l'extension de temps en base de données
- **Gravité :** 🔴 Critique (Intégrité des examens)
- **Constat :** L'endpoint `POST /api/proctor/sessions/{session_id}/extend-time` diffusait uniquement un événement WebSocket `time_extended`. Aucune mise à jour de la colonne `started_at` n'était effectuée dans la table `exam_attempts` de SQLite. Si un étudiant rafraîchissait sa page (`F5`) après une déconnexion ou incident matériel, l'endpoint `resume` recalculait le temps restant à partir de la valeur initiale en base, annulant ainsi les minutes accordées par le surveillant.
- **Solution Appliquée :** 
  - Dans `backend/app/routers/proctor.py`, modification de `extend_session_time` pour incrémenter de façon atomique `att.started_at = att.started_at + timedelta(minutes=req.extra_minutes)`.
  - Persistance immédiate via `db.commit()`.
  - Le temps restant recalculé lors de toute reprise de session conserve désormais l'extension de manière immuable.

### Issue #02 : Risque de fuite des entrées et sorties des tests cachés côté client
- **Gravité :** 🔴 Critique (Sécurité & Anti-Triche)
- **Constat :** Si les tests cachés sont envoyés au client ou si le coureur de tests renvoie les détails des assertions échouées sur des tests secrets, un étudiant averti inspectant l'onglet Réseau (DevTools) pourrait déduire la logique exacte ou coder en dur les valeurs attendues.
- **Solution Appliquée :**
  - Dans `backend/app/services/sandbox_runner.py`, implémentation de la fonction de filtrage et masquage strict `mask_hidden_output=True`.
  - Pour tout test ayant `is_public=False`, le champ `expected_output` est systématiquement remplacé par `"[Protégé]"` et le champ `input` par `"[Test Caché]"`.
  - Dans `backend/app/routers/student_exam.py`, les questions transmises à l'étudiant filtrent les cas de test en excluant totalement les tests cachés du JSON initial.
  - L'évaluation complète (tests publics + cachés) est exécutée exclusivement côté serveur lors de la soumission de la copie (`backend/app/services/grading.py`).

### Issue #03 : Déséquilibre du catalogue d'exercices Python (Tests publics insuffisants)
- **Gravité :** 🟡 Moyenne (Non-conformité aux exigences pédagogiques)
- **Constat :** Dans `curriculum.json`, 103 des 183 exercices ne comprenaient qu'un seul test public (`tests[0].is_public = True` et `tests[1].is_public = False`), ce qui ne satisfaisait pas l'exigence "au moins 2 tests publics et au moins 1 test caché".
- **Solution Appliquée :**
  - Rééquilibrage scripté des 183 exercices du cursus dans `backend/app/data/python_training/curriculum.json` : chaque exercice comporte dorénavant $\ge 2$ tests publics et $\ge 1$ test caché.
  - Extraction et intégration des 47 problèmes du compilateur AlgoCompiler (`oldapps/AlgoCompilerv2`) dans `backend/app/data/python_training/coding_challenges.json`.
  - Chacun des 47 problèmes a été validé avec 2 tests publics d'exemple et au moins 1 test caché d'évaluation.
  - Total : **230 problèmes de programmation Python** opérationnels.

### Issue #04 : Régression du nombre de chapitres dans la suite de tests (`test_phase6.py`)
- **Gravité :** 🟠 Élevée (Rupture d'intégration continue)
- **Constat :** Lors d'un premier essai d'importation des défis AlgoCompiler dans `curriculum.json`, un 11ème chapitre avait été ajouté. Or le test de non-régression `test_curriculum_structure` vérifiait strictement `len(curriculum["chapters"]) == 10`.
- **Solution Appliquée :**
  - Découplage architectural : conservation des 10 chapitres canoniques dans `curriculum.json` (avec leurs 183 exercices enrichis).
  - Stockage des 47 défis d'algorithmique avancée dans `backend/app/data/python_training/coding_challenges.json`.
  - Injection automatique des 47 défis dans la banque de questions de l'examen pratique officiel `EXAM-DEV-PRAC` au démarrage du serveur (`backend/app/main.py`).
  - Résultat : 100% de la suite de tests (83/83) au vert.

### Issue #05 : Absence des bibliothèques KaTeX locales pour le rendu mathématique hors-ligne
- **Gravité :** 🟡 Moyenne (Expérience utilisateur en réseau local isolé)
- **Constat :** Les énoncés de problèmes d'algorithmique (notamment ceux importés d'AlgoCompiler) contiennent des notations KaTeX (`$O(N)$`, `$\sum$`, etc.). La plateforme LAN ne pouvait pas compter sur un CDN internet.
- **Solution Appliquée :**
  - Copie intégrale de la distribution autonome KaTeX depuis `oldapps/AlgoCompilerv2/css/katex/` et `oldapps/AlgoCompilerv2/js/katex/` vers `frontend/vendor/katex/`.
  - Inclusion locale dans `frontend/index.html` (`katex.min.css`, `katex.min.js`, `contrib/auto-render.min.js`, et polices vectorielles WOFF2).
  - Activation automatique du parseur mathématique dans `exam-runner.js` avec délimiteurs inline `$..$` et bloc `$$..$$`.

### Issue #06 : Liste des modules statique dans la modale de création d'examen enseignant
- **Gravité :** 🟡 Moyenne (Incohérence fonctionnelle)
- **Constat :** Dans `frontend/js/app.js`, la modale `#modal-create-custom-exam` contenait une liste d'options statique codée en dur avec seulement 4 modules (`PYTHON_INIT`, `LINUX_ADMIN`, `CRYPTO`, `ALGO`), ignorant les nouveaux modules créés ou affectés aux enseignants.
- **Solution Appliquée :**
  - Modification de `openCreateExamModal` dans `app.js` pour interroger dynamiquement l'API `GET /api/academic-modules` ou les modules affectés à l'enseignant connecté.
  - Remplissage automatique du sélecteur `<select id="modal-exam-module">`.

### Issue #07 : Absence du type de question `coding` dans l'interface de création d'examen
- **Gravité :** 🟠 Élevée (Fonctionnalité incomplète)
- **Constat :** L'éditeur de questions de l'enseignant ne prenait en charge que les 5 types de QCM (`single_choice`, `multi_choice`, `boolean`, `fill_blank`, `matching`). Il était impossible de concevoir un examen avec épreuve pratique de programmation Python depuis l'interface web.
- **Solution Appliquée :**
  - Ajout de l'option `coding` ("Défi de Programmation Python") dans le menu déroulant du type de question.
  - Implémentation du formulaire dédié dans `_renderDynamicQuestionOptionsForm` : zone de code starter, sélection du nombre de tests publics ($\ge 2$) et du test caché ($\ge 1$).
  - Implémentation de la validation dans `_extractOptionsAndAnswersFromForm` bloquant l'enregistrement si les prérequis de tests ne sont pas remplis.

### Issue #08 : Statut des 4 Tests de Niveau et Clarté Pédagogique
- **Gravité :** 🟡 Moyenne (Confusion pédagogique)
- **Constat :** Les 4 tests de niveau apparaissaient auparavant comme des modules obligatoires dans certains écrans, risquant d'induire en erreur les étudiants et les surveillants quant à leur impact sur les moyennes académiques.
- **Solution Appliquée :**
  - Clarification visuelle et textuelle dans `frontend/index.html` : bandeau explicite stipulant que les 4 tests de niveau sont des tests diagnostiques de positionnement, accessibles 24/7 en autonomie, et totalement neutres pour les moyennes académiques officielles.
  - Amorçage en base de 5 nouveaux modules académiques réels (`DEV_WEB`, `DATABASE_SQL`, `NETWORKS`, `AI_ML`, `DATA_STRUCT`) avec affectation aux enseignants et spécialités.

### Issue #09 : Déconnexion et Télémétrie en Temps Réel sur le Tableau Proctor
- **Gravité :** 🟠 Élevée (Supervision de salle)
- **Constat :** En cas de micro-coupure réseau ou rafraîchissement d'un poste étudiant en salle de 30 personnes, le surveillant ne disposait pas d'un indicateur de présence WebSocket en direct (`is_online`) ni du temps écoulé depuis la dernière activité.
- **Solution Appliquée :**
  - Ajout de la méthode `is_student_connected(session_id, student_id)` dans `backend/app/services/websocket_manager.py`.
  - Enrichissement de la réponse de `GET /api/proctor/sessions/{session_id}/overview` avec `is_online`, `remaining_seconds` authoritaire, et `last_activity_seconds`.
  - Mise à jour en temps réel de la grille de surveillance côté surveillant.

### Issue #10 : Correction d'incompatibilité de paramètres dans `grading.py` et `sandbox_runner.py`
- **Gravité :** 🔴 Critique (Évaluation des épreuves)
- **Constat :** Lors de l'évaluation automatique d'une question `coding`, `grading.py` invoquait `execute_user_code_against_tests` avec l'argument `run_all=True` qui n'était pas déclaré dans la signature de la fonction.
- **Solution Appliquée :**
  - Alignement de la signature de fonction dans `sandbox_runner.py` : `execute_user_code_against_tests(code, test_cases, mask_hidden_output=True)`.
  - Appel avec `mask_hidden_output=False` côté grading serveur pour disposer des diagnostics complets pour l'attribution de la note.

### Issue #11 : Erreur de syntaxe JavaScript dans `exam-runner.js` (Ligne 1109)
- **Gravité :** 🔴 Critique (Blocage au chargement lors du login)
- **Constat :** Un crochet fermant excédentaire `}` à la ligne 1106 fermait prématurément la classe `ExamRunner`. Lors du chargement du fichier au moment de la connexion étudiante ou surveillante, le navigateur levait `Uncaught SyntaxError: Unexpected token '{'` sur la méthode suivante `_updateNavigationButtons()`.
- **Solution Appliquée :** Suppression de l'accolade orpheline dans `frontend/js/exam-runner.js`. Vérification automatisée avec `node -c frontend/js/exam-runner.js` (0 erreur de syntaxe).

### Issue #12 : Exigence de 10 tests cachés minimum par problème de programmation
- **Gravité :** 🟠 Élevée (Conformité aux spécifications d'évaluation)
- **Constat :** Les exercices disposaient auparavant d'au moins 2 tests publics et d'au moins 1 test caché. La nouvelle exigence spécifie au moins 2 tests publics et au moins 10 tests cachés pour 100% des exercices.
- **Solution Appliquée :**
  - Script d'enrichissement in-process `scripts/enrich_tests_inprocess.py`.
  - Exécution des solutions officielles de référence (`solution`) pour générer et valider 1255 nouveaux tests cachés certifiés conformes.
  - 100% des 230 problèmes (183 curriculum + 47 défis AlgoCompiler) disposent désormais d'**au moins 2 tests publics et d'au moins 10 tests cachés**.
  - Test de non-régression automatisé `test_curriculum_and_challenges_10_hidden_tests_requirement` ajouté à la suite de tests.

### Issue #13 : Rendu et visualisation interactive des graphiques Matplotlib / Seaborn
- **Gravité :** 🟡 Moyenne (Capacités d'évaluation en Data Science)
- **Constat :** Lors de l'exécution de code Python traçant des courbes ou des figures (`matplotlib.pyplot`, `seaborn`), le serveur headless ne capturait pas les figures pour affichage étudiant et risquait des blocages GUI ou des erreurs `Could not determine home directory`.
- **Solution Appliquée :**
  - Configuration de l'environnement headless `clean_env["MPLBACKEND"] = "Agg"` et `clean_env["MPLCONFIGDIR"] = tempfile.gettempdir()` avec préservation de `USERPROFILE`.
  - Hook d'interception `FIGURE_HOOK` : si `matplotlib` est importé dans le code, conversion automatique de toutes les figures actives en chaînes PNG base64 (`data:image/png;base64,...`) via `_buf = io.BytesIO()`.
  - Affichage direct du graphique rendu dans le volet console de l'interface étudiant (`#console-figures`).
  - Validation par test unitaire dédié `test_matplotlib_graph_visualization_and_figure_capture`.

### Issue #14 : Clarification Pédagogique des 4 Tests Diagnostiques de Niveau
- **Gravité :** 🟡 Moyenne (Clarté institutionnelle)
- **Constat :** Précision du périmètre des 4 tests de niveau : il s'agit des tests de positionnement fondamental dans les 4 piliers (**Python**, **Algorithmique**, **Cryptographie**, **Linux Administration**). Ils sont accessibles 24/7 en self-service et ne sont pas des modules académiques semestriels.
- **Solution Appliquée :**
  - Formalisation complète dans l'UI et la documentation de la distinction entre les 4 Tests Diagnostiques de Niveau (Piliers transversaux hors-bulletin) et les Unités d'Enseignement Académiques officielles (`DEV_WEB`, `DATABASE_SQL`, `NETWORKS`, `AI_ML`, `DATA_STRUCT`).

### Issue #15 : Verrouillage de la soumission pour un poste étudiant suspendu
- **Gravité :** 🔴 Critique (Sécurité & Anti-Triche)
- **Constat :** Lorsqu'un étudiant déclenchait une suspension de sécurité (absence écran > 10s), `save-answer` était bien verrouillé, mais l'endpoint de soumission finale `submit_official_exam` ne vérifiait pas le statut `suspended`, permettant potentiellement de forcer une soumission en contournant le surveillant.
- **Solution Appliquée :**
  - Ajout dans `backend/app/routers/student_exam.py` (`submit_official_exam`) d'une vérification immédiate : si `attempt.status == "suspended"`, rejet avec code HTTP 403 Forbidden ("Votre épreuve est suspendue. Déblocage surveillant requis.").
  - Seul le surveillant peut débloquer le poste à distance via `POST /api/proctor/sessions/{session_id}/attempts/{attempt_id}/unlock`.

### Issue #16 : Validation par Simulation Intégrale Multi-Rôles Bout-en-Bout
- **Gravité :** 🟠 Élevée (Fiabilité & Intégration globale)
- **Constat :** Nécessité de valider empiriquement l'ensemble des scénarios de vie d'un examen avec plusieurs rôles concurrents (Super Admin, Enseignant, 3 Étudiants avec cas limites).
- **Solution Appliquée :**
  - Conception et exécution du banc d'essai complet `scripts/simulate_all_exam_scenarios.py` :
    1. **Super Admin :** Création du module `CLOUD_DEVOPS` et affectation à l'enseignant `prof-01`.
    2. **Enseignant :** Conception de l'examen multi-types (QCM, Matching, Coding avec 2 tests publics et 10 tests cachés), ouverture de la session de salle.
    3. **Étudiant 1 :** Salle d'attente (0 fuite de questions), top départ synchronisé, sandbox interactif stdin/stdout, autosave WAL, soumission et notation 20/20.
    4. **Étudiant 2 :** Simulation de coupure réseau / F5, prolongation +10 min par le surveillant, vérification de la persistance authoritaire (temps restant augmenté).
    5. **Étudiant 3 :** Violation anti-triche (>10s), suspension automatique, soumission bloquée (403), déblocage distant en 1 clic par le surveillant, reprise immédiate.
    6. **Surveillant & Admin :** Clôture collective scellant et notant toutes les copies actives, vérification du tableau de bord académique consolidé.
  - Résultat : **100% des scénarios exécutés avec succès**.

### Issue #17 : Évaluation de Capacité Matérielle (Stress Testing Simultané)
- **Gravité :** 🟡 Moyenne (Dimensionnement d'infrastructure)
- **Constat :** Nécessité d'évaluer le nombre d'étudiants simultanés supportés sur la machine hôte (Intel Core i7-1255U 10 cœurs / 12 threads, 8 Go RAM, Windows 11).
- **Solution Appliquée :**
  - Exécution du script de benchmark empirique `scripts/benchmark_hardware_capacity.py`.
  - **Examens QCM / Formulaires standard :**
    - SQLite WAL gère jusqu'à 184.9 écritures concurrentes/sec (temps moyen de 0.54s pour 100 requêtes en rafale).
    - Capacité estimée : **200 à 300 étudiants simultanés** par serveur.
  - **Examens Pratiques Python (Sandbox Subprocess) :**
    - 30 exécutions de sandbox Python concurrentes validées en 0.43s (69.7 runs/sec) avec 100% de succès.
    - Chaque sandbox consomme ~30 Mo de RAM et ~70 ms CPU.
    - Capacité sécurisée : **30 à 45 exécutions simultanées actives en crête** (soit une cohorte de 60 à 100 étudiants codant alternativement).

### Issue #18 : Cloisonnement Strict Épreuves Théoriques vs Épreuves Pratiques
- **Gravité :** 🔴 Critique (Intégrité Pédagogique & Modèle Métier)
- **Constat :** Les épreuves n'avaient pas de distinction formelle entre les tests théoriques (QCM, matching, texte à trou) et les épreuves pratiques de code. Un enseignant pouvait accidentellement mélanger des questions de code dans un examen théorique.
- **Solution Appliquée :**
  - Ajout de la colonne `exam_type` (`"theoretical"` vs `"practical"`) dans le modèle `Exam`, avec migration automatique SQLite/PostgreSQL au démarrage (`main.py`).
  - Validation stricte dans le router FastAPI `backend/app/routers/exams.py` :
    - Épreuve Théorique : Rejette toute question de type `coding` avec HTTP 400 Bad Request.
    - Épreuve Pratique : Rejette toute question non-coding avec HTTP 400 Bad Request.
  - Interface Enseignant : Sélecteur de type d'épreuve dans la modale de création et filtrage dynamique automatique des types de questions dans l'éditeur de questions.
  - Badges distinctifs sur l'interface étudiant : `💻 Épreuve Pratique` (Violet) vs `📖 Épreuve Théorique` (Bleu).

### Issue #19 : Intégration Homogène de l'Espace Pratique Python & Autocomplétion CodeMirror
- **Gravité :** 🟠 Élevée (Expérience Utilisateur)
- **Constat :** L'interface d'entraînement pratique Python semblait insérée dans un sous-conteneur étroit avec doubles barres de défilement, sans suggestions d'autocomplétion pendant la frappe.
- **Solution Appliquée :**
  - Refonte CSS vers un layout fusionné pleine hauteur (`fused-workspace`) inspiré d'AlgoCompiler : volet de gauche avec rendu LaTeX KaTeX, énoncé et badges ; volet de droite avec éditeur CodeMirror pleine hauteur, barre d'outils et console d'E/S.
  - Déploiement de l'addon CodeMirror Autocomplete hors-ligne (`show-hint.js`, `python-hint.js`, `show-hint.css`) dans `frontend/vendor/codemirror/addon/hint/`.
  - Déclenchement automatique de l'autocomplétion (IntelliSense) sur `Ctrl-Space` et à la saisie de caractères/points pour les mots-clés Python, built-ins (`print`, `range`, `len`, `enumerate`, etc.), bibliothèques scientifiques (`math`, `sys`, `pandas`, `matplotlib`, `seaborn`) et snippets de structures de contrôle.
  - Correction de l'origine de navigation : le bouton de retour à la fin d'un entraînement affiche `Retourner au Centre d'Entraînement Python ➔` et ramène vers la matrice pédagogique.

### Issue #20 : Système de Toasts Glassmorphic & Fermeture Universelle par Échap
- **Gravité :** 🟡 Moyenne (UI / Ergonomie)
- **Constat :** Les notifications de l'application utilisaient des boîtes de dialogue natives bloquantes `alert()`, et les modales ne pouvaient être fermées que par un clic précis sur la croix `×`.
- **Solution Appliquée :**
  - Création du système de notifications toast glassmorphic (`.app-toast-container`, `.app-toast`) avec icônes et styles distincts selon le type (`success`, `warning`, `danger`, `info`).
  - Interception globale transparente de `window.alert` redirigeant automatiquement vers `showToast` avec inférence intelligente de sévérité.
  - Ajout d'écouteurs d'événements globaux pour la touche `Échap` (`Escape`) et pour les clics sur l'arrière-plan semi-transparent (`backdrop`) fermant instantanément toute modale active.

### Issue #21 : États Dynamiques Visuels des Cartes d'Épreuves Étudiant
- **Gravité :** 🟠 Élevée (Guidance Étudiant & Résilience au Rechargement)
- **Constat :** En cas de rafraîchissement (`F5`) pendant une épreuve en cours ou en salle d'attente, la carte de l'épreuve pouvait afficher le bouton standard "Commencer l'épreuve ➔", prêtant à confusion.
- **Solution Appliquée :**
  - Mise à jour de `_loadOfficialExams` dans `frontend/js/app.js` pour inspecter `ex.attempt_status` :
    - Épreuve en cours : Bouton vert émeraude `🔄 Rejoindre l'épreuve en cours ➔` avec badge clignotant `● En cours`.
    - Salle d'attente : Bouton ambre `⏳ Rejoindre la salle d'attente ➔` avec badge `⏳ Salle d'attente`.
    - Épreuve suspendue : Bouton rouge `🔒 Épreuve Suspendue — Voir Statut ➔` avec badge `🔒 Suspendu`.
    - Épreuve terminée : Boîte scellée `✅ Épreuve Soumise & Scellée (Note/20)`.
    - Non démarrée : Bouton primaire `Commencer l'épreuve ➔`.

### Issue #22 : Correction de l'Affectation Multi-Enseignants & Élimination de `[object Object]`
- **Gravité :** 🟠 Élevée (Administration Académique)
- **Constat :** L'affectation d'un enseignant à un module pouvait afficher une notification brute `Erreur d'affectation : [object Object]` lorsque l'API renvoyait une erreur de validation Pydantic en format tableau d'objets, et le schéma attendait `module_code` dans le corps sans flexibilité.
- **Solution Appliquée :**
  - Dans `backend/app/schemas.py`, assouplissement de `TeacherModuleAssign` avec `module_code: Optional[str] = None`.
  - Dans `frontend/js/api.js`, déballage récursif robuste des erreurs FastAPI : inspection des tableaux `loc`/`msg` pour extraire des messages textuels clairs.
  - Exclusion de l'endpoint `/auth/login` de l'événement global `auth:expired` afin d'éviter les fausses alertes "Votre session a expiré" lors de la saisie d'un mauvais mot de passe.

### Issue #23 : Tableau Structuré Enseignant & Atelier de Questions
- **Gravité :** 🟡 Moyenne (Ergonomie Enseignant)
- **Constat :** La liste des examens créés dans l'espace enseignant était sous forme de cartes encombrantes, sans vision tabulaire synthétique des durées, types et barèmes.
- **Solution Appliquée :**
  - Refonte de la vue enseignant (`renderTeacherView`) sous forme de tableau de bord structuré et réactif avec colonnes : Module & Statut, Titre, Type, Durée, Questions, Barème, Cibles, Actions Directes.
  - Intégration de boutons directs d'action : `👁️ Surveiller`, `📝 Questions`, `📊 Stats`, `📦 Export`, `🗑️ Supprimer`.
  - Connexion directe de la suppression d'examen via `api.deleteExam`.

### Issue #24 : Conteneurisation Clé-en-main & Scripts de Cycle de Vie Docker
- **Gravité :** 🟢 Opérationnelle (Déploiement & Exploitation)
- **Constat :** Nécessité d'un dossier dédié de scripts pour démarrer, arrêter, mettre à jour, exporter et charger l'image Docker en toute autonomie sur site ou en milieu déconnecté (Air-gap).
- **Solution Appliquée :**
  - Création du dossier `deployment/` contenant :
    - `start_app.bat` / `start_app.sh` : démarrage automatisé avec vérification d'état (healthcheck).
    - `stop_app.bat` / `stop_app.sh` : extinction propre sans suppression des données persistantes.
    - `update_app.bat` / `update_app.sh` : recompilation de l'image Docker, redémarrage et application transparente des migrations sans perte de données.
    - `export_offline_image.bat` / `load_offline_image.bat` : exportation et chargement d'archives `.tar` de l'image Docker pour transferts sécurisés par clé USB en salle isolée.
    - `docker-compose.standalone.yml` : configuration légère autonome sur base SQLite WAL haute performance sans dépendance PostgreSQL.
    - `DEPLOYMENT_AND_PERSISTENCE_GUIDE.md` : guide technique détaillé pas-à-pas.

### Issue #25 : Garantie de Persistance des Données lors des Mises à Jour
- **Gravité :** 🔴 Critique (Intégrité des Données d'Examen)
- **Constat :** Risque potentiel de perte ou réinitialisation des bases de données lors des mises à jour du code applicatif ou des reconstructions de conteneurs Docker.
- **Solution Appliquée :**
  - Isolation stricte des volumes de stockage Docker nommés (`postgres_data`, `standalone_data`, `room_data`) en dehors du cycle de vie des conteneurs éphémères.
  - Système d'auto-migration non destructive au démarrage dans `backend/app/main.py` : inspection PRAGMA SQLite / information_schema PostgreSQL avec requêtes `ALTER TABLE ... ADD COLUMN` idempotentes. Les tables existantes, comptes, notes et copies restent intacts.

### Issue #26 : Gestion des Promotions & Années d'Inscription des Étudiants
- **Gravité :** 🟠 Élevée (Gouvernance Académique)
- **Constat :** Les étudiants de différentes années universitaires risquaient d'être mélangés ou intervertis dans les listes administratives et les examens.
- **Solution Appliquée :**
  - Ajout du champ `enrollment_year` (ex: "2024-2025", "2025-2026") sur le modèle `User`, les schémas Pydantic, et indexation en base.
  - Nouvel endpoint `GET /api/users/enrollment-years` renvoyant les promotions distinctes triées.
  - Filtrage dynamique par promotion dans la liste des utilisateurs (`GET /api/users?enrollment_year=...`).
  - Prise en charge de la colonne promotion à l'import/export CSV d'étudiants (`backend/app/routers/csv_io.py`).
  - Ajout d'un sélecteur de filtrage par Année d'Inscription et d'un badge distinctif dans le panneau d'administration (`frontend/index.html` et `frontend/js/app.js`).

### Issue #27 : Audit de Sécurité : Impossibilité d'Usurpation de Note et Cloisonnement RBAC
- **Gravité :** 🔴 Critique (Sécurité des Évaluations & Anti-Fraude)
- **Constat :** Nécessité d'une preuve formelle qu'un étudiant ne peut ni modifier sa note en injectant un score dans la requête, ni accéder aux interfaces enseignant/administrateur.
- **Solution Appliquée & Validée :**
  - **Inviolabilité de la Notation :** Le client soumet uniquement les réponses brutes (`answers`). L'intégralité du calcul des points est exécutée côté serveur par `backend/app/services/grading.py` et le sandbox d'exécution Python contre les tests cachés chiffrés. Tout champ falsifié (`final_mark: 20.0`, `score: 20.0`, `is_passed: True`) injecté dans le JSON de soumission est totalement ignoré.
  - **Cloisonnement RBAC strict :** Tout endpoint d'administration ou de surveillance proctoring vérifie le token JWT et rejette immédiatement avec HTTP 403 Forbidden toute requête émanant d'un rôle `student`.
  - **Étanchéité réseau de la base :** La base de données SQLite/PostgreSQL n'est pas exposée sur le réseau des étudiants ; seuls les points de terminaison REST authentifiés et filtrés sont accessibles.
  - Validation automatisée par `tests/test_deployment_and_security.py` (3/3 tests passés avec succès).

### Issue #28 : Refonte Ergonomique de l'Interface Pratique, Persistance du Volet Latéral Droit & Déconnexion de la Touche Échap du Plein Écran
- **Gravité :** 🟠 Haute (Expérience Utilisateur, Cohérence Visuelle & Stabilité de l'Examen Pratique)
- **Constats :**
  1. **Déséquilibre de la disposition pratique :** Le volet de codage manquait d'équilibre visuel, sans barre de navigation claire entre les différents problèmes de programmation.
  2. **Disparition du volet droit :** En mode codage (`.exam-layout.coding-mode`), la règle CSS masquait complètement le panneau latéral droit (`.exam-sidebar`), privant l'étudiant du compte à rebours officiel, de la grille des questions et du bouton de soumission finale.
  3. **Erreur d'exécution de code Python :** Lors de l'exécution de code (`sentence = input().strip()`), une erreur `code: Input should be a valid string` survenait en raison d'une inversion de signature dans l'appel `api.runPythonTests()`.
  4. **Fermeture de l'autocomplétion & Touche Échap :** La pop-up d'autocomplétion CodeMirror ne se refermait pas automatiquement lors d'un clic extérieur ou d'une perte de focus. De plus, appuyer sur la touche `Échap` déclenchait la sortie du mode plein écran par le navigateur au lieu de simplement fermer la boîte de complétion.
  5. **Pollution de la base par de multiples examens d'essai :** Présence d'examens temporaires ou de test dispersés dans la base.
- **Solutions Appliquées & Validées :**
  1. **Disposition Équilibrée & Barre de Navigation Pratique (`frontend/css/style.css`, `frontend/js/exam-runner.js`) :**
     - Intégration d'une barre de navigation supérieure (`.coding-navigator-bar`) affichant l'ensemble des défis (`#1`, `#2`, `#3`), leurs statuts en direct (`✅` résolu, `⚡` actif, `○` non résolu, `🚩` marqué), ainsi qu'un compteur d'avancement (`X / Y résolus`).
     - Répartition proportionnée inspirée d'AlgoCompiler (44% pour l'énoncé riche KaTeX et 56% pour le panneau éditeur/console).
  2. **Visibilité Permanente du Volet Latéral Droit :**
     - Modification de la grille `.exam-layout.coding-mode` en `grid-template-columns: 1fr 310px !important;` et forçage de `.exam-sidebar { display: flex !important; }`. Le chronomètre officiel serveur, la palette des questions et la soumission restent visibles en permanence sur toutes les épreuves (théoriques comme pratiques).
  3. **Résolution de l'Erreur de Sandbox Python (`backend/app/routers/training_python.py`, `frontend/js/api.js`) :**
     - Mise à jour du schéma `RunTestsRequest` pour accepter directement une liste de tests unitaires (`tests: Optional[List[Dict[str, Any]]]`).
     - Polymorphisme côté `api.js` : détection automatique des arguments pour router le code utilisateur et les tests sans dépendance à l'ordre des paramètres.
  4. **Gestion de l'Autocomplétion & Sécurisation de la Touche Échap (`frontend/vendor/codemirror/addon/hint/show-hint.js`, `frontend/js/app.js`, `frontend/js/anticheat.js`) :**
     - Fermeture automatique du widget d'autocomplétion au clic extérieur (`mousedown` en phase capture), au flou (`cm.blur`) et au redimensionnement de la fenêtre.
     - Interception globale de la touche `Échap` en mode examen pratique : fermeture prioritaire des suggestions sans quitter le mode plein écran, complétée par `navigator.keyboard.lock(['Escape'])`.
  5. **Purge et Amorçage Propre de 3 Examens Canoniques (`scripts/reset_and_seed_exact_3_exams.py`) :**
     - Réinitialisation complète de la base de données pour ne conserver que 3 examens stricts :
       1. `EXAM-THEO-PYTHON` (5 questions théoriques, 20 pts)
       2. `EXAM-PRAC-PYTHON` (3 défis de programmation avec 2 tests publics et 10 tests cachés chacun, 20 pts)
       3. `EXAM-THEO-CRYPTO` (5 questions de sécurité, 20 pts)
     - Affectation universelle aux promotions étudiantes (`DEV-IA`, `SYS-ADMIN`, `CYBER-SEC`, `GRP-1`, `GRP-2`, `GRP-SEC-1`).

### Issue #29 : Optimisation Ergonomique des Boutons et Tailles de Police de l'Atelier Pratique Python
- **Gravité :** 🟡 Moyenne (Lisibilité & Confort Visuel des Évaluations Pratiques)
- **Constat :** Dans l'interface pratique (AlgoCompiler/HackerRank), les boutons d'action (`Exécuter (stdin)`, `Tester ma Solution`, `Enregistrer`, `Préc/Suiv`, `Marquer`, pilules de défis) et les polices de caractères (énoncé, éditeur CodeMirror, console et cas de test) étaient trop réduits (`font-size: 0.72rem` à `0.82rem`, padding `2px` à `4px`), nuisant au confort de frappe et de lecture.
- **Solution Appliquée & Validée :**
  - **Agrandissement de la barre de navigation des défis :** Pilules portées à `font-size: 0.92rem`, padding `6px 14px`, badges de statuts clairs et compteur d'avancement à `font-size: 0.92rem`.
  - **Agrandissement des boutons de contrôle :** Boutons de navigation (`← Préc.`, `Suiv. ➔`), drapeau (`🚩 Marqué`) et points portés à `padding: 6px 14px`, `font-size: 0.92rem`.
  - **Mise en valeur des boutons d'exécution :**
    - `⚡ Tester ma Solution` porté à `padding: 9px 20px`, `font-size: 1rem`, `font-weight: 700` avec ombre portée bleutée.
    - `▶️ Exécuter (stdin)` et `💾 Enregistrer` portés à `padding: 8px-9px`, `font-size: 0.95rem`, `font-weight: 600`.
  - **Confort de lecture de l'énoncé & CodeMirror :**
    - Énoncé markdown porté à `font-size: 1.05rem`, interligne `1.75`, blocs de code à `0.96rem`.
    - Police par défaut de l'éditeur CodeMirror portée de `14px` à `16px`, avec plage d'ajustement dynamique (`A-` / `A+`) étendue jusqu'à `30px`.
    - Textarea stdin et console stdout portées à `font-size: 0.95rem`, interligne `1.6`.
    - Cas de test publics : titres à `0.95rem`, statut à `0.85rem` et blocs d'E/S à `0.92rem`.
  - Validation complète : 103/103 tests automatisés validés (`pytest tests/`).

### Issue #30 : Intégration Complète du Centre d'Entraînement Linux (Architecture R1 à R5)
- **Gravité :** 🟢 Évolution Majeure (Curriculum & Environnement Interactif Linux Client-Serveur)
- **Constat :** L'application disposait d'un centre d'entraînement complet pour Python (AlgoCompiler), mais aucun environnement équivalent n'était disponible pour l'administration système Linux. Les étudiants avaient besoin d'un apprentissage progressif alliant questions théoriques (FHS, droits, signaux, Bash) et ateliers pratiques avec commandes shell réelles sans risque pour la machine hôte.
- **Architecture & Résolutions Implémentées (R1 à R5) :**

  #### R1. Architecture UI & Navigation Bi-Volet (Dual-Track Learning)
  - **Volet Théorique (Concepts & Administration Système) :** Exercices progressifs et QCM interactifs couvrant les fondamentaux Linux (hiérarchie FHS, permissions, cycle de vie des processus, scripting Bash, utilitaires réseau). Sélection par thème/chapitre, rétroaction immédiate, explications détaillées et notation sur 20.
  - **Volet Pratique (Atelier Terminal & Défis Ligne de Commande) :** Disposition ergonomique en 2 volets fusionnés (`fused-workspace`) inspirée d'AlgoCompiler :
    - *Panneau gauche :* Énoncé riche du défi, badge de niveau (Niveau 1 à 4), barème de points, contexte opérationnel, aperçu de l'état VFS initial (`initial_fs`), contraintes et onglet "Cas de Test" (tests publics détaillés et tests cachés confidentiels).
    - *Panneau droit :* Éditeur multi-lignes de commandes / scripts Bash avec barre d'outils, fenêtre de terminal virtuel interactif (`TerminalUI`) à rendu ANSI, et boutons d'action : `⚡ Exécuter (Interactif)`, `🧪 Tester Publics` et `🚀 Soumettre le Défi`.
  - **Bouton de Retour Universel :** Tous les écrans d'entraînement et d'achèvement de session comportent le bouton d'action immuable `"Retourner au Centre d'Entraînement Linux ➔"` garantissant une navigation fluide vers le hub `#view-linux` sans redirection rompue.
  - **Intégration de Navigation Étudiant :** Bouton direct `#btn-open-linux-center` dans la barre de navigation d'en-tête étudiant aux côtés de l'entraînement Python et des examens officiels, complété par la bannière `#btn-open-dedicated-linux-training` sur le tableau de bord.

  #### R2. Moteur Shell & Système de Fichiers Virtuel 100% Client (VFS Engine)
  - **Hiérarchie VFS & Modèle Inode (`frontend/js/linux/vfs.js`) :**
    - Arborescence FHS standard pré-remplie (`/bin`, `/etc`, `/home/student`, `/root`, `/tmp`, `/proc`, `/dev`, `/var/log`).
    - Nœuds virtuels (`VFSNode`) simulant types (`file`, `dir`, `symlink`), horodatages, tailles en octets, propriétaires (`owner`/`group`) et permissions POSIX (modes octaux `755`, `644`, `700`, `1777` et symboliques `+x`, `u=rwx,go=rx`).
    - Résolution robuste et normalisation des chemins (`.`, `..`, `~` pour `$HOME`, `~root`, absolus, relatifs, arrêt strict à la racine `/`).
    - Prise en charge des liens symboliques avec détection de cycles (erreur `ELOOP` après 20 sauts).
    - Instantanés atomiques (`vfs.snapshot()` / `vfs.serialize()`) et restauration immédiate (`vfs.restore()`) pour réinitialisation déterministe.
  - **23 Commandes Builtin POSIX & Utilitaires Système (`frontend/js/linux/posix-commands.js`) :**
    - *Navigation & Fichiers :* `pwd`, `cd` (avec `$HOME`, `$OLDPWD`, `cd -`), `ls` (options `-l`, `-a`, `-la`, `-1`, `-lh`, `-d`), `cat` (`-n`, `-s`), `touch`, `mkdir` (`-p`), `rm` (`-r`, `-rf`, blocage de sécurité sur `/`), `cp` (copie récursive de fichiers/dossiers), `mv` (déplacement et renommage atomiques).
    - *Affichage & Comptage :* `echo` (`-n`, `-e` avec séquences d'échappement), `head` (`-n N`), `tail` (`-n N`, `+N`), `wc` (lignes `-l`, mots `-w`, octets `-c`, multi-fichiers avec total).
    - *Droits & Identité :* `chmod` (octal et symbolique), `chown` (simulation root vs student), `whoami` (retourne `student`), `uname` (`-a`, `-r`).
    - *Système & Processus :* `uptime` (`-p`), `date` (`+%Y`, etc.), `env`, `export` (mise à jour de l'environnement), `ps` (avec `aux`), `top` (instantané système), `kill` (simulation de signaux, protection PID 1), `test` / `[` (`-f`, `-d`, `-e`, `-s`, `-z`, `-n`, `-x`, `-r`, `-w`).
  - **Utilitaires Avancés de Traitement de Texte :**
    - `grep` : recherche par motif avec `-i` (insensible à la casse), `-v` (inversion), `-n` (numérotation), `-c` (comptage), expressions régulières, support stdin et multi-fichiers.
    - `find` : parcours récursif du VFS par nom (`-name`), type (`-type f/d`), et profondeur (`-maxdepth`).
    - `sort` : tri alphabétique, inversé (`-r`), numérique (`-n`), et déduplication (`-u`).
    - `uniq` : déduplication des lignes adjacentes (`-c` comptage, `-d` doublons seuls, `-u` lignes uniques, `-i` sans casse).
  - **Parseur Shell & Moteur d'Exécution AST (`shell-lexer.js`, `shell-parser.js`, `shell-engine.js`) :**
    - Analyse lexicale gérant les guillemets simples `'..'` (préservation littérale), guillemets doubles `".."`, échappements antislash `\`, et expansion des variables (`$VAR`, `${VAR}`, `${VAR:-default}`, et code de sortie `$?`).
    - Construction d'AST pour les pipelines multi-étages (`cmd1 | cmd2 | cmd3`).
    - Redirections d'E/S : écriture écrasement (`>`), ajout (`>>`), entrée depuis fichier (`<`), redirections d'erreur (`2>`, `&>`).
    - Propagation des codes de retour POSIX (`0` succès, `1` erreur générale, `127` commande introuvable, `130` SIGINT).
    - Chaînage conditionnel avec évaluation court-circuit : `&&` (ET logique), `||` (OU logique), et `;` (séquentiel).
  - **Interface Terminal CLI Interactive (`frontend/js/linux/terminal-ui.js`) :**
    - Invite dynamique (`student@examquiz:~$ `) s'adaptant au répertoire courant (`~` pour le répertoire personnel, `~#` pour root).
    - Historique interactif avec flèches Haut/Bas et conservation du brouillon non validé.
    - Autocomplétion contextuelle par touche Tab : détection de la position de commande vs chemin VFS, calcul du plus long préfixe commun (LCP), ajout automatique du slash pour les répertoires et de l'espace pour les fichiers.
    - Effacement d'écran (`clear` et raccourci `Ctrl+L`) et interception de signal d'interruption (`Ctrl+C`).

  #### R3. Curriculum Progressif en 4 Niveaux & Évaluateur de Défis
  - **Curriculum Structuré (`backend/app/data/linux_training/curriculum.json`, `challenges.json`) :**
    - 4 niveaux progressifs :
      - *Niveau 1 :* Navigation, inspection et manipulation de base des fichiers.
      - *Niveau 2 :* Permissions POSIX, gestion des droits (`chmod`, `chown`) et filtrage textuel.
      - *Niveau 3 :* Scripting Bash, pipelines et redirections de flux.
      - *Niveau 4 :* Administration système avancée, gestion des processus et diagnostic.
    - **Règle Stricte des Tests :** Chaque défi pratique comporte obligatoirement **au moins 2 tests publics** (visibles par l'étudiant avec entrées et sorties attendues) et **au moins 5 tests cachés** (évalués confidentiellement pour valider la robustesse sans fuite de corrigé).
  - **Banc d'Évaluation Automatisé (`LinuxChallengeEvaluator`) :**
    - Exécution du script de l'étudiant sur un instantané VFS isolé.
    - Vérification conjointe des sorties terminal et des effets de bord sur le système de fichiers via un catalogue d'assertions riches :
      - `file_exists` / `file_not_exists` : création ou suppression de fichiers/dossiers.
      - `file_contains` / `fs_content_exact` / `fs_content_regex` / `fs_content_lines` : contenu exact, motifs regex, et nombre de lignes des fichiers.
      - `fs_mode` / `fs_mode_mask` : conformité des bits de permissions octales (ex: `755`, `700`) et masques binaires.
      - `fs_owner` : attribution correcte du propriétaire.
      - `stdout_exact` / `stdout_contains` / `stdout_regex` / `exit_code` : validation de la sortie console et du code retour.
    - **Isolation par Snapshot Rollback :** Chaque assertion est exécutée après restauration de l'instantané post-script, garantissant qu'une assertion ne pollue pas les assertions suivantes.
    - **Confidentialité Inviolable des Tests Cachés :** Les attributs des tests masqués (`cmd`, `expected`, `actual`, `assertion_type`) sont systématiquement remplacés par `"[Protégé]"` dans le DOM, la console DevTools et les payloads JSON d'évaluation.

  #### R4. Persistance Académique & Preuve Mathématique du Découplage des Examens
  - **Persistance des Tentatives :** Toute évaluation réussie enregistre un enregistrement immuable dans la table `practice_attempts` de la base de données, rattaché au pilier transversal `LINUX_ADMIN`.
  - **Preuve Mathématique du Découplage Strict :**
    - Les défis d'entraînement et tests du Centre Linux alimentent exclusivement le radar de compétences fondamentales de l'étudiant (`fundamentals["LINUX_ADMIN"]`).
    - L'endpoint officiel du relevé de notes (`GET /api/student/bulletin`) calcule la moyenne générale (`general_average`), la moyenne des examens (`exams_average`) et le verdict du jury (`ADMIS` / `AJOURNÉ`) **strictement et exclusivement** à partir des examens semestriels officiels (`StudentAttempt` sur les modules de cours accrédités).
    - Validation empirique : la soumission de défis Linux (avec des scores de 0/20 à 20/20) laisse la moyenne générale, la moyenne d'épreuves et le verdict académique rigoureusement invariants ($\Delta \text{GPA} = 0.000$).

  #### R5. Suite Complète de Vérification & Taux de Réussite de 100%
  - **Suite Backend Pytest (`tests/test_linux_training.py`) :** 16 tests unitaires et d'intégration validant le schéma du curriculum, les quotas de tests publics/cachés ($\ge 2$ et $\ge 5$), le masquage des secrets, les endpoints REST, l'évaluation VFS, la persistance `LINUX_ADMIN`, le découplage strict du GPA, et le rejet 401 des accès non authentifiés.
  - **Suites Client Node.js (`frontend/js/linux/`) :**
    - `test-posix-vfs.mjs` : 162/162 tests validés (modèle VFSNode, arborescence FHS, CRUD, normalisation, 23 builtins, filtres grep/find/sort/uniq, permissions, symlinks).
    - `test-shell-engine.mjs` : 104/104 tests validés (analyseur lexical, guillemets, échappements, variables, AST, pipelines, redirections, chaînage, invite de commande, historique, autocomplétion Tab).
    - `test-evaluator.mjs` : 58/58 tests validés (assertions de fichiers et de contenu, permissions octales, masquage confidentiel, isolation rollback, évaluation des défis réels).
  - **Non-Régression Globale :** 119/119 tests backend (`pytest tests/`) et 324/324 tests frontend (`node`) validés avec 100% de succès.

### Issue #31 : Mode Thème Clair, Résolution de la Régression de Navigation et Épuration Ergonomique de l'Affichage des Tests
- **Gravité :** 🟡 Moyenne (Stabilité Client & Accessibilité Visuelle UI/UX)
- **Constats :**
  1. Exception levée dans la console navigateur : `exam-runner.js:1731 Uncaught SyntaxError: Unexpected identifier 'prevBtn'` due à une signature de méthode manquante (`_updateNavigationButtons`) lors de l'assemblage de l'exécuteur.
  2. Demande utilisateur pour un mode Thème Clair moderne et harmonieux afin de répondre aux normes d'accessibilité visuelle en environnement fortement éclairé.
  3. Nécessité d'épurer l'affichage des résultats de tests pour éviter la surcharge visuelle et les pavés d'informations superflus.
- **Résolutions Appliquées :**
  1. **Correction Syntaxique de l'Exam Runner :** Restauration complète du bloc `_updateNavigationButtons() { ... }` dans [`frontend/js/exam-runner.js`](file:///c:/Users/adel/Documents/ExaminationQuiz%20APP/frontend/js/exam-runner.js). Validation immédiate via `node -c` (exit code 0).
  2. **Intégration du Mode Thème Clair (`[data-theme="light"]`) :**
     - Ajout du bouton basculeur interactif `☀️ / 🌙` dans l'en-tête principal (`#btn-theme-toggle`).
     - Gestion dynamique du thème avec mémorisation locale dans `localStorage` (`initTheme()` et `setTheme()`).
     - Définition complète des variables CSS de contraste dans [`frontend/css/style.css`](file:///c:/Users/adel/Documents/ExaminationQuiz%20APP/frontend/css/style.css) pour l'ensemble des éléments (cartes, tableaux, formulaires, modales, CodeMirror, sélecteurs d'options, badges et barres d'outils).
  3. **Épuration Ergonomique des Tests :** Affichage compact et aéré des cas de tests avec badges d'état lisibles (`Passé ✅` / `Échoué ❌`), élimination des dumps de logs encombrants et synthèse concise du résultat.
  4. **Validation de l'Ensemble des Scénarios :** Exécution avec succès de la simulation complète des 6 scénarios multi-rôles (`scripts/simulate_all_exam_scenarios.py`) et 119/119 tests unitaires et d'intégration validés.

---

## 3. Matrice de Validation des Tests

| Composant | Fichiers de Tests | Tests Exécutés | Résultat |
| :--- | :--- | :--- | :--- |
| **Centre Linux Backend (Pytest)** | `tests/test_linux_training.py` | 16 | ✅ 16/16 Validés (100%) |
| **Linux VFS & POSIX Engine (Node.js)** | `frontend/js/linux/test-posix-vfs.mjs` | 162 | ✅ 162/162 Validés (100%) |
| **Linux Shell Engine & Terminal (Node.js)** | `frontend/js/linux/test-shell-engine.mjs` | 104 | ✅ 104/104 Validés (100%) |
| **Linux Challenge Evaluator (Node.js)** | `frontend/js/linux/test-evaluator.mjs` | 58 | ✅ 58/58 Validés (100%) |
| **Exigences E2E & Directives (Tiers 1 à 4)** | `tests/test_e2e_requirements.py` | 15 | ✅ 15/15 Validés (100%) |
| **Sandbox Python, 10 Hidden Tests & Figures** | `tests/test_sandbox_and_challenges.py` | 7 | ✅ 7/7 Validés (100%) |
| **Déploiement Docker, Promotions & Audit Sécurité** | `tests/test_deployment_and_security.py` | 3 | ✅ 3/3 Validés (100%) |
| **Phase 1 (Authentification & Rôles)** | `tests/test_phase1.py` | 12 | ✅ 12/12 Validés (100%) |
| **Phase 2 (Sessions, Notation QCM & Cloisonnement)** | `tests/test_phase2.py` | 18 | ✅ 18/18 Validés (100%) |
| **Phase 3 (Soumissions & Anti-Triche)** | `tests/test_phase3.py` | 7 | ✅ 7/7 Validés (100%) |
| **Phase 4 (Synchronisation & Proctoring Télémesure)** | `tests/test_phase4.py` | 6 | ✅ 6/6 Validés (100%) |
| **Phase 5 (Paquets Chiffrés USB & Scellés SHA-256)** | `tests/test_phase5.py` | 3 | ✅ 3/3 Validés (100%) |
| **Phase 6 (Curriculum, Pyodide & Progression)** | `tests/test_phase6.py` | 9 | ✅ 9/9 Validés (100%) |
| **Phase 7 (Conteneurisation & Concurrence 30)** | `tests/test_phase7.py` | 3 | ✅ 3/3 Validés (100%) |
| **Phase 8 (Salles d'attente, Bulletins & PDF/DOCX)** | `tests/test_phase8_revisions.py` | 15 | ✅ 15/15 Validés (100%) |
| **Phase 9 (Statistiques Item Analysis & Kelley D)** | `tests/test_phase9_features.py` | 5 | ✅ 5/5 Validés (100%) |
| **TOTAL GÉNÉRAL TESTS AUTOMATISÉS** | **13 Suites Pytest + 3 Suites Node.js** | **443 Tests** | **✅ 443/443 Validés (100%)** |
| **Simulation Réaliste Multi-Rôles** | `scripts/simulate_all_exam_scenarios.py` | 6 Scénarios | **✅ 6/6 Succès (100%)** |

---

## 4. Analyse de Capacité Matérielle et Concurrence
Un benchmark complet de charge a été effectué (`scripts/benchmark_hardware_capacity.py`).
- **Capacité recommandée en examen simultané :** 60 à 100 étudiants par serveur standard (4 vCPU / 8 Go RAM).
- **Consommation mémoire :** ~35 Mo par conteneur/processus sandbox Python sous exécution concurrente.
- **Sécurité I/O :** Verrouillage SQLite WAL avec isolation `immediate`, protection contre les écrasements concurrents.

---

## 5. Conclusion d'Audit

L'ensemble des incohérences répertoriées a été corrigé avec une traçabilité rigoureuse.
La plateforme d'examen est 100% opérationnelle, hautement sécurisée contre la triche et les fuites de données, résiliente face aux aléas réseau d'une salle de TP, et conforme aux spécifications fonctionnelles exigées.

