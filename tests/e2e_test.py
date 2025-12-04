import os
import json
import subprocess
import unittest
from pathlib import Path
from gtts import gTTS


class TestMeetingAgentE2E(unittest.TestCase):
    """End-to-end test: generate meeting audio, run meeting_agent.py, validate output."""

    @classmethod
    def setUpClass(cls):
        # Create synthetic meeting audio
        cls.audio_path = Path("meeting_sample.m4a")
        meeting_str = """
        Good morning everyone. Let's begin with the status update for the product launch.
        We agreed last week that the design should be finalized by Friday. Alice, how is that going?
        ...
        We're on track. The visual assets are almost done, and I'll send the final mockups by tomorrow.
        ...
        Great. Regarding marketing, I've started drafting the announcement post and coordinating with the social media team.
        ...
        I have a note about QA. We found two bugs in the new build, one critical and one minor. The fix should be ready by Thursday.
        ...
        Perfect. Let's make sure QA gets another round after that. The launch date is still June 10th, right?
        ...
        Yes, that's correct.
        ...
        We should schedule a final review meeting on June 7th.
        ...
        Good idea. I'll send a calendar invite after this call.
        Any blockers we should discuss?
        ...
        None from design.
        ...
        Just waiting for one confirmation from DevOps about the deployment window.
        ...
        Okay, please follow up today. If there are no other issues, let's wrap up.
        Summary of actions:
        - Alice will send final mockups by tomorrow.
        - Sarah will deliver QA fixes by Thursday.
        - John will schedule the final review meeting for June 7th.
        Launch remains on June 10th.
        Thanks everyone. Have a great day!
        """

        # Output paths
        cls.json_out = Path("meeting_result.json")
        cls.txt_out = Path("meeting_result.txt")

    def test_meeting_agent_end_to_end(self):
        """Run meeting_agent.py on the generated audio and validate JSON output."""
        # Run the agent
        cmd = [
            "python",
            "../meeting_agent.py",
            "--audio",
            str(self.audio_path),
            "--lang",
            "English",
            "--json-out",
            str(self.json_out),
            "--txt-out",
            str(self.txt_out),
        ]
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",  # or "ignore" if you prefer
        )
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        self.assertEqual(result.returncode, 0, "meeting_agent.py exited with error")

        # Check output files exist
        self.assertTrue(self.json_out.exists(), "JSON output file missing")
        self.assertTrue(self.txt_out.exists(), "Text output file missing")

        # Load and validate JSON structure
        with open(self.json_out, "r", encoding="utf-8") as f:
            data = json.load(f)

        required_keys = [
            "language",
            "summary",
            "decisions",
            "action_items",
            "risks_or_open_points",
            "key_quotes",
        ]
        for key in required_keys:
            self.assertIn(key, data, f"Missing key in output: {key}")

        # Basic semantic checks
        self.assertIn("Launch", data["summary"], "Summary seems unrelated to meeting")
        self.assertTrue(len(data["action_items"]) >= 2, "Expected multiple action items")

    @classmethod
    def tearDownClass(cls):
        """Clean up test artifacts."""
        for f in [cls.json_out, cls.txt_out]:
            if Path(f).exists():
                os.remove(f)
                print(f"Removed {f}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
