import os
import sys
import time
import json
import tempfile
import subprocess
from typing import List, Dict, Any, Optional

DEFAULT_TIMEOUT_SECONDS = 3.0
POLL_INTERVAL_SECONDS = 0.01

FIGURE_HOOK = (
    "\ntry:\n"
    "    import sys as _mpl_sys\n"
    "    if 'matplotlib' in _mpl_sys.modules:\n"
    "        import matplotlib.pyplot as _mpl_plt\n"
    "        import io as _mpl_io, base64 as _mpl_base64\n"
    "        _mpl_figs = _mpl_plt.get_fignums()\n"
    "        if _mpl_figs:\n"
    "            _mpl_b64_list = []\n"
    "            for _fnum in _mpl_figs:\n"
    "                _fig = _mpl_plt.figure(_fnum)\n"
    "                _buf = _mpl_io.BytesIO()\n"
    "                _fig.savefig(_buf, format='png', bbox_inches='tight', dpi=100)\n"
    "                _buf.seek(0)\n"
    "                _b64 = _mpl_base64.b64encode(_buf.read()).decode('ascii')\n"
    "                _mpl_b64_list.append(f'data:image/png;base64,{_b64}')\n"
    "                _mpl_plt.close(_fig)\n"
    "            if _mpl_b64_list:\n"
    "                import json as _mpl_json\n"
    "                print(f'\\n__ALGO_FIGURES_JSON__:{_mpl_json.dumps(_mpl_b64_list)}:__ALGO_FIGURES_JSON__')\n"
    "except Exception:\n"
    "    pass\n"
)

def extract_figures_and_clean_stdout(raw_stdout: str) -> tuple[str, List[str]]:
    """Extrait les graphiques matplotlib/seaborn convertis en base64 et nettoie le stdout."""
    figures = []
    if "__ALGO_FIGURES_JSON__:" in raw_stdout:
        parts = raw_stdout.split("__ALGO_FIGURES_JSON__:")
        clean_parts = [parts[0]]
        for p in parts[1:]:
            subparts = p.split(":__ALGO_FIGURES_JSON__")
            if subparts:
                try:
                    figs_data = json.loads(subparts[0].strip())
                    if isinstance(figs_data, list):
                        figures.extend(figs_data)
                except Exception:
                    pass
                if len(subparts) > 1:
                    clean_parts.append(subparts[1])
        raw_stdout = "".join(clean_parts).strip()
    return raw_stdout, figures

def normalize_output(value: Any) -> str:
    """Normalise les sorties pour comparaison équitable sans faux négatifs d'espaces blancs."""
    text = "" if value is None else str(value)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    return "\n".join(lines).strip()

