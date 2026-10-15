# MyAssist: Local Desktop Companion and Voice Dictation

**Status:** Proposed design for review  
**Date:** 2026-10-15  
**Target:** Windows x64

## Goal
Build an original Windows desktop companion with a movable full-body character and offline push-to-talk dictation. Holding a configurable shortcut records speech; release triggers local transcription and inserts the result into the app that was focused when recording began. No cloud speech service, API key, or LLM/SLM is included in version 1. A local language model can be considered later after resource use is measured.

## Constraints
- Laptop: Intel Core i7-13650HX, RTX 4050 Laptop GPU (6 GB VRAM), 16 GB RAM. The screenshot showed 13.3 GB RAM in use at that moment, so we treat memory as constrained.
- `D:\MyAssist` was empty at inspection. Node 22 and Python 3.11 are installed; Unity and .NET SDK are not.
- Deliver a Windows setup `.exe` plus installed app files. Electron cannot be delivered as one self-contained executable.

## Version 1 scope
- One original stylized full-body 3D companion in a transparent, always-on-top overlay; drag, resize, idle animation, click reaction, tray menu, and configurable show/hide shortcut.
- Optional VRM import for models the user is licensed to use. The built-in character must be original; do not reuse Mate Engine's protected default avatar, Desktop Mate assets, or cracked downloads.
- Configurable hold-to-talk shortcut and cancel shortcut; a visible listening/transcribing state and on-screen cancel button; shortcut conflict detection and rebinding.
- Microphone selection and input-level check.
- Offline speech recognition via `whisper.cpp` using an approved multilingual base-class model, on CPU by default. Include its model in the installer only after recording its source and license.
- At dictation start, capture the foreground window. Keep the overlay non-activating. Insert text only if the same window remains foreground at completion.
- If focus changes, the target closes, or Windows blocks insertion, show a transcript panel with copy action. Never force focus back to the old window or type into a different app.
- Keep audio in memory only for the active recording/transcription; do not save audio, transcripts, keyboard events, or telemetry. Clear buffers on completion/cancel. Maximum recording duration defaults to 90 seconds.

Deferred: any LLM/SLM or chat; window/taskbar sitting; multiple characters; music sync, alarms, screen reading, app control, game/anti-cheat compatibility; cloud services, accounts, telemetry, auto-update, and non-Windows builds.

## Architecture
- **Desktop shell:** Electron + TypeScript. Main process owns app lifecycle, transparent overlay, tray, settings, and worker communication. Use context isolation and a narrow preload API; renderer pages do not receive Node.js access.
- **Character:** Three.js with `@pixiv/three-vrm` for optional VRM support. Default character uses original simple geometry/art. Use a low idle frame rate; pause animation while hidden.
- **Hotkeys:** A small Python worker uses Windows `RegisterHotKey` for only the configured combinations. For hold-to-talk release, it polls `GetAsyncKeyState` only for the configured key and modifiers while dictation is active. It does not install a low-level keyboard hook, record/log arbitrary keystrokes, or transmit key events. It reports only named actions and captures the foreground window handle at dictation start. Package the worker so Python is not needed on the user's machine. If a shortcut is occupied, show a conflict and do not start recording.
- **Audio/STT:** Capture microphone audio only while the hotkey is held. A local `faster-whisper` worker (CTranslate2 CPU int8) transcribes the completed recording using the local model. This replaces whisper.cpp because no C++ compiler is installed on the target PC and faster-whisper accepts in-memory decoded audio. Recognition has no network dependency.
- **Insertion:** A narrow Windows adapter verifies the saved target is still foreground, then injects Unicode text. Windows privilege boundaries can block this; do not run elevated or bypass them.
- **Packaging:** Electron Builder creates a Windows app folder distributed as a ZIP, bundling the Electron runtime, app resources, Python hotkey worker, speech runtime, and MIT-licensed Systran faster-whisper-base model. Keep generated models/build artifacts out of source control. The app is unsigned, so Windows may show SmartScreen warnings.

## Flow and failure handling
1. Hold shortcut: the worker reports the registered hotkey and captures the foreground target; app begins microphone capture without activating the overlay and shows a listening indicator.
2. Release: stop capture, show transcribing state, run local STT, clear audio buffer.
3. If the captured target remains foreground and insertion succeeds, type the transcript there. Otherwise, show the transcript panel with copy/dismiss actions.
4. Cancel, shutdown, or duration cap stops capture and clears audio.
5. Microphone denial, missing/corrupt model, STT failure, and shortcut conflicts each show an actionable message; never silently switch microphones or destinations.
6. Unregister shortcuts and stop the worker on exit. No runtime network use for recording or recognition. Model acquisition is limited to an explicit build/install step or user-controlled import.

## Resource and privacy strategy
- No LLM/SLM process in v1; no cloud endpoint or API key.
- Start with CPU speech recognition; measure latency and peak RAM before considering a larger model or GPU inference. If memory/speed is poor, use a smaller Whisper model.
- Keep audio/transcripts out of logs and persistent storage. The worker only handles configured shortcuts and does not retain key events.

## Acceptance criteria
1. Setup `.exe` installs and launches without Unity, .NET SDK, API key, or cloud service.
2. Character appears over ordinary windows, moves/resizes, and hides/restores from tray/shortcut.
3. Hold-to-talk starts on press, stops on release, shows states, and can be cancelled.
4. Speech transcribes with the network disconnected and inserts into a standard text editor when the original target remains focused.
5. If focus changes or Windows blocks injection, no text is sent to another app and transcript fallback appears.
6. Audio and keyboard input are not written to logs or retained after the operation.
7. Shortcut conflicts, microphone denial, and missing/corrupt model files produce actionable messages.
8. Actual memory use and transcription latency are recorded before future SLM work.

## Known limitations / prototype gates
- Prove `RegisterHotKey` conflict handling, key-release polling, cancellation, foreground capture, and that the chosen hotkey does not trigger an unwanted action in the target app before building the full interface. Use non-repeat registration where available.
- Validate transparent-window hit testing and click-through on Windows. If both interaction and pass-through are unreliable, use a small bounded character window with a clear drag handle rather than intercepting the desktop.
- `SendInput` can be blocked across privilege boundaries. Secure fields, elevated apps, full-screen games, anti-cheat-protected software, and remote desktop are not guaranteed targets.
- First character will be simple and original; visual polish and more licensed VRM models can follow.
- Do not promise a transcription speed or language-specific accuracy until measured on this laptop.

## References
- Mate Engine README: https://github.com/shinyflvre/Mate-Engine
- Electron BrowserWindow: https://www.electronjs.org/docs/latest/api/browser-window
- Electron global shortcuts: https://www.electronjs.org/docs/latest/api/global-shortcut
- Windows RegisterHotKey: https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-registerhotkey
- Windows GetAsyncKeyState: https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getasynckeystate
- Windows SendInput: https://learn.microsoft.com/windows/win32/api/winuser/nf-winuser-sendinput
- Three-VRM: https://github.com/pixiv/three-vrm
- whisper.cpp: https://github.com/ggml-org/whisper.cpp
- Electron packaging: https://www.electronjs.org/docs/latest/tutorial/application-distribution

