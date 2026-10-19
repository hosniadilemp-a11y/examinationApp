// Pyodide Runner avec Watchdog de 5 secondes pour sécurité anti-boucle infinie
export class PyodideRunner {
    constructor(workerScriptUrl = '/js/pyodide-worker.js') {
        this.workerScriptUrl = workerScriptUrl;
        this.worker = null;
        this.pendingRequests = new Map();
        this._initWorker();
    }

    _initWorker() {
        if (this.worker) {
            try { this.worker.terminate(); } catch (e) { }
            this.worker = null;
        }
        try {
            this.worker = new Worker(this.workerScriptUrl, { type: 'module' });
        } catch (e) {
            console.error("Échec de création du Worker ES module:", e);
            return;
        }
        this.worker.onmessage = (e) => {
            const { id, success, ...data } = e.data;
            if (this.pendingRequests.has(id)) {
                const { resolve, reject, timer } = this.pendingRequests.get(id);
                clearTimeout(timer);
                this.pendingRequests.delete(id);
                if (success) {
                    resolve(data);
                } else {
                    reject(new Error(data.error || "Erreur d'exécution"));
                }
            }
        };

        this.worker.onerror = (err) => {
            console.error("Erreur critique Pyodide Worker:", err);
            for (const [id, req] of this.pendingRequests.entries()) {
                clearTimeout(req.timer);
                req.reject(new Error(err.message || "Erreur lors de l'exécution du script Python."));
            }
            this.pendingRequests.clear();
        };
    }

    executeWithWatchdog(action, payload = {}, timeoutMs = 5000) {
        return new Promise((resolve, reject) => {
            const id = 'req_' + Math.random().toString(36).substr(2, 9);
            
            // Watchdog Timer de 5 secondes pour interrompre les boucles infinies (while True: pass)
            const timer = setTimeout(() => {
                if (this.pendingRequests.has(id)) {
                    this.pendingRequests.delete(id);
                    console.warn(`Watchdog 5s déclenché pour la requête ${id}. Interruption du Worker.`);
                    
                    // Terminaison immédiate du thread bloqué
                    this.worker.terminate();
                    this.worker = null;
                    
                    // Réinstanciation immédiate d'un Worker tout neuf
                    this._initWorker();
                    
                    reject({
                        timeout: true,
                        error: "Temps d'exécution dépassé (Watchdog 5s). Boucle infinie interrompue proprement sans figer le navigateur."
                    });
                }
            }, timeoutMs);

            this.pendingRequests.set(id, { resolve, reject, timer });

            try {
                if (!this.worker) {
                    this._initWorker();
                }
                this.worker.postMessage({ action, id, ...payload });
            } catch (err) {
                clearTimeout(timer);
                this.pendingRequests.delete(id);
                reject(err);
            }
        });
    }

    async runCode(code, inputStr = "") {
        return this.executeWithWatchdog("RUN", { code, input: inputStr });
    }

    async runTests(code, tests = []) {
        return this.executeWithWatchdog("TEST_SUITE", { code, tests });
    }
}

// Instance singleton pour l'application
export const pythonRunner = new PyodideRunner();
