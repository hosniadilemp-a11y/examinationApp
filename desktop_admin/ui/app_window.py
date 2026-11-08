"""
Interface graphique moderne de l'application desktop d'administration et de cartographie réseau.
Développée avec un design Windows 11 / Slate moderne, fluide, sobre et professionnel.
Exécution 100% silencieuse sans aucune console parasite.
Boutons Démarrer et Arrêter empilés verticalement et mutuellement exclusifs.
Affichage Géant de l'Adresse IP du serveur, renommage dynamique du domaine mDNS,
création de point de restauration 1-clic (Snapshot) et déblocage Pare-Feu Windows.
"""

import os
import sys
import threading
import time
import webbrowser
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from typing import Dict, Any, List, Optional

from desktop_admin.core.docker_manager import DockerManager
from desktop_admin.core.health_checker import HealthChecker
from desktop_admin.core.network_scanner import NetworkScanner
from desktop_admin.core.pc_renamer import PCRenamer
from desktop_admin.core.mdns_broadcaster import MDNSBroadcaster
from desktop_admin.core.backup_manager import BackupManager

# Configuration CustomTkinter & Thème
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

FONT_FAMILY = "Segoe UI"

# Palette de couleurs sobre & moderne (Windows 11 Fluent / Slate & Deep Navy)
COLOR_BG_DARK = "#090d16"          # Deep Obsidian Slate
COLOR_PANEL_DARK = "#131b2e"       # Elevated Slate Card
COLOR_BORDER_DARK = "#1e293b"      # Slate Border
COLOR_TEXT_DARK = "#f8fafc"        # Crisp White
COLOR_MUTED_DARK = "#94a3b8"       # Slate Muted 400

COLOR_BG_LIGHT = "#f1f5f9"         # Slate Light 100
COLOR_PANEL_LIGHT = "#ffffff"      # Pure White
COLOR_BORDER_LIGHT = "#cbd5e1"     # Slate 300
COLOR_TEXT_LIGHT = "#0f172a"       # Slate Dark 900
COLOR_MUTED_LIGHT = "#64748b"      # Slate Muted 500

ACCENT_BLUE = "#3b82f6"            # Indigo Blue
ACCENT_BLUE_HOVER = "#2563eb"
STATUS_GREEN = "#059669"           # Vibrant Emerald
STATUS_GREEN_HOVER = "#047857"
STATUS_RED = "#dc2626"             # Crimson Red
STATUS_RED_HOVER = "#b91c1c"
STATUS_AMBER = "#d97706"           # Warm Amber
STATUS_DISABLED = "#1e293b"        # Disabled slate background

class ExamMasterApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configuration de la fenêtre principale
        self.title("Exam Control Master — Supervision Réseau & Contrôle Serveur")
        self.geometry("1200x820")
        self.minsize(1060, 740)
        self.configure(fg_color=(COLOR_BG_LIGHT, COLOR_BG_DARK))

        # Instanciation des moteurs métier
        self.renamer = PCRenamer()
        self.docker_mgr = DockerManager()
        self.health_checker = HealthChecker()
        self.scanner = NetworkScanner(renamer=self.renamer)
        self.mdns = MDNSBroadcaster(hostname="exam", port=8000)
        self.backup_mgr = BackupManager()

        # Démarrage de la diffusion mDNS (purement en mémoire réseau)
        self.mdns.start()

        # Variables d'état
        self.network_devices: List[Dict[str, Any]] = []
        self.is_scanning = False
        self.is_busy = False
        self.busy_operation_title = ""
        self.auto_refresh_active = True
        self.docker_is_up = False
        self.server_is_running = False
        self.last_telemetry: Dict[str, Any] = {}

        # Construction de l'interface graphique moderne
        self._build_header()
        self._build_docker_alert_banner()
        self._build_tabs()
        self._build_footer()

        # Gestion de fermeture propre
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Thread de télémétrie en arrière-plan (léger et non-bloquant)
        self.telemetry_thread = threading.Thread(target=self._telemetry_loop, daemon=True)
        self.telemetry_thread.start()

        # Scan réseau initial doux différé de 600ms
        self.after(600, self._initial_light_scan)

    # =========================================================================
    # EN-TÊTE ÉLÉGANT & NAVIGATION SUPÉRIEURE
    # =========================================================================
    def _build_header(self):
        """En-tête supérieur moderne avec statut en temps réel et bascule de thème."""
        header_frame = ctk.CTkFrame(
            self,
            height=70,
            corner_radius=0,
            fg_color=(COLOR_PANEL_LIGHT, COLOR_PANEL_DARK),
            border_width=1,
            border_color=(COLOR_BORDER_LIGHT, COLOR_BORDER_DARK)
        )
        header_frame.pack(fill="x", side="top", padx=0, pady=0)

        # Titre et Badge de statut
        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.pack(side="left", padx=20, pady=12)

        lbl_app = ctk.CTkLabel(
            title_box,
            text="🎓 EXAM CONTROL MASTER",
            font=ctk.CTkFont(family=FONT_FAMILY, size=18, weight="bold"),
            text_color=(COLOR_TEXT_LIGHT, COLOR_TEXT_DARK)
        )
        lbl_app.pack(side="left", padx=(0, 12))

        self.pill_status = ctk.CTkFrame(
            title_box,
            corner_radius=16,
            fg_color=("#fef3c7", "#291b00"),
            border_width=1,
            border_color=("#fde68a", "#78350f")
        )
        self.pill_status.pack(side="left", padx=0)

        self.lbl_global_status = ctk.CTkLabel(
            self.pill_status,
            text="● INITIALISATION...",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=("#b45309", "#fbbf24")
        )
        self.lbl_global_status.pack(padx=14, pady=4)

        # Actions à droite
        right_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        right_box.pack(side="right", padx=20, pady=12)

        self.theme_switch = ctk.CTkSwitch(
            right_box,
            text="Mode Sombre",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            command=self._toggle_theme,
            onvalue="Dark",
            offvalue="Light"
        )
        self.theme_switch.select()
        self.theme_switch.pack(side="right", padx=(14, 0))

        btn_open_browser = ctk.CTkButton(
            right_box,
            text="🌐 Ouvrir l'Examen",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            width=160,
            height=34,
            corner_radius=6,
            fg_color=ACCENT_BLUE,
            hover_color=ACCENT_BLUE_HOVER,
            command=self._open_web_browser
        )
        btn_open_browser.pack(side="right", padx=10)

    # =========================================================================
    # BANNIÈRE D'ÉTAT DOCKER (STABLE, SANS CLIGNOTEMENT)
    # =========================================================================
    def _build_docker_alert_banner(self):
        """Bannière d'état Docker sobre et rassurante."""
        self.banner_frame = ctk.CTkFrame(
            self,
            corner_radius=8,
            fg_color=("#fef3c7", "#1a1608"),
            border_width=1,
            border_color=("#f59e0b", "#78350f")
        )
        self.banner_frame.pack(fill="x", padx=18, pady=(10, 0))

        self.lbl_banner_title = ctk.CTkLabel(
            self.banner_frame,
            text="⏳ VÉRIFICATION DE DOCKER DESKTOP...",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=("#b45309", "#fbbf24")
        )
        self.lbl_banner_title.pack(anchor="w", padx=14, pady=(8, 2))

        self.lbl_banner_msg = ctk.CTkLabel(
            self.banner_frame,
            text="Détection du démon de conteneurisation en cours...",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=("#92400e", "#fde68a"),
            justify="left"
        )
        self.lbl_banner_msg.pack(anchor="w", padx=14, pady=(0, 8))

    # =========================================================================
    # ONGLETS DE NAVIGATION
    # =========================================================================
    def _build_tabs(self):
        """Onglets principaux de navigation."""
        self.tabview = ctk.CTkTabview(
            self,
            corner_radius=10,
            fg_color=(COLOR_PANEL_LIGHT, COLOR_PANEL_DARK),
            segmented_button_selected_color=ACCENT_BLUE,
            segmented_button_selected_hover_color=ACCENT_BLUE_HOVER,
            segmented_button_unselected_color=(COLOR_BORDER_LIGHT, COLOR_BORDER_DARK)
        )
        self.tabview.pack(fill="both", expand=True, padx=18, pady=10)

        self.tab_dash = self.tabview.add("📊 Tableau de Bord & Contrôle")
        self.tab_diag = self.tabview.add("🩺 Diagnostic & Résolution")
        self.tab_net = self.tabview.add("🌐 Cartographie Réseau & Renommage")
        self.tab_domain = self.tabview.add("🔗 Accès Convivial (Nom & IP)")
        self.tab_docker = self.tabview.add("📜 Journal & Sauvegardes")

        self._init_dashboard_tab()
        self._init_diag_tab()
        self._init_network_tab()
        self._init_domain_tab()
        self._init_docker_tab()

    # =========================================================================
    # ONGLET 1 : TABLEAU DE BORD & CONTRÔLE SERVEUR
    # =========================================================================
    def _init_dashboard_tab(self):
        container = ctk.CTkScrollableFrame(self.tab_dash, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=2, pady=2)

        # 1. EN-TÊTE GÉANT "HERO IP & ACCÈS RÉSEAU" (Demande de l'utilisateur)
        hero_ip_box = ctk.CTkFrame(
            container,
            corner_radius=10,
            fg_color=("#eef2ff", "#101b38"),
            border_width=1,
            border_color=("#c7d2fe", "#2563eb")
        )
        hero_ip_box.pack(fill="x", pady=(0, 12))

        hero_inner = ctk.CTkFrame(hero_ip_box, fg_color="transparent")
        hero_inner.pack(fill="x", padx=16, pady=12)

        # Ligne supérieure : Titre et sous-titre
        h_top = ctk.CTkFrame(hero_inner, fg_color="transparent")
        h_top.pack(fill="x")

        ctk.CTkLabel(
            h_top,
            text="📡 ADRESSE IP DU SERVEUR D'EXAMEN (À COMMUNIQUER EN SALLE) :",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=("#4338ca", "#93c5fd")
        ).pack(side="left")

        self.lbl_hero_iface = ctk.CTkLabel(
            h_top,
            text="Interface : Détection...",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=(COLOR_MUTED_LIGHT, COLOR_MUTED_DARK)
        )
        self.lbl_hero_iface.pack(side="right")

        # Ligne centrale : Affichage Grand Format de l'IP et du Nom Convivial
        h_mid = ctk.CTkFrame(hero_inner, fg_color="transparent")
        h_mid.pack(fill="x", pady=(6, 8))

        self.lbl_hero_ip = ctk.CTkLabel(
            h_mid,
            text="192.168.1.XX:8000",
            font=ctk.CTkFont(family=FONT_FAMILY, size=24, weight="bold"),
            text_color=ACCENT_BLUE
        )
        self.lbl_hero_ip.pack(side="left")

        ctk.CTkLabel(
            h_mid,
            text="   ou lien convivial :   ",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=(COLOR_MUTED_LIGHT, COLOR_MUTED_DARK)
        ).pack(side="left")

        self.lbl_hero_domain = ctk.CTkLabel(
            h_mid,
            text=f"http://{self.mdns.hostname}.local:8000",
            font=ctk.CTkFont(family=FONT_FAMILY, size=18, weight="bold"),
            text_color=STATUS_GREEN
        )
        self.lbl_hero_domain.pack(side="left")

        # Boutons d'action rapide sur l'IP
        h_btn_row = ctk.CTkFrame(hero_inner, fg_color="transparent")
        h_btn_row.pack(fill="x")

        btn_copy_ip_only = ctk.CTkButton(
            h_btn_row,
            text="📋 Copier IP Seule",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            width=130,
            height=28,
            corner_radius=4,
            fg_color=(COLOR_BORDER_LIGHT, "#1e293b"),
            hover_color=("#cbd5e1", "#334155"),
            text_color=(COLOR_TEXT_LIGHT, COLOR_TEXT_DARK),
            command=self._copy_ip_only
        )
        btn_copy_ip_only.pack(side="left", padx=(0, 8))

        btn_copy_full_url = ctk.CTkButton(
            h_btn_row,
            text="📋 Copier URL Complète",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            width=150,
            height=28,
            corner_radius=4,
            fg_color=(COLOR_BORDER_LIGHT, "#1e293b"),
            hover_color=("#cbd5e1", "#334155"),
            text_color=(COLOR_TEXT_LIGHT, COLOR_TEXT_DARK),
            command=self._copy_full_ip_url
        )
        btn_copy_full_url.pack(side="left", padx=(0, 8))

        btn_copy_domain = ctk.CTkButton(
            h_btn_row,
            text="📋 Copier Lien .local",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            width=140,
            height=28,
            corner_radius=4,
            fg_color=(COLOR_BORDER_LIGHT, "#1e293b"),
            hover_color=("#cbd5e1", "#334155"),
            text_color=(COLOR_TEXT_LIGHT, COLOR_TEXT_DARK),
            command=self._copy_url
        )
        btn_copy_domain.pack(side="left", padx=(0, 8))

        btn_test_open = ctk.CTkButton(
            h_btn_row,
            text="🌐 Tester dans Navigateur",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            width=170,
            height=28,
            corner_radius=4,
            fg_color=ACCENT_BLUE,
            hover_color=ACCENT_BLUE_HOVER,
            command=self._open_web_browser
        )
        btn_test_open.pack(side="left")

        # Ligne LAN Câblé dédiée (Déblocage Switch/Ethernet)
        lan_bar = ctk.CTkFrame(hero_inner, fg_color="transparent")
        lan_bar.pack(fill="x", pady=(8, 0))

        self.lbl_lan_status = ctk.CTkLabel(
            lan_bar,
            text="🔌 Réseau Câblé (Ethernet LAN) : Détection...",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=(COLOR_MUTED_LIGHT, COLOR_MUTED_DARK)
        )
        self.lbl_lan_status.pack(side="left")

        btn_unlock_lan = ctk.CTkButton(
            lan_bar,
            text="🚀 Débloquer Accès Câblé (LAN)",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            width=210,
            height=26,
            corner_radius=4,
            fg_color=STATUS_GREEN,
            hover_color=STATUS_GREEN_HOVER,
            command=self._action_unlock_lan
        )
        btn_unlock_lan.pack(side="right")

        # 2. Bannière d'activité en direct
        self.activity_banner = ctk.CTkFrame(
            container,
            corner_radius=8,
            fg_color=("#e0f2fe", "#082f49"),
            border_width=1,
            border_color=("#7dd3fc", "#0369a1")
        )
        self.activity_banner.pack(fill="x", pady=(0, 12))

        act_inner = ctk.CTkFrame(self.activity_banner, fg_color="transparent")
        act_inner.pack(fill="x", padx=14, pady=10)

        self.lbl_activity_title = ctk.CTkLabel(
            act_inner,
            text="🟢 SYSTÈME PRÊT",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=("#0369a1", "#38bdf8")
        )
        self.lbl_activity_title.pack(anchor="w")

        self.lbl_activity_detail = ctk.CTkLabel(
            act_inner,
            text="Le tableau de bord est opérationnel. Prêt pour les actions de démarrage ou de surveillance.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=("#0284c7", "#bae6fd"),
            justify="left"
        )
        self.lbl_activity_detail.pack(anchor="w", pady=(2, 4))

        self.prog_activity = ctk.CTkProgressBar(act_inner, height=4, corner_radius=2, progress_color=ACCENT_BLUE)
        self.prog_activity.set(0)
        self.prog_activity.pack(fill="x", pady=(4, 0))

        # 3. Grille principale : Contrôle Serveur (Gauche) & Télémétrie / Sauvegarde (Droite)
        grid_frame = ctk.CTkFrame(container, fg_color="transparent")
        grid_frame.pack(fill="both", expand=True, pady=(0, 10))
        grid_frame.grid_columnconfigure(0, weight=4)  # Contrôle Serveur (35%)
        grid_frame.grid_columnconfigure(1, weight=6)  # Télémétrie & Snapshots (65%)

        # =====================================================================
        # COLONNE GAUCHE : CONTRÔLE SERVEUR (BOUTONS EMPILÉS VERTICALEMENT)
        # =====================================================================
        col_left = ctk.CTkFrame(
            grid_frame,
            corner_radius=10,
            fg_color=(COLOR_PANEL_LIGHT, COLOR_PANEL_DARK),
            border_width=1,
            border_color=(COLOR_BORDER_LIGHT, COLOR_BORDER_DARK)
        )
        col_left.grid(row=0, column=0, padx=(0, 8), sticky="nsew")

        ctk.CTkLabel(
            col_left,
            text="⚡ Contrôle du Serveur d'Examen",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold")
        ).pack(anchor="w", padx=16, pady=(14, 6))

        ctk.CTkLabel(
            col_left,
            text="Boutons de cycle de vie mutuellement exclusifs :",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=(COLOR_MUTED_LIGHT, COLOR_MUTED_DARK)
        ).pack(anchor="w", padx=16, pady=(0, 12))

        # BOUTON 1 (EN HAUT) : DÉMARRER LE SERVEUR
        self.btn_start = ctk.CTkButton(
            col_left,
            text="▶ DÉMARRER LE SERVEUR",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            height=46,
            corner_radius=8,
            fg_color=STATUS_GREEN,
            hover_color=STATUS_GREEN_HOVER,
            command=self._action_start_docker
        )
        self.btn_start.pack(fill="x", padx=16, pady=(0, 10))

        # BOUTON 2 (EN DESSOUS) : ARRÊTER LE SERVEUR
        self.btn_stop = ctk.CTkButton(
            col_left,
            text="⏹ ARRÊTER LE SERVEUR",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            height=46,
            corner_radius=8,
            fg_color=STATUS_RED,
            hover_color=STATUS_RED_HOVER,
            command=self._action_stop_docker
        )
        self.btn_stop.pack(fill="x", padx=16, pady=(0, 12))

        # Séparateur discret
        sep = ctk.CTkFrame(col_left, height=1, fg_color=(COLOR_BORDER_LIGHT, COLOR_BORDER_DARK))
        sep.pack(fill="x", padx=16, pady=(0, 10))

        # Boutons secondaires
        sub_row = ctk.CTkFrame(col_left, fg_color="transparent")
        sub_row.pack(fill="x", padx=16, pady=(0, 12))
        sub_row.grid_columnconfigure((0, 1), weight=1)

        self.btn_restart = ctk.CTkButton(
            sub_row,
            text="🔄 Redémarrer",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            height=32,
            corner_radius=6,
            fg_color=(COLOR_BORDER_LIGHT, "#1e293b"),
            hover_color=("#cbd5e1", "#334155"),
            text_color=(COLOR_TEXT_LIGHT, COLOR_TEXT_DARK),
            command=self._action_restart_docker
        )
        self.btn_restart.grid(row=0, column=0, padx=(0, 4), sticky="ew")

        self.btn_load_tar = ctk.CTkButton(
            sub_row,
            text="📥 Importer .tar",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            height=32,
            corner_radius=6,
            fg_color=ACCENT_BLUE,
            hover_color=ACCENT_BLUE_HOVER,
            command=self._action_load_tar
        )
        self.btn_load_tar.grid(row=0, column=1, padx=(4, 0), sticky="ew")

        # Mini journal d'activité
        ctk.CTkLabel(
            col_left,
            text="Événements récents :",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=(COLOR_MUTED_LIGHT, COLOR_MUTED_DARK)
        ).pack(anchor="w", padx=16, pady=(0, 4))

        self.txt_mini_log = ctk.CTkTextbox(
            col_left,
            height=85,
            corner_radius=6,
            font=ctk.CTkFont(family="Consolas", size=10),
            fg_color=(COLOR_BG_LIGHT, "#070c18")
        )
        self.txt_mini_log.pack(fill="x", padx=16, pady=(0, 14))
        self.txt_mini_log.insert("end", "[Info] Exam Control Master prêt.\n")

        # =====================================================================
        # COLONNE DROITE : TÉLÉMÉTRIE & SAUVEGARDE 1-CLIC (SNAPSHOT ITEM 4)
        # =====================================================================
        col_right = ctk.CTkFrame(grid_frame, fg_color="transparent")
        col_right.grid(row=0, column=1, padx=(8, 0), sticky="nsew")

        # 1. Cartes de statut en ligne
        stat_cards = ctk.CTkFrame(col_right, fg_color="transparent")
        stat_cards.pack(fill="x", pady=(0, 10))
        stat_cards.grid_columnconfigure((0, 1), weight=1)

        self.card_docker = self._create_card(stat_cards, 0, 0)
        ctk.CTkLabel(self.card_docker, text="🐳 Démon Docker", font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"), text_color=(COLOR_MUTED_LIGHT, COLOR_MUTED_DARK)).pack(anchor="w", padx=14, pady=(10, 2))
        self.lbl_docker_state = ctk.CTkLabel(self.card_docker, text="Vérification...", font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"))
        self.lbl_docker_state.pack(anchor="w", padx=14, pady=(0, 10))

        self.card_server = self._create_card(stat_cards, 0, 1)
        ctk.CTkLabel(self.card_server, text="⚡ Serveur d'Examen", font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"), text_color=(COLOR_MUTED_LIGHT, COLOR_MUTED_DARK)).pack(anchor="w", padx=14, pady=(10, 2))
        self.lbl_server_state = ctk.CTkLabel(self.card_server, text="Vérification...", font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"))
        self.lbl_server_state.pack(anchor="w", padx=14, pady=(0, 10))

        # 2. Panneau Snapshot Base de Données 1-Clic (Amélioration Item 4)
        snap_box = ctk.CTkFrame(
            col_right,
            corner_radius=10,
            fg_color=(COLOR_PANEL_LIGHT, COLOR_PANEL_DARK),
            border_width=1,
            border_color=(COLOR_BORDER_LIGHT, COLOR_BORDER_DARK)
        )
        snap_box.pack(fill="x", pady=(0, 10))

        snap_inner = ctk.CTkFrame(snap_box, fg_color="transparent")
        snap_inner.pack(fill="x", padx=16, pady=12)

        s_top = ctk.CTkFrame(snap_inner, fg_color="transparent")
        s_top.pack(fill="x")

        ctk.CTkLabel(
            s_top,
            text="🛡️ Sauvegarde & Point de Restauration (Snapshot 1-Clic)",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold")
        ).pack(side="left")

        self.btn_snapshot = ctk.CTkButton(
            s_top,
            text="📸 Créer Snapshot Base",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            width=160,
            height=28,
            corner_radius=6,
            fg_color=ACCENT_BLUE,
            hover_color=ACCENT_BLUE_HOVER,
            command=self._action_create_snapshot
        )
        self.btn_snapshot.pack(side="right")

        self.lbl_snap_info = ctk.CTkLabel(
            snap_inner,
            text="Créez un point de restauration complet avant l'examen pour garantir 0 perte de données.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=(COLOR_MUTED_LIGHT, COLOR_MUTED_DARK)
        )
        self.lbl_snap_info.pack(anchor="w", pady=(4, 0))

        # 3. Télémétrie en temps réel
        telem_box = ctk.CTkFrame(
            col_right,
            corner_radius=10,
            fg_color=(COLOR_PANEL_LIGHT, COLOR_PANEL_DARK),
            border_width=1,
            border_color=(COLOR_BORDER_LIGHT, COLOR_BORDER_DARK)
        )
        telem_box.pack(fill="x")

        ctk.CTkLabel(
            telem_box,
            text="📈 Télémétrie Serveur & Ressources Hôte",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold")
        ).pack(anchor="w", padx=16, pady=(10, 4))

        gauges_frame = ctk.CTkFrame(telem_box, fg_color="transparent")
        gauges_frame.pack(fill="x", padx=16, pady=(0, 12))
        gauges_frame.grid_columnconfigure((0, 1), weight=1)

        f_cpu = ctk.CTkFrame(gauges_frame, fg_color="transparent")
        f_cpu.grid(row=0, column=0, padx=(0, 8), pady=2, sticky="ew")
        self.lbl_cpu_val = ctk.CTkLabel(f_cpu, text="CPU : 0%", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.lbl_cpu_val.pack(anchor="w")
        self.prog_cpu = ctk.CTkProgressBar(f_cpu, height=6, corner_radius=3, progress_color=ACCENT_BLUE)
        self.prog_cpu.set(0)
        self.prog_cpu.pack(fill="x", pady=2)

        f_ram = ctk.CTkFrame(gauges_frame, fg_color="transparent")
        f_ram.grid(row=0, column=1, padx=(8, 0), pady=2, sticky="ew")
        self.lbl_ram_val = ctk.CTkLabel(f_ram, text="RAM : 0 Mo", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.lbl_ram_val.pack(anchor="w")
        self.prog_ram = ctk.CTkProgressBar(f_ram, height=6, corner_radius=3, progress_color=STATUS_GREEN)
        self.prog_ram.set(0)
        self.prog_ram.pack(fill="x", pady=2)

        f_stats = ctk.CTkFrame(gauges_frame, fg_color="transparent")
        f_stats.grid(row=1, column=0, columnspan=2, pady=(4, 0), sticky="ew")
        f_stats.grid_columnconfigure((0, 1), weight=1)

        self.lbl_req_val = ctk.CTkLabel(f_stats, text="Requêtes : 0", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color=ACCENT_BLUE)
        self.lbl_req_val.grid(row=0, column=0, sticky="w")

        self.lbl_net_val = ctk.CTkLabel(f_stats, text="Trafic : ↓ 0 Ko/s  ↑ 0 Ko/s", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.lbl_net_val.grid(row=0, column=1, sticky="e")

    # =========================================================================
    # ONGLET 2 : DIAGNOSTIC & RÉSOLUTION (AVEC PARE-FEU ITEM 8)
    # =========================================================================
    def _init_diag_tab(self):
        container = ctk.CTkScrollableFrame(self.tab_diag, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=2, pady=2)

        top_d = ctk.CTkFrame(container, fg_color="transparent")
        top_d.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            top_d,
            text="🩺 Diagnostic de Santé & Aide à la Résolution",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold")
        ).pack(side="left")

        btn_refresh_diag = ctk.CTkButton(
            top_d,
            text="🔄 Actualiser Diagnostic",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            width=160,
            height=32,
            corner_radius=6,
            fg_color=ACCENT_BLUE,
            hover_color=ACCENT_BLUE_HOVER,
            command=self._refresh_diagnosis
        )
        btn_refresh_diag.pack(side="right")

        self.diag_container = ctk.CTkFrame(container, fg_color="transparent")
        self.diag_container.pack(fill="both", expand=True)

        self._refresh_diagnosis()

    def _create_card(self, parent, row, col):
        card = ctk.CTkFrame(
            parent,
            corner_radius=8,
            fg_color=(COLOR_PANEL_LIGHT, COLOR_PANEL_DARK),
            border_width=1,
            border_color=(COLOR_BORDER_LIGHT, COLOR_BORDER_DARK)
        )
        card.grid(row=row, column=col, padx=4, pady=0, sticky="nsew")
        return card

    # =========================================================================
    # ONGLET 3 : CARTOGRAPHIE RÉSEAU & RENOMMAGE (APPROCHE 1)
    # =========================================================================
    def _init_network_tab(self):
        container = ctk.CTkFrame(self.tab_net, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=2, pady=2)

        top_bar = ctk.CTkFrame(container, fg_color="transparent")
        top_bar.pack(fill="x", padx=4, pady=(0, 10))

        self.btn_scan = ctk.CTkButton(
            top_bar,
            text="🔍 Lancer le Scan Réseau",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            width=180,
            height=34,
            corner_radius=6,
            fg_color=ACCENT_BLUE,
            hover_color=ACCENT_BLUE_HOVER,
            command=self._trigger_network_scan
        )
        self.btn_scan.pack(side="left", padx=(0, 10))

        self.search_entry = ctk.CTkEntry(
            top_bar,
            placeholder_text="Filtrer par IP, MAC ou Nom...",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            width=200,
            height=34
        )
        self.search_entry.pack(side="left", padx=(0, 10))
        self.search_entry.bind("<KeyRelease>", self._on_filter_search)

        self.lbl_scan_info = ctk.CTkLabel(
            top_bar,
            text="Prêt à scanner le réseau de la salle.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=(COLOR_MUTED_LIGHT, COLOR_MUTED_DARK)
        )
        self.lbl_scan_info.pack(side="left", padx=5)

        btn_export = ctk.CTkButton(
            top_bar,
            text="📥 Exporter CSV",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            width=110,
            height=34,
            corner_radius=6,
            fg_color=(COLOR_BORDER_LIGHT, COLOR_BORDER_DARK),
            hover_color=("#cbd5e1", "#475569"),
            text_color=(COLOR_TEXT_LIGHT, COLOR_TEXT_DARK),
            command=self._export_topology
        )
        btn_export.pack(side="right", padx=(6, 0))

        btn_import = ctk.CTkButton(
            top_bar,
            text="📤 Importer CSV",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            width=110,
            height=34,
            corner_radius=6,
            fg_color=(COLOR_BORDER_LIGHT, COLOR_BORDER_DARK),
            hover_color=("#cbd5e1", "#475569"),
            text_color=(COLOR_TEXT_LIGHT, COLOR_TEXT_DARK),
            command=self._import_topology
        )
        btn_import.pack(side="right", padx=6)

        table_hdr = ctk.CTkFrame(
            container,
            height=36,
            corner_radius=6,
            fg_color=(COLOR_BORDER_LIGHT, "#162032"),
            border_width=1,
            border_color=(COLOR_BORDER_LIGHT, COLOR_BORDER_DARK)
        )
        table_hdr.pack(fill="x", padx=4, pady=(0, 4))
        table_hdr.grid_columnconfigure((0, 1, 2, 3, 4, 5, 6), weight=1)

        headers = ["IP Locale", "Adresse MAC", "Nom d'Hôte OS", "Nom Convivial (Salle)", "Latence", "Statut", "Action"]
        for col_idx, h in enumerate(headers):
            lbl = ctk.CTkLabel(
                table_hdr,
                text=h,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
                text_color=(COLOR_TEXT_LIGHT, COLOR_TEXT_DARK)
            )
            lbl.grid(row=0, column=col_idx, padx=6, pady=6, sticky="w" if col_idx < 4 else "")

        self.network_table_body = ctk.CTkScrollableFrame(
            container,
            corner_radius=6,
            fg_color=(COLOR_PANEL_LIGHT, "#0f172a"),
            border_width=1,
            border_color=(COLOR_BORDER_LIGHT, COLOR_BORDER_DARK)
        )
        self.network_table_body.pack(fill="both", expand=True, padx=4, pady=0)

    # =========================================================================
    # ONGLET 4 : ACCÈS CONVIVIAL (RENOMMAGE DYNAMIQUE & SÉLECTEUR IP)
    # =========================================================================
    def _init_domain_tab(self):
        container = ctk.CTkScrollableFrame(self.tab_domain, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=2, pady=2)

        # 1. CARTE DE PERSONNALISATION DU NOM DE DOMAINE (Demande de l'utilisateur)
        rename_box = ctk.CTkFrame(
            container,
            corner_radius=10,
            fg_color=(COLOR_PANEL_LIGHT, COLOR_PANEL_DARK),
            border_width=1,
            border_color=(COLOR_BORDER_LIGHT, COLOR_BORDER_DARK)
        )
        rename_box.pack(fill="x", padx=4, pady=(0, 12))

        r_inner = ctk.CTkFrame(rename_box, fg_color="transparent")
        r_inner.pack(fill="x", padx=16, pady=14)

        ctk.CTkLabel(
            r_inner,
            text="🏷️ Personnalisation du Nom d'Accès Convivial (mDNS)",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold")
        ).pack(anchor="w")

        ctk.CTkLabel(
            r_inner,
            text="Vous pouvez changer le nom de domaine de la salle en direct (ex: 'quiz', 'exam', 'concours-2026') :\nLe changement est immédiat et ne nécessite pas de redémarrer le serveur.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=(COLOR_MUTED_LIGHT, COLOR_MUTED_DARK)
        ).pack(anchor="w", pady=(2, 10))

        # Formulaire de renommage
        form_row = ctk.CTkFrame(r_inner, fg_color="transparent")
        form_row.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(
            form_row,
            text="http://",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=ACCENT_BLUE
        ).pack(side="left")

        self.entry_custom_name = ctk.CTkEntry(
            form_row,
            placeholder_text="nom-examen",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            width=220,
            height=34
        )
        self.entry_custom_name.insert(0, self.mdns.hostname)
        self.entry_custom_name.pack(side="left", padx=6)

        ctk.CTkLabel(
            form_row,
            text=f".local:{self.mdns.port}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=ACCENT_BLUE
        ).pack(side="left", padx=(0, 12))

        btn_apply_name = ctk.CTkButton(
            form_row,
            text="💾 Appliquer Nouveau Nom",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            width=180,
            height=34,
            corner_radius=6,
            fg_color=STATUS_GREEN,
            hover_color=STATUS_GREEN_HOVER,
            command=self._apply_custom_domain_name
        )
        btn_apply_name.pack(side="left")

        self.lbl_domain_feedback = ctk.CTkLabel(
            r_inner,
            text=f"Diffusion active sur le réseau : http://{self.mdns.hostname}.local:8000",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=STATUS_GREEN
        )
        self.lbl_domain_feedback.pack(anchor="w", pady=(6, 0))

        # 2. SÉLECTEUR DE CARTE RÉSEAU (Ethernet vs Wi-Fi)
        iface_box = ctk.CTkFrame(
            container,
            corner_radius=10,
            fg_color=(COLOR_PANEL_LIGHT, COLOR_PANEL_DARK),
            border_width=1,
            border_color=(COLOR_BORDER_LIGHT, COLOR_BORDER_DARK)
        )
        iface_box.pack(fill="x", padx=4, pady=(0, 12))

        i_inner = ctk.CTkFrame(iface_box, fg_color="transparent")
        i_inner.pack(fill="x", padx=16, pady=14)

        ctk.CTkLabel(
            i_inner,
            text="🔌 Sélection de l'Interface Réseau Serveur",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold")
        ).pack(anchor="w")

        ctk.CTkLabel(
            i_inner,
            text="Si votre ordinateur dispose à la fois d'un câble Ethernet et du Wi-Fi, sélectionnez la carte de la salle :",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=(COLOR_MUTED_LIGHT, COLOR_MUTED_DARK)
        ).pack(anchor="w", pady=(2, 8))

        ifaces = self.mdns.list_network_interfaces()
        iface_options = [i["display"] for i in ifaces] if ifaces else ["Interface Principale"]
        
        self.combo_ifaces = ctk.CTkComboBox(
            i_inner,
            values=iface_options,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            width=420,
            height=34,
            command=self._on_iface_selected
        )
        if iface_options:
            self.combo_ifaces.set(iface_options[0])
        self.combo_ifaces.pack(anchor="w", pady=(0, 6))

        # 3. Secours par script clé USB
        backup_box = ctk.CTkFrame(
            container,
            corner_radius=10,
            fg_color=(COLOR_PANEL_LIGHT, COLOR_PANEL_DARK),
            border_width=1,
            border_color=(COLOR_BORDER_LIGHT, COLOR_BORDER_DARK)
        )
        backup_box.pack(fill="x", padx=4)

        ctk.CTkLabel(
            backup_box,
            text="🛠️ Script de Secours pour Postes Étudiants",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold")
        ).pack(anchor="w", padx=16, pady=(14, 4))

        ctk.CTkLabel(
            backup_box,
            text="Si le switch réseau bloque les paquets multicast mDNS (UDP 5353),\ngénérez ce script sur clé USB : un double-clic sur le poste étudiant résout immédiatement l'adresse.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=(COLOR_MUTED_LIGHT, COLOR_MUTED_DARK)
        ).pack(anchor="w", padx=16, pady=(0, 10))

        btn_gen_script = ctk.CTkButton(
            backup_box,
            text="💾 Enregistrer 'installer_nom_local.bat' pour Clé USB",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            width=360,
            height=34,
            corner_radius=6,
            fg_color=(COLOR_BORDER_LIGHT, COLOR_BORDER_DARK),
            hover_color=("#cbd5e1", "#475569"),
            text_color=(COLOR_TEXT_LIGHT, COLOR_TEXT_DARK),
            command=self._generate_hosts_script
        )
        btn_gen_script.pack(anchor="w", padx=16, pady=(0, 14))

    # =========================================================================
    # ONGLET 5 : JOURNAL & MAINTENANCE DOCKER
    # =========================================================================
    def _init_docker_tab(self):
        container = ctk.CTkScrollableFrame(self.tab_docker, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=2, pady=2)

        # Boîte de mise à jour par archive .tar
        update_box = ctk.CTkFrame(
            container,
            corner_radius=10,
            fg_color=(COLOR_PANEL_LIGHT, COLOR_PANEL_DARK),
            border_width=1,
            border_color=(COLOR_BORDER_LIGHT, COLOR_BORDER_DARK)
        )
        update_box.pack(fill="x", padx=4, pady=(0, 12))

        ctk.CTkLabel(
            update_box,
            text="📦 Mise à Jour d'Image Hors-Ligne (Clé USB)",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold")
        ).pack(anchor="w", padx=16, pady=(12, 4))

        ctk.CTkLabel(
            update_box,
            text="Chargez l'archive '.tar' de l'image 'examination-quiz-server' sans dépendance à Internet :",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=(COLOR_MUTED_LIGHT, COLOR_MUTED_DARK)
        ).pack(anchor="w", padx=16, pady=(0, 10))

        up_row = ctk.CTkFrame(update_box, fg_color="transparent")
        up_row.pack(fill="x", padx=16, pady=(0, 14))

        self.entry_tar_path = ctk.CTkEntry(
            up_row,
            placeholder_text="Chemin vers le fichier image archive (.tar)...",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            height=34
        )
        self.entry_tar_path.pack(side="left", fill="x", expand=True, padx=(0, 8))

        btn_browse = ctk.CTkButton(
            up_row,
            text="Parcourir...",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            width=90,
            height=34,
            corner_radius=6,
            fg_color=(COLOR_BORDER_LIGHT, COLOR_BORDER_DARK),
            hover_color=("#cbd5e1", "#475569"),
            text_color=(COLOR_TEXT_LIGHT, COLOR_TEXT_DARK),
            command=self._browse_tar_file
        )
        btn_browse.pack(side="left", padx=(0, 8))

        self.btn_apply_update = ctk.CTkButton(
            up_row,
            text="🚀 Appliquer Mise à Jour",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            width=170,
            height=34,
            corner_radius=6,
            fg_color=STATUS_GREEN,
            hover_color=STATUS_GREEN_HOVER,
            command=self._apply_docker_update
        )
        self.btn_apply_update.pack(side="left")

        # Journal complet
        log_box = ctk.CTkFrame(
            container,
            corner_radius=10,
            fg_color=(COLOR_PANEL_LIGHT, COLOR_PANEL_DARK),
            border_width=1,
            border_color=(COLOR_BORDER_LIGHT, COLOR_BORDER_DARK)
        )
        log_box.pack(fill="both", expand=True, padx=4)

        ctk.CTkLabel(
            log_box,
            text="📜 Journal Détaillé des Opérations Docker",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold")
        ).pack(anchor="w", padx=16, pady=(12, 4))

        self.txt_docker_logs = ctk.CTkTextbox(
            log_box,
            height=260,
            corner_radius=6,
            font=ctk.CTkFont(family="Consolas", size=10),
            fg_color=(COLOR_BG_LIGHT, "#070c18")
        )
        self.txt_docker_logs.pack(fill="both", expand=True, padx=16, pady=(0, 14))
        self.txt_docker_logs.insert("end", "[Système] Journal prêt. Les opérations détaillées s'afficheront ici.\n")

    # =========================================================================
    # PIED DE PAGE
    # =========================================================================
    def _build_footer(self):
        """Pied de page sobre avec IP locale et statut mDNS."""
        footer_frame = ctk.CTkFrame(
            self,
            height=30,
            corner_radius=0,
            fg_color=(COLOR_PANEL_LIGHT, "#070c18"),
            border_width=1,
            border_color=(COLOR_BORDER_LIGHT, COLOR_BORDER_DARK)
        )
        footer_frame.pack(fill="x", side="bottom")

        self.lbl_footer_ip = ctk.CTkLabel(
            footer_frame,
            text=f"IP Serveur : {self.mdns.get_local_ip()}  |  Port : 8000  |  mDNS : {self.mdns.hostname}.local",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=(COLOR_MUTED_LIGHT, COLOR_MUTED_DARK)
        )
        self.lbl_footer_ip.pack(side="left", padx=16)

        self.lbl_footer_sync = ctk.CTkLabel(
            footer_frame,
            text="Synchronisation : En cours...",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=(COLOR_MUTED_LIGHT, COLOR_MUTED_DARK)
        )
        self.lbl_footer_sync.pack(side="right", padx=16)

    # =========================================================================
    # ACTIONS RÉSEAU & NOM DYNAMIQUE
    # =========================================================================
    def _apply_custom_domain_name(self):
        new_name = self.entry_custom_name.get().strip()
        res = self.mdns.set_hostname(new_name)
        if res["success"]:
            self.lbl_domain_feedback.configure(
                text=f"✅ Nouveau nom actif : {res['full_url']}",
                text_color=STATUS_GREEN
            )
            self.lbl_hero_domain.configure(text=res["full_url"])
            self.lbl_footer_ip.configure(
                text=f"IP Serveur : {self.mdns.get_local_ip()}  |  Port : 8000  |  mDNS : {self.mdns.hostname}.local"
            )
            messagebox.showinfo(
                "Nom de Domaine Mis à Jour",
                f"L'adresse de la salle a été modifiée avec succès !\n\nNouveau lien : {res['full_url']}\n\nLa diffusion sur le réseau local a été actualisée instantanément."
            )
        else:
            self.lbl_domain_feedback.configure(
                text=f"❌ {res['message']}",
                text_color=STATUS_RED
            )
            messagebox.showerror("Erreur de Nom", res["message"])

    def _on_iface_selected(self, choice: str):
        ifaces = self.mdns.list_network_interfaces()
        for i in ifaces:
            if i["display"] == choice:
                self.mdns.set_selected_ip(i["ip"])
                self.lbl_hero_ip.configure(text=f"{i['ip']}:8000")
                self.lbl_hero_iface.configure(text=f"Interface : {i['name']} ({i['type_label']})")
                self.lbl_footer_ip.configure(
                    text=f"IP Serveur : {i['ip']}  |  Port : 8000  |  mDNS : {self.mdns.hostname}.local"
                )
                self._append_log(f"[Réseau] Carte active sélectionnée : {i['name']} ({i['ip']})")
                break

    def _copy_ip_only(self):
        ip = self.mdns.get_local_ip()
        self.clipboard_clear()
        self.clipboard_append(ip)
        messagebox.showinfo("Presse-papier", f"L'adresse IP brute '{ip}' a été copiée !")

    def _copy_full_ip_url(self):
        url = f"http://{self.mdns.get_local_ip()}:8000"
        self.clipboard_clear()
        self.clipboard_append(url)
        messagebox.showinfo("Presse-papier", f"L'URL complète '{url}' a été copiée !")

    def _copy_url(self):
        url = f"http://{self.mdns.hostname}.local:8000"
        self.clipboard_clear()
        self.clipboard_append(url)
        messagebox.showinfo("Presse-papier", f"L'adresse '{url}' a été copiée !")

    # =========================================================================
    # ACTIONS SAUVEGARDE 1-CLIC (SNAPSHOT ITEM 4)
    # =========================================================================
    def _action_create_snapshot(self):
        self._append_log("[Snapshot] Création d'un point de restauration de la base de données...")
        res = self.backup_mgr.create_snapshot(label="Avant_Epreuve")
        if res["success"]:
            meta = res["meta"]
            self.lbl_snap_info.configure(
                text=f"✅ Dernier snapshot : {meta['timestamp']} ({meta['size_kb']} Ko - {meta['type']})",
                text_color=STATUS_GREEN
            )
            self._append_log(f"[Snapshot Réussi] {res['message']} -> {meta['filename']}")
            messagebox.showinfo("Point de Restauration Créé", f"{res['message']}\n\nFichier : {meta['filename']}")
        else:
            self._append_log(f"[Snapshot Échec] {res['message']}")
            messagebox.showwarning("Avertissement Snapshot", res["message"])

    # =========================================================================
    # BOUCLE DE TÉLÉMÉTRIE (LÉGÈRE & SILENCIEUSE, SANS FAUX POSITIFS)
    # =========================================================================
    def _telemetry_loop(self):
        while self.auto_refresh_active:
            try:
                docker_state = self.docker_mgr.is_docker_running()
                telemetry = self.health_checker.get_server_telemetry()
                self.after(0, self._update_ui_telemetry, telemetry, docker_state)
            except Exception:
                pass
            time.sleep(3.0)

    def _update_ui_telemetry(self, t: Dict[str, Any], d: Dict[str, Any]):
        self.last_telemetry = t
        
        # Jauges CPU & RAM
        cpu = t.get("host_cpu_percent", 0.0)
        self.prog_cpu.set(cpu / 100.0)
        self.lbl_cpu_val.configure(text=f"Charge CPU : {cpu:.1f}%")

        mem_pct = t.get("host_mem_percent", 0.0)
        self.prog_ram.set(mem_pct / 100.0)
        self.lbl_ram_val.configure(
            text=f"RAM : {t.get('host_mem_used_mb', 0):.0f} Mo / {t.get('host_mem_total_mb', 0):.0f} Mo ({mem_pct:.0f}%)"
        )

        reqs = t.get("total_requests_received", 0)
        self.lbl_req_val.configure(text=f"Requêtes : {reqs}")

        self.lbl_net_val.configure(
            text=f"Trafic : ↓ {t.get('net_kb_recv_per_sec', 0)} Ko/s  ↑ {t.get('net_kb_sent_per_sec', 0)} Ko/s"
        )

        # Mise à jour Hero IP
        curr_ip = self.mdns.get_local_ip()
        self.lbl_hero_ip.configure(text=f"{curr_ip}:8000")
        self.lbl_hero_domain.configure(text=f"http://{self.mdns.hostname}.local:8000")

        # Mise à jour du statut Réseau Câblé (Ethernet LAN)
        if hasattr(self, 'lbl_lan_status'):
            eth = self.health_checker.lan_unlocker.get_physical_ethernet_info()
            if eth["is_connected"]:
                apipa_note = " ⚠️ [IP APIPA - Switch sans DHCP]" if eth["is_apipa"] else ""
                cat_note = f" [{eth['category']}]" if eth.get('category') else ""
                self.lbl_lan_status.configure(
                    text=f"🔌 Câble Réseau Détecté : {eth['name']} ({eth['ip']}){cat_note}{apipa_note}",
                    text_color=STATUS_AMBER if eth["is_apipa"] or eth.get("category") == "Public" else STATUS_GREEN
                )
            else:
                self.lbl_lan_status.configure(
                    text=f"🔌 Carte Ethernet : {eth['name']} (Câble non branché sur le switch)",
                    text_color=COLOR_MUTED_DARK
                )

        # État Docker
        is_docker_up = d.get("running", False)
        self.docker_is_up = is_docker_up

        if is_docker_up:
            self.card_docker.configure(border_color=STATUS_GREEN)
            self.lbl_docker_state.configure(text=f"🟢 En ligne (v{d.get('version', '')})", text_color=STATUS_GREEN)
            
            self.banner_frame.configure(fg_color=("#ecfdf5", "#042f2e"), border_color=("#a7f3d0", "#059669"))
            self.lbl_banner_title.configure(text="🟢 DOCKER DESKTOP EST OPÉRATIONNEL", text_color=("#065f46", "#34d399"))
            self.lbl_banner_msg.configure(
                text="Le moteur Docker est actif. Le serveur et la base de données peuvent être pilotés.",
                text_color=("#047857", "#a7f3d0")
            )
        else:
            self.card_docker.configure(border_color=STATUS_AMBER)
            self.lbl_docker_state.configure(text="⏸️ Non démarré", text_color=STATUS_AMBER)
            
            self.banner_frame.configure(fg_color=("#fef3c7", "#1a1608"), border_color=("#f59e0b", "#78350f"))
            self.lbl_banner_title.configure(text="⚠️ DOCKER DESKTOP N'EST PAS LANCÉ", text_color=("#b45309", "#fbbf24"))
            self.lbl_banner_msg.configure(
                text="Veuillez ouvrir Docker Desktop sous Windows. L'application se synchronisera automatiquement dès qu'il sera prêt.",
                text_color=("#92400e", "#fde68a")
            )

        # État du Serveur d'Examen (Port 8000)
        api_up = t.get("api_online", False)
        self.server_is_running = api_up

        if api_up:
            lat = t.get("api_latency_ms")
            lat_str = f" ({lat} ms)" if lat is not None else ""
            self.card_server.configure(border_color=STATUS_GREEN)
            self.lbl_server_state.configure(text=f"🟢 En Ligne (Port 8000){lat_str}", text_color=STATUS_GREEN)

            self.pill_status.configure(fg_color=("#d1fae5", "#064e3b"), border_color=("#a7f3d0", "#059669"))
            self.lbl_global_status.configure(text="● SERVEUR OPÉRATIONNEL", text_color=("#065f46", "#34d399"))
        elif is_docker_up:
            self.card_server.configure(border_color=STATUS_AMBER)
            self.lbl_server_state.configure(text="🟡 Port 8000 Fermé", text_color=STATUS_AMBER)

            self.pill_status.configure(fg_color=("#fef3c7", "#291b00"), border_color=("#fde68a", "#78350f"))
            self.lbl_global_status.configure(text="● SERVEUR ARRÊTÉ", text_color=("#b45309", "#fbbf24"))
        else:
            self.card_server.configure(border_color=STATUS_AMBER)
            self.lbl_server_state.configure(text="⏸️ En attente de Docker", text_color=STATUS_AMBER)

            self.pill_status.configure(fg_color=("#fef3c7", "#291b00"), border_color=("#fde68a", "#78350f"))
            self.lbl_global_status.configure(text="● EN ATTENTE DE DOCKER", text_color=("#b45309", "#fbbf24"))

        # Synchronisation boutons Start/Stop
        self._sync_control_buttons_state()

        self.lbl_footer_sync.configure(text=f"Synchronisation : {time.strftime('%H:%M:%S')}")

    def _sync_control_buttons_state(self):
        """Exclusivité mutuelle stricte des boutons Start et Stop empilés."""
        if self.is_busy:
            self.btn_start.configure(state="disabled", fg_color=STATUS_DISABLED, text_color=COLOR_MUTED_DARK, text=f"⏳ {self.busy_operation_title or 'Action en cours...'}")
            self.btn_stop.configure(state="disabled", fg_color=STATUS_DISABLED, text_color=COLOR_MUTED_DARK, text="⏳ Action en cours...")
            self.btn_restart.configure(state="disabled")
            self.btn_load_tar.configure(state="disabled")
            if hasattr(self, 'btn_apply_update'):
                self.btn_apply_update.configure(state="disabled")
            return

        self.btn_restart.configure(state="normal" if self.docker_is_up else "disabled")
        self.btn_load_tar.configure(state="normal" if self.docker_is_up else "disabled")
        if hasattr(self, 'btn_apply_update'):
            self.btn_apply_update.configure(state="normal" if self.docker_is_up else "disabled")

        if not self.docker_is_up:
            self.btn_start.configure(state="disabled", fg_color=STATUS_DISABLED, text_color=COLOR_MUTED_DARK, text="▶ DÉMARRER (Docker Requis)")
            self.btn_stop.configure(state="disabled", fg_color=STATUS_DISABLED, text_color=COLOR_MUTED_DARK, text="⏹ ARRÊTER (Docker Fermé)")
            return

        if self.server_is_running:
            self.btn_start.configure(state="disabled", fg_color=STATUS_DISABLED, text_color=COLOR_MUTED_DARK, text="✔ SERVEUR DÉJÀ ACTIF")
            self.btn_stop.configure(state="normal", fg_color=STATUS_RED, hover_color=STATUS_RED_HOVER, text_color="#ffffff", text="⏹ ARRÊTER LE SERVEUR")
        else:
            self.btn_start.configure(state="normal", fg_color=STATUS_GREEN, hover_color=STATUS_GREEN_HOVER, text_color="#ffffff", text="▶ DÉMARRER LE SERVEUR")
            self.btn_stop.configure(state="disabled", fg_color=STATUS_DISABLED, text_color=COLOR_MUTED_DARK, text="⏹ SERVEUR DÉJÀ ARRÊTÉ")

    def _set_busy(self, busy: bool, title: str = "", detail: str = ""):
        self.is_busy = busy
        self.busy_operation_title = title
        if busy:
            self.activity_banner.configure(fg_color=("#fef3c7", "#2a1c02"), border_color=("#f59e0b", "#92400e"))
            self.lbl_activity_title.configure(text=f"⏳ {title.upper()}", text_color=("#b45309", "#fbbf24"))
            self.lbl_activity_detail.configure(text=detail, text_color=("#92400e", "#fde68a"))
            self.prog_activity.configure(mode="indeterminate")
            self.prog_activity.start()
        else:
            self.activity_banner.configure(fg_color=("#e0f2fe", "#082f49"), border_color=("#7dd3fc", "#0369a1"))
            self.lbl_activity_title.configure(text="🟢 SYSTÈME PRÊT", text_color=("#0369a1", "#38bdf8"))
            self.lbl_activity_detail.configure(
                text=detail or "Opération terminée. Serveur opérationnel.",
                text_color=("#0284c7", "#bae6fd")
            )
            self.prog_activity.stop()
            self.prog_activity.configure(mode="determinate")
            self.prog_activity.set(1.0)
        self._sync_control_buttons_state()

    # =========================================================================
    # ACTIONS SERVEUR DOCKER
    # =========================================================================
    def _action_start_docker(self):
        if not self.docker_is_up:
            messagebox.showwarning(
                "Docker Non Détecté",
                "Docker Desktop n'est pas lancé.\n\nVeuillez démarrer Docker Desktop depuis Windows, puis réessayez."
            )
            return

        self._set_busy(True, title="Démarrage du Serveur", detail="Initialisation des conteneurs PostgreSQL et FastAPI...")
        self._append_log("[Action] Démarrage des conteneurs via 'docker compose up -d'...")
        threading.Thread(target=self._worker_start_docker, daemon=True).start()

    def _worker_start_docker(self):
        res = self.docker_mgr.start_app(progress_callback=self._append_log)
        time.sleep(1.0)
        if res["success"]:
            self._append_log(f"[Succès] Conteneurs démarrés :\n{res['stdout']}")
            self.after(0, self._set_busy, False, "", "Conteneurs démarrés avec succès. Le port 8000 est en ligne.")
        else:
            self._append_log(f"[Erreur] Échec du démarrage :\n{res['stderr']}")
            self.after(0, self._set_busy, False, "", f"Erreur au démarrage : {res['stderr']}")
        self.after(0, self._refresh_diagnosis)

    def _action_stop_docker(self):
        if not self.docker_is_up:
            messagebox.showwarning("Docker", "Docker Desktop n'est pas actif.")
            return

        self._set_busy(True, title="Arrêt du Serveur", detail="Arrêt ordonné des conteneurs...")
        self._append_log("[Action] Arrêt des conteneurs via 'docker compose stop'...")
        threading.Thread(target=self._worker_stop_docker, daemon=True).start()

    def _worker_stop_docker(self):
        res = self.docker_mgr.stop_app(progress_callback=self._append_log)
        time.sleep(1.0)
        if res["success"]:
            self._append_log("[Succès] Conteneurs arrêtés proprement.")
            self.after(0, self._set_busy, False, "", "Conteneurs arrêtés avec succès.")
        else:
            self._append_log(f"[Erreur] Échec de l'arrêt :\n{res['stderr']}")
            self.after(0, self._set_busy, False, "", f"Erreur lors de l'arrêt : {res['stderr']}")
        self.after(0, self._refresh_diagnosis)

    def _action_restart_docker(self):
        if not self.docker_is_up:
            messagebox.showwarning("Docker", "Docker Desktop n'est pas actif.")
            return

        self._set_busy(True, title="Redémarrage du Serveur", detail="Redémarrage des conteneurs en cours...")
        self._append_log("[Action] Redémarrage des conteneurs...")
        threading.Thread(target=self._worker_restart_docker, daemon=True).start()

    def _worker_restart_docker(self):
        res = self.docker_mgr.restart_app(progress_callback=self._append_log)
        time.sleep(1.0)
        self._append_log(f"[Résultat Redémarrage] {'Succès' if res['success'] else 'Échec'}")
        self.after(0, self._set_busy, False, "", "Redémarrage terminé.")
        self.after(0, self._refresh_diagnosis)

    def _action_load_tar(self):
        if not self.docker_is_up:
            messagebox.showwarning("Docker Non Détecté", "Docker Desktop n'est pas lancé.")
            return

        initial_dir = os.path.join(self.docker_mgr.project_root, "images_docker")
        f = filedialog.askopenfilename(
            initialdir=initial_dir if os.path.exists(initial_dir) else None,
            filetypes=[("Docker Images", "*.tar *.tar.gz")]
        )
        if f:
            self.entry_tar_path.delete(0, "end")
            self.entry_tar_path.insert(0, f)
            size_mb = os.path.getsize(f) / (1024 * 1024)
            self._set_busy(
                True,
                title="Importation Image Docker",
                detail=f"Décompression de '{os.path.basename(f)}' ({size_mb:.1f} Mo) dans le moteur Docker..."
            )
            self._append_log(f"[Action] Chargement de l'archive d'image : {f} ({size_mb:.1f} Mo)...")
            threading.Thread(target=self._worker_load_tar, args=(f,), daemon=True).start()

    def _worker_load_tar(self, path: str):
        res = self.docker_mgr.load_image_from_tar(path, progress_callback=self._append_log)
        if res["success"]:
            self._append_log(f"[Succès] Image chargée dans Docker :\n{res['stdout']}")
            self.after(0, self._set_busy, False, "", f"Image chargée avec succès ({res.get('elapsed_sec', 0)}s) !")
            messagebox.showinfo("Docker Load", "Image Docker chargée avec succès !")
        else:
            self._append_log(f"[Erreur] Échec du chargement :\n{res['stderr']}")
            self.after(0, self._set_busy, False, "", "Échec de l'importation de l'image.")
            messagebox.showerror("Erreur Docker", res["stderr"])
        self.after(0, self._refresh_diagnosis)

    def _browse_tar_file(self):
        initial_dir = os.path.join(self.docker_mgr.project_root, "images_docker")
        f = filedialog.askopenfilename(
            initialdir=initial_dir if os.path.exists(initial_dir) else None,
            filetypes=[("Docker Images", "*.tar *.tar.gz")]
        )
        if f:
            self.entry_tar_path.delete(0, "end")
            self.entry_tar_path.insert(0, f)

    def _apply_docker_update(self):
        if not self.docker_is_up:
            messagebox.showwarning("Docker Non Détecté", "Docker Desktop n'est pas lancé.")
            return

        tar_path = self.entry_tar_path.get().strip()
        self._set_busy(True, title="Mise à Jour Applicative", detail="Déploiement de la nouvelle image et recréation...")
        self._append_log(f"[Mise à Jour] Application de la version ({tar_path or 'Image locale'})...")
        threading.Thread(target=self._worker_apply_update, args=(tar_path,), daemon=True).start()

    def _worker_apply_update(self, tar_path: str):
        res = self.docker_mgr.update_and_recreate(tar_path if tar_path else None, progress_callback=self._append_log)
        if res["success"]:
            self._append_log("[Succès] Plateforme mise à jour et conteneurs recréés !")
            self.after(0, self._set_busy, False, "", "Mise à jour appliquée avec succès !")
            messagebox.showinfo("Mise à Jour", "La plateforme a été mise à jour avec succès !")
        else:
            self._append_log(f"[Erreur] Échec de la mise à jour :\n{res['stderr']}")
            self.after(0, self._set_busy, False, "", "Erreur lors de la mise à jour.")
            messagebox.showerror("Erreur Mise à Jour", res["stderr"])
        self.after(0, self._refresh_diagnosis)

    def _append_log(self, text: str):
        timestamp = time.strftime("[%H:%M:%S] ")
        full = timestamp + text + "\n"
        self.after(0, self._append_log_main, full)

    def _append_log_main(self, full_text: str):
        if hasattr(self, 'txt_mini_log'):
            self.txt_mini_log.insert("end", full_text)
            self.txt_mini_log.see("end")
        if hasattr(self, 'txt_docker_logs'):
            self.txt_docker_logs.insert("end", full_text)
            self.txt_docker_logs.see("end")

    # =========================================================================
    # DIAGNOSTIC DE SANTÉ & RÉSOLUTION D'INCIDENTS (AVEC PARE-FEU ITEM 8)
    # =========================================================================
    def _refresh_diagnosis(self):
        for w in self.diag_container.winfo_children():
            w.destroy()

        diag_items = self.health_checker.run_full_diagnosis()
        for idx, item in enumerate(diag_items):
            status = item["status"]
            if status == "ok":
                badge_color = STATUS_GREEN
                icon = "🟢"
            elif status == "warning":
                badge_color = STATUS_AMBER
                icon = "🟡"
            else:
                badge_color = STATUS_RED
                icon = "🔴"

            row_card = ctk.CTkFrame(
                self.diag_container,
                corner_radius=8,
                fg_color=(COLOR_PANEL_LIGHT, "#131b2e"),
                border_width=1,
                border_color=(COLOR_BORDER_LIGHT, COLOR_BORDER_DARK)
            )
            row_card.pack(fill="x", pady=4)

            r_left = ctk.CTkFrame(row_card, fg_color="transparent")
            r_left.pack(side="left", fill="x", expand=True, padx=14, pady=10)

            title_txt = f"{icon} [{item['component']}] {item['title']}"
            ctk.CTkLabel(
                r_left,
                text=title_txt,
                font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
                text_color=badge_color
            ).pack(anchor="w")

            detail_txt = f"Constat : {item['detail']}  |  Action recommandée : {item['solution']}"
            ctk.CTkLabel(
                r_left,
                text=detail_txt,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                text_color=(COLOR_MUTED_LIGHT, COLOR_MUTED_DARK)
            ).pack(anchor="w", pady=(3, 0))

            if item.get("auto_fixable") and item.get("action_code"):
                code = item["action_code"]
                btn_fix = ctk.CTkButton(
                    row_card,
                    text="Résoudre",
                    font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
                    width=90,
                    height=28,
                    corner_radius=6,
                    fg_color=ACCENT_BLUE,
                    hover_color=ACCENT_BLUE_HOVER,
                    command=lambda c=code: self._execute_diagnostic_fix(c)
                )
                btn_fix.pack(side="right", padx=14, pady=10)

    def _execute_diagnostic_fix(self, action_code: str):
        if action_code == "start_app":
            self._action_start_docker()
        elif action_code == "kill_port_8000":
            res = self.health_checker.kill_process_on_port(8000)
            messagebox.showinfo("Libération du port 8000", res["message"])
            self._refresh_diagnosis()
        elif action_code == "fix_firewall":
            res = self.health_checker.firewall_checker.configure_firewall_rules()
            messagebox.showinfo("Configuration Pare-Feu Windows", res["message"])
            self._refresh_diagnosis()
        elif action_code == "fix_firewall" or action_code == "unlock_lan":
            self._action_unlock_lan()

    def _action_unlock_lan(self):
        """Débloque en 1 clic l'accès câblé pour la salle (Pare-feu, PortProxy, Profil Privé)."""
        self._append_log("[Réseau Câblé] Déblocage des règles Pare-Feu, PortProxy et profil Privé...")
        res = self.health_checker.lan_unlocker.unlock_lan_access()
        if res["success"]:
            self._append_log(f"[Succès LAN] {res['message']}")
            messagebox.showinfo(
                "Accès Réseau Câblé (LAN) Débloqué",
                f"{res['message']}\n\n- Pare-Feu Windows : Port 8000 (TCP), 5353 (UDP) et Ping autorisés sur profil Public & Privé.\n- Relais PortProxy : Redirection 0.0.0.0:8000 vers Docker activée.\n- Les autres PC de la salle peuvent désormais joindre le serveur."
            )
        else:
            self._append_log(f"[Avertissement LAN] {res['message']}")
            messagebox.showwarning("Avertissement Déblocage LAN", res["message"])
        self._refresh_diagnosis()

    # =========================================================================
    # CARTOGRAPHIE RÉSEAU & RENOMMAGE (APPROCHE 1)
    # =========================================================================
    def _initial_light_scan(self):
        threading.Thread(target=self._worker_scan_network, args=(True,), daemon=True).start()

    def _trigger_network_scan(self):
        if self.is_scanning:
            return
        self.is_scanning = True
        self.btn_scan.configure(text="⏳ Balayage en cours...", state="disabled")
        self.lbl_scan_info.configure(text="Détection des postes connectés sur le sous-réseau...")
        threading.Thread(target=self._worker_scan_network, args=(False,), daemon=True).start()

    def _worker_scan_network(self, fast_mode: bool = False):
        try:
            devices = self.scanner.scan_network(max_threads=8, fast_mode=fast_mode)
            self.network_devices = devices
            self.after(0, self._render_network_table, devices)
        except Exception as e:
            self.after(0, self.lbl_scan_info.configure, {"text": f"Erreur scan : {str(e)}"})
        finally:
            self.is_scanning = False
            self.after(0, self._finish_scan_ui)

    def _finish_scan_ui(self):
        self.btn_scan.configure(text="🔍 Lancer le Scan Réseau", state="normal")
        count = len(self.network_devices)
        self.lbl_scan_info.configure(text=f"Cartographie terminée : {count} poste(s) détecté(s).")

    def _on_filter_search(self, event=None):
        query = self.search_entry.get().strip().lower()
        if not query:
            self._render_network_table(self.network_devices)
            return

        filtered = [
            d for d in self.network_devices
            if query in d.get("ip", "").lower()
            or query in d.get("mac", "").lower()
            or query in d.get("hostname", "").lower()
            or query in (d.get("alias") or "").lower()
        ]
        self._render_network_table(filtered)

    def _render_network_table(self, devices: List[Dict[str, Any]]):
        for w in self.network_table_body.winfo_children():
            w.destroy()

        if not devices:
            ctk.CTkLabel(
                self.network_table_body,
                text="Aucun équipement détecté sur ce sous-réseau.",
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                text_color=(COLOR_MUTED_LIGHT, COLOR_MUTED_DARK)
            ).pack(pady=20)
            return

        for idx, dev in enumerate(devices):
            row_bg = (COLOR_PANEL_LIGHT, "#131b2e") if idx % 2 == 0 else (COLOR_BG_LIGHT, "#0c1322")
            row = ctk.CTkFrame(
                self.network_table_body,
                height=38,
                corner_radius=6,
                fg_color=row_bg
            )
            row.pack(fill="x", padx=4, pady=2)
            row.grid_columnconfigure((0, 1, 2, 3, 4, 5, 6), weight=1)

            # 1. IP
            ip_txt = dev["ip"]
            if dev.get("is_self"):
                ip_txt += " ★ (Serveur)"
            lbl_ip = ctk.CTkLabel(row, text=ip_txt, font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"))
            lbl_ip.grid(row=0, column=0, padx=6, pady=6, sticky="w")

            # 2. MAC
            lbl_mac = ctk.CTkLabel(row, text=dev["mac"], font=ctk.CTkFont(family="Consolas", size=10), text_color=(COLOR_MUTED_LIGHT, COLOR_MUTED_DARK))
            lbl_mac.grid(row=0, column=1, padx=6, pady=6, sticky="w")

            # 3. Nom d'hôte OS
            lbl_host = ctk.CTkLabel(row, text=dev["hostname"], font=ctk.CTkFont(family=FONT_FAMILY, size=11))
            lbl_host.grid(row=0, column=2, padx=6, pady=6, sticky="w")

            # 4. Alias Convivial (Salle)
            alias = dev.get("alias") or "—"
            alias_color = ACCENT_BLUE if dev.get("alias") else (COLOR_MUTED_LIGHT, COLOR_MUTED_DARK)
            lbl_alias = ctk.CTkLabel(row, text=alias, font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color=alias_color)
            lbl_alias.grid(row=0, column=3, padx=6, pady=6, sticky="w")

            # 5. Latence
            lat = dev.get("latency_ms", -1)
            lat_str = f"{lat} ms" if lat >= 0 else "—"
            lbl_lat = ctk.CTkLabel(row, text=lat_str, font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=(COLOR_MUTED_LIGHT, COLOR_MUTED_DARK))
            lbl_lat.grid(row=0, column=4, padx=6, pady=6, sticky="")

            # 6. Statut
            is_on = dev.get("status") == "online"
            st_color = STATUS_GREEN if is_on else (COLOR_MUTED_LIGHT, COLOR_MUTED_DARK)
            lbl_st = ctk.CTkLabel(row, text="● En ligne" if is_on else "○ Hors ligne", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color=st_color)
            lbl_st.grid(row=0, column=5, padx=6, pady=6, sticky="")

            # 7. Action Renommer
            btn_rename = ctk.CTkButton(
                row,
                text="Renommer",
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                width=80,
                height=26,
                corner_radius=4,
                fg_color=(COLOR_BORDER_LIGHT, COLOR_BORDER_DARK),
                hover_color=("#cbd5e1", "#475569"),
                text_color=(COLOR_TEXT_LIGHT, COLOR_TEXT_DARK),
                command=lambda d=dev: self._open_rename_dialog(d)
            )
            btn_rename.grid(row=0, column=6, padx=6, pady=6, sticky="")

    def _open_rename_dialog(self, dev: Dict[str, Any]):
        dialog = ctk.CTkInputDialog(
            title="Étiqueter le Poste (Approche 1)",
            text=f"Attribuez un nom de salle pour l'adresse {dev['ip']} (MAC : {dev['mac']}) :\nExemple : 'Poste 01', 'Table 12'"
        )
        new_alias = dialog.get_input()
        if new_alias is not None:
            self.renamer.set_alias(
                mac=dev["mac"],
                alias=new_alias,
                ip=dev["ip"],
                hostname=dev["hostname"]
            )
            for d in self.network_devices:
                if d["mac"] == dev["mac"] or d["ip"] == dev["ip"]:
                    d["alias"] = new_alias
            self._render_network_table(self.network_devices)

    def _export_topology(self):
        f = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        if f:
            if self.renamer.export_csv(f):
                messagebox.showinfo("Exportation", "Topologie et étiquettes exportées avec succès.")
            else:
                messagebox.showerror("Erreur", "Échec de l'exportation.")

    def _import_topology(self):
        f = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if f:
            cnt = self.renamer.import_csv(f)
            messagebox.showinfo("Importation", f"{cnt} étiquette(s) de postes importée(s) avec succès.")
            self._trigger_network_scan()

    def _generate_hosts_script(self):
        f = filedialog.asksaveasfilename(
            defaultextension=".bat",
            initialfile="installer_nom_local.bat",
            filetypes=[("Batch Scripts", "*.bat")]
        )
        if f:
            if self.mdns.generate_hosts_script(f):
                messagebox.showinfo(
                    "Script de Secours",
                    f"Script généré avec succès :\n{f}\n\nCopiez ce fichier sur clé USB pour les postes étudiants."
                )
            else:
                messagebox.showerror("Erreur", "Impossible de générer le script.")

    def _open_web_browser(self):
        webbrowser.open(f"http://localhost:8000")

    def _toggle_theme(self):
        val = self.theme_switch.get()
        ctk.set_appearance_mode(val)

    def _on_close(self):
        self.auto_refresh_active = False
        try:
            self.mdns.stop()
        except Exception:
            pass
        self.destroy()

if __name__ == "__main__":
    app = ExamMasterApp()
    app.mainloop()
