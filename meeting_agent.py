#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, json, argparse, tempfile
from typing import List, Optional, Dict, Any

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator
from rich import print
from rich.panel import Panel
from rich.console import Console
from tenacity import retry, wait_exponential, stop_after_attempt

import whisper
import ffmpeg
import openai
import smtplib
from email.mime.text import MIMEText
import requests

# ---------- Configuration ----------

load_dotenv()
console = Console()
openai.api_key = os.getenv("OPENAI_API_KEY")

# ---------- Models ----------

class ActionItem(BaseModel):
    owner: Optional[str] = Field(None, description="Responsible person")
    task: str
    due: Optional[str] = Field(None, description="Due date if mentioned")

class MeetingAnalysis(BaseModel):
    language: str
    summary: str
    decisions: List[str] = Field(default_factory=list)
    action_items: List[ActionItem] = Field(default_factory=list)
    risks_or_open_points: List[str] = Field(default_factory=list)
    key_quotes: List[str] = Field(default_factory=list)

    @field_validator("summary", mode="before")
    @classmethod
    def coerce_summary(cls, v: Any):
        if isinstance(v, list):
            return " ".join(str(part) for part in v)
        return v

    @field_validator("action_items", mode="before")
    @classmethod
    def coerce_action_items(cls, v: Any):
        """
        Allow:
          - list[dict]  -> list[ActionItem] (handled by Pydantic)
          - list[str]   -> convert each string to ActionItem(task=..., owner=None, due=None)
          - None        -> []
        """
        if v is None:
            return []

        if isinstance(v, list):
            if not v:
                return v

            first = v[0]

            # Already list of dicts/ActionItem -> let Pydantic handle it
            if isinstance(first, (dict, ActionItem)):
                return v

            # If list of strings -> convert to ActionItem dicts
            if isinstance(first, str):
                converted = []
                for s in v:
                    converted.append(
                        {
                            "owner": None,
                            "task": s,
                            "due": None,
                        }
                    )
                return converted

        return v

# ---------- Audio Utilities ----------

def ensure_wav(input_path: str) -> str:
    """Convert any audio/video file to wav (16k mono)."""
    if input_path.lower().endswith(".wav"):
        return input_path
    out = tempfile.mktemp(suffix=".wav")
    (
        ffmpeg
        .input(input_path)
        .output(out, ac=1, ar=16000)
        .overwrite_output()
        .run(quiet=True)
    )
    return out

def transcribe(audio_path: str, model_size: str = "small") -> Dict[str, Any]:
    console.log(f"Loading Whisper model: {model_size}")
    model = whisper.load_model(model_size)
    wav_path = ensure_wav(audio_path)
    result = model.transcribe(wav_path, verbose=False)
    return result  # contains 'text', 'segments', 'language'

# ---------- LLM Call ----------

