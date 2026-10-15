$ErrorActionPreference = 'Stop'
$root = Resolve-Path "$PSScriptRoot\.."
Set-Location $root
$env:COREPACK_HOME = Join-Path $root '.corepack'
$env:electron_config_cache = Join-Path $root '.electron-cache'
$env:ELECTRON_BUILDER_CACHE = Join-Path $root '.electron-builder-cache'
$env:HF_HOME = Join-Path $root '.hf-cache'
$env:HF_HUB_DISABLE_TELEMETRY = '1'
corepack pnpm install --force
node node_modules\electron\install.js
powershell -ExecutionPolicy Bypass -File scripts\fetch-whisper.ps1
powershell -ExecutionPolicy Bypass -File worker\build.ps1
corepack pnpm exec electron-vite build
corepack pnpm exec electron-builder --win dir
$zip = Join-Path $root 'release\MyAssist-Windows-x64.zip'
if (Test-Path $zip) { Remove-Item -LiteralPath $zip -Force }
Compress-Archive -Path (Join-Path $root 'release\win-unpacked\*') -DestinationPath $zip -CompressionLevel Fastest
Write-Output "Built app: $(Join-Path $root 'release\win-unpacked\MyAssist.exe')"
Write-Output "Bundle: $zip"
