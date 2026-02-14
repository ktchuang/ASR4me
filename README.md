# ASR4me — Voice to Organized Text

A local web service that records your voice, transcribes it with a local ASR model ([OpenAI Whisper](https://github.com/openai/whisper) or [Meta Omnilingual ASR](https://github.com/facebookresearch/omnilingual-asr)), and uses an LLM ([Claude](https://docs.anthropic.com/) or [Google Gemini](https://ai.google.dev/)) to clean up and reorganize the text. The improved text is **auto-copied to your clipboard** so you can paste it anywhere with `Cmd + V`.

## How It Works

1. **Register** an account, then **log in**.
2. Click the mic button to **start recording**.
3. Click again to **stop**.
4. The audio is preprocessed to 16 kHz mono WAV, then sent to the ASR model:
   - **Whisper** or **Omnilingual ASR** (local) transcribes the speech → `txt_orig`
   - **Claude or Gemini** reorganizes and polishes the text → `txt_improved`
5. Both versions are displayed side by side, with an accumulated "Appended Text" panel.
6. `txt_improved` is **automatically copied** to your clipboard.

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.10+ | 3.12 recommended (required for Omnilingual ASR) |
| ffmpeg | any | Required for audio preprocessing |
| libsndfile | any | Required only for Omnilingual ASR (`brew install libsndfile`) |
| LLM API key | — | Claude **or** Gemini (see below) |

## Step-by-Step Setup

### 1. Install system dependencies

```bash
# macOS (Homebrew)
brew install ffmpeg libsndfile

# Ubuntu / Debian
sudo apt update && sudo apt install ffmpeg libsndfile1

# Windows (Chocolatey)
choco install ffmpeg
```

Verify ffmpeg is installed:

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
python3.12 -m venv .venv
source .venv/bin/activate   # macOS / Linux
# .venv\Scripts\activate    # Windows
```

### 4. Install Python dependencies

```bash
pip install -r requirements.txt
```

> The first run will download the ASR model weights automatically. Whisper `base` is ~140 MB; Omnilingual `300M` is ~1.2 GB.

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
# ── LLM provider: "claude" or "gemini" ──
LLM_PROVIDER=claude
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
# GEMINI_API_KEY=your-gemini-key-here

# ── ASR provider: "whisper" or "omnilingual" ──
ASR_PROVIDER=whisper

# ── Flask ──
SECRET_KEY=dev-secret-change-me
```

#### ASR provider options

**Whisper** (default) — OpenAI's speech recognition model, supports 99 languages.

| Model | Size | Relative Speed | Best For |
|---|---|---|---|
| `tiny` | 39 MB | Fastest | Quick drafts, testing |
| `base` | 140 MB | Fast | **Good default** |
| `small` | 460 MB | Medium | Better accuracy |
| `medium` | 1.5 GB | Slow | High accuracy |
| `large` | 2.9 GB | Slowest | Best accuracy |

Whisper-specific settings: `WHISPER_MODEL`, `WHISPER_LANG`, `WHISPER_TEMPERATURE`, `WHISPER_PROMPT`.

**Omnilingual ASR** — Meta's multilingual model, supports 1,600+ languages.

| Model | Size | Download | Notes |
|---|---|---|---|
| `omniASR_LLM_300M` | 300M | 1.2 GB | Fast, works on CPU |
| `omniASR_LLM_1B` | 1B | 4 GB | GPU recommended |
| `omniASR_LLM_7B` | 7.8B | 30 GB | Best accuracy, GPU required |
| `omniASR_LLM_Unlimited_*` | varies | varies | No audio length limit |
| `omniASR_CTC_*` | varies | varies | Up to 96x faster, no language conditioning |

Omnilingual-specific settings: `OMNILINGUAL_MODEL`, `OMNILINGUAL_LANG` (uses ISO 639-3 + script codes, e.g. `cmn_Hant`, `eng_Latn`, `jpn_Jpan`).

> **Note:** Standard Omnilingual models have a 40-second audio limit. Use `Unlimited` variants for longer recordings. Output has no punctuation — the LLM improvement step adds it automatically.

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

Or with Omnilingual ASR:

```
Loading Omnilingual ASR model 'omniASR_LLM_300M' …
Omnilingual ASR model loaded (lang=cmn_Hant).
LLM provider: Gemini (gemini-2.0-flash)
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

## System Prompts

The system prompt that guides the LLM text improvement is loaded from an external text file, making it easy to customize for different LLM models or use cases.

| Setting | Default | Description |
|---|---|---|
| `SYSTEM_PROMPT_FILE` | `prompts/default.txt` | Path to the prompt file |

The `prompts/` directory ships with a default prompt. To customize:

1. Copy an existing prompt file:
   ```bash
   cp prompts/default.txt prompts/my-custom-prompt.txt
   ```
2. Edit the new file to suit your needs.
3. Point to it in `.env`:
   ```bash
   SYSTEM_PROMPT_FILE=prompts/my-custom-prompt.txt
   ```

> **Recommended:** `prompts/gemini-2.0-flash-v2.txt` is the recommended system prompt for Gemini. Set `SYSTEM_PROMPT_FILE=prompts/gemini-2.0-flash-v2.txt` in your `.env` when using Gemini as the LLM provider.

> **Tip:** Different LLM models may respond better to different prompt styles. Create a prompt file per model (e.g., `prompts/gemini-2.0-flash.txt`, `prompts/claude-sonnet.txt`) and switch via `SYSTEM_PROMPT_FILE` when changing `LLM_PROVIDER`.

## Per-User Term Replacements

Each user has a personal **Term Replacements** panel on the web UI. This allows post-processing of the LLM output to fix recurring terminology — for example, replacing simplified Chinese terms with traditional Chinese equivalents, or standardizing proper nouns.

- Replacement files are stored in `user_term/<username>_keywords.txt`.
- An empty file is created automatically when a user account is created.
- The file uses CSV format — one replacement per line: `original,replacement`.
- Replacements are applied **after** the LLM improvement step, before the final text is returned.
- Users can edit and save their replacements directly from the web UI (no server restart needed).

Example `user_term/alice_keywords.txt`:
```
人工智慧,人工智能
machine learning,機器學習
OpenAi,OpenAI
```

## Project Structure

```
ASR4me/
├── server.py            # Flask backend (auth, ASR, LLM text improvement)
├── term_replace.py      # CSV-based keyword replacement utility
├── templates/
│   ├── index.html       # Recording UI (clipboard copy, appended text, term editor)
│   └── login.html       # Login page
├── prompts/
│   └── default.txt      # Default system prompt (configurable via SYSTEM_PROMPT_FILE)
├── user_term/           # Per-user keyword replacement files (auto-created)
│   └── .gitkeep
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variable template
└── README.md            # This file
```

## Notes

- **ASR providers:** Switch between Whisper (99 languages) and Omnilingual ASR (1,600+ languages) via `ASR_PROVIDER` in `.env`.
- **Language support:** Whisper uses ISO 639-1 codes (`zh`, `en`); Omnilingual uses ISO 639-3 + script (`cmn_Hant`, `eng_Latn`).
- **Privacy:** Audio is processed locally by the ASR model. Only the transcribed *text* is sent to the LLM API.
- **Clipboard:** Auto-copy uses the browser's Clipboard API. If it fails (e.g., due to browser permissions), click the "Copy to Clipboard" button manually.
- **LLM models:** Claude uses `claude-sonnet-4-5-20250929`; Gemini defaults to `gemini-2.0-flash`. Both are configurable in `.env`.
- **Database:** User accounts are stored in a local SQLite file (`asr4me.db`), created automatically on first run.
