import unittest

import meeting_agent
from meeting_agent import MeetingAnalysis, ActionItem


class TestMeetingAnalysisModel(unittest.TestCase):
    def test_summary_list_is_coerced_to_string(self):
        """LLM sometimes returns summary as a list[str]; model should coerce to str."""
        data = {
            "language": "English",
            "summary": [
                "Design finalization is on track.",
                "Launch is confirmed for June 10th."
            ],
            "decisions": [],
            "action_items": [],
            "risks_or_open_points": [],
            "key_quotes": [],
        }

        model = MeetingAnalysis(**data)

        # Should be a plain string now, not a list
        self.assertIsInstance(model.summary, str)
        self.assertIn("Design finalization is on track.", model.summary)
        self.assertIn("Launch is confirmed for June 10th.", model.summary)

    def test_action_items_accept_list_of_dicts(self):
        """LLM returns action_items as list of dicts; model should parse into ActionItem objects."""
        data = {
            "language": "English",
            "summary": "Short summary.",
            "decisions": [],
            "action_items": [
                {
                    "owner": "Alice",
                    "task": "Send final mockups",
                    "due": "2024-06-06",
                },
                {
                    "owner": "Sarah",
                    "task": "Deliver QA fixes",
                    "due": "2024-06-06",
                },
                {
                    "owner": "John",
                    "task": "Schedule final review meeting",
                    "due": "2024-06-07",
                },
                {
                    "owner": None,
                    "task": "Get DevOps deployment confirmation",
                    "due": None,
                },
            ],
            "risks_or_open_points": [],
            "key_quotes": [],
        }

        model = MeetingAnalysis(**data)

        # action_items should be a list of ActionItem objects
        self.assertIsInstance(model.action_items, list)
        self.assertGreaterEqual(len(model.action_items), 4)
        for item in model.action_items:
            self.assertIsInstance(item, ActionItem)
            self.assertIsInstance(item.task, str)
            self.assertTrue(item.task)  # non-empty task

        # Spot-check one of the items
        first = model.action_items[0]
        self.assertEqual(first.owner, "Alice")
        self.assertIn("mockups", first.task)

    def test_action_items_also_accept_list_of_strings(self):
        """
        Backwards-compat: if the LLM returns simple strings for action_items,
        the model should still accept them if your schema/prompt allows that.
        This test will fail if MeetingAnalysis is strictly List[ActionItem]
        with no 'before' coercion.
        """
        data = {
            "language": "English",
            "summary": "Summary.",
            "decisions": [],
            "action_items": [
                "Alice: Send final mockups (due 2024-06-06)",
                "Sarah: Deliver QA fixes (due 2024-06-06)",
            ],
            "risks_or_open_points": [],
            "key_quotes": [],
        }

        # If you decide you want to allow this,
        # you can either:
        # - change type to Union[List[str], List[ActionItem]], or
        # - add a field_validator("action_items", mode="before") to coerce.
        #
        # For now, we assert it works, so if you later break it, this test will catch it.
        model = MeetingAnalysis(**data)
        self.assertEqual(len(model.action_items), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
