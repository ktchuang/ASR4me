# ASR4me — Voice to Organized Text

A local web service that records your voice, transcribes it with [OpenAI Whisper](https://github.com/openai/whisper) (runs locally, free), and uses the [Claude API](https://docs.anthropic.com/) to clean up and reorganize the text. The improved text is **auto-copied to your clipboard** so you can paste it anywhere with `Cmd + V`.

## How It Works

1. Click the mic button to **start recording**.
2. Click again to **stop**.
3. The audio is sent to the server where:
   - **Whisper** (local) transcribes the speech → `txt_orig`
   - **Claude** reorganizes and polishes the text → `txt_improved`
4. Both versions are displayed side by side.
5. `txt_improved` is **automatically copied** to your clipboard.

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.9+ | Tested on 3.11 |
| ffmpeg | any | Required by Whisper for audio decoding |
| Anthropic API key | — | See [Get your API key](#get-your-claude-api-key) below |

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
git clone <your-repo-url>
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

### 5. Get your Claude API key

1. Go to **[https://console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys)**.
2. Sign up or log in to your Anthropic account.
3. Click **"Create Key"** to generate a new API key.
4. Copy the key (it starts with `sk-ant-`).
5. You will need to add billing credits; see [Anthropic pricing](https://www.anthropic.com/pricing) for details.

### 6. Configure the environment

```bash
cp .env.example .env
```

Open `.env` and paste your API key:

```
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
WHISPER_MODEL=base
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
 * Running on http://127.0.0.1:5000
```

### 8. Open in your browser

Navigate to **[http://127.0.0.1:5000](http://127.0.0.1:5000)** in Chrome, Edge, or Firefox.

> **Important:** Use Chrome for the best microphone and clipboard support.

### 9. Record and transcribe

1. Click the **mic button** — your browser will ask for microphone permission. Allow it.
2. Speak clearly into your microphone.
3. Click the mic button again to **stop**.
4. Wait a few seconds while the audio is transcribed and improved.
5. The improved text is **auto-copied** to your clipboard. Paste it with `Cmd + V` (Mac) or `Ctrl + V` (Windows/Linux).

## Project Structure

```
ASR4me/
├── server.py            # Flask backend (Whisper ASR + Claude text improvement)
├── templates/
│   └── index.html       # Frontend (recording UI, clipboard copy)
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variable template
└── README.md            # This file
```

## Notes

- **Language support:** Whisper automatically detects the spoken language. It supports 99+ languages.
- **Privacy:** Audio is processed locally by Whisper. Only the transcribed *text* is sent to the Claude API.
- **Clipboard:** Auto-copy uses the browser's Clipboard API. If it fails (e.g., due to browser permissions), click the "Copy to Clipboard" button manually.
- **Claude model:** The server uses `claude-sonnet-4-5-20250929` for text improvement. You can change this in `server.py`.
