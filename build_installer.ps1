param(
    [string]$Version = '1.1.0'
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root '.venv\Scripts\python.exe'
$WinSW = Join-Path $Root 'packaging\tools\WinSW-x64.exe'
$IsccCandidates = @(
    (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'),
    (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe')
)

Set-Location $Root

if (-not (Test-Path $Python)) {
    throw 'Missing .venv. Run: uv venv --python 3.14'
}

Write-Host '[1/7] Installing locked runtime and build dependencies...'
uv pip install --python $Python -r requirements.txt
uv pip install --python $Python -r requirements-build.txt

Write-Host '[2/7] Validating migrations, tests, and static files...'
& $Python manage.py check
if ($LASTEXITCODE -ne 0) { throw 'Django system check failed.' }
& $Python manage.py makemigrations --check --dry-run
if ($LASTEXITCODE -ne 0) { throw 'Model changes are missing a committed migration.' }
& $Python manage.py test core --verbosity 1
if ($LASTEXITCODE -ne 0) { throw 'Core tests failed.' }
& $Python manage.py collectstatic --noinput --clear
if ($LASTEXITCODE -ne 0) { throw 'Static file collection failed.' }

Write-Host '[3/7] Downloading the pinned WinSW service wrapper...'
if (-not (Test-Path $WinSW)) {
    New-Item -ItemType Directory -Force (Split-Path $WinSW) | Out-Null
    Invoke-WebRequest `
        -Uri 'https://github.com/winsw/winsw/releases/download/v2.12.0/WinSW-x64.exe' `
        -OutFile $WinSW `
        -UseBasicParsing
}

Write-Host '[4/7] Building the PyInstaller one-directory application...'
Remove-Item build, dist -Recurse -Force -ErrorAction SilentlyContinue
& $Python -m PyInstaller --noconfirm --clean packaging\JalaramCNC.spec
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed.' }

Write-Host '[5/7] Adding the Windows service wrapper...'
Copy-Item $WinSW 'dist\JalaramCNC\JalaramCNCService.exe'
Copy-Item 'packaging\JalaramCNCService.xml' 'dist\JalaramCNC\JalaramCNCService.xml'

Write-Host '[6/7] Locating Inno Setup...'
$Iscc = $IsccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $Iscc) {
    Write-Host 'Installing Inno Setup through winget...'
    winget install --id JRSoftware.InnoSetup --exact --source winget --silent --accept-package-agreements --accept-source-agreements
    $Iscc = $IsccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}
if (-not $Iscc) {
    throw 'Inno Setup 6 was not found. Install it, then rerun this script.'
}

Write-Host '[7/7] Compiling the single Windows installer...'
& $Iscc "/DMyAppVersion=$Version" 'packaging\installer.iss'
if ($LASTEXITCODE -ne 0) { throw 'Inno Setup compilation failed.' }

$Installer = Join-Path $Root 'packaging\output\JalaramCNC-Setup.exe'
Write-Host ''
Write-Host "Installer ready: $Installer" -ForegroundColor Green
Write-Host 'Send only this EXE to the destination laptop.'