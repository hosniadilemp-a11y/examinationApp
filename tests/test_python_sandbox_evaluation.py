import pytest

def test_user_reported_alternative_code_awarded_full_points(client, student_headers):
    """
    Vérifie qu'un code valide alternatif soumis par un étudiant pour un exercice de programmation
    (ici l'exercice 'Premier, milieu, dernier' id=3026) est exécuté contre les cas de test
    et validé à 100%, même si sa chaîne de caractères diffère de la solution de référence.
    """
    payload = {
        "assessment_type": "training",
        "selected_topics": ["python_basics"],
        "selected_difficulties": ["medium"],
        "target_topic": "python_basics",
        "target_difficulty": "medium",
        "answers": [
            {
                "id": 3026,
                "type": "coding",
                "topic": "Python Basics",
                "difficulty": "medium",
                # Solution alternative correcte utilisant l'indexation au lieu du tuple unpacking
                "student_answer": (
                    "values = list(map(int, input().split()))\n"
                    "# print first middle last\n"
                    "print(values[0],values[len(values)//2],values[-1])\n"
                ),
                "hints_used": 0,
                "is_correct": None
            }
        ]
    }

    res = client.post("/api/training/python/submit-session", headers=student_headers, json=payload)
    assert res.status_code == 200, f"Submit failed: {res.text}"
    data = res.json()

    assert data["percentage"] == 100.0, f"Expected 100%, got {data['percentage']}"
    assert len(data["feedback"]) == 1
    feedback = data["feedback"][0]
    assert feedback["is_correct"] is True, f"Exercise was expected to be correct. Explanation: {feedback.get('explanation')}"
    assert feedback["awarded_points"] == feedback["max_points"]
    assert "validé avec succès" in feedback["explanation"]

