import unittest
import unittest.mock
import tempfile
from pathlib import Path

from core.models import LearningDiagnostic, LearningPlan, PlanRequest, PlanWeek
from storage import database
from services.materials import (
    build_learning_material_prompt,
    generate_learning_material,
    recommend_materials,
)
from services.planner import generate_plan


class PlannerTest(unittest.TestCase):
    def test_diagnostic_validates_preferences(self):
        diagnostic = LearningDiagnostic(
            interests="Практика",
            preferred_format="Проектная работа",
            available_days=("Суббота",),
        )

        self.assertEqual(diagnostic.available_days, ("Суббота",))
        with self.assertRaisesRegex(ValueError, "формат занятий"):
            LearningDiagnostic(preferred_format="Неизвестный")

    def test_generates_requested_number_of_weeks(self):
        plan = generate_plan("Python", "Начинающий", 4, 5)

        self.assertEqual(len(plan), 4)
        self.assertEqual([week.week for week in plan], [1, 2, 3, 4])
        self.assertTrue(all(isinstance(week, PlanWeek) for week in plan))
        self.assertTrue(all(week.hours == 5 for week in plan))
        self.assertTrue(all(3 <= len(week.tasks) <= 5 for week in plan))

    def test_request_validation_messages_are_in_russian(self):
        with self.assertRaisesRegex(ValueError, "Цель обучения не может быть пустой"):
            PlanRequest("", "Начинающий", 4, 5)

        with self.assertRaisesRegex(
            ValueError, "Название цели не может состоять только из цифр"
        ):
            PlanRequest("12345", "Начинающий", 4, 5)

        with self.assertRaisesRegex(
            ValueError, "Количество недель должно быть целым числом"
        ):
            PlanRequest("Python", "Начинающий", "4", 5)

    def test_week_validation_messages_are_in_russian(self):
        with self.assertRaisesRegex(
            ValueError, "Неделя должна содержать от 3 до 5 задач"
        ):
            PlanWeek(1, "Основы", 5, ("только одна задача",))

    def test_material_url_validation(self):
        with self.assertRaisesRegex(ValueError, "http"):
            database.save_material(
                999999, "Документация", "not-a-url", "Документация"
            )

    def test_material_recommendations_filter_invalid_and_duplicate_urls(self):
        response = (
            '[{"title":"Документация Python","url":"https://python.ru/docs","material_type":"Документация"},'
            '{"title":"Bad","url":"javascript:bad","material_type":"Статья"},'
            '{"title":"Duplicate Python","url":"https://python.ru/docs","material_type":"Статья"}]'
        )
        with unittest.mock.patch(
            "services.materials._request_plan",
            return_value=response,
        ), unittest.mock.patch(
            "services.materials.check_material_url",
            return_value=(True, "ok"),
        ), unittest.mock.patch(
            "services.materials.check_material_relevance",
            return_value=(True, "ok"),
        ):
            recommendations = recommend_materials(
                "Python", "Начинающий", "Python основы"
            )

        self.assertEqual(len(recommendations), 1)
        self.assertEqual(recommendations[0]["title"], "Документация Python")

    def test_material_recommendations_reject_unrelated_page_content(self):
        response = (
            '[{"title":"Курс по Python","url":"https://python.ru/sql",'
            '"material_type":"Курс","tags":"Python"}]'
        )
        with unittest.mock.patch(
            "services.materials._request_plan",
            return_value=response,
        ), unittest.mock.patch(
            "services.materials.check_material_url",
            return_value=(True, "ok"),
        ), unittest.mock.patch(
            "services.materials.check_material_relevance",
            return_value=(
                False,
                "Тема блока не подтверждена содержимым страницы.",
            ),
        ):
            recommendations = recommend_materials(
                "Python", "Начинающий", "Основы SQL"
            )

        self.assertEqual(recommendations, [])

    def test_learning_material_contains_theory_and_quiz_without_resources(self):
        response = (
            '{"theory":"Основы темы","quiz":['
            '{"question":"Что изучаем?","options":["Тему","Ничего"],'
            '"correct":0,"explanation":"Это тема блока."},'
            '{"question":"Как практиковаться?","options":["Решать задачи","Не пробовать"],'
            '"correct":0,"explanation":"Практика закрепляет знания."},'
            '{"question":"Что сделать после?","options":["Проверить результат","Игнорировать"],'
            '"correct":0,"explanation":"Проверка помогает найти ошибки."}'
            '],"resources":[]}'
        )
        with unittest.mock.patch(
            "services.materials._request_plan",
            return_value=response,
        ):
            material = generate_learning_material(
                "Python", "Начинающий", "Основы Python"
            )

        self.assertEqual(material["theory"], "Основы темы")
        self.assertEqual(len(material["quiz"]), 3)
        self.assertEqual(material["resources"], [])

    def test_learning_material_falls_back_to_local_content(self):
        with unittest.mock.patch(
            "services.materials._request_plan",
            return_value='{"theory":"","quiz":[]}',
        ):
            material = generate_learning_material(
                "Python", "Начинающий", "Основы Python"
            )

        self.assertTrue(material["theory"])
        self.assertEqual(len(material["quiz"]), 3)

    def test_learning_material_prompt_uses_tasks_and_preferred_format(self):
        prompt = build_learning_material_prompt(
            "Python",
            "Начинающий",
            "Циклы",
            5,
            tasks=("Решить задачи", "Сделать мини-проект"),
            preferred_format="Практика",
        )

        self.assertIn("Решить задачи", prompt)
        self.assertIn("Сделать мини-проект", prompt)
        self.assertIn("Предпочтительный формат занятий: Практика", prompt)
        self.assertIn("5 часов", prompt)

    def test_overall_progress_includes_completed_materials(self):
        original_path = database.DATABASE_PATH
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                database.DATABASE_PATH = Path(temp_dir) / "progress.db"
                database.init_database()
                plan_id = database.save_plan(
                    "Python",
                    "Начинающий",
                    1,
                    5,
                    LearningPlan(
                        (
                            PlanWeek(
                                1,
                                "Python основы",
                                5,
                                ("Изучить синтаксис", "Решить задачи", "Сделать проект"),
                            ),
                        ),
                    ),
                )
                material_id = database.save_material(
                    plan_id,
                    "Курс Python",
                    "https://python.ru/python",
                    "Курс",
                    week=1,
                )

                self.assertEqual(database.get_plan_progress(plan_id), 0)
                task_id = database.get_plan_tasks(plan_id)[0].id
                database.update_task_status(task_id, True)
                database.update_material_status(material_id, completed=True)
                self.assertEqual(database.get_plan_progress(plan_id), 1 / 3)
        finally:
            database.DATABASE_PATH = original_path

    def test_learning_block_progress_and_quiz_result_are_persisted(self):
        original_path = database.DATABASE_PATH
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                database.DATABASE_PATH = Path(temp_dir) / "block_progress.db"
                database.init_database()
                plan_id = database.save_plan(
                    "Python",
                    "Начинающий",
                    1,
                    5,
                    LearningPlan(
                        (
                            PlanWeek(
                                1,
                                "Python основы",
                                5,
                                ("Изучить синтаксис", "Решить задачи", "Сделать проект"),
                            ),
                        )
                    ),
                )
                database.save_learning_block(
                    plan_id=plan_id,
                    week=1,
                    topic="Python основы",
                    theory="Короткая теория",
                    quiz=[
                        {
                            "question": "Q1",
                            "options": ["A", "B"],
                            "correct": 0,
                            "explanation": "E1",
                        },
                        {
                            "question": "Q2",
                            "options": ["A", "B"],
                            "correct": 0,
                            "explanation": "E2",
                        },
                        {
                            "question": "Q3",
                            "options": ["A", "B"],
                            "correct": 0,
                            "explanation": "E3",
                        },
                    ],
                    resources=[],
                    task_guides=[],
                )
                self.assertEqual(
                    database.get_plan_preferred_format(plan_id),
                    "Смешанный формат",
                )

                self.assertEqual(database.get_plan_progress(plan_id), 0)
                database.mark_learning_block_theory_completed(plan_id, 1)
                database.save_learning_block_quiz_result(plan_id, 1, score=2, total_questions=3)
                block = database.get_learning_block(plan_id, 1)
                self.assertIsNotNone(block)
                self.assertEqual(block.quiz_last_score, 2)
                self.assertEqual(block.quiz_total_questions, 3)
                self.assertEqual(block.quiz_attempts, 1)
                self.assertFalse(block.quiz_passed)
                attempts = database.get_learning_block_quiz_attempts(plan_id, 1)
                self.assertEqual(len(attempts), 1)
                self.assertFalse(attempts[0]["passed"])
                self.assertEqual(database.get_plan_progress(plan_id), 1 / 5)
                database.save_learning_block_quiz_result(
                    plan_id,
                    1,
                    score=3,
                    total_questions=3,
                )
                self.assertTrue(database.get_learning_block(plan_id, 1).quiz_passed)
                self.assertEqual(database.get_plan_progress(plan_id), 2 / 5)
        finally:
            database.DATABASE_PATH = original_path

    def test_stage_seven_preferences_and_study_time_are_persisted(self):
        original_path = database.DATABASE_PATH
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                database.DATABASE_PATH = Path(temp_dir) / "stage_seven.db"
                database.init_database()
                user = database.register_user("stage7@example.com", "password123")
                plan_id = database.save_plan(
                    "Python",
                    "Начинающий",
                    1,
                    5,
                    LearningPlan(
                        (
                            PlanWeek(
                                1,
                                "Python основы",
                                5,
                                ("Изучить синтаксис", "Решить задачи", "Сделать проект"),
                            ),
                        )
                    ),
                    user_id=user.id,
                )

                database.update_study_preferences(
                    user.id,
                    ("Пн", "Ср"),
                    "20:30",
                    "Europe/Moscow",
                    True,
                    "Только в дни занятий",
                )
                preferences = database.get_study_preferences(user.id)
                self.assertEqual(preferences.study_days, ("Пн", "Ср"))
                self.assertEqual(preferences.study_time, "20:30")
                self.assertEqual(preferences.reminder_frequency, "Только в дни занятий")

                database.log_study_session(user.id, plan_id, 45, "Синтаксис")
                database.log_study_session(user.id, plan_id, 15)
                stats = database.get_study_stats(plan_id, user.id)
                self.assertEqual(stats.study_minutes, 60)
                self.assertEqual(stats.total_tasks, 3)
                with self.assertRaises(ValueError):
                    database.log_study_session(user.id, plan_id, 0)
        finally:
            database.DATABASE_PATH = original_path


if __name__ == "__main__":
    unittest.main()
