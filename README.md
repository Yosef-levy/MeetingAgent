# MeetingAgent

MeetingAgent is an end-to-end tool that:
- Transcribes meeting audio using OpenAI Whisper
- Analyzes discussions using OpenAI GPT models
- Generates structured JSON summaries
- Produces a clean human‑readable report
- Optionally sends results via Email or Telegram

This repository includes:
- Full meeting analysis pipeline (`meeting_agent.py`)
- Unit tests and E2E tests
- A custom cross‑platform **FFmpeg installer** created specifically for this project
- Output rendering + delivery modules

---

## 1. Project Structure

```
MeetingAgent/
│
├── meeting_agent.py              # Main application (CLI)
├── setup/
│   └── install_ffmpeg.py         # Custom FFmpeg installer (Windows/macOS/Linux)
│
├── tests/
│   ├── unittests.py              # Whisper, transcription, and model validation tests
│   ├── test_models.py            # Pydantic models & validators unit tests
│   └── e2e_test.py               # Full pipeline audio → transcript → LLM → report
│
├── requirements.txt              # Python dependencies
└── README.md                     # This documentation
```

---

## 2. Requirements

### Python Version
Python **3.10–3.13** is supported.

### Install Dependencies
```
pip install -r requirements.txt
```

### Required External Tools
- **FFmpeg** (mandatory for audio processing)
- **OpenAI API key** (for GPT-based analysis)
- Optional: SMTP credentials (for email delivery)
- Optional: Telegram bot token (for Telegram delivery)

---

## 3. FFmpeg Installation

This project includes a custom, cross‑platform installer:

```
python setup/install_ffmpeg.py
```

It supports:
- Windows (winget / choco / scoop)
- macOS (Homebrew)
- Linux (apt / dnf / yum / pacman / zypper)

The installer:
- Detects available package managers
- Installs FFmpeg
- Validates installation (not in Windows)

Restart your terminal or IDE if FFmpeg is still not detected.

---

## 4. Environment Configuration

Create a `.env` file in the repository root:

```
OPENAI_API_KEY=your_key_here

# Optional SMTP
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=example@gmail.com
SMTP_PASSWORD=xxxxxx

# Optional Telegram
TELEGRAM_BOT_TOKEN=123456789:ABCDEF...
TELEGRAM_CHAT_ID=987654321
```

---

## 5. Running the Application

### Transcribe + Analyze (audio input)
```
python meeting_agent.py --audio meeting.m4a --lang en --txt-out report.txt
```

### Analyze from an existing transcript
```
python meeting_agent.py --transcript notes.txt
```

### Output Options
```
--json-out output.json
--txt-out  report.txt
--email someone@example.com
--telegram
```

---

## 6. Running Tests

### Unit tests
```
pytest tests/unittests.py
pytest tests/test_models.py
```

### End‑to‑end test
```
pytest tests/e2e_test.py
```

This test:
- Loads audio
- Runs Whisper + GPT
- Produces JSON + text reports
- Validates structure and semantics

---

## 7. Script Features (`meeting_agent.py`)

- Whisper transcription (tiny/base/small/medium/large)
- Automatic audio conversion via FFmpeg
- GPT‑4.1 meeting summarization pipeline
- Pydantic models with validators
- Tenacity retry logic for model calls
- Rich-based CLI output
- Email + Telegram export options

---

## 8. Notes

- On Windows, IDEs cache PATH; restart if FFmpeg errors appear.
- Action items support multiple formats, including raw strings.
- Running the E2E test may take **1–2 minutes** on CPU Whisper.

---

## 9. Repository
GitHub:
https://github.com/Yosef-levy/MeetingAgent
