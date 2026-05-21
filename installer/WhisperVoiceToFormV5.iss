#define MyAppName "Whisper Voice To Form V5"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "Bamamana"
#define MyAppSubDir "v5_legal_assistant"
#define MyAppLauncherScript "windows_launch_v5.pyw"
#define MyAppPythonw "{app}\v5_legal_assistant\.venv\Scripts\pythonw.exe"

[Setup]
AppId={{0F7B2F42-86B7-49F1-BD65-58DE4C8F60A4}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\Whisper Voice To Form V5
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist\windows-installer-v5
OutputBaseFilename=WhisperVoiceToFormV5Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
ChangesEnvironment=no
UninstallDisplayIcon={sys}\shell32.dll

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\bootstrap_windows.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\{#MyAppSubDir}\*"; DestDir: "{app}\{#MyAppSubDir}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: ".venv\*,model-cache\*,templates\*,matter-profiles\*,__pycache__\*,.gemini-api-key,.gmail-token.json,gmail-credentials.json,.v5-drive-settings.json,*.pyc"

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{#MyAppPythonw}"; Parameters: """{app}\{#MyAppSubDir}\{#MyAppLauncherScript}"""; WorkingDir: "{app}\{#MyAppSubDir}"; IconFilename: "{sys}\shell32.dll"; IconIndex: 22
Name: "{autodesktop}\{#MyAppName}"; Filename: "{#MyAppPythonw}"; Parameters: """{app}\{#MyAppSubDir}\{#MyAppLauncherScript}"""; WorkingDir: "{app}\{#MyAppSubDir}"; IconFilename: "{sys}\shell32.dll"; IconIndex: 22; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppSubDir}\install_windows_v5.bat"; WorkingDir: "{app}\{#MyAppSubDir}"; StatusMsg: "Installing dependencies and preparing the V5 app..."; Flags: waituntilterminated
Filename: "{#MyAppPythonw}"; Parameters: """{app}\{#MyAppSubDir}\{#MyAppLauncherScript}"""; Description: "Launch {#MyAppName}"; WorkingDir: "{app}\{#MyAppSubDir}"; Flags: postinstall nowait skipifsilent unchecked
