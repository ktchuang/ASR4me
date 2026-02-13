import os
import tempfile

import whisper
from anthropic import Anthropic
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

load_dotenv()

app = Flask(__name__)

# ── Claude client ───────────────────────────────────────────────────────────
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# ── Whisper ASR model ───────────────────────────────────────────────────────
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
print(f"Loading Whisper model '{WHISPER_MODEL}' …")
whisper_model = whisper.load_model(WHISPER_MODEL)
print("Whisper model loaded.")

# ── System prompt for text improvement ──────────────────────────────────────
SYSTEM_PROMPT = """You are a professional text editor specializing in converting raw speech \
transcriptions into polished, well-organized written text.

Your task
---------
1. Please keep the original language, tone, style, and level of formality of the speaker intact.
2. Please keep the output is multi-lingual if the input is multi-lingual. Do NOT translate the text into a single language.
3. Clean up the transcribed text while preserving the speaker's original meaning and intent.
4. Fix grammar, punctuation, capitalization, and spelling.
5. Remove speech artifacts: filler words (um, uh, like, you know, so, basically), \
false starts, repeated words, and verbal pauses.
6. Organize content into logical paragraphs.
7. If the content contains enumerable items, format them as a numbered or bulleted list.
8. If multiple distinct topics are discussed, add concise section headers (## Header).
9. Maintain the speaker's original tone, style, and level of formality.
10. Do NOT add, infer, or embellish information beyond what was spoken.
11. Do NOT include any meta-commentary, explanations, or notes about your edits.

Output ONLY the improved text."""


# ── Routes ──────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/transcribe", methods=["POST"])
def transcribe():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files["audio"]

    # Save uploaded audio to a temp file so Whisper can read it
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
        audio_file.save(tmp.name)
        tmp_path = tmp.name

    try:
        # Step 1 – ASR with Whisper (local, free)
        result = whisper_model.transcribe(tmp_path)
        txt_orig = result["text"].strip()

        if not txt_orig:
            return jsonify({"error": "No speech detected in the recording."}), 400

        # Step 2 – Improve / reorganize text with Claude
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": txt_orig}],
        )
        txt_improved = response.content[0].text

        return jsonify({"txt_orig": txt_orig, "txt_improved": txt_improved})

    finally:
        os.unlink(tmp_path)


# ── Main ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
