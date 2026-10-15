$ErrorActionPreference = 'Stop'
$root = Resolve-Path "$PSScriptRoot\.."
$model = Join-Path $root 'resources\models\base'
New-Item -ItemType Directory -Force $model | Out-Null
$python = Join-Path $root 'worker\.venv\Scripts\python.exe'
if (!(Test-Path $python)) { python -m venv (Join-Path $root 'worker\.venv'); $python = Join-Path $root 'worker\.venv\Scripts\python.exe' }
& $python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='Systran/faster-whisper-base', revision='ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66', local_dir=r'$model', allow_patterns=['config.json','model.bin','tokenizer.json','vocabulary.txt'])"
"Model: Systran/faster-whisper-base`nRevision: ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66`nLicense: MIT`nSource: https://huggingface.co/Systran/faster-whisper-base/tree/ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66`nFetched at build time; runtime is offline." | Set-Content (Join-Path $model 'MODEL-PROVENANCE.txt') -Encoding utf8
