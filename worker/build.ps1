$ErrorActionPreference = 'Stop'
$venv = Join-Path $PSScriptRoot '.venv'
if (!(Test-Path $venv)) { python -m venv $venv }
& "$venv\Scripts\python.exe" -m pip install --cache-dir "$PSScriptRoot\..\.pip-cache" -r "$PSScriptRoot\requirements.txt"
New-Item -ItemType Directory -Force "$PSScriptRoot\..\resources\worker" | Out-Null
& "$venv\Scripts\pyinstaller.exe" --clean --onefile --console --name MyAssistHotkeys --distpath "$PSScriptRoot\..\resources\worker" "$PSScriptRoot\hotkeys.py"
& "$venv\Scripts\pyinstaller.exe" --clean --onefile --console --name MyAssistSpeech --collect-all faster_whisper --collect-all ctranslate2 --collect-all onnxruntime --collect-all av --distpath "$PSScriptRoot\..\resources\worker" "$PSScriptRoot\speech.py"
