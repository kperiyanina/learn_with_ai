from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PlanRequest:
    goal: str
    level: str
    weeks: int
    hours_per_week: int

    def __post_init__(self):
        if not isinstance(self.goal, str) or not self.goal.strip():
            raise ValueError("Цель обучения не может быть пустой.")
        if self.goal.strip().isdigit():
            raise ValueError(
                "Название цели не может состоять только из цифр."
            )
        if not isinstance(self.level, str) or not self.level.strip():
            raise ValueError("Уровень обучения не может быть пустым.")
        if not isinstance(self.weeks, int) or isinstance(self.weeks, bool):
            raise ValueError("Количество недель должно быть целым числом.")
        if not 1 <= self.weeks <= 12:
            raise ValueError("Количество недель должно быть от 1 до 12.")
        if not isinstance(self.hours_per_week, int) or isinstance(
            self.hours_per_week, bool
        ):
            raise ValueError("Количество часов должно быть целым числом.")
        if not 1 <= self.hours_per_week <= 40:
            raise ValueError("Количество часов должно быть от 1 до 40.")


@dataclass(frozen=True)
class LearningDiagnostic:
    interests: str = ""
    preferred_format: str = "Смешанный формат"
    available_days: tuple[str, ...] = ()

    def __post_init__(self):
        if not isinstance(self.interests, str) or len(self.interests) > 500:
            raise ValueError("Интересы должны содержать не более 500 символов.")
        if self.preferred_format not in {
            "Смешанный формат",
            "Теория",
            "Практика",
            "Проектная работа",
        }:
            raise ValueError("Выбран некорректный формат занятий.")
        if not isinstance(self.available_days, tuple) or not all(
            isinstance(day, str) and day.strip() for day in self.available_days
        ):
            raise ValueError("Дни занятий указаны некорректно.")


@dataclass(frozen=True)
class PlanWeek:
    week: int
    topic: str
    hours: int
    tasks: tuple[str, ...]

    def __post_init__(self):
        if not isinstance(self.week, int) or isinstance(self.week, bool):
            raise ValueError("Номер недели должен быть целым числом.")
        if self.week < 1:
            raise ValueError("Номер недели должен быть положительным.")
        if not isinstance(self.topic, str) or not self.topic.strip():
            raise ValueError("Тема недели не может быть пустой.")
        if not isinstance(self.hours, int) or isinstance(self.hours, bool):
            raise ValueError("Количество часов должно быть целым числом.")
        if self.hours < 1:
            raise ValueError("Количество часов должно быть положительным.")
        if not 3 <= len(self.tasks) <= 5:
            raise ValueError("Неделя должна содержать от 3 до 5 задач.")
        if any(not isinstance(task, str) or not task.strip() for task in self.tasks):
            raise ValueError("Задачи не могут быть пустыми.")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlanWeek":
        try:
            tasks = tuple(data["tasks"])
            return cls(
                week=int(data["week"]),
                topic=str(data["topic"]),
                hours=int(data["hours"]),
                tasks=tasks,
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("ИИ вернул некорректные данные недели.") from error


@dataclass(frozen=True)
class LearningPlan:
    weeks: tuple[PlanWeek, ...]

    def __post_init__(self):
        if not self.weeks:
            raise ValueError("Учебный план не может быть пустым.")
        expected_weeks = tuple(range(1, len(self.weeks) + 1))
        actual_weeks = tuple(week.week for week in self.weeks)
        if actual_weeks != expected_weeks:
            raise ValueError("Номера недель должны идти последовательно.")

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        expected_weeks: int,
        expected_hours: int,
    ) -> "LearningPlan":
        if not isinstance(data, dict) or not isinstance(data.get("weeks"), list):
            raise ValueError("ИИ вернул план без списка недель.")

        weeks = tuple(PlanWeek.from_dict(week) for week in data["weeks"])
        plan = cls(weeks=weeks)

        if len(plan.weeks) != expected_weeks:
            raise ValueError("ИИ вернул план с неверным количеством недель.")
        if any(week.hours != expected_hours for week in plan.weeks):
            raise ValueError("ИИ вернул неверное количество часов.")

        return plan


@dataclass(frozen=True)
class PlanRecord:
    id: int
    goal: str
    level: str
    weeks: int
    hours_per_week: int


@dataclass(frozen=True)
class TaskRecord:
    id: int
    week: int
    topic: str
    task: str
    completed: bool


@dataclass(frozen=True)
class MaterialRecord:
    id: int
    plan_id: int
    task_id: int | None
    week: int | None
    title: str
    url: str
    material_type: str
    tags: str
    is_favorite: bool
    completed: bool


@dataclass(frozen=True)
class LearningBlockRecord:
    plan_id: int
    week: int
    topic: str
    theory: str
    quiz: tuple[dict[str, Any], ...]
    resources: tuple[dict[str, str], ...]
    task_guides: tuple[dict[str, str], ...]
    theory_completed: bool
    quiz_completed: bool
    quiz_last_score: int | None
    quiz_total_questions: int | None
    quiz_attempts: int
    quiz_best_score: int | None
    quiz_best_total_questions: int | None
    quiz_passed: bool


@dataclass(frozen=True)
class UserRecord:
    id: int
    email: str


@dataclass(frozen=True)
class ProfileRecord:
    user_id: int
    display_name: str


@dataclass(frozen=True)
class StudyPreferencesRecord:
    user_id: int
    study_days: tuple[str, ...]
    study_time: str
    timezone: str
    reminders_enabled: bool
    reminder_frequency: str


@dataclass(frozen=True)
class StudyStatsRecord:
    plan_id: int
    total_tasks: int
    completed_tasks: int
    total_weeks: int
    completed_theory: int
    passed_quizzes: int
    total_quizzes: int
    completed_materials: int
    total_materials: int
    study_minutes: int
    progress: float
