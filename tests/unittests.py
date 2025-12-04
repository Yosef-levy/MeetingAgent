import io
import json
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure the project root is on sys.path so `import meeting_agent` works
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import meeting_agent  # noqa: E402


class TestEnsureWav(unittest.TestCase):
    @patch("meeting_agent.ffmpeg")
    def test_ensure_wav_converts_non_wav(self, mock_ffmpeg):
        # Arrange
        input_path = "meeting_sample.m4a"
        # Build the chained call ffmpeg.input(...).output(...).overwrite_output().run(...)
        mock_stream = MagicMock()
        mock_ffmpeg.input.return_value = mock_stream
        mock_stream.output.return_value = mock_stream
        mock_stream.overwrite_output.return_value = mock_stream

        # Act
        out_path = meeting_agent.ensure_wav(input_path)

        # Assert
        self.assertTrue(out_path.endswith(".wav"))
        mock_ffmpeg.input.assert_called_once_with(input_path)
        mock_stream.output.assert_called_once()
        mock_stream.overwrite_output.assert_called_once()
        mock_stream.run.assert_called_once_with(quiet=True)

    def test_ensure_wav_returns_original_when_wav(self):
        wav = "already.wav"
        self.assertEqual(meeting_agent.ensure_wav(wav), wav)


class TestBuildPrompt(unittest.TestCase):
    def test_build_prompt_contains_transcript_and_schema_en(self):
        transcript = "This is a test transcript."
        prompt = meeting_agent.build_prompt(transcript, language="en")
        self.assertIn("Schema:", prompt)
        self.assertIn(transcript, prompt)
        self.assertIn("You will receive a meeting transcript", prompt)


class TestOpenAICompleteAndAnalyze(unittest.TestCase):
    @patch("meeting_agent.openai")
    def test_openai_complete_returns_text(self, mock_openai):
        # Simulate SDK response shape
        mock_resp = types.SimpleNamespace(
            choices=[
                types.SimpleNamespace(
                    message=types.SimpleNamespace(content='{"ok": true}')
                )
            ]
        )
        mock_openai.chat.completions.create.return_value = mock_resp
        out = meeting_agent.openai_complete("hello", model="gpt-4.1")
        self.assertEqual(out, '{"ok": true}')
        mock_openai.chat.completions.create.assert_called_once()

    @patch("meeting_agent.openai_complete")
    def test_analyze_meeting_parses_json(self, mock_complete):
        json_payload = {
            "language": "English",
            "summary": "A short summary.",
            "decisions": ["Decision A"],
            "action_items": [{"owner": "Alice", "task": "Do X", "due": "2025-01-01"}],
            "risks_or_open_points": ["Risk 1"],
            "key_quotes": ["Quote 1"],
        }
        mock_complete.return_value = json.dumps(json_payload)
        report = meeting_agent.analyze_meeting("transcript", language="en", model="gpt-4.1")
        self.assertEqual(report.summary, "A short summary.")
        self.assertEqual(report.action_items[0].owner, "Alice")


class TestRenderAndDelivery(unittest.TestCase):
    def test_render_text_en(self):
        data = meeting_agent.MeetingAnalysis(
            language="English",
            summary="Bulleted summary.",
            decisions=["Decide X"],
            action_items=[meeting_agent.ActionItem(owner="John", task="Send doc", due="2025-02-02")],
            risks_or_open_points=["Missing approval"],
            key_quotes=["We will deliver."]
        )
        txt = meeting_agent.render_text(data)
        self.assertIn("Meeting Summary", txt)
        self.assertIn("Decisions", txt)
        self.assertIn("Action Items", txt)
        self.assertIn("Risks/Open Points", txt)
        self.assertIn("John: Send doc (due 2025-02-02)", txt)


    @patch("meeting_agent.smtplib.SMTP")
    def test_send_email_smtp(self, mock_smtp):
        with patch.dict(os.environ, {
            "SMTP_HOST": "smtp.gmail.com",
            "SMTP_PORT": "587",
            "SMTP_USERNAME": "you@example.com",
            "SMTP_PASSWORD": "app-password"
        }, clear=False):
            meeting_agent.send_email_smtp("Subject", "Body", "to@example.com")
            mock_smtp.assert_called_once_with("smtp.gmail.com", 587)
            instance = mock_smtp.return_value.__enter__.return_value
            instance.starttls.assert_called_once()
            instance.login.assert_called_once_with("you@example.com", "app-password")
            instance.sendmail.assert_called_once()

    @patch("meeting_agent.requests.post")
    def test_send_telegram(self, mock_post):
        with patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": "123:ABC",
            "TELEGRAM_CHAT_ID": "999"
        }, clear=False):
            meeting_agent.send_telegram("Hello")
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            self.assertIn("https://api.telegram.org/bot123:ABC/sendMessage", args[0])
            self.assertEqual(kwargs["json"]["chat_id"], "999")
            self.assertEqual(kwargs["json"]["text"], "Hello")


class TestTranscribe(unittest.TestCase):
    """
    Integration-style test for meeting_agent.transcribe() using a real audio file.

    Requires:
    - tests/meeting_sample.m4a to exist
    - ffmpeg installed on the system
    - whisper + ffmpeg-python installed in the environment
    """

    AUDIO_PATH = Path(__file__).resolve().parent / "meeting_sample.m4a"

    @unittest.skipUnless(AUDIO_PATH.exists(), "meeting_sample.m4a not found in tests folder")
    def test_transcribe_meeting_sample(self):
        # Act
        result = meeting_agent.transcribe(str(self.AUDIO_PATH), model_size="small")

        # Basic structure checks
        self.assertIsInstance(result, dict)
        self.assertIn("text", result, "Result should contain 'text' key")
        self.assertIn("language", result, "Result should contain 'language' key")

        text = result["text"]
        lang = result["language"]

        # Basic content checks
        self.assertIsInstance(text, str)
        self.assertGreater(len(text.strip()), 0, "Transcript should not be empty")

        # Language check (Whisper usually returns 'en' for English)
        self.assertIsInstance(lang, str)
        self.assertTrue(
            lang.lower().startswith("en"),
            f"Expected English transcription, got language='{lang}'"
        )

        # Very loose semantic check – avoid being brittle
        # We just check that at least one expected keyword from the meeting appears.
        lowered = text.lower()
        keywords = ["good morning", "launch", "mockups", "qa"]
        self.assertTrue(
            any(k in lowered for k in keywords),
            f"Transcript does not contain any expected keywords: {keywords}"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