def openai_complete(prompt: str, model: str = "gpt-4.1") -> str:
    response = openai.chat.completions.create(  # type: ignore
        model=model,
        messages=[
            {"role": "system", "content": "You are a precise meeting-minutes assistant. Output must be valid JSON only."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content

# ---------- Prompt Builder ----------

def build_prompt(transcript: str, language: str = "English") -> str:
    schema = {
        "language": f"{language}",
        "summary": "string (3-6 bullets, concise, factual)",
        "decisions": ["string"],
        "action_items": [
            {"owner": "string|null", "task": "string", "due": "YYYY-MM-DD|null"}
        ],
        "risks_or_open_points": ["string"],
        "key_quotes": ["string"]
    }
    instructions = f"""
        You will receive a meeting transcript in {language}. Extract structured minutes.
        
        Rules:
        - Output VALID JSON that matches this schema exactly (no extra keys, no trailing prose).
        - Parse dates you find into YYYY-MM-DD when possible, else null.
        - Keep it concise. Avoid duplication.
        
        Schema:
        {json.dumps(schema, ensure_ascii=False, indent=2)}
        
        Transcript:
        \"\"\"{transcript.strip()}\"\"\"
        """
    return instructions

# ---------- Analyzer ----------

@retry(wait=wait_exponential(min=1, max=16), stop=stop_after_attempt(3))
def analyze_meeting(transcript: str, language: str, model: str = "gpt-4.1") -> MeetingAnalysis:
    prompt = build_prompt(transcript, language)
    raw = openai_complete(prompt, model=model)

    raw_stripped = raw.strip()
    if raw_stripped.startswith("```"):
        raw_stripped = raw_stripped.strip("`")
        raw_stripped = raw_stripped.split("\n", 1)[-1]
    data = json.loads(raw_stripped)
    return MeetingAnalysis(**data)

# ---------- Rendering ----------

def render_text(report: MeetingAnalysis) -> str:
    title = "Meeting Summary"
    decisions_title = "Decisions"
    actions_title = "Action Items"
    risks_title = "Risks/Open Points"
    quotes_title = "Key Quotes"

    lines = [title, ""]
    lines.append(report.summary.strip())
    lines += ["", decisions_title]
    lines += [f"- {d}" for d in report.decisions] or ["- (none)"]
    lines += ["", actions_title]
    if report.action_items:
        for a in report.action_items:
            who = a.owner or "Unassigned"
            due = a.due or "N/A"
            lines.append(f"- {who}: {a.task} (due {due})")
    else:
        lines.append("- (none)")
    lines += ["", risks_title]
    lines += [f"- {r}" for r in report.risks_or_open_points] or ["- (none)"]
    if report.key_quotes:
        lines += ["", quotes_title]
        lines += [f"- “{q}”" for q in report.key_quotes]
    return "\n".join(lines).strip()

# ---------- Delivery ----------

def send_email_smtp(subject: str, body: str, to_email: str):
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USERNAME")
    pwd  = os.getenv("SMTP_PASSWORD")
    if not (user and pwd):
        print("SMTP credentials missing in environment. The email was not sent.")
        return

    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to_email

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(user, pwd)
        server.sendmail(user, [to_email], msg.as_string())

def send_telegram(body: str, chat_id: Optional[str] = None):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat = chat_id or os.getenv("TELEGRAM_CHAT_ID")
    if not (token and chat):
        print("Telegram token/chat_id missing in environment. The Telegram message was not sent.")
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    r = requests.post(url, json={"chat_id": chat, "text": body}, timeout=60)
    r.raise_for_status()

# ---------- CLI ----------

def main():
    parser = argparse.ArgumentParser(description="Meeting Analyzer: audio→transcript→summary/actions.")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--audio", type=str, help="Path to audio/video file")
    g.add_argument("--transcript", type=str, help="Raw transcript text (or path to .txt)")
    parser.add_argument("--whisper", default="small", help="Whisper model size (tiny/base/small/medium/large)")
    parser.add_argument("--lang", default="he", help="Output language: he/en")
    parser.add_argument("--llm-model", default="gpt-4.1", help="OpenAI model name")
    parser.add_argument("--email", default=None, help="Send results to this email")
    parser.add_argument("--telegram", action="store_true", help="Also send to Telegram (uses env CHAT_ID)")
    parser.add_argument("--json-out", default=None, help="Save raw JSON to path")
    parser.add_argument("--txt-out", default=None, help="Save pretty text to path")

    args = parser.parse_args()

    # Step 1: Transcript
    if args.audio:
        console.rule("[bold]Transcribing")
        result = transcribe(args.audio, model_size=args.whisper)
        transcript = result["text"]
        console.log(f"Detected language: {result.get('language','?')}; len={len(transcript)} chars")
    else:
        if os.path.isfile(args.transcript):
            transcript = open(args.transcript, "r", encoding="utf-8").read()
        else:
            transcript = args.transcript

    # Step 2: Analyze
    console.rule("[bold]Analyzing")
    report = analyze_meeting(transcript, language=args.lang, model=args.llm_model)

    # Step 3: Render
    pretty = render_text(report)
    console.rule("[bold]Result")
    print(Panel(pretty, title="Meeting Report", expand=True))

    # Step 4: Save
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(report.model_dump(), f, ensure_ascii=False, indent=2)
        console.log(f"Saved JSON to {args.json_out}")
    if args.txt_out:
        with open(args.txt_out, "w", encoding="utf-8") as f:
            f.write(pretty)
        console.log(f"Saved text to {args.txt_out}")

    # Step 5: Deliver
    subject = "Meeting Summary"
    if args.email:
        console.log(f"Sending email to {args.email}…")
        send_email_smtp(subject, pretty, args.email)
        console.log("Email sent.")
    if args.telegram:
        console.log("Sending Telegram…")
        send_telegram(pretty)
        console.log("Telegram sent.")

if __name__ == "__main__":
    main()
