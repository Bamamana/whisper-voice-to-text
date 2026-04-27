param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('ensure-python', 'ensure-ffmpeg', 'ensure-vcredist', 'resolve-python')]
    [string]$Action,

    [string]$AppDir = ''
)

$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

function Test-PythonExecutable {
    param([string]$PythonExe)

    if ([string]::IsNullOrWhiteSpace($PythonExe) -or -not (Test-Path $PythonExe)) {
        return $false
    }

    try {
        & $PythonExe -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" 2>$null
        return $LASTEXITCODE -eq 0
    }
    catch {
        return $false
    }
}

function Get-PythonExecutable {
    $pyCmd = Get-Command py -ErrorAction SilentlyContinue
    if ($null -ne $pyCmd) {
        try {
            $resolved = (& py -3 -c "import sys; print(sys.executable)" 2>$null | Select-Object -First 1).Trim()
            if (Test-PythonExecutable $resolved) {
                return $resolved
            }
        }
        catch {
        }
    }

    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($null -ne $pythonCmd) {
        try {
            $resolved = (& python -c "import sys; print(sys.executable)" 2>$null | Select-Object -First 1).Trim()
            if (Test-PythonExecutable $resolved) {
                return $resolved
            }
        }
        catch {
        }
    }

    $searchRoots = @(
        (Join-Path $env:LocalAppData 'Programs\Python'),
        (Join-Path $env:ProgramFiles 'Python'),
        (Join-Path ${env:ProgramFiles(x86)} 'Python')
    ) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) -and (Test-Path $_) }

    foreach ($root in $searchRoots) {
        $candidate = Get-ChildItem -Path $root -Filter python.exe -Recurse -ErrorAction SilentlyContinue |
            Sort-Object FullName -Descending |
            Select-Object -ExpandProperty FullName
        foreach ($pythonExe in $candidate) {
            if (Test-PythonExecutable $pythonExe) {
                return $pythonExe
            }
        }
    }

    return $null
}

function Download-File {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,

        [Parameter(Mandatory = $true)]
        [string]$Destination
    )

    Invoke-WebRequest -Uri $Url -OutFile $Destination -UseBasicParsing
}

function Ensure-PythonInstalled {
    $pythonExe = Get-PythonExecutable
    if ($pythonExe) {
        return $pythonExe
    }

    $downloadCandidates = @(
        'https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe',
        'https://www.python.org/ftp/python/3.11.11/python-3.11.11-amd64.exe'
    )

    $tempDir = Join-Path $env:TEMP 'whisper-vtt-bootstrap'
    New-Item -ItemType Directory -Force -Path $tempDir | Out-Null

    $installerPath = Join-Path $tempDir 'python-installer.exe'
    $downloaded = $false
    foreach ($url in $downloadCandidates) {
        try {
            Download-File -Url $url -Destination $installerPath
            $downloaded = $true
            break
        }
        catch {
        }
    }

    if (-not $downloaded) {
        throw 'Unable to download Python installer from python.org.'
    }

    $arguments = @(
        '/quiet',
        'InstallAllUsers=0',
        'PrependPath=1',
        'Include_launcher=1',
        'AssociateFiles=0',
        'Shortcuts=0',
        'Include_test=0',
        'Include_tcltk=1',
        'Include_pip=1',
        'Include_doc=0',
        'Include_dev=0',
        'CompileAll=0'
    )

    $process = Start-Process -FilePath $installerPath -ArgumentList $arguments -PassThru -Wait
    if ($process.ExitCode -ne 0) {
        throw "Python installer exited with code $($process.ExitCode)."
    }

    $pythonExe = Get-PythonExecutable
    if (-not $pythonExe) {
        throw 'Python installation completed, but Python 3.11+ could not be located afterwards.'
    }

    return $pythonExe
}

function Ensure-FFmpegInstalled {
    param([string]$BaseDir)

    $ffmpegCmd = Get-Command ffmpeg -ErrorAction SilentlyContinue
    if ($null -ne $ffmpegCmd) {
        return (Split-Path -Parent $ffmpegCmd.Source)
    }

    if ([string]::IsNullOrWhiteSpace($BaseDir)) {
        throw 'AppDir is required when ensuring FFmpeg.'
    }

    $targetBin = Join-Path $BaseDir 'tools\ffmpeg\bin'
    if (Test-Path (Join-Path $targetBin 'ffmpeg.exe')) {
        return $targetBin
    }

    $tempDir = Join-Path $env:TEMP 'whisper-vtt-bootstrap'
    $downloadDir = Join-Path $tempDir 'ffmpeg'
    $zipPath = Join-Path $downloadDir 'ffmpeg.zip'
    $extractDir = Join-Path $downloadDir 'extract'

    New-Item -ItemType Directory -Force -Path $downloadDir | Out-Null
    if (Test-Path $extractDir) {
        Remove-Item -Path $extractDir -Recurse -Force
    }

    Download-File -Url 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' -Destination $zipPath
    Expand-Archive -Path $zipPath -DestinationPath $extractDir -Force

    $ffmpegExe = Get-ChildItem -Path $extractDir -Filter ffmpeg.exe -Recurse -ErrorAction SilentlyContinue |
        Select-Object -First 1 -ExpandProperty FullName
    if (-not $ffmpegExe) {
        throw 'FFmpeg download completed, but ffmpeg.exe was not found in the extracted archive.'
    }

    $sourceBin = Split-Path -Parent $ffmpegExe
    New-Item -ItemType Directory -Force -Path $targetBin | Out-Null
    Copy-Item -Path (Join-Path $sourceBin '*') -Destination $targetBin -Recurse -Force
    return $targetBin
}

function Ensure-VcRedistributableInstalled {
    $runtimeDll = Join-Path $env:WINDIR 'System32\vcruntime140.dll'
    if (Test-Path $runtimeDll) {
        return $runtimeDll
    }

    $tempDir = Join-Path $env:TEMP 'whisper-vtt-bootstrap'
    New-Item -ItemType Directory -Force -Path $tempDir | Out-Null

    $installerPath = Join-Path $tempDir 'VC_redist.x64.exe'
    Download-File -Url 'https://aka.ms/vs/17/release/vc_redist.x64.exe' -Destination $installerPath

    $process = Start-Process -FilePath $installerPath -ArgumentList '/install', '/quiet', '/norestart' -PassThru -Wait
    if ($process.ExitCode -ne 0 -and $process.ExitCode -ne 3010) {
        throw "Visual C++ Redistributable installer exited with code $($process.ExitCode)."
    }

    if (-not (Test-Path $runtimeDll)) {
        throw 'Visual C++ Redistributable installation completed, but vcruntime140.dll is still missing.'
    }

    return $runtimeDll
}

switch ($Action) {
    'resolve-python' {
        $pythonExe = Get-PythonExecutable
        if ($pythonExe) {
            Write-Output $pythonExe
            exit 0
        }
        exit 1
    }
    'ensure-python' {
        Write-Output (Ensure-PythonInstalled)
        exit 0
    }
    'ensure-ffmpeg' {
        Write-Output (Ensure-FFmpegInstalled -BaseDir $AppDir)
        exit 0
    }
    'ensure-vcredist' {
        Write-Output (Ensure-VcRedistributableInstalled)
        exit 0
    }
}