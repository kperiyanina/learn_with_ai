import unittest

from planner import generate_plan


class PlannerTest(unittest.TestCase):
    def test_generates_requested_number_of_weeks(self):
        plan = generate_plan("Python", "Начинающий", 4, 5)

        self.assertEqual(len(plan), 4)
        self.assertEqual([week["week"] for week in plan], [1, 2, 3, 4])
        self.assertTrue(all(week["hours"] == 5 for week in plan))
        self.assertTrue(all(3 <= len(week["tasks"]) <= 5 for week in plan))


if __name__ == "__main__":
    unittest.main()
