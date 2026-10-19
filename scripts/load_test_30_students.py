import asyncio
import time
import statistics
from typing import List, Dict, Any
import httpx

BASE_URL = "http://127.0.0.1:8000"

async def simulate_student(client: httpx.AsyncClient, student_index: int, session_id: str, exam_id: str) -> Dict[str, Any]:
    username = f"etudiant_{student_index:02d}"
    password = f"pass_{student_index:02d}"
    latencies = []
    
    # 1. Authentification
    t0 = time.perf_counter()
    res_login = await client.post(f"{BASE_URL}/api/auth/login", json={"username": username, "password": password})
    latencies.append(time.perf_counter() - t0)
    if res_login.status_code != 200:
        return {"student": username, "success": False, "step": "login", "status": res_login.status_code}
    
    token = res_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Démarrage de l'examen et récupération des questions mélangées
    t0 = time.perf_counter()
    res_start = await client.post(f"{BASE_URL}/api/student/exam/{exam_id}/start?session_id={session_id}", headers=headers)
    latencies.append(time.perf_counter() - t0)
    if res_start.status_code != 200:
        return {"student": username, "success": False, "step": "start", "status": res_start.status_code}
    
    start_data = res_start.json()
    attempt_id = start_data["attempt_id"]
    questions = start_data.get("questions", [])
    
    # 3. Simulation de 3 cycles d'autosauvegarde simultanée avec télémétrie de sécurité
    for cycle in range(3):
        # Envoi d'un événement de télémétrie
        t0 = time.perf_counter()
        res_sec = await client.post(
            f"{BASE_URL}/api/student/exam/{attempt_id}/security-event",
            headers=headers,
            json={"event_type": "FOCUS_VERIFIED", "details": f"Heartbeat cycle {cycle}"}
        )
        latencies.append(time.perf_counter() - t0)
        
        # Envoi d'autosauvegarde pour chaque question
        answers_payload = {}
        for q in questions:
            answers_payload[q["id"]] = "a"  # Réponse simulée
            
        t0 = time.perf_counter()
        res_save = await client.post(
            f"{BASE_URL}/api/student/exam/{attempt_id}/autosave",
            headers=headers,
            json={"answers": answers_payload}
        )
        latencies.append(time.perf_counter() - t0)
        if res_save.status_code != 200:
            return {"student": username, "success": False, "step": "autosave", "status": res_save.status_code}
            
        await asyncio.sleep(0.1) # Micro-pause entre cycles
        
    # 4. Soumission finale de l'examen
    t0 = time.perf_counter()
    res_submit = await client.post(f"{BASE_URL}/api/student/exam/{attempt_id}/submit", headers=headers)
    latencies.append(time.perf_counter() - t0)
    if res_submit.status_code != 200:
        return {"student": username, "success": False, "step": "submit", "status": res_submit.status_code}
        
    score_data = res_submit.json()
    return {
        "student": username,
        "success": True,
        "final_mark": score_data.get("final_mark", 0.0),
        "requests_count": len(latencies),
        "latencies": latencies
    }

async def run_load_test_30_students(session_id: str, exam_id: str, student_count: int = 30) -> Dict[str, Any]:
    print(f"\n🚀 Lancement du test de charge : {student_count} étudiants simultanés...")
    start_time = time.perf_counter()
    
    limits = httpx.Limits(max_keepalive_connections=50, max_connections=100)
    async with httpx.AsyncClient(limits=limits, timeout=30.0) as client:
        tasks = [simulate_student(client, i, session_id, exam_id) for i in range(1, student_count + 1)]
        results = await asyncio.gather(*tasks)
        
    total_duration = time.perf_counter() - start_time
    
    successes = [r for r in results if r.get("success")]
    failures = [r for r in results if not r.get("success")]
    
    all_latencies = []
    for r in successes:
        all_latencies.extend(r.get("latencies", []))
        
    metrics = {
        "student_count": student_count,
        "total_duration_seconds": round(total_duration, 2),
        "successful_students": len(successes),
        "failed_students": len(failures),
        "total_requests": len(all_latencies),
        "requests_per_second": round(len(all_latencies) / total_duration, 1) if total_duration > 0 else 0,
        "latency_mean_ms": round(statistics.mean(all_latencies) * 1000, 2) if all_latencies else 0,
        "latency_p95_ms": round(statistics.quantiles(all_latencies, n=20)[18] * 1000, 2) if len(all_latencies) >= 20 else 0,
        "latency_max_ms": round(max(all_latencies) * 1000, 2) if all_latencies else 0
    }
    
    print("\n📊 Résultats du Test de Charge Concurrente (30 Postes) :")
    print(f"  • Étudiants réussis : {metrics['successful_students']} / {student_count} (100% requis)")
    print(f"  • Requêtes totales  : {metrics['total_requests']} en {metrics['total_duration_seconds']}s")
    print(f"  • Débit moyen       : {metrics['requests_per_second']} requêtes/sec")
    print(f"  • Latence moyenne   : {metrics['latency_mean_ms']} ms")
    print(f"  • Latence P95       : {metrics['latency_p95_ms']} ms")
    print(f"  • Latence Max       : {metrics['latency_max_ms']} ms")
    
    return metrics

if __name__ == "__main__":
    print("Script de test de charge 30 étudiants.")
