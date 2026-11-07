# 🖥️ Guide d'Utilisation : Application Desktop EXAM CONTROL MASTER

Ce guide détaille l'utilisation de l'application desktop autonome Windows (`ExamControlMaster.exe`) permettant de superviser les conteneurs Docker, de monitorer la télémétrie serveur en direct, de cartographier les postes clients sur le réseau local et d'offrir une adresse conviviale (`http://exam.local:8000`) sans dépendance à Internet.

---

## 1. Lancement de l'Application

Vous pouvez lancer l'application de deux manières simples :
1. **Fichier Exécutable Autonome** : Double-cliquez sur `dist/ExamControlMaster.exe` (aucun Python ou logiciel préinstallé requis).
2. **Script de Lancement Rapide** : Double-cliquez sur `lancer_desktop_admin.bat` à la racine du projet.

---

## 2. Fonctionnalités par Onglet

### 📊 Onglet 1 : Tableau de Bord, Santé & Télémétrie Serveur
- **Indicateurs d'État Immédiats** :
  - **Démon Docker** : Affiche si Docker Desktop est actif (🟢 En ligne) ou arrêté (🔴 Déconnecté).
  - **Serveur FastAPI & Base de Données** : Vérifie l'accessibilité du port 8000 et de PostgreSQL (port 5432).
  - **Lien Convivial Actif** : `http://exam.local:8000`.
- **Télémétrie Serveur en Temps Réel** :
  - **Charge CPU** (en %) avec jauge dynamique.
  - **Consommation Mémoire RAM** (Mo utilisés / Mo totaux et pourcentage).
  - **Compteur de Requêtes Reçues** : Total des requêtes traitées par le serveur d'examen.
  - **Débit Réseau** (Ko/s entrant et sortant).
- **Actions Rapides Docker en 1 Clic** :
  - `▶ Démarrer Serveur` : Lance les conteneurs via `docker compose up -d`.
  - `⏹ Arrêter Serveur` : Met en pause propre les conteneurs via `docker compose stop`.
  - `🔄 Redémarrer` : Redémarre l'ensemble des services.
  - `📥 Charger Image (.tar)` : Importe une image sans connexion Internet depuis une clé USB.
- **Diagnostic Intelligent & Aide à la Résolution** :
  - Analyse les 6 composants critiques (Docker, conteneurs, port 8000, port 5432, espace disque, réseau).
  - Affiche pour chaque problème **ce qui ne va pas** et **comment le résoudre**.
  - Propose des boutons d'auto-résolution (ex: libérer le port 8000 si un processus parasite le bloque).

---

### 🌐 Onglet 2 : Cartographie Réseau & Étiquetage des Postes (Approche 1)
- **Balayage Réseau Express** :
  - Cliquez sur `🔍 Lancer le Scan Réseau` pour lister tous les ordinateurs connectés au sous-réseau en moins de 3 secondes.
  - Affiche pour chaque machine : Adresse IP, Adresse MAC physique, Nom d'hôte système, Étiquette de salle, Latence ping (en ms) et statut (🟢 En ligne / 🔴 Injoignable).
- **Renommage & Étiquetage (Approche 1 Validée)** :
  - Cliquez sur le bouton `✏️ Renommer` d'une ligne pour lui attribuer un nom convivial (ex: *"Poste 01"*, *"Rangée A - Table 2"*).
  - **Aucun privilège requis sur les postes clients** : L'association est enregistrée dans le fichier local `network_topology.json`.
- **Import / Export CSV** :
  - Sauvegardez ou restaurez la cartographie de vos salles de TP en 1 clic.

---

### 🐳 Onglet 3 : Gestion Docker & Mises à Jour
- **Mise à Jour Déconnectée par Fichier `.tar`** :
  - Cliquez sur `Parcourir...` pour sélectionner une nouvelle archive d'image (ex: sur une clé USB).
  - Cliquez sur `🚀 Appliquer Mise à Jour` : l'application charge l'image dans Docker et recrée le conteneur applicatif sans détruire la base de données.
- **Console d'Exécution en Direct** :
  - Visualisez les logs et messages de retour de Docker en temps réel.

---

### 🔗 Onglet 4 : Nom de Domaine Convivial (`http://exam.local:8000`)
- **Accès Étudiant Sans Adresse IP** :
  - Grâce au répondeur mDNS intégré, les étudiants tapent simplement `http://exam.local:8000` dans leur navigateur.
  - Bouton `📋 Copier le Lien` et `🌐 Tester dans le Navigateur`.
- **Générateur de Script de Secours** :
  - Si le routeur ou switch de la salle bloque le protocole multicast mDNS, cliquez sur `💾 Enregistrer le Script 'installer_nom_local.bat'`.
  - Copiez ce script sur une clé USB : un double-clic sur le poste étudiant configure la redirection locale immédiatement.

