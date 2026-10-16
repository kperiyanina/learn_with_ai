import json
import unittest
from unittest.mock import patch

from core.models import LearningPlan
from services import ai


class AIHelpersTest(unittest.TestCase):
    def test_strip_json_fences(self):
        content = '```json\n{"weeks": []}\n```'

        self.assertEqual(ai._strip_json_fences(content), '{"weeks": []}')

    @patch("services.ai.GROQ_API_KEY", None)
    def test_missing_api_key_uses_local_fallback(self):
        plan = ai.generate_ai_plan("Python", "Начинающий", 4, 5)

        self.assertIsInstance(plan, LearningPlan)
        self.assertEqual(len(plan.weeks), 4)

    @patch("services.ai.GROQ_API_KEY", "test-key")
    def test_request_range_is_validated_before_ai_call(self):
        with self.assertRaisesRegex(
            ValueError, "Количество часов должно быть от 1 до 40"
        ):
            ai.generate_ai_plan("Python", "Начинающий", 4, 41)

    def test_stripped_content_is_valid_json(self):
        content = ai._strip_json_fences("```json\n{\"weeks\": []}\n```")

        self.assertEqual(json.loads(content), {"weeks": []})

    def test_ai_plan_response_is_validated_into_domain_model(self):
        with patch("services.ai.GROQ_API_KEY", "test-key"), patch(
            "services.ai.Groq"
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

    @patch("services.ai.GROQ_API_KEY", "test-key")
    def test_provider_failure_uses_local_fallback(self):
        with patch("services.ai.Groq") as groq_class:
            groq_class.return_value.chat.completions.create.side_effect = (
                TimeoutError("timeout")
            )

            plan = ai.generate_ai_plan("Python", "Начинающий", 1, 5)

        self.assertIsInstance(plan, LearningPlan)
        self.assertEqual(len(plan.weeks), 1)

    @patch("services.ai.GROQ_API_KEY", "test-key")
    def test_provider_is_retried_before_success(self):
        with patch("services.ai.Groq") as groq_class:
            create = groq_class.return_value.chat.completions.create
            create.side_effect = [
                TimeoutError("temporary"),
                type(
                    "Response",
                    (),
                    {
                        "choices": [
                            type(
                                "Choice",
                                (),
                                {
                                    "message": type(
                                        "Message",
                                        (),
                                        {
                                            "content": (
                                                '{"weeks": [{"week": 1, '
                                                '"topic": "Основы", "hours": 5, '
                                                '"tasks": ["a", "b", "c"]}]}'
                                            )
                                        },
                                    )()
                                },
                            )()
                        ]
                    },
                )(),
            ]

            plan = ai.generate_ai_plan("Python", "Начинающий", 1, 5)

        self.assertEqual(create.call_count, 2)
        self.assertEqual(plan.weeks[0].topic, "Основы")


if __name__ == "__main__":
    unittest.main()
