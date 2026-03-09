from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)


def goal_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="🆕 С нуля", callback_data="goal:from_zero")],
        [InlineKeyboardButton(text="💬 Разговорный", callback_data="goal:conversational")],
        [InlineKeyboardButton(text="💼 Для работы", callback_data="goal:for_work")],
        [InlineKeyboardButton(text="📝 Для экзамена", callback_data="goal:for_exam")],
        [InlineKeyboardButton(text="✈️ Для путешествий", callback_data="goal:for_travel")],
        [InlineKeyboardButton(text="💻 Для IT", callback_data="goal:for_it")],
        [InlineKeyboardButton(text="🏥 Для медицины", callback_data="goal:for_medicine")],
        [InlineKeyboardButton(text="📊 Для бизнеса", callback_data="goal:for_business")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def minutes_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="10 мин", callback_data="minutes:10"),
            InlineKeyboardButton(text="20 мин", callback_data="minutes:20"),
        ],
        [
            InlineKeyboardButton(text="30 мин", callback_data="minutes:30"),
            InlineKeyboardButton(text="45 мин", callback_data="minutes:45"),
        ],
        [InlineKeyboardButton(text="60 мин", callback_data="minutes:60")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="📚 Начать урок"), KeyboardButton(text="📖 Мой план")],
        [KeyboardButton(text="🔤 Слова"), KeyboardButton(text="💬 Практика диалога")],
        [KeyboardButton(text="❌ Мои ошибки"), KeyboardButton(text="📊 Прогресс")],
        [KeyboardButton(text="⚙️ Настройки")],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def lesson_topic_keyboard(level: str) -> InlineKeyboardMarkup:
    topics_by_level = {
        "A0": [
            ("Алфавит и звуки", "lesson:alphabet_and_sounds"),
            ("Приветствия", "lesson:greetings"),
            ("Числа 1-20", "lesson:numbers"),
            ("Цвета", "lesson:colors"),
            ("Простые фразы", "lesson:basic_phrases"),
        ],
        "A1": [
            ("Present Simple", "lesson:present_simple"),
            ("To be", "lesson:to_be"),
            ("Артикли a/an/the", "lesson:articles"),
            ("Предлоги места", "lesson:prepositions_place"),
            ("Еда и напитки", "lesson:food_and_drinks"),
        ],
        "A2": [
            ("Past Simple", "lesson:past_simple"),
            ("Present Continuous", "lesson:present_continuous"),
            ("Модальные глаголы", "lesson:modal_verbs"),
            ("Сравнительные степени", "lesson:comparatives"),
            ("Путешествия", "lesson:travel"),
        ],
        "B1": [
            ("Present Perfect", "lesson:present_perfect"),
            ("Future forms", "lesson:future_forms"),
            ("Условные предложения", "lesson:conditionals"),
            ("Reported Speech", "lesson:reported_speech"),
            ("Работа и карьера", "lesson:work_career"),
        ],
        "B2": [
            ("Passive Voice", "lesson:passive_voice"),
            ("Advanced Conditionals", "lesson:advanced_conditionals"),
            ("Gerund vs Infinitive", "lesson:gerund_infinitive"),
            ("Фразовые глаголы", "lesson:phrasal_verbs"),
            ("Бизнес-английский", "lesson:business_english"),
        ],
        "C1": [
            ("Inversion", "lesson:inversion"),
            ("Cleft sentences", "lesson:cleft_sentences"),
            ("Advanced idioms", "lesson:advanced_idioms"),
            ("Academic writing", "lesson:academic_writing"),
            ("Debate & argumentation", "lesson:debate"),
        ],
    }
    topics = topics_by_level.get(level, topics_by_level["A1"])
    buttons = [[InlineKeyboardButton(text=name, callback_data=data)] for name, data in topics]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def vocabulary_topic_keyboard() -> InlineKeyboardMarkup:
    topics = [
        ("🏠 Дом и быт", "vocab_topic:home"),
        ("🍕 Еда", "vocab_topic:food"),
        ("✈️ Путешествия", "vocab_topic:travel"),
        ("💼 Работа", "vocab_topic:work"),
        ("💻 Технологии", "vocab_topic:technology"),
        ("😀 Эмоции", "vocab_topic:emotions"),
        ("🏥 Здоровье", "vocab_topic:health"),
        ("🎓 Образование", "vocab_topic:education"),
    ]
    buttons = [[InlineKeyboardButton(text=name, callback_data=data)] for name, data in topics]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirm_keyboard(yes_data: str = "confirm:yes", no_data: str = "confirm:no") -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="✅ Да", callback_data=yes_data),
            InlineKeyboardButton(text="❌ Нет", callback_data=no_data),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def assessment_start_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="🎯 Пройти тест уровня", callback_data="assessment:start")],
        [InlineKeyboardButton(text="⏭ Пропустить (A0)", callback_data="assessment:skip")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 В меню", callback_data="back_to_menu")]]
    )


def settings_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="🔔 Напоминания вкл/выкл", callback_data="settings:reminder")],
        [InlineKeyboardButton(text="🎯 Изменить цель", callback_data="settings:goal")],
        [InlineKeyboardButton(text="⏱ Время занятий", callback_data="settings:minutes")],
        [InlineKeyboardButton(text="📋 Пройти тест заново", callback_data="settings:retest")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