def run_python_script(script_path: str, input_data: str, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS) -> Dict[str, Any]:
    """Exécute un script Python dans un sous-processus isolé avec capture métriques."""
    start_time = time.perf_counter()
    timed_out = False
    
    # Environnement propre avec backend matplotlib non-interactif Agg
    clean_env = os.environ.copy()
    clean_env["PYTHONIOENCODING"] = "utf-8"
    clean_env["MPLBACKEND"] = "Agg"
    default_mpl_dir = os.path.join(os.path.expanduser("~"), ".matplotlib")
    if os.path.exists(default_mpl_dir):
        clean_env["MPLCONFIGDIR"] = default_mpl_dir
    else:
        clean_env["MPLCONFIGDIR"] = tempfile.gettempdir()
    
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    
    try:
        process = subprocess.Popen(
            [sys.executable, "-X", "utf8", script_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=clean_env,
            cwd=project_root
        )
        
        try:
            stdout, stderr = process.communicate(input=input_data or "", timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            stdout, stderr = process.communicate()
            
    except Exception as e:
        return {
            "returncode": -1,
            "stdout": "",
            "stderr": f"Erreur système d'exécution : {str(e)}",
            "timed_out": False,
            "execution_time_ms": round((time.perf_counter() - start_time) * 1000, 2)
        }
        
    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
    return {
        "returncode": process.returncode,
        "stdout": stdout or "",
        "stderr": stderr or "",
        "timed_out": timed_out,
        "execution_time_ms": elapsed_ms
    }

def execute_user_code_with_input(python_code: str, custom_input: str, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS) -> Dict[str, Any]:
    """Exécute le code Python de l'étudiant avec une entrée personnalisée (Console E/S)."""
    sandbox_header = "import sys\n"
    full_code = sandbox_header + "\n" + python_code + "\n" + FIGURE_HOOK
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as temp_file:
        temp_file.write(full_code)
        script_path = temp_file.name
        
    try:
        run_res = run_python_script(script_path, custom_input, timeout_seconds)
        clean_out, figs = extract_figures_and_clean_stdout(run_res["stdout"])
        return {
            "success": not run_res["timed_out"] and run_res["returncode"] == 0,
            "stdout": clean_out,
            "stderr": run_res["stderr"],
            "figures": figs,
            "timed_out": run_res["timed_out"],
            "execution_time_ms": run_res["execution_time_ms"]
        }
    finally:
        if os.path.exists(script_path):
            try:
                os.remove(script_path)
            except OSError:
                pass

def execute_user_code_against_tests(
    python_code: str,
    test_cases: List[Dict[str, Any]],
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    mask_hidden_output: bool = True
) -> Dict[str, Any]:
    """
    Exécute le code Python de l'étudiant contre une liste de cas de test.
    Si mask_hidden_output=True, les sorties attendues des tests cachés ne sont jamais révélées au client.
    """
    sandbox_header = "import sys\n"
    full_code = sandbox_header + "\n" + python_code + "\n" + FIGURE_HOOK
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as temp_file:
        temp_file.write(full_code)
        script_path = temp_file.name
        
    results = []
    all_passed = True
    total_time_ms = 0.0
    
    try:
        for idx, tc in enumerate(test_cases, start=1):
            tc_id = tc.get("id", f"tc_{idx}")
            input_data = tc.get("input", "")
            raw_expected = tc.get("output", tc.get("expected_output", ""))
            expected_normalized = normalize_output(raw_expected)
            is_public = tc.get("is_public", True)
            
            run_res = run_python_script(script_path, input_data, timeout_seconds)
            total_time_ms += run_res["execution_time_ms"]
            
            clean_out, figs = extract_figures_and_clean_stdout(run_res["stdout"])
            actual_normalized = normalize_output(clean_out)
            
            passed = False
            error_msg = None
            
            if run_res["timed_out"]:
                error_msg = f"Délai d'exécution dépassé (> {timeout_seconds}s)"
            elif run_res["returncode"] != 0:
                error_msg = run_res["stderr"] or "Erreur d'exécution"
            else:
                passed = (
                    actual_normalized == expected_normalized
                    or actual_normalized.split() == expected_normalized.split()
                )
                
            if not passed:
                all_passed = False
                
            # Sécurité & Secret absolu : masquer les détails si test caché
            if not is_public and mask_hidden_output:
                res_item = {
                    "test_case_id": tc_id,
                    "is_public": False,
                    "passed": passed,
                    "input": "[Test Caché]",
                    "expected_output": "[Protégé]",
                    "actual_output": "[Protégé]" if passed else (clean_out[:80] + "..." if len(clean_out) > 80 else clean_out),
                    "figures": [],
                    "error": error_msg,
                    "execution_time_ms": run_res["execution_time_ms"]
                }
            else:
                res_item = {
                    "test_case_id": tc_id,
                    "is_public": is_public,
                    "passed": passed,
                    "input": input_data,
                    "expected_output": expected_normalized,
                    "actual_output": actual_normalized,
                    "figures": figs,
                    "error": error_msg,
                    "execution_time_ms": run_res["execution_time_ms"]
                }
            results.append(res_item)
            
    finally:
        if os.path.exists(script_path):
            try:
                os.remove(script_path)
            except OSError:
                pass
                
    passed_count = sum(1 for r in results if r["passed"])
    return {
        "success": True,
        "all_passed": all_passed,
        "passed_count": passed_count,
        "total_count": len(results),
        "total_execution_time_ms": round(total_time_ms, 2),
        "avg_execution_time_ms": round(total_time_ms / len(results), 2) if results else 0.0,
        "results": results
    }


