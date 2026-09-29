import json
import unittest
from unittest.mock import patch

import ai
from models import LearningPlan


class AIHelpersTest(unittest.TestCase):
    def test_strip_json_fences(self):
        content = '```json\n{"weeks": []}\n```'

        self.assertEqual(ai._strip_json_fences(content), '{"weeks": []}')

    @patch("ai.GROQ_API_KEY", None)
    def test_missing_api_key_is_reported_when_generating(self):
        with self.assertRaisesRegex(RuntimeError, "GROQ_API_KEY"):
            ai.generate_ai_plan("Python", "Начинающий", 4, 5)

    def test_stripped_content_is_valid_json(self):
        content = ai._strip_json_fences("```json\n{\"weeks\": []}\n```")

        self.assertEqual(json.loads(content), {"weeks": []})

    def test_ai_plan_response_is_validated_into_domain_model(self):
        with patch("ai.GROQ_API_KEY", "test-key"), patch(
            "ai.Groq"
        ) as groq_class:
            groq_class.return_value.chat.completions.create.return_value.choices[
                0
            ].message.content = (
                '{"weeks": [{"week": 1, "topic": "Основы", '
                '"hours": 5, "tasks": ["a", "b", "c"]}]}'
            )

            plan = ai.generate_ai_plan("Python", "Начинающий", 1, 5)

        self.assertIsInstance(plan, LearningPlan)
        self.assertEqual(plan.weeks[0].topic, "Основы")


if __name__ == "__main__":
    unittest.main()
