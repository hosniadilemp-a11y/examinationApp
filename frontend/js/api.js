/**
 * Module de communication API REST pour la plateforme d'examen.
 * Gère les jetons JWT, les en-têtes et la mise en cache locale en cas de coupure réseau.
 */

const API_BASE = '/api';

class ApiClient {
  constructor() {
    this.token = localStorage.getItem('exam_token') || null;
    this.user = JSON.parse(localStorage.getItem('exam_user') || 'null');
    this.offlineQueueKey = 'exam_offline_answer_queue';
  }

  setSession(token, user) {
    this.token = token;
    this.user = user;
    localStorage.setItem('exam_token', token);
    localStorage.setItem('exam_user', JSON.stringify(user));
  }

  clearSession() {
    this.token = null;
    this.user = null;
    localStorage.removeItem('exam_token');
    localStorage.removeItem('exam_user');
  }

  getHeaders() {
    const headers = { 'Content-Type': 'application/json' };
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    return headers;
  }

  async request(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const headers = { ...this.getHeaders(), ...(options.headers || {}) };

    try {
      const response = await fetch(url, { ...options, headers });
      
      if (response.status === 401) {
        if (!endpoint.includes('/auth/login')) {
          this.clearSession();
          window.dispatchEvent(new CustomEvent('auth:expired'));
          throw new Error("Session expirée. Veuillez vous reconnecter.");
        }
      }

      if (!response.ok) {
        let errorMsg = `Erreur HTTP ${response.status}`;
        try {
          const errData = await response.json();
          if (typeof errData.detail === 'string') {
            errorMsg = errData.detail;
          } else if (Array.isArray(errData.detail)) {
            errorMsg = errData.detail.map(d => d.msg ? `${d.loc && d.loc.length > 1 ? d.loc.slice(1).join('.') + ': ' : ''}${d.msg}` : JSON.stringify(d)).join(' | ');
          } else if (errData.detail && typeof errData.detail === 'object') {
            errorMsg = errData.detail.message || JSON.stringify(errData.detail);
          } else if (errData.message) {
            errorMsg = errData.message;
          }
        } catch (_) {}
        const err = new Error(errorMsg);
        err.status = response.status;
        throw err;
      }

      if (response.status === 204) return null;
      return await response.json();
    } catch (err) {
      // Si la requête échoue en raison du réseau
      if (!navigator.onLine || err.message.includes('Failed to fetch')) {
        window.dispatchEvent(new CustomEvent('network:offline'));
      }
      throw err;
    }
  }

