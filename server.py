import os
import subprocess
import tempfile
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, flash, jsonify, redirect, render_template, request, url_for
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()

# ── App config ──────────────────────────────────────────────────────────────
app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(basedir, "asr4me.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"


# ── User model ──────────────────────────────────────────────────────────────
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@login_manager.unauthorized_handler
def unauthorized():
    # Return JSON 401 for AJAX / API calls, HTML redirect for browser navigation
    if request.content_type and "multipart/form-data" in request.content_type:
        return jsonify({"error": "Authentication required"}), 401
    return redirect(url_for("login"))


# ── ASR provider ───────────────────────────────────────────────────────────
ASR_PROVIDER = os.getenv("ASR_PROVIDER", "whisper").lower()

if ASR_PROVIDER == "omnilingual":
    from omnilingual_asr.models.inference.pipeline import ASRInferencePipeline

    OMNILINGUAL_MODEL = os.getenv("OMNILINGUAL_MODEL", "omniASR_LLM_300M")
    OMNILINGUAL_LANG = os.getenv("OMNILINGUAL_LANG", "").strip() or None
    print(f"Loading Omnilingual ASR model '{OMNILINGUAL_MODEL}' …")
    asr_pipeline = ASRInferencePipeline(model_card=OMNILINGUAL_MODEL)
    lang_display = OMNILINGUAL_LANG or "auto-detect"
    print(f"Omnilingual ASR model loaded (lang={lang_display}).")
else:
    import whisper

    WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
    WHISPER_LANG = os.getenv("WHISPER_LANG", "zh")
    WHISPER_TEMPERATURE = float(os.getenv("WHISPER_TEMPERATURE", "0"))
    WHISPER_PROMPT = os.getenv("WHISPER_PROMPT", "")
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

# ── LLM provider ───────────────────────────────────────────────────────────
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "claude").lower()

if LLM_PROVIDER == "gemini":
    import google.generativeai as genai

    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    gemini_model = genai.GenerativeModel(
        model_name=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
        system_instruction=SYSTEM_PROMPT,
    )
    print(f"LLM provider: Gemini ({os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')})")
else:
    from anthropic import Anthropic

    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    print("LLM provider: Claude (claude-sonnet-4-5-20250929)")


def improve_text(raw_text: str) -> str:
    """Send raw transcription to the configured LLM and return improved text."""
    if LLM_PROVIDER == "gemini":
        response = gemini_model.generate_content(raw_text)
        return response.text
    else:
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": raw_text}],
        )
        return response.content[0].text


# ── Auth routes ─────────────────────────────────────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("index"))

        flash("Invalid username or password.", "error")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# ── App routes ──────────────────────────────────────────────────────────────
@app.route("/")
@login_required
def index():
    return render_template("index.html")


@app.route("/transcribe", methods=["POST"])
@login_required
def transcribe():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files["audio"]

    # Save uploaded audio to a temp file so Whisper can read it
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
        audio_file.save(tmp.name)
        tmp_path = tmp.name

    # Preprocess: convert to 16 kHz mono WAV (Whisper's expected format)
    wav_path = tmp_path + ".wav"
    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", tmp_path,
                "-ar", "16000", "-ac", "1", "-sample_fmt", "s16",
                wav_path,
            ],
            capture_output=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        os.unlink(tmp_path)
        if os.path.exists(wav_path):
            os.unlink(wav_path)
        return jsonify({"error": f"Audio preprocessing failed: {exc}"}), 500

    try:
        # Step 1 – ASR (local, free)
        if ASR_PROVIDER == "omnilingual":
            lang_arg = [OMNILINGUAL_LANG] if OMNILINGUAL_LANG else None
            results = asr_pipeline.transcribe(
                [wav_path], lang=lang_arg, batch_size=1,
            )
            txt_orig = results[0].strip()
        else:
            transcribe_opts = {"language": WHISPER_LANG, "temperature": WHISPER_TEMPERATURE}
            if WHISPER_PROMPT:
                transcribe_opts["initial_prompt"] = WHISPER_PROMPT
            result = whisper_model.transcribe(wav_path, **transcribe_opts)
            txt_orig = result["text"].strip()

        if not txt_orig:
            return jsonify({"error": "No speech detected in the recording."}), 400

        # Step 2 – Improve / reorganize text with LLM
        txt_improved = improve_text(txt_orig)

        return jsonify({"txt_orig": txt_orig, "txt_improved": txt_improved})

    finally:
        os.unlink(tmp_path)
        os.unlink(wav_path)


# ── CLI: create user ─────────────────────────────────────────────────────────
@app.cli.command("create-user")
def create_user_cmd():
    """Create a new user account (interactive)."""
    import getpass

    username = input("Username (min 3 chars): ").strip()
    if len(username) < 3:
        print("Error: username must be at least 3 characters.")
        return

    if User.query.filter_by(username=username).first():
        print(f"Error: username '{username}' already taken.")
        return

    password = getpass.getpass("Password (min 6 chars): ")
    if len(password) < 6:
        print("Error: password must be at least 6 characters.")
        return

    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Error: passwords do not match.")
        return

    user = User(
        username=username,
        password_hash=generate_password_hash(password, method="pbkdf2:sha256"),
    )
    db.session.add(user)
    db.session.commit()
    print(f"User '{username}' created successfully.")


# ── Main ────────────────────────────────────────────────────────────────────
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
