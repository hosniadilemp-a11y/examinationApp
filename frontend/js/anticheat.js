/**
 * Dispositif Anti-Triche Client :
 * - Mode Plein Écran obligatoire
 * - Blocage du copier/coller, clic droit et raccourcis d'inspection
 * - Règle des 10 secondes d'absence : suspension automatique avec écran rouge
 * - Déblocage en temps réel par le surveillant
 * - Tolérance aux coupures réseau locales sans fausse suspension
 */

import { api } from './api.js';

export class AntiCheatManager {
  constructor(attemptId, options = {}) {
    this.attemptId = attemptId;
    this.isActive = false;
    this.awayTimer = null;
    this.awaySeconds = 0;
    this.isSuspended = false;
    this.statusPollInterval = null;

    this.warningsCount = 0;
    this.maxWarnings = options.maxWarnings || 4;
    this.lastWarningTime = 0;
    this.isPracticeMode = options.isPracticeMode || false;

    this.onWarning = options.onWarning || (() => {});
    this.onMaxWarningsReached = options.onMaxWarningsReached || (() => {});
    this.onSuspended = options.onSuspended || (() => {});
    this.onUnlocked = options.onUnlocked || (() => {});

    this._boundOnBlur = this._handleWindowBlur.bind(this);
    this._boundOnFocus = this._handleWindowFocus.bind(this);
    this._boundOnVisibility = this._handleVisibilityChange.bind(this);
    this._boundOnFullscreen = this._handleFullscreenChange.bind(this);
    this._boundOnKeyDown = this._handleKeyDown.bind(this);
    this._boundBlockEvent = (e) => e.preventDefault();
  }

  start() {
    this.isActive = true;
    this.awaySeconds = 0;
    this.isSuspended = false;
    this.warningsCount = 0;

    // 1. Passage en Plein Écran
    this.requestFullscreen();

    // 2. Écouteurs de perte de focus et d'absence
    window.addEventListener('blur', this._boundOnBlur);
    window.addEventListener('focus', this._boundOnFocus);
    document.addEventListener('visibilitychange', this._boundOnVisibility);
    document.addEventListener('fullscreenchange', this._boundOnFullscreen);
    document.addEventListener('webkitfullscreenchange', this._boundOnFullscreen);

    // 3. Blocage du Copier/Coller, Clic Droit et Sélections (actif en Examen Officiel)
    if (!this.isPracticeMode) {
      document.addEventListener('copy', this._boundBlockEvent, true);
      document.addEventListener('cut', this._boundBlockEvent, true);
      document.addEventListener('paste', this._boundBlockEvent, true);
      document.addEventListener('contextmenu', this._boundBlockEvent, true);
      document.addEventListener('selectstart', this._boundBlockEvent, true);
      window.addEventListener('keydown', this._boundOnKeyDown, true);
    }

    // 4. Écouteurs de déconnexion réseau (Tolérance sans suspension)
    window.addEventListener('offline', this._handleOffline);
    window.addEventListener('online', this._handleOnline);
  }

  stop() {
    this.isActive = false;
    this._clearAwayTimer();
    this._stopPracticeFullscreenCountdown();
    this._stopStatusPolling();

    window.removeEventListener('blur', this._boundOnBlur);
    window.removeEventListener('focus', this._boundOnFocus);
    document.removeEventListener('visibilitychange', this._boundOnVisibility);
    document.removeEventListener('fullscreenchange', this._boundOnFullscreen);
    document.removeEventListener('webkitfullscreenchange', this._boundOnFullscreen);

    document.removeEventListener('copy', this._boundBlockEvent, true);
    document.removeEventListener('cut', this._boundBlockEvent, true);
    document.removeEventListener('paste', this._boundBlockEvent, true);
    document.removeEventListener('contextmenu', this._boundBlockEvent, true);
    document.removeEventListener('selectstart', this._boundBlockEvent, true);
    window.removeEventListener('keydown', this._boundOnKeyDown, true);

    window.removeEventListener('offline', this._handleOffline);
    window.removeEventListener('online', this._handleOnline);

    const examView = document.getElementById('view-exam');
    const waitingView = document.getElementById('view-waiting-room');
    const overlayFs = document.getElementById('overlay-fullscreen-required');
    if (examView) examView.classList.remove('exam-fullscreen-lost-blurred');
    if (waitingView) waitingView.classList.remove('exam-fullscreen-lost-blurred');
    if (overlayFs) overlayFs.classList.remove('active');
  }

