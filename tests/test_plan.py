import unittest

from core.models import PlanRequest, PlanWeek
from services.planner import generate_plan


class PlannerTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
