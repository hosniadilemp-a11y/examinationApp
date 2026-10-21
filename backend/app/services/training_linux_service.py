# Compatibility re-export module: delegating to linux_training_service
from backend.app.services.linux_training_service import (
    load_linux_curriculum,
    load_linux_challenges,
    get_levels_summary,
    get_safe_challenges_list,
    get_challenge_detail_student,
    get_theory_quizzes,
    evaluate_linux_challenge,
    sync_student_linux_pillar,
    get_student_linux_progress,
    get_student_linux_history,
    list_linux_chapters,
    get_linux_chapter_details,
    generate_linux_session,
    evaluate_linux_session_submission,
    get_linux_progression_stats
)
