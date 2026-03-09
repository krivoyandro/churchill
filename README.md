# 🇬🇧 Churchill — AI English Tutor Bot

Telegram-бот — AI-репетитор по английскому языку. Определяет уровень, строит персональную программу, объясняет темы, даёт упражнения, проверяет ошибки, тренирует слова и грамматику, ведёт от A0 до C1.

## Возможности (MVP)

- 🎯 **Определение уровня** — CEFR-тест (A0–C1)
- 📋 **Персональный план** — программа по неделям под цель и темп
- 📚 **Уроки** — грамматика, лексика, упражнения с проверкой AI
- 🔤 **Словарь** — spaced repetition (SM-2), темы, повторение
- 💬 **Практика диалога** — свободное общение с AI на английском
- ❌ **Учёт ошибок** — запоминание и проработка слабых мест
- 📊 **Прогресс** — статистика, серия дней, аналитика
- ⏰ **Напоминания** — ежедневные push-уведомления

## Стек

- **Python 3.12+**
- **aiogram 3** — Telegram Bot API
- **OpenAI API** (GPT-4o-mini) — AI-преподаватель
- **PostgreSQL** — хранение данных
- **Redis** — кеш
- **APScheduler** — напоминания
- **SQLAlchemy 2** + **Alembic** — ORM и миграции
- **Docker Compose** — деплой

## Структура

```
churchill/
├── main.py                  # Точка входа
├── config.py                # Настройки
├── bot/
│   ├── handlers/
│   │   ├── start.py         # /start, онбординг
│   │   ├── assessment.py    # Тест уровня
│   │   ├── lessons.py       # Уроки
│   │   ├── vocabulary.py    # Словарь и повторение
│   │   ├── conversation.py  # Практика диалога
│   │   └── menu.py          # Меню, прогресс, ошибки
│   ├── keyboards/
│   │   └── inline.py        # Клавиатуры
│   ├── middlewares/
│   │   └── db.py            # DB-сессия middleware
│   └── states/
│       └── states.py        # FSM-состояния
├── services/
│   ├── ai/
│   │   ├── engine.py        # OpenAI интеграция
│   │   └── prompts.py       # Системные промпты
│   └── progress/
│       └── spaced_repetition.py  # SM-2 алгоритм
├── db/
│   ├── base.py              # DeclarativeBase
│   ├── models.py            # SQLAlchemy модели
│   ├── repo.py              # Репозиторий (CRUD)
│   └── session.py           # Async-сессия
├── scheduler/
│   └── reminders.py         # Ежедневные напоминания
├── alembic/                 # Миграции
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## Быстрый старт

### 1. Клонировать

```bash
git clone git@github.com:krivoyandro/churchill.git
cd churchill
```

### 2. Настроить

```bash
cp .env.example .env
# Заполнить TELEGRAM_BOT_TOKEN и OPENAI_API_KEY
```

### 3. Запустить (Docker)

```bash
docker compose up -d
```

### 4. Запустить (локально)

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Нужен PostgreSQL
python main.py
```

## Таблицы БД

| Таблица | Описание |
|---------|----------|
| `users` | Пользователи, уровень, цель, подписка, стрик |
| `learning_goals` | Цели обучения |
| `level_assessments` | Результаты тестирования |
| `lessons` | Шаблоны уроков |
| `user_lessons` | Пройденные уроки |
| `vocabulary_words` | Словарь |
| `user_vocabulary` | Изученные слова + spaced repetition |
| `grammar_topics` | Грамматические темы |
| `mistakes` | Ошибки пользователя |
| `daily_tasks` | Ежедневные задания |

## Цели обучения

- 🆕 С нуля
- 💬 Разговорный
- 💼 Для работы
- 📝 Для экзамена
- ✈️ Для путешествий
- 💻 Для IT
- 🏥 Для медицины
- 📊 Для бизнеса

## Roadmap

### MVP 2
- [ ] Режим диалога по ролям
- [ ] Темы по профессиям (IT, медицина)
- [ ] Платная подписка (Telegram Payments)
- [ ] Детальная аналитика ошибок

### MVP 3
- [ ] Голосовые сообщения (Whisper)
- [ ] Speaking-анализ
- [ ] Мини-экзамены и сертификаты
- [ ] Реферальная система
- [ ] Leaderboard

## Лицензия

MIT
