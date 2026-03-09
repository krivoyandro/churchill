from aiogram.fsm.state import State, StatesGroup


class OnboardingStates(StatesGroup):
    choosing_goal = State()
    choosing_minutes = State()
    assessment_in_progress = State()
    showing_result = State()


class LessonStates(StatesGroup):
    in_lesson = State()
    waiting_answer = State()


class ConversationStates(StatesGroup):
    chatting = State()


class VocabularyStates(StatesGroup):
    reviewing = State()
    learning_new = State()


class DrillStates(StatesGroup):
    drilling = State()
    follow_up = State()
