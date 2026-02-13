# ASR4me — Voice to Organized Text

A local web service that records your voice, transcribes it with [OpenAI Whisper](https://github.com/openai/whisper) (runs locally, free), and uses an LLM ([Claude](https://docs.anthropic.com/) or [Google Gemini](https://ai.google.dev/)) to clean up and reorganize the text. The improved text is **auto-copied to your clipboard** so you can paste it anywhere with `Cmd + V`.

## How It Works

1. **Register** an account, then **log in**.
2. Click the mic button to **start recording**.
3. Click again to **stop**.
4. The audio is sent to the server where:
   - **Whisper** (local) transcribes the speech → `txt_orig`
   - **Claude or Gemini** reorganizes and polishes the text → `txt_improved`
5. Both versions are displayed side by side.
6. `txt_improved` is **automatically copied** to your clipboard.

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.9+ | Tested on 3.11 |
| ffmpeg | any | Required by Whisper for audio decoding |
| LLM API key | — | Claude **or** Gemini (see below) |

## Step-by-Step Setup

### 1. Install ffmpeg

Whisper needs `ffmpeg` to decode audio files.

```bash
# macOS (Homebrew)
brew install ffmpeg

# Ubuntu / Debian
sudo apt update && sudo apt install ffmpeg

# Windows (Chocolatey)
choco install ffmpeg
```

Verify it's installed:

```bash
ffmpeg -version
```

### 2. Clone the repository

```bash
git clone https://github.com/ktchuang/ASR4me.git
cd ASR4me
```

### 3. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate   # macOS / Linux
# venv\Scripts\activate    # Windows
```

### 4. Install Python dependencies

```bash
pip install -r requirements.txt
```

> The first run will download the Whisper model (~140 MB for `base`). This only happens once.

### 5. Get your LLM API key

You need **one** of the following:

#### Option A — Claude (default)

1. Go to **[https://console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys)**.
2. Sign up or log in to your Anthropic account.
3. Click **"Create Key"** to generate a new API key.
4. Copy the key (it starts with `sk-ant-`).
5. You will need to add billing credits; see [Anthropic pricing](https://www.anthropic.com/pricing) for details.

#### Option B — Google Gemini

1. Go to **[https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)**.
2. Sign in with your Google account.
3. Click **"Create API key"** and copy it.
4. Gemini offers a free tier; see [Google AI pricing](https://ai.google.dev/pricing) for details.

### 6. Configure the environment

```bash
cp .env.example .env
```

Open `.env` and fill in your settings:

```bash
# Choose your LLM provider: "claude" or "gemini"
LLM_PROVIDER=claude

# If using Claude:
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here

# If using Gemini:
GEMINI_API_KEY=your-gemini-key-here
GEMINI_MODEL=gemini-2.0-flash

# Generate a real secret for production:
#   python3 -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=dev-secret-change-me
```

**Whisper model options** (trade-off: accuracy vs. speed):

| Model | Size | Relative Speed | Best For |
|---|---|---|---|
| `tiny` | 39 MB | Fastest | Quick drafts, testing |
| `base` | 140 MB | Fast | **Good default** |
| `small` | 460 MB | Medium | Better accuracy |
| `medium` | 1.5 GB | Slow | High accuracy |
| `large` | 2.9 GB | Slowest | Best accuracy |

### 7. Start the server

```bash
python server.py
```

You should see:

```
Loading Whisper model 'base' …
Whisper model loaded.
LLM provider: Claude (claude-sonnet-4-5-20250929)
 * Running on http://127.0.0.1:5000
```

### 8. Open in your browser

Navigate to **[http://127.0.0.1:5000](http://127.0.0.1:5000)** in Chrome, Edge, or Firefox.

> **Important:** Use Chrome for the best microphone and clipboard support.

### 9. Create a user account

Users are created from the command line (no self-registration):

```bash
flask --app server create-user
```

You'll be prompted for a username and password interactively.

### 10. Log in

Open the browser, enter your credentials, and you'll see the recording interface with your username and a **Log out** link.

### 11. Record and transcribe

1. Click the **mic button** — your browser will ask for microphone permission. Allow it.
2. Speak clearly into your microphone.
3. Click the mic button again to **stop**.
4. Wait a few seconds while the audio is transcribed and improved.
5. The improved text is **auto-copied** to your clipboard. Paste it with `Cmd + V` (Mac) or `Ctrl + V` (Windows/Linux).

## Project Structure

```
ASR4me/
├── server.py            # Flask backend (auth, Whisper ASR, LLM text improvement)
├── templates/
│   ├── index.html       # Recording UI (clipboard copy, logout)
│   └── login.html       # Login page
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variable template
└── README.md            # This file
```

## Notes

- **Language support:** Whisper automatically detects the spoken language. It supports 99+ languages. Default is set to Traditional Chinese (`zh`) via `WHISPER_LANG`.
- **Privacy:** Audio is processed locally by Whisper. Only the transcribed *text* is sent to the LLM API.
- **Clipboard:** Auto-copy uses the browser's Clipboard API. If it fails (e.g., due to browser permissions), click the "Copy to Clipboard" button manually.
- **LLM models:** Claude uses `claude-sonnet-4-5-20250929`; Gemini defaults to `gemini-2.0-flash`. Both are configurable in `server.py` / `.env`.
- **Database:** User accounts are stored in a local SQLite file (`asr4me.db`), created automatically on first run.
