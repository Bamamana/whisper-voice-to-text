param(
    [string]$StageDir = '',
    [string[]]$Models = @('base')
)

$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($StageDir)) {
    $StageDir = Join-Path $rootDir 'build\offline-v3-stage'
}

$bootstrapScript = Join-Path $rootDir 'bootstrap_windows.ps1'
$v3Dir = Join-Path $rootDir 'v3_auto_form_filler'
$venvPython = Join-Path $v3Dir '.venv\Scripts\python.exe'
$stageV3Dir = Join-Path $StageDir 'v3_auto_form_filler'
$stagePythonDir = Join-Path $StageDir 'python-runtime'
$stageFfmpegDir = Join-Path $StageDir 'tools\ffmpeg'
$stageRedistDir = Join-Path $StageDir 'redist'
$vcRedistPath = Join-Path $stageRedistDir 'VC_redist.x64.exe'

function Invoke-Robocopy {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Source,

        [Parameter(Mandatory = $true)]
        [string]$Destination,

        [string[]]$ExtraArgs = @()
    )

    New-Item -ItemType Directory -Force -Path $Destination | Out-Null

    $arguments = @($Source, $Destination, '/MIR', '/R:1', '/W:1', '/NFL', '/NDL', '/NJH', '/NJS', '/NP') + $ExtraArgs
    $process = Start-Process -FilePath 'robocopy.exe' -ArgumentList $arguments -PassThru -Wait -NoNewWindow
    if ($process.ExitCode -gt 7) {
        throw "robocopy failed for $Source with exit code $($process.ExitCode)."
    }
}

function Get-PreparedPythonExecutable {
    $pythonExe = (& $bootstrapScript -Action ensure-python | Select-Object -First 1).Trim()
    if ([string]::IsNullOrWhiteSpace($pythonExe) -or -not (Test-Path $pythonExe)) {
        throw 'Python 3.11 or newer could not be prepared for the V3 offline installer.'
    }

    return $pythonExe
}

function Ensure-V3VirtualEnvironment {
    if (Test-Path $venvPython) {
        return
    }

    Write-Host 'Preparing the V3 virtual environment...'
    $installer = Join-Path $v3Dir 'install_windows_v3.bat'
    $process = Start-Process -FilePath $installer -WorkingDirectory $v3Dir -PassThru -Wait -NoNewWindow
    if ($process.ExitCode -ne 0) {
        throw "install_windows_v3.bat failed with exit code $($process.ExitCode)."
    }

    if (-not (Test-Path $venvPython)) {
        throw 'The V3 virtual environment is still missing after running install_windows_v3.bat.'
    }
}

function Ensure-FfmpegDirectory {
    $ffmpegBinDir = (& $bootstrapScript -Action ensure-ffmpeg -AppDir $rootDir | Select-Object -First 1).Trim()
    if ([string]::IsNullOrWhiteSpace($ffmpegBinDir) -or -not (Test-Path (Join-Path $ffmpegBinDir 'ffmpeg.exe'))) {
        throw 'FFmpeg could not be prepared for the V3 offline installer.'
    }

    return Split-Path -Parent $ffmpegBinDir
}

function Ensure-VcRedistInstaller {
    New-Item -ItemType Directory -Force -Path $stageRedistDir | Out-Null

    if (Test-Path $vcRedistPath) {
        return
    }

    Write-Host 'Downloading Microsoft Visual C++ Redistributable...'
    Invoke-WebRequest -Uri 'https://aka.ms/vs/17/release/vc_redist.x64.exe' -OutFile $vcRedistPath -UseBasicParsing
}

function Copy-BundledPythonRuntime {
    param([string]$PythonExe)

    $pythonHome = Split-Path -Parent $PythonExe
    if (-not (Test-Path (Join-Path $pythonHome 'pythonw.exe'))) {
        throw "The Python runtime at $pythonHome is incomplete."
    }

    Write-Host 'Copying bundled Python runtime...'
    Invoke-Robocopy -Source $pythonHome -Destination $stagePythonDir -ExtraArgs @('/XD', (Join-Path $pythonHome 'Lib\site-packages'), (Join-Path $pythonHome 'Tools'), '__pycache__', '/XF', '*.pyc')
}

function Copy-V3Application {
    Write-Host 'Copying V3 application payload...'
    Invoke-Robocopy -Source $v3Dir -Destination $stageV3Dir -ExtraArgs @('/XD', (Join-Path $v3Dir 'templates'), (Join-Path $v3Dir 'model-cache'), '__pycache__', '/XF', '.gemini-api-key', '.gmail-token.json', 'gmail-credentials.json', '*.pyc')
}

function Copy-FfmpegPayload {
    param([string]$FfmpegRoot)

    Write-Host 'Copying bundled FFmpeg...'
    Invoke-Robocopy -Source $FfmpegRoot -Destination $stageFfmpegDir -ExtraArgs @('/XD', '__pycache__', '/XF', '*.log')
}

function Ensure-OfflineModels {
    param([string[]]$ModelNames)

    if ($ModelNames.Count -eq 0) {
        return
    }

    $modelCacheDir = Join-Path $stageV3Dir 'model-cache'
    New-Item -ItemType Directory -Force -Path $modelCacheDir | Out-Null

    foreach ($modelName in $ModelNames) {
        Write-Host "Downloading Whisper model '$modelName' into the offline payload..."
        $env:HF_HUB_DISABLE_SYMLINKS_WARNING = '1'
        $downloadCommand = "from faster_whisper import WhisperModel; WhisperModel('$modelName', device='cpu', compute_type='int8', download_root=r'$modelCacheDir')"
        & $venvPython -c $downloadCommand
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to pre-download Whisper model '$modelName'."
        }
    }
}

Write-Host 'Preparing the V3 offline installer payload...'
Ensure-V3VirtualEnvironment

$pythonExe = Get-PreparedPythonExecutable
$ffmpegRoot = Ensure-FfmpegDirectory

if (Test-Path $StageDir) {
    Remove-Item -Path $StageDir -Recurse -Force
}

New-Item -ItemType Directory -Force -Path $StageDir | Out-Null

Copy-V3Application
Copy-BundledPythonRuntime -PythonExe $pythonExe
Copy-FfmpegPayload -FfmpegRoot $ffmpegRoot
Ensure-VcRedistInstaller
Ensure-OfflineModels -ModelNames $Models

Write-Host ''
Write-Host 'V3 offline payload prepared at:'
Write-Host "  $StageDir"