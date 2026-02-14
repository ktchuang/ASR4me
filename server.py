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

from term_replace import apply_replacements

load_dotenv()

# ── App config ──────────────────────────────────────────────────────────────
app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
USER_TERM_DIR = os.path.join(basedir, "user_term")
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
    """Flask-Login callback: look up a User by their primary-key ID.

    Called automatically on every request that requires authentication
    to restore the logged-in user from the session cookie.
    """
    return db.session.get(User, int(user_id))


@login_manager.unauthorized_handler
def unauthorized():
    """Handle unauthenticated access attempts.

    AJAX / API calls (detected by multipart/form-data content type) receive
    a JSON 401 response so the frontend can redirect programmatically.
    Normal browser navigation is redirected to the login page.
    """
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
SYSTEM_PROMPT_FILE = os.getenv(
    "SYSTEM_PROMPT_FILE",
    os.path.join(basedir, "prompts", "default.txt"),
)
with open(SYSTEM_PROMPT_FILE, encoding="utf-8") as _f:
    SYSTEM_PROMPT = _f.read().strip()
print(f"System prompt loaded from: {SYSTEM_PROMPT_FILE}")

# ── LLM provider ───────────────────────────────────────────────────────────
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "claude").lower()

GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

if LLM_PROVIDER == "gemini":
    from google import genai

    gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    print(f"LLM provider: Gemini ({GEMINI_MODEL_NAME})")
else:
    from anthropic import Anthropic

    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    print("LLM provider: Claude (claude-sonnet-4-5-20250929)")


def user_keywords_path(username: str) -> str:
    """Return the filesystem path to a user's term-replacement CSV file.

    The file lives at ``user_term/<username>_keywords.txt`` and is created
    automatically when the user account is first provisioned via the
    ``create-user`` CLI command.
    """
    return os.path.join(USER_TERM_DIR, f"{username}_keywords.txt")


def improve_text(raw_text: str, username: str) -> str:
    """Send raw ASR transcription to the configured LLM for cleanup, then
    apply the user's personal term replacements.

    Pipeline:
        1. Send *raw_text* to Gemini or Claude (controlled by ``LLM_PROVIDER``)
           along with the externalized system prompt (``SYSTEM_PROMPT``).
        2. Apply per-user CSV term replacements from
           ``user_term/<username>_keywords.txt`` to the LLM output.

    Args:
        raw_text: Unprocessed transcription text straight from the ASR model.
        username: The logged-in user's name, used to locate their keywords file.

    Returns:
        The polished, term-replaced text ready for display and clipboard copy.
    """
    if LLM_PROVIDER == "gemini":
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=raw_text,
            config={"system_instruction": SYSTEM_PROMPT},
        )
        llm_output = response.text
    else:
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": raw_text}],
        )
        llm_output = response.content[0].text

    return apply_replacements(user_keywords_path(username), llm_output)


# ── Auth routes ─────────────────────────────────────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    """Show the login form (GET) or authenticate credentials (POST).

    On successful login the user is redirected to the ``next`` query-param
    URL if present, otherwise to the main index page.
    """
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
    """Log the current user out and redirect to the login page."""
    logout_user()
    return redirect(url_for("login"))


# ── App routes ──────────────────────────────────────────────────────────────
@app.route("/")
@login_required
def index():
    """Serve the main recording / transcription UI."""
    return render_template("index.html")


@app.route("/keywords", methods=["GET"])
@login_required
def get_keywords():
    """Return the current user's term-replacement CSV as a JSON string.

    Response: ``{"content": "<file contents>"}``
    Returns an empty string if the file does not exist yet.
    Called by the frontend on page load to populate the Term Replacements panel.
    """
    kw_path = user_keywords_path(current_user.username)
    if os.path.isfile(kw_path):
        with open(kw_path, encoding="utf-8") as f:
            content = f.read()
    else:
        content = ""
    return jsonify({"content": content})


@app.route("/keywords", methods=["POST"])
@login_required
def save_keywords():
    """Persist the updated term-replacement CSV for the current user.

    Expects JSON body: ``{"content": "<new file contents>"}``.
    The ``user_term/`` directory is created if it does not already exist.
    Called by the frontend Save button in the Term Replacements panel.
    """
    data = request.get_json()
    if data is None or "content" not in data:
        return jsonify({"error": "No content provided"}), 400

    os.makedirs(USER_TERM_DIR, exist_ok=True)
    kw_path = user_keywords_path(current_user.username)
    with open(kw_path, "w", encoding="utf-8") as f:
        f.write(data["content"])

    return jsonify({"ok": True})


@app.route("/transcribe", methods=["POST"])
@login_required
def transcribe():
    """Accept an uploaded audio recording and return transcribed + improved text.

    Pipeline:
        1. Save the uploaded WebM blob to a temp file.
        2. Use ffmpeg to convert it to 16 kHz mono WAV (required by ASR models).
        3. Run the configured ASR provider (Whisper or Omnilingual) to get
           the raw transcription (``txt_orig``).
        4. Pass the raw text through ``improve_text()`` which calls the LLM
           and applies per-user term replacements (``txt_improved``).

    Returns JSON: ``{"txt_orig": "...", "txt_improved": "..."}``.
    Temp files are cleaned up in a ``finally`` block regardless of outcome.
    """
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
        txt_improved = improve_text(txt_orig, current_user.username)

        return jsonify({"txt_orig": txt_orig, "txt_improved": txt_improved})

    finally:
        os.unlink(tmp_path)
        os.unlink(wav_path)


# ── CLI: create user ─────────────────────────────────────────────────────────
@app.cli.command("create-user")
def create_user_cmd():
    """Create a new user account interactively from the command line.

    Prompts for username and password, validates both, inserts a new row
    into the User table, and creates an empty per-user keywords file at
    ``user_term/<username>_keywords.txt``.

    Usage:
        flask --app server create-user
    """
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

    os.makedirs(USER_TERM_DIR, exist_ok=True)
    kw_path = user_keywords_path(username)
    open(kw_path, "a", encoding="utf-8").close()
    print(f"User '{username}' created successfully.")
    print(f"Keywords file created: {kw_path}")


# ── Main ────────────────────────────────────────────────────────────────────
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
