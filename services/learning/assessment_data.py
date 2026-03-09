"""
Deterministic assessment questions pool.
Questions are grouped by CEFR level, from A0 upwards.
Each question has: text, type, expected answer(s), level.
The bot asks questions in order; AI evaluates free-form answers.
"""

ASSESSMENT_QUESTIONS: list[dict] = [
    # --- A0 ---
    {
        "level": "A0",
        "text": "Переведи на английский: «Привет»",
        "type": "translate",
        "answers": ["hello", "hi", "hey"],
    },
    {
        "level": "A0",
        "text": "Переведи на английский: «Спасибо»",
        "type": "translate",
        "answers": ["thank you", "thanks"],
    },
    {
        "level": "A0",
        "text": "Как по-английски «кошка»?",
        "type": "translate",
        "answers": ["cat", "a cat"],
    },
    # --- A1 ---
    {
        "level": "A1",
        "text": "Вставь пропущенное слово:\nShe ___ a student. (is/are/am)",
        "type": "fill",
        "answers": ["is"],
    },
    {
        "level": "A1",
        "text": "Переведи: «У меня есть собака»",
        "type": "translate",
        "answers": ["i have a dog"],
    },
    {
        "level": "A1",
        "text": "Выбери правильный вариант:\nHe go / goes to school every day.",
        "type": "choice",
        "answers": ["goes"],
    },
    # --- A2 ---
    {
        "level": "A2",
        "text": "Поставь глагол в Past Simple:\nYesterday I (go) to the park.",
        "type": "fill",
        "answers": ["went"],
    },
    {
        "level": "A2",
        "text": "Выбери правильный артикль:\nI saw ___ interesting film. (a/an/the)",
        "type": "fill",
        "answers": ["an"],
    },
    {
        "level": "A2",
        "text": "Переведи: «Что ты делал вчера вечером?»",
        "type": "translate",
        "answers": [
            "what did you do yesterday evening",
            "what did you do last evening",
            "what were you doing yesterday evening",
            "what were you doing last night",
            "what did you do last night",
        ],
    },
    # --- B1 ---
    {
        "level": "B1",
        "text": "Закончи предложение:\nIf it rains tomorrow, I ___ (stay) at home.",
        "type": "fill",
        "answers": ["will stay"],
    },
    {
        "level": "B1",
        "text": "Выбери правильное время:\nI ___ (live) in Moscow for 5 years. (lived / have lived / am living)",
        "type": "fill",
        "answers": ["have lived"],
    },
    {
        "level": "B1",
        "text": "Переведи: «Он сказал, что придёт завтра»",
        "type": "translate",
        "answers": [
            "he said he would come tomorrow",
            "he said that he would come tomorrow",
            "he said he would come the next day",
        ],
    },
    # --- B2 ---
    {
        "level": "B2",
        "text": "Перепиши в пассивном залоге:\nSomeone stole my bike yesterday.",
        "type": "transform",
        "answers": [
            "my bike was stolen yesterday",
            "my bike was stolen",
        ],
    },
    {
        "level": "B2",
        "text": "Вставь правильную форму:\nI wish I ___ (know) the answer.",
        "type": "fill",
        "answers": ["knew"],
    },
    {
        "level": "B2",
        "text": "Объясни разницу между 'make' и 'do' — дай по одному примеру.",
        "type": "free",
        "answers": [],  # AI evaluates
    },
    # --- C1 ---
    {
        "level": "C1",
        "text": "Перефразируй, используя инверсию:\nI have never seen such a beautiful sunset.",
        "type": "transform",
        "answers": [
            "never have i seen such a beautiful sunset",
            "never have i seen so beautiful a sunset",
        ],
    },
    {
        "level": "C1",
        "text": "Что значит идиома 'to bite the bullet'? Дай пример использования.",
        "type": "free",
        "answers": [],
    },
]

LEVEL_ORDER = ["A0", "A1", "A2", "B1", "B2", "C1"]

# How many correct answers needed at a level to "pass" it
PASS_THRESHOLD = 2  # out of 3 questions per level


def get_question(index: int) -> dict | None:
    """Get question by index. Returns None if out of range."""
    if 0 <= index < len(ASSESSMENT_QUESTIONS):
        return ASSESSMENT_QUESTIONS[index]
    return None


def total_questions() -> int:
    return len(ASSESSMENT_QUESTIONS)


def check_answer_deterministic(question: dict, user_answer: str) -> bool:
    """Quick deterministic check. Returns True if answer matches any expected answer."""
    if not question["answers"]:
        return False  # free-form — needs AI check
    normalized = user_answer.strip().lower().rstrip(".!?")
    return any(normalized == a.lower() for a in question["answers"])


def calculate_level(scores_by_level: dict[str, dict]) -> tuple[str, dict]:
    """
    Given scores like {"A0": {"correct": 2, "total": 3}, ...}
    determine the final CEFR level and sub-scores.
    """
    determined_level = "A0"

    for level in LEVEL_ORDER:
        stats = scores_by_level.get(level, {"correct": 0, "total": 0})
        if stats["total"] == 0:
            break
        if stats["correct"] >= PASS_THRESHOLD:
            determined_level = level
        else:
            break

    # Calculate sub-scores
    total_correct = sum(s["correct"] for s in scores_by_level.values())
    total_q = sum(s["total"] for s in scores_by_level.values())
    overall_score = total_correct / total_q if total_q > 0 else 0.0

    # Approximate sub-scores from level distribution
    grammar_levels = {"A1", "A2", "B1", "B2"}
    vocab_levels = {"A0", "A1"}

    grammar_correct = sum(scores_by_level.get(l, {}).get("correct", 0) for l in grammar_levels)
    grammar_total = sum(scores_by_level.get(l, {}).get("total", 0) for l in grammar_levels)
    vocab_correct = sum(scores_by_level.get(l, {}).get("correct", 0) for l in vocab_levels)
    vocab_total = sum(scores_by_level.get(l, {}).get("total", 0) for l in vocab_levels)

    return determined_level, {
        "overall_score": overall_score,
        "grammar_score": grammar_correct / grammar_total if grammar_total else 0.0,
        "vocabulary_score": vocab_correct / vocab_total if vocab_total else 0.0,
    }
