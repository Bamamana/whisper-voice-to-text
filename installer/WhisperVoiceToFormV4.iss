#define MyAppName "Whisper Voice To Form V4"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "Bamamana"
#define MyAppSubDir "v4_legal_assistant"
#define MyAppLauncherScript "windows_launch_v4.pyw"
#define MyAppPythonw "{app}\v4_legal_assistant\.venv\Scripts\pythonw.exe"

[Setup]
AppId={{350E2EF7-E814-4D7E-B1E9-A4CB5E562725}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\Whisper Voice To Form V4
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist\windows-installer-v4
OutputBaseFilename=WhisperVoiceToFormV4Setup
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
Source: "..\{#MyAppSubDir}\*"; DestDir: "{app}\{#MyAppSubDir}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: ".venv\*,model-cache\*,templates\*,matter-profiles\*,__pycache__\*,.gemini-api-key,.gmail-token.json,gmail-credentials.json,*.pyc"

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{#MyAppPythonw}"; Parameters: """{app}\{#MyAppSubDir}\{#MyAppLauncherScript}"""; WorkingDir: "{app}\{#MyAppSubDir}"; IconFilename: "{sys}\shell32.dll"; IconIndex: 22
Name: "{autodesktop}\{#MyAppName}"; Filename: "{#MyAppPythonw}"; Parameters: """{app}\{#MyAppSubDir}\{#MyAppLauncherScript}"""; WorkingDir: "{app}\{#MyAppSubDir}"; IconFilename: "{sys}\shell32.dll"; IconIndex: 22; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppSubDir}\install_windows_v4.bat"; WorkingDir: "{app}\{#MyAppSubDir}"; StatusMsg: "Installing dependencies and preparing the V4 app..."; Flags: waituntilterminated
Filename: "{#MyAppPythonw}"; Parameters: """{app}\{#MyAppSubDir}\{#MyAppLauncherScript}"""; Description: "Launch {#MyAppName}"; WorkingDir: "{app}\{#MyAppSubDir}"; Flags: postinstall nowait skipifsilent unchecked
