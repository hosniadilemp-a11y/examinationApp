// Pyodide Web Worker - Exécution Python 100% Hors-Ligne dans un thread isolé (ES Module)
// Neutralisation stricte de importScripts pour empêcher le faux positif isClassicWorker() dans Pyodide v0.26+
try {
    delete self.importScripts;
    delete globalThis.importScripts;
} catch (e) {}
try {
    self.importScripts = undefined;
    globalThis.importScripts = undefined;
} catch (e) {}

let pyodideReadyPromise = null;
let pyodide = null;

async function initPyodideWorker() {
    if (!pyodideReadyPromise) {
        pyodideReadyPromise = (async () => {
            const { loadPyodide } = await import('/vendor/pyodide/pyodide.mjs');
            pyodide = await loadPyodide({
                indexURL: '/vendor/pyodide/'
            });
            return pyodide;
        })();
    }
    return pyodideReadyPromise;
}

self.onmessage = async (e) => {
    const { action, id, code, tests } = e.data;
    
    try {
        await initPyodideWorker();
        
        if (action === "RUN") {
            const result = runPythonCode(code, e.data.input || "");
            self.postMessage({ id, success: true, ...result });
        } else if (action === "TEST_SUITE") {
            const results = runTestSuite(code, tests || []);
            self.postMessage({ id, success: true, ...results });
        } else {
            self.postMessage({ id, success: false, error: "Action inconnue" });
        }
    } catch (err) {
        self.postMessage({ id, success: false, error: err.message || String(err) });
    }
};

function runPythonCode(code, inputStr) {
    const startTime = performance.now();

    // Configuration de la redirection stdout / stdin, exécution sécurisée et extraction de traceback (REV-19, REV-24)
    pyodide.globals.set("_raw_input_data", inputStr || "");
    pyodide.globals.set("_student_code_to_exec", code);

    const setupAndRunPython = `
import sys
import io
import builtins
import traceback

_raw_input = _raw_input_data if isinstance(_raw_input_data, str) else ""
_input_lines = _raw_input.splitlines()
_cur_input_idx = 0

def _safe_input_mock(prompt=""):
    global _cur_input_idx
    if _cur_input_idx < len(_input_lines):
        val = _input_lines[_cur_input_idx]
        _cur_input_idx += 1
        return val
    return "0"

builtins.input = _safe_input_mock

class SafeStdin:
    def __init__(self, text):
        self.lines = text.splitlines(keepends=True)
        self.idx = 0
    def readline(self):
        if self.idx < len(self.lines):
            line = self.lines[self.idx]
            self.idx += 1
            return line
        return "0\\n"
    def read(self, n=-1):
        rem = "".join(self.lines[self.idx:])
        self.idx = len(self.lines)
        return rem if rem else "0\\n"

sys.stdin = SafeStdin(_raw_input)
sys.stdout = io.StringIO()
sys.stderr = io.StringIO()

_student_error = None
_user_globals = {"__name__": "__main__", "input": _safe_input_mock}

try:
    _compiled = compile(_student_code_to_exec, "<script.py>", "exec")
    exec(_compiled, _user_globals)
except SyntaxError as se:
    _student_error = f"SyntaxError: {se.msg} (à la ligne {se.lineno})"
except Exception:
    _raw_tb = traceback.format_exc()
    _student_error = _raw_tb.strip()
`;

    let jsError = null;
    try {
        pyodide.runPython(setupAndRunPython);
    } catch (err) {
        jsError = err.message || String(err);
    }
    
    const extractPython = `
stdout_val = sys.stdout.getvalue()
stderr_val = sys.stderr.getvalue()
error_val = _student_error
`;
    pyodide.runPython(extractPython);
    const stdout = pyodide.globals.get("stdout_val");
    const stderr = pyodide.globals.get("stderr_val");
    const pyError = pyodide.globals.get("error_val");
    const executionTimeMs = Math.round(performance.now() - startTime);

    let finalError = pyError || jsError || null;
    if (finalError && typeof finalError === "string" && finalError.startsWith("PythonError: ")) {
        finalError = finalError.substring("PythonError: ".length);
    }
    
    return {
        stdout: stdout || "",
        stderr: stderr || "",
        error: finalError,
        executionTimeMs
    };
}

function runTestSuite(code, tests) {
    const testResults = [];
    let allPassed = true;
    
    for (let i = 0; i < tests.length; i++) {
        const test = tests[i];
        const res = runPythonCode(code, test.input || "");
        const actualOutput = (res.stdout || "").trim();
        const expectedOutput = (test.output || "").trim();
        const passed = !res.error && (actualOutput === expectedOutput);
        
        if (!passed) allPassed = false;
        
        testResults.push({
            test_number: i + 1,
            input: test.input,
            expected: expectedOutput,
            actual: actualOutput,
            error: res.error,
            passed: passed
        });
    }
    
    return {
        all_passed: allPassed,
        passed_count: testResults.filter(t => t.passed).length,
        total_tests: tests.length,
        tests: testResults
    };
}
