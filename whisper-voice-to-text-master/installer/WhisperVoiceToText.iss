#define MyAppName "Whisper Voice To Text"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Bamamana"
#define MyAppLauncherScript "windows_launch.pyw"

[Setup]
AppId={{E84E1548-79B7-4E04-8B77-6B2BD54D27B0}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\Whisper Voice To Text
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist\windows-installer
OutputBaseFilename=WhisperVoiceToTextSetup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
ChangesEnvironment=no
UninstallDisplayIcon={app}\.venv\Scripts\pythonw.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked
Name: "predownloadmodels"; Description: "Pre-download tiny, base, and small models"; GroupDescription: "Optional content:"; Flags: unchecked

[Files]
Source: "..\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: ".git\*,.venv\*,model-cache\*,dist\*,__pycache__\*,.cache\*,desktop-launch.log,.whisper-profile*.env,*.whisper.txt"

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\.venv\Scripts\pythonw.exe"; Parameters: """{app}\{#MyAppLauncherScript}"""; WorkingDir: "{app}"; IconFilename: "{sys}\shell32.dll"; IconIndex: 22
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\.venv\Scripts\pythonw.exe"; Parameters: """{app}\{#MyAppLauncherScript}"""; WorkingDir: "{app}"; IconFilename: "{sys}\shell32.dll"; IconIndex: 22; Tasks: desktopicon

[Run]
Filename: "{app}\setup_windows.bat"; Parameters: "auto --skip-shortcut"; WorkingDir: "{app}"; StatusMsg: "Installing dependencies and preparing the app..."; Flags: waituntilterminated
Filename: "{app}\.venv\Scripts\python.exe"; Parameters: """{app}\download_models.py"" tiny base small"; WorkingDir: "{app}"; StatusMsg: "Pre-downloading tiny, base, and small models..."; Flags: waituntilterminated; Tasks: predownloadmodels; Check: FileExists(ExpandConstant('{app}\.venv\Scripts\python.exe'))
Filename: "{app}\.venv\Scripts\pythonw.exe"; Parameters: """{app}\{#MyAppLauncherScript}"""; Description: "Launch {#MyAppName}"; WorkingDir: "{app}"; Flags: postinstall nowait skipifsilent unchecked; Check: FileExists(ExpandConstant('{app}\.venv\Scripts\pythonw.exe'))