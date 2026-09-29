import json
import unittest
from unittest.mock import patch

import ai


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


if __name__ == "__main__":
    unittest.main()