  requestFullscreen() {
    const elem = document.documentElement;
    if (elem.requestFullscreen) {
      elem.requestFullscreen().catch(() => {});
    } else if (elem.webkitRequestFullscreen) {
      elem.webkitRequestFullscreen();
    }
  }

  _registerWarning(reason) {
    if (!this.isActive || this.isSuspended) return;
    const now = Date.now();
    // Anti-rebond (1.5s) pour éviter les doublons lors des transitions fenêtres
    if (now - this.lastWarningTime < 1500) return;
    this.lastWarningTime = now;

    this.warningsCount++;
    console.warn(`[AntiCheat] Avertissement ${this.warningsCount}/${this.maxWarnings} : ${reason}`);

    if (this.attemptId) {
      api.reportSecurityEvent(this.attemptId, "SECURITY_WARNING", {
        reason,
        warning_number: this.warningsCount,
        max_warnings: this.maxWarnings
      }).catch(() => {});
    }

    // Mise à jour du badge et notification
    this.onWarning(this.warningsCount, this.maxWarnings, reason);

    // Si 4 avertissements atteints :
    // - En examen officiel : suspension avec déblocage enseignant et remise à zéro (REV-29)
    // - En entraînement : fin de la session
    if (this.warningsCount >= this.maxWarnings) {
      if (!this.isPracticeMode) {
        this._triggerSuspension("4 avertissements atteints (sorties plein écran ou perte de focus répétées). Contactez votre enseignant pour déblocage.");
      } else {
        this.stop();
        this.onMaxWarningsReached(reason);
      }
    }
  }

  _handleFullscreenChange() {
    if (!this.isActive) return;
    const isFull = !!(document.fullscreenElement || document.webkitFullscreenElement);
    const examView = document.getElementById('view-exam');
    const waitingView = document.getElementById('view-waiting-room');
    const overlayFs = document.getElementById('overlay-fullscreen-required');

    if (!isFull && !this.isSuspended) {
      // REV-27 / REV-34 : Flou d'obstruction immédiat et affichage du panneau bloquant
      if (examView) examView.classList.add('exam-fullscreen-lost-blurred');
      if (waitingView) waitingView.classList.add('exam-fullscreen-lost-blurred');
      if (overlayFs) {
        overlayFs.classList.add('active');
        const btnRestore = document.getElementById('btn-restore-fullscreen');
        if (btnRestore) {
          btnRestore.onclick = () => this.requestFullscreen();
        }
      }

      this._registerWarning("Sortie du mode plein écran détectée.");
      if (this.isPracticeMode) {
        this._startPracticeFullscreenCountdown();
      } else {
        this._startAwayCountdown("Sortie du mode plein écran détectée.");
      }
    } else if (isFull && !this.isSuspended) {
      // Rétablissement du plein écran : lever le flou
      if (examView) examView.classList.remove('exam-fullscreen-lost-blurred');
      if (waitingView) waitingView.classList.remove('exam-fullscreen-lost-blurred');
      if (overlayFs) overlayFs.classList.remove('active');

      if (this.isPracticeMode) {
        this._stopPracticeFullscreenCountdown();
      } else {
        this._stopAwayCountdown();
      }
    }
  }

  _startPracticeFullscreenCountdown() {
    if (this.practiceAwayTimer) return;
    this.practiceAwaySeconds = 0;
    this.practiceAwayTimer = setInterval(() => {
      this.practiceAwaySeconds++;
      const remaining = 10 - this.practiceAwaySeconds;
      if (remaining > 0) {
        this.onWarning(this.warningsCount, this.maxWarnings, `⚠️ Plein écran quitté ! Revenez en plein écran : clôture automatique et sauvegarde dans ${remaining}s...`);
      } else {
        this._stopPracticeFullscreenCountdown();
        this.stop();
        this.onMaxWarningsReached("Plein écran quitté pendant plus de 10 secondes. Le test est terminé et vos résultats sont enregistrés.");
      }
    }, 1000);
  }

  _stopPracticeFullscreenCountdown() {
    if (this.practiceAwayTimer) {
      clearInterval(this.practiceAwayTimer);
      this.practiceAwayTimer = null;
      this.practiceAwaySeconds = 0;
    }
  }

  _handleVisibilityChange() {
    if (!this.isActive) return;
    // En test de niveau / entraînement : navigation libre entre onglets autorisée pour consulter la doc
    if (this.isPracticeMode) return;

    if (document.hidden && !this.isSuspended) {
      this._registerWarning("Changement d'onglet ou minimisation de fenêtre détectée.");
      this._startAwayCountdown("Changement d'onglet ou minimisation de fenêtre détectée.");
    } else if (!document.hidden && !this.isSuspended) {
      this._stopAwayCountdown();
    }
  }