  // --- Authentification ---
  async login(username, password) {
    const data = await this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password })
    });
    this.setSession(data.access_token, data.user);
    return data;
  }

  async getMe() {
    return await this.request('/auth/me');
  }

  // --- Examens Officiels Étudiant ---
  async getAvailableExams() {
    return await this.request('/student/exams/available');
  }

  async startOrResumeExam(examId) {
    return await this.request(`/student/exams/${examId}/start`, { method: 'POST' });
  }

  async saveAnswer(attemptId, questionId, answer) {
    try {
      return await this.request(`/student/attempts/${attemptId}/save-answer`, {
        method: 'POST',
        body: JSON.stringify({ question_id: questionId, answer })
      });
    } catch (err) {
      // En cas de panne réseau, mise en cache locale de sécurité
      this._queueOfflineAnswer(attemptId, questionId, answer);
      return { success: true, cached_locally: true };
    }
  }

  async reportSecurityEvent(attemptId, eventType, details = {}) {
    try {
      return await this.request(`/student/attempts/${attemptId}/security-event`, {
        method: 'POST',
        body: JSON.stringify({ event_type: eventType, details })
      });
    } catch (err) {
      console.warn("Échec d'envoi de l'événement de sécurité (réseau) :", err);
      return { is_suspended: false };
    }
  }

  async checkAttemptStatus(attemptId) {
    return await this.request(`/student/attempts/${attemptId}/status`);
  }

  async submitOfficialExam(attemptId) {
    // Vider d'abord la file d'attente hors-ligne si le réseau est revenu
    await this.flushOfflineQueue();
    return await this.request(`/student/attempts/${attemptId}/submit`, { method: 'POST' });
  }

  // --- Statistiques & Profil Étudiant ---
  async getStudentStatistics() {
    return await this.request('/student/statistics');
  }

  // --- Tests de Niveau par Module ---
  async getPracticeModules() {
    return await this.request('/practice/modules');
  }

  async getPracticeQuestions(moduleCode, count = 20) {
    const query = count ? `?count=${count}` : '';
    return await this.request(`/practice/exams/${moduleCode}/questions${query}`);
  }

  async submitPracticeExam(moduleCode, answers, warningsCount = 0, questionIds = null) {
    const payload = { answers, warnings_count: warningsCount };
    if (questionIds && Array.isArray(questionIds)) {
      payload.question_ids = questionIds;
    }
    return await this.request(`/practice/exams/${moduleCode}/submit`, {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  async getPracticeHistory() {
    return await this.request('/practice/history');
  }

  // --- Centre d'Entraînement Python Évolutif ---
  async getPythonChapters() {
    return await this.request('/training/python/chapters');
  }

  async getPythonChapter(chapterId) {
    return await this.request(`/training/python/chapters/${chapterId}`);
  }

  async generatePythonSession(payload) {
    return await this.request('/training/python/generate-session', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  async submitPythonSession(payload) {
    return await this.request('/training/python/submit-session', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  async getPythonProgression() {
    return await this.request('/training/python/progression');
  }

  async getPythonStudentAnalytics() {
    return await this.request('/training/python/student-analytics');
  }

  async getPythonHistory() {
    return await this.request('/training/python/history');
  }

  // --- Enseignant & Gestion des Examens (REV-13, REV-15) ---
  async listExams(moduleCode = null) {
    const query = moduleCode ? `?module_code=${encodeURIComponent(moduleCode)}` : '';
    return await this.request(`/exams${query}`);
  }

  async getExamDetail(examId) {
    return await this.request(`/exams/${examId}`);
  }

  async listExamTemplates() {
    return await this.request('/exams/templates');
  }

  async loadExamTemplate(templateId) {
    return await this.request(`/exams/templates/${encodeURIComponent(templateId)}/load`, {
      method: 'POST'
    });
  }

  async importExamTemplate(payload) {
    return await this.request('/exams/import-template', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  async createCustomExam(payload) {
    return await this.request('/exams', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  // --- Surveillance & Proctoring Temps Réel (REV-16) ---
  async listProctorSessions(roomId = null) {
    const query = roomId ? `?room_id=${encodeURIComponent(roomId)}` : '';
    return await this.request(`/proctor/sessions${query}`);
  }

  async openProctorSession(examId, roomId = 'SALLE-TP-1') {
    return await this.request('/proctor/sessions', {
      method: 'POST',
      body: JSON.stringify({ exam_id: examId, room_id: roomId })
    });
  }

  async getProctorSessionOverview(sessionId) {
    return await this.request(`/proctor/sessions/${sessionId}/overview`);
  }

  async launchProctorSession(sessionId) {
    return await this.request(`/proctor/sessions/${sessionId}/launch`, {
      method: 'POST'
    });
  }

  async extendProctorTime(sessionId, extraMinutes = 5, studentId = null) {
    return await this.request(`/proctor/sessions/${sessionId}/extend-time`, {
      method: 'POST',
      body: JSON.stringify({ extra_minutes: extraMinutes, student_id: studentId })
    });
  }

  async forceSubmitAttempt(sessionId, attemptId) {
    return await this.request(`/proctor/sessions/${sessionId}/attempts/${attemptId}/force-submit`, {
      method: 'POST'
    });
  }

  async unlockStudentAttempt(sessionId, attemptId) {
    return await this.request(`/proctor/sessions/${sessionId}/attempts/${attemptId}/unlock`, {
      method: 'POST'
    });
  }

  async closeExamSession(sessionId) {
    return await this.request(`/proctor/sessions/${sessionId}/close`, {
      method: 'POST'
    });
  }

  // --- Gestion du Cache Hors-Ligne ---
  _queueOfflineAnswer(attemptId, questionId, answer) {
    const queue = JSON.parse(localStorage.getItem(this.offlineQueueKey) || '[]');
    queue.push({ attemptId, questionId, answer, timestamp: Date.now() });
    localStorage.setItem(this.offlineQueueKey, JSON.stringify(queue));
  }

  async flushOfflineQueue() {
    const queue = JSON.parse(localStorage.getItem(this.offlineQueueKey) || '[]');
    if (queue.length === 0) return;

    for (const item of queue) {
      try {
        await this.request(`/student/attempts/${item.attemptId}/save-answer`, {
          method: 'POST',
          body: JSON.stringify({ question_id: item.questionId, answer: item.answer })
        });
      } catch (_) {}
    }
    localStorage.removeItem(this.offlineQueueKey);
  }

  // --- Administration Globale & Multi-Salles (REV-39, REV-40) ---
  async getAdminOverview() {
    return await this.request('/admin/statistics/overview');
  }

  async getAdminResults(params = {}) {
    const searchParams = new URLSearchParams();
    if (params.exam_id) searchParams.append('exam_id', params.exam_id);
    if (params.group_id) searchParams.append('group_id', params.group_id);
    if (params.room_id) searchParams.append('room_id', params.room_id);
    const qs = searchParams.toString();
    return await this.request(`/admin/results${qs ? '?' + qs : ''}`);
  }

  async importResultsCsv(file) {
    const formData = new FormData();
    formData.append('file', file);
    const url = `${API_BASE}/admin/csv/import/results`;
    const headers = {};
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: formData
    });
    if (!response.ok) {
      let errorMsg = `Erreur HTTP ${response.status}`;
      try {
        const errData = await response.json();
        errorMsg = errData.detail || errorMsg;
      } catch (_) {}
      throw new Error(errorMsg);
    }
    return await response.json();
  }

  async listUsers(role = null, groupId = null, enrollmentYear = null) {
    const params = new URLSearchParams();
    if (role) params.append('role', role);
    if (groupId) params.append('group_id', groupId);
    if (enrollmentYear) params.append('enrollment_year', enrollmentYear);
    const qs = params.toString();
    return await this.request(`/users${qs ? '?' + qs : ''}`);
  }

  async listEnrollmentYears() {
    try {
      return await this.request('/users/enrollment-years');
    } catch (_) {
      return [];
    }
  }

  async createUser(payload) {
    return await this.request('/users', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  async updateUser(userId, payload) {
    return await this.request(`/users/${encodeURIComponent(userId)}`, {
      method: 'PUT',
      body: JSON.stringify(payload)
    });
  }

  async deleteUser(userId) {
    return await this.request(`/users/${encodeURIComponent(userId)}`, {
      method: 'DELETE'
    });
  }

  async listGroups() {
    return await this.request('/groups');
  }

  async listAdminModules() {
    return await this.request('/modules');
  }

  async createModule(payload) {
    return await this.request('/modules', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  async updateModule(code, payload) {
    return await this.request(`/modules/${encodeURIComponent(code)}`, {
      method: 'PUT',
      body: JSON.stringify(payload)
    });
  }

  async deleteModule(code) {
    return await this.request(`/modules/${encodeURIComponent(code)}`, {
      method: 'DELETE'
    });
  }

  async assignTeacherModule(code, teacherId) {
    return await this.request(`/modules/${encodeURIComponent(code)}/teachers`, {
      method: 'POST',
      body: JSON.stringify({ teacher_id: teacherId, module_code: code })
    });
  }

  async removeTeacherModule(code, teacherId) {
    return await this.request(`/modules/${encodeURIComponent(code)}/teachers/${encodeURIComponent(teacherId)}`, {
      method: 'DELETE'
    });
  }

  async deleteExam(examId) {
    return await this.request(`/exams/${encodeURIComponent(examId)}`, {
      method: 'DELETE'
    });
  }

  async importStudentsCsv(file) {
    const formData = new FormData();
    formData.append('file', file);
    const url = `${API_BASE}/admin/csv/import/students`;
    const headers = {};
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: formData
    });
    if (!response.ok) {
      let errorMsg = `Erreur HTTP ${response.status}`;
      try {
        const errData = await response.json();
        errorMsg = errData.detail || errorMsg;
      } catch (_) {}
      throw new Error(errorMsg);
    }
    return await response.json();
  }

  async importTeachersCsv(file) {
    const formData = new FormData();
    formData.append('file', file);
    const url = `${API_BASE}/admin/csv/import/teachers`;
    const headers = {};
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: formData
    });
    if (!response.ok) {
      let errorMsg = `Erreur HTTP ${response.status}`;
      try {
        const errData = await response.json();
        errorMsg = errData.detail || errorMsg;
      } catch (_) {}
      throw new Error(errorMsg);
    }
    return await response.json();
  }

  async getAdminBulletins(params = {}) {
    const searchParams = new URLSearchParams();
    if (params.speciality) searchParams.append('speciality', params.speciality);
    if (params.search) searchParams.append('search', params.search);
    const qs = searchParams.toString();
    return await this.request(`/admin/bulletins${qs ? '?' + qs : ''}`);
  }

  async getSingleStudentBulletin(studentId) {
    return await this.request(`/admin/bulletins/${encodeURIComponent(studentId)}`);
  }

  async getMyBulletin() {
    return await this.request('/student/bulletin');
  }

  // --- Téléchargements Fichiers Binaires Authentifiés (PDF, DOCX, ZIP) ---
  async downloadBlob(url, defaultFilename) {
    const headers = {};
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    const response = await fetch(`${API_BASE}${url}`, { headers });
    if (!response.ok) {
      let errorMsg = `Erreur de téléchargement (${response.status})`;
      try {
        const err = await response.json();
        errorMsg = err.detail || errorMsg;
      } catch (_) {}
      throw new Error(errorMsg);
    }
    
    // Détection du nom de fichier depuis le header Content-Disposition si présent
    let filename = defaultFilename;
    const cd = response.headers.get('content-disposition');
    if (cd && cd.includes('filename=')) {
      const match = cd.match(/filename=["']?([^"']+)["']?/);
      if (match && match[1]) filename = match[1];
    }
    
    const blob = await response.blob();
    const blobUrl = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = blobUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => window.URL.revokeObjectURL(blobUrl), 15000);
  }

  async downloadStudentBulletinPdf(studentId, filename) {
    return await this.downloadBlob(`/admin/bulletins/${encodeURIComponent(studentId)}/export-pdf`, filename || `bulletin_${studentId}.pdf`);
  }

  async downloadStudentBulletinDocx(studentId, filename) {
    return await this.downloadBlob(`/admin/bulletins/${encodeURIComponent(studentId)}/export-docx`, filename || `bulletin_${studentId}.docx`);
  }

  async downloadBulletinsZip(format = 'pdf', speciality = '') {
    const qs = new URLSearchParams();
    qs.append('format', format);
    if (speciality) qs.append('speciality', speciality);
    const specTag = speciality || 'toutes_specialites';
    return await this.downloadBlob(`/admin/bulletins/export-zip?${qs.toString()}`, `bulletins_${format}_${specTag}.zip`);
  }

  async downloadSpecialityResultsPdf(speciality = '', sortByModule = '') {
    const qs = new URLSearchParams();
    if (speciality) qs.append('speciality', speciality);
    if (sortByModule) qs.append('sort_by_module', sortByModule);
    const specTag = speciality || 'toutes_specialites';
    const sortTag = sortByModule ? `_${sortByModule.toLowerCase()}` : '';
    return await this.downloadBlob(`/admin/results/export-pdf?${qs.toString()}`, `palmares_${specTag}${sortTag}.pdf`);
  }

  async downloadSpecialityResultsDocx(speciality = '', sortByModule = '') {
    const qs = new URLSearchParams();
    if (speciality) qs.append('speciality', speciality);
    if (sortByModule) qs.append('sort_by_module', sortByModule);
    const specTag = speciality || 'toutes_specialites';
    const sortTag = sortByModule ? `_${sortByModule.toLowerCase()}` : '';
    return await this.downloadBlob(`/admin/results/export-docx?${qs.toString()}`, `palmares_${specTag}${sortTag}.docx`);
  }

  async downloadMyBulletinPdf() {
    return await this.downloadBlob('/student/bulletin/export-pdf', 'mon_bulletin_officiel.pdf');
  }

  async downloadMyBulletinDocx() {
    return await this.downloadBlob('/student/bulletin/export-docx', 'mon_bulletin_officiel.docx');
  }

  // --- PV & Bulletins de Classe par Spécialité et Module ---
  async getClassSheet(speciality, moduleCode) {
    const qs = new URLSearchParams({ speciality, module_code: moduleCode });
    return await this.request(`/admin/bulletins/class-sheet?${qs.toString()}`);
  }

  async downloadClassSheetPdf(speciality, moduleCode, filename = null) {
    const qs = new URLSearchParams({ speciality, module_code: moduleCode });
    const fn = filename || `pv_classe_${speciality}_${moduleCode}.pdf`;
    return await this.downloadBlob(`/admin/bulletins/class-sheet/export-pdf?${qs.toString()}`, fn);
  }

  async downloadClassSheetCsv(speciality, moduleCode, filename = null) {
    const qs = new URLSearchParams({ speciality, module_code: moduleCode });
    const fn = filename || `pv_classe_${speciality}_${moduleCode}.csv`;
    return await this.downloadBlob(`/admin/bulletins/class-sheet/export-csv?${qs.toString()}`, fn);
  }

  async clearAllExamsAndScores(clearPractice = false) {
    return await this.request(`/admin/clear-exams-and-scores?clear_practice=${clearPractice}`, {
      method: 'POST'
    });
  }

  // --- Générateur d'Épreuves Python (Banque d'Exercices) ---
  async getPythonBankStats() {
    return await this.request('/exams/python/bank-stats');
  }

  async generatePythonExam(payload) {
    return await this.request('/exams/python/generate', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  // --- Analyse Psychométrique & Discrimination des Questions ---
  async getItemAnalysis(examId) {
    return await this.request(`/exams/${examId}/item-analysis`);
  }

  async downloadItemAnalysisCsv(examId, filename = null) {
    const fn = filename || `analyse_questions_${examId}.csv`;
    return await this.downloadBlob(`/exams/${examId}/item-analysis/csv`, fn);
  }

  // --- Téléchargement des Notes Finales par Examen (Tous les Étudiants) ---
  async getExamResults(examId) {
    return await this.request(`/exams/${encodeURIComponent(examId)}/results`);
  }

  async downloadExamResultsCsv(examId, moduleCode = '', filename = null) {
    const fn = filename || `notes_finales_${moduleCode ? moduleCode + '_' : ''}${examId}.csv`;
    return await this.downloadBlob(`/exams/${encodeURIComponent(examId)}/results/export-csv`, fn);
  }

  async downloadExamResultsPdf(examId, moduleCode = '', filename = null) {
    const fn = filename || `pv_notes_finales_${moduleCode ? moduleCode + '_' : ''}${examId}.pdf`;
    return await this.downloadBlob(`/exams/${encodeURIComponent(examId)}/results/export-pdf`, fn);
  }

  async getSessionItemAnalysis(sessionId) {
    return await this.request(`/proctor/sessions/${sessionId}/item-analysis`);
  }

  async downloadSessionItemAnalysisCsv(sessionId, filename = null) {
    const fn = filename || `analyse_questions_session_${sessionId}.csv`;
    return await this.downloadBlob(`/proctor/sessions/${sessionId}/item-analysis/csv`, fn);
  }

  // --- Synchronisation USB & Déploiement Hors-Ligne (Phase 5) ---
  async exportExamPackage(examId, filename = null) {
    const fn = filename || `examen_${examId}.exam.zip`;
    return await this.downloadBlob(`/sync/exams/${examId}/export-package`, fn);
  }

  async importExamPackage(file) {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/sync/exams/import-package`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.token}`
      },
      body: formData
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Erreur lors de l'importation du package d'examen.");
    }
    return await res.json();
  }

  async exportSessionResultsZip(sessionId, filename = null) {
    const fn = filename || `resultats_${sessionId}.results.zip`;
    return await this.downloadBlob(`/sync/sessions/${sessionId}/export-results`, fn);
  }

  async importResultsZip(file) {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/sync/master/import-results`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.token}`
      },
      body: formData
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Erreur lors de la réconciliation de l'archive de résultats.");
    }
    return await res.json();
  }

  async downloadConsolidatedGradebook(moduleCode = null) {
    const qs = moduleCode ? `?module_code=${encodeURIComponent(moduleCode)}` : '';
    const fn = `notes_consolidees_${moduleCode || 'tous'}.csv`;
    return await this.downloadBlob(`/sync/master/consolidated-gradebook${qs}`, fn);
  }

  // --- Gestion & Création Manuelle de Questions (Web Editor) ---
  async createQuestion(examId, payload) {
    return await this.request(`/exams/${examId}/questions`, {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  async updateQuestion(examId, questionId, payload) {
    return await this.request(`/exams/${examId}/questions/${questionId}`, {
      method: 'PUT',
      body: JSON.stringify(payload)
    });
  }

  async deleteQuestion(examId, questionId) {
    return await this.request(`/exams/${examId}/questions/${questionId}`, {
      method: 'DELETE'
    });
  }

  async importQuestionsJson(examId, payload) {
    return await this.request(`/exams/${examId}/questions/import-json`, {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  async exportQuestionsJson(examId) {
    return await this.request(`/exams/${examId}/questions/export-json`);
  }

  // --- Exécution Python & Tests AlgoCompiler (Sandbox) ---
  async runPythonCode(code, stdin = "", timeout = 3.0) {
    return await this.request('/training/python/run-code', {
      method: 'POST',
      body: JSON.stringify({ code, stdin, timeout })
    });
  }

  async runPythonTests(param1, param2, runAll = false, timeout = 3.0) {
    let payload = {};
    if (Array.isArray(param2)) {
      // Appel sous forme: runPythonTests(code, testsArray, runAll, timeout)
      payload = { code: String(param1 || ''), tests: param2, run_all: Boolean(runAll), timeout };
    } else if (Array.isArray(param1)) {
      // Appel inversé: runPythonTests(testsArray, code, runAll, timeout)
      payload = { code: String(param2 || ''), tests: param1, run_all: Boolean(runAll), timeout };
    } else {
      // Appel standard: runPythonTests(exerciseId, code, runAll, timeout)
      payload = { exercise_id: param1, code: String(param2 || ''), run_all: Boolean(runAll), timeout };
    }
    return await this.request('/training/python/run-tests', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  // --- Centre d'Entraînement Linux (POSIX & Shell) ---
  async getLinuxChapters() {
    return await this.request('/training/linux/chapters');
  }

  async getLinuxChapter(chapterId, sessionType = null) {
    const qs = sessionType ? `?session_type=${encodeURIComponent(sessionType)}` : '';
    return await this.request(`/training/linux/chapters/${encodeURIComponent(chapterId)}${qs}`);
  }

  async getLinuxProgression() {
    return await this.request('/training/linux/progression');
  }

  async generateLinuxSession(params = {}) {
    return await this.request('/training/linux/generate-session', {
      method: 'POST',
      body: JSON.stringify(params)
    });
  }

  async submitLinuxSession(answers = []) {
    return await this.request('/training/linux/submit-session', {
      method: 'POST',
      body: JSON.stringify({ answers })
    });
  }

  async getLinuxCurriculum() {
    return await this.request('/training/linux/curriculum');
  }

  async getLinuxChallenges(level = null) {
    const qs = level ? `?level=${encodeURIComponent(level)}` : '';
    return await this.request(`/training/linux/challenges${qs}`);
  }

  async getLinuxChallenge(challengeId) {
    return await this.request(`/training/linux/challenges/${encodeURIComponent(challengeId)}`);
  }

  async getLinuxTheoryQuizzes(level = null, topic = null) {
    const params = new URLSearchParams();
    if (level) params.append('level', level);
    if (topic) params.append('topic', topic);
    const qs = params.toString() ? `?${params.toString()}` : '';
    return await this.request(`/training/linux/theory/quizzes${qs}`);
  }

  async submitLinuxChallenge(payload) {
    return await this.request('/training/linux/submit-challenge', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }
}

export const api = new ApiClient();
