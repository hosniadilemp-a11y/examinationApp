import re

path = 'backend/app/routers/student_exam.py'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

target = '''        detailed_questions.append({
            "index": idx,
            "id": q.id,
            "type": q.type,
            "prompt": q.prompt_markdown,
            "points": q.points,
            "options": opts,
            "user_answer": user_ans,
            "correct_answer": corr_ans,'''

replacement = '''        display_corr_ans = corr_ans
        if isinstance(corr_ans, dict):
            if "solution" in corr_ans:
                display_corr_ans = corr_ans["solution"]
            elif "answer" in corr_ans:
                display_corr_ans = corr_ans["answer"]

        detailed_questions.append({
            "index": idx,
            "id": q.id,
            "type": q.type,
            "prompt": q.prompt_markdown,
            "points": q.points,
            "options": opts,
            "user_answer": user_ans,
            "correct_answer": display_corr_ans,'''

if target in text:
    text = text.replace(target, replacement, 1)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)
    print("SUCCESSFULLY PATCHED student_exam.py")
else:
    # Try normalizing newlines
    norm_text = text.replace('\r\n', '\n')
    if target in norm_text:
        norm_text = norm_text.replace(target, replacement, 1)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(norm_text)
        print("SUCCESSFULLY PATCHED student_exam.py (normalized)")
    else:
        print("FAILED TO MATCH TARGET")

