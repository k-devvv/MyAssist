# MyAssist

A Windows x64 desktop companion with an original floating character and offline push-to-talk dictation. Version 1 has no chat assistant, API key, cloud endpoint, telemetry, or auto-update.

## Included in the current package

- Transparent, always-on-top companion window with two original SVG characters, tray menu, settings window, drag/resize, and idle motion.
- Hold **Ctrl + Shift + Space** to record; release to transcribe. **Ctrl + Shift + M** shows or hides the companion; **Escape** cancels while recording.
- Audio is captured in a bounded memory buffer, sent to the local worker, and cleared after transcription/cancel. The worker uses CPU int8 inference.
- Text insertion is guarded: it is attempted only if the same window captured at recording start remains foreground. Otherwise, the companion offers a copyable transcript.
- Settings include microphone selection and an input-level meter.
- Speech model: `Systran/faster-whisper-base`, pinned to revision `ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66`, MIT license. Provenance is included with the model.
- The model is loaded only for transcription and the process is released after 90 seconds idle to keep memory usage down.

## Run the packaged app

1. Extract `release\MyAssist-Windows-x64.zip` to a folder.
2. Open `MyAssist.exe` at the extraction root (the same executable is also at `release\win-unpacked\MyAssist.exe` in the project folder).
3. Focus a normal text field, hold **Ctrl + Shift + Space**, speak, and release. Start with Notepad.

This ZIP contains the full Electron app folder; `MyAssist.exe` is not a single-file executable. Keep the adjacent files and `resources` folder in place. This build is unsigned, so Windows may show a SmartScreen notice.

## Build on Windows x64

Requirements: Node.js 22 and Python 3.11. Network is used only during build to fetch packages and the model; transcription runs offline.

Run from PowerShell in `D:\MyAssist`:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build.ps1
```

The script produces `release\MyAssist-Windows-x64.zip` and `release\win-unpacked\MyAssist.exe`.

## Privacy and limitations

- The model and audio processing stay local; no SLM/LLM or cloud speech service is included.
- Audio is held in memory for the active recording and transcription. It is not intentionally written to disk or included in logs. Text is retained only until insertion or fallback copy.
- The hotkey worker monitors only the configured combinations and Escape during dictation. It does not install a general keyboard hook or persist key events.
- Windows can refuse text insertion into elevated or protected apps. In that case, use the copyable fallback. Secure fields, full-screen games, and anti-cheat software are unsupported.
- Shortcut display currently shows the built-in combinations; rebinding, VRM import, and SLM integration are follow-up work.
- Verified the TypeScript typecheck, production build, Python syntax, local CPU model loading/audio decoding, and the packaged speech worker on generated audio.
- The restricted validation environment denied Windows global hotkey registration with error 5 and could not keep even a minimal Electron app running. GUI launch, live microphone capture, hotkey behavior, and insertion into another app still need verification in a normal Windows desktop session.



## Current companion update

The Wayfinder and Signal Scout can be selected from the companion toolbar. Actions include wave, dance, and sit. The Walk/Pause control requests movement around the display work area. The AI panel reserves Local and Cloud provider choices; these are placeholders without model connections.

The latest diagnostic build displays `MOTION DIAGNOSTIC 04` and requested movement coordinates. Character rendering and screen roaming remain under investigation following user reports; successful compilation and packaging do not establish working desktop behavior.

Generated executables, Electron distributions, downloaded speech models, caches, and local mockup sessions are excluded from Git. Use the build scripts to acquire dependencies and create a local package.
