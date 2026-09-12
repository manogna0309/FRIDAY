# FRIDAY — Offline Voice Assistant

FRIDAY is a Python-only desktop voice assistant designed for a 24-hour hackathon demo.

## Highlights

- Fully offline core workflow
- Vosk offline speech recognition
- pyttsx3 offline text-to-speech
- Deterministic intent detection
- Animated FRIDAY Core
- Listening / Thinking / Ready status
- Elegant dark desktop UI
- Quick command buttons
- Local notes
- Local user-name memory
- Opens Calculator, Notepad and File Explorer
- Text input fallback
- No cloud API required for core features

The original starter already used Tkinter, Vosk and pyttsx3; this version adds a clearer intent layer and a more polished animated interface.

## Install

Python 3.10+ recommended.

```bash
pip install -r requirements.txt
```

## Add offline speech model

Download an appropriate Vosk offline model and extract it into:

```text
FRIDAY_Hackathon/model/
```

The app still works in text mode if the model is missing.

## Run

```bash
python main.py
```

On Windows you can also double-click `run_friday.bat`.

## Demo commands

- Hello FRIDAY
- What time is it?
- What is today's date?
- Open calculator
- Open notepad
- Open file explorer
- Take note finish hackathon presentation
- Show my notes
- Call me Tejas
- What is my name?
- Voice off
- Help
- Exit

## Architecture

```text
Microphone
   ↓
Vosk Offline Speech Recognition
   ↓
Intent Detection
   ↓
Action Executor
   ↓
FRIDAY Response
   ↓
Tkinter UI + pyttsx3
```

## Suggested 4-person hackathon split

1. Voice module — Vosk + microphone
2. Intelligence module — intent detection + commands
3. UI module — animation + interface
4. Integration/demo — testing, packaging, presentation

## Deployment

 For a standalone executable, package the project with PyInstaller after confirming the Vosk model is included.

Important: this project is intentionally offline-first. Internet search is not part of the core design.