  _handleWindowBlur() {
    if (!this.isActive || this.isSuspended) return;
    // En test de niveau / entraînement : perte de focus pour lecture documentaire autorisée
    if (this.isPracticeMode) return;

    this._registerWarning("Perte de focus sur la fenêtre d'examen.");
    this._startAwayCountdown("Perte de focus sur la fenêtre d'examen.");
  }

  _handleWindowFocus() {
    if (!this.isActive || this.isSuspended) return;
    this._stopAwayCountdown();
  }

  _startAwayCountdown(reason) {
    if (this.awayTimer) return;
    console.warn(`[AntiCheat] Début du décompte d'absence : ${reason}`);

    this.awaySeconds = 0;
    this.awayTimer = setInterval(() => {
      this.awaySeconds++;

      // Envoi d'une alerte dès la première seconde
      if (this.awaySeconds === 1) {
        api.reportSecurityEvent(this.attemptId, "FOCUS_LOST", { reason });
      }

      // Si l'étudiant est absent pendant 10 secondes ou plus -> SUSPENSION
      if (this.awaySeconds >= 10) {
        this._clearAwayTimer();
        this._triggerSuspension("Sortie d'écran non autorisée supérieure à 10 secondes.");
      }
    }, 1000);
  }

  _stopAwayCountdown() {
    if (this.awayTimer) {
      this._clearAwayTimer();
      console.log(`[AntiCheat] Retour sur l'épreuve après ${this.awaySeconds} seconde(s).`);
      this.awaySeconds = 0;
    }
  }

  _clearAwayTimer() {
    if (this.awayTimer) {
      clearInterval(this.awayTimer);
      this.awayTimer = null;
    }
  }

  async _triggerSuspension(reason) {
    this.isSuspended = true;
    console.error(`[AntiCheat] SUSPENSION DÉCLENCHÉE : ${reason}`);

    // Notification au serveur backend
    await api.reportSecurityEvent(this.attemptId, "AWAY_10S", {
      reason,
      duration_seconds: this.awaySeconds
    });

    // Déclenchement de l'affichage de l'écran rouge de suspension
    this.onSuspended(reason);

    // Démarrage de l'écoute du déblocage par le surveillant (polling toutes les 2 secondes)
    this._startStatusPolling();
  }

  _startStatusPolling() {
    this._stopStatusPolling();
    this.statusPollInterval = setInterval(async () => {
      try {
        const statusData = await api.checkAttemptStatus(this.attemptId);
        if (statusData && statusData.status === "in_progress") {
          // L'enseignant a cliqué sur "Débloquer" !
          this._stopStatusPolling();
          this.isSuspended = false;
          this.warningsCount = 0; // REV-29 : Remise à zéro du compteur d'avertissements au déblocage
          this.lastWarningTime = 0;
          this.awaySeconds = 0;
          this.requestFullscreen();
          const examView = document.getElementById('view-exam');
          const overlayFs = document.getElementById('overlay-fullscreen-required');
          if (examView) examView.classList.remove('exam-fullscreen-lost-blurred');
          if (overlayFs) overlayFs.classList.remove('active');
          this.onUnlocked();
        }
      } catch (_) {}
    }, 2000);
  }

  _stopStatusPolling() {
    if (this.statusPollInterval) {
      clearInterval(this.statusPollInterval);
      this.statusPollInterval = null;
    }
  }

  _handleKeyDown(e) {
    // Blocage des touches dangereuses (F12, Ctrl+Shift+I, Ctrl+C, Ctrl+V, etc.)
    const isCtrl = e.ctrlKey || e.metaKey;
    const forbiddenKeys = ['c', 'v', 'x', 'a', 'u', 'p', 's'];

    if (e.key === 'F12' || (isCtrl && e.shiftKey && (e.key === 'I' || e.key === 'i' || e.key === 'C' || e.key === 'J'))) {
      e.preventDefault();
      return false;
    }

    if (isCtrl && forbiddenKeys.includes(e.key.toLowerCase())) {
      e.preventDefault();
      return false;
    }
  }

  _handleOffline() {
    const banner = document.getElementById('banner-offline');
    if (banner) banner.classList.add('active');
  }

  _handleOnline() {
    const banner = document.getElementById('banner-offline');
    if (banner) banner.classList.remove('active');
    api.flushOfflineQueue();
  }
}
