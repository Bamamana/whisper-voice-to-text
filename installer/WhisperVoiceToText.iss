#define MyAppName "Whisper Voice To Text"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Bamamana"
#define MyAppLauncherScript "windows_shortcut_launch.bat"

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
UninstallDisplayIcon={sys}\shell32.dll

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: ".git\*,.venv\*,model-cache\*,dist\*,__pycache__\*,.cache\*,desktop-launch.log,.whisper-profile*.env,*.whisper.txt,tools\ffmpeg\*"

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{cmd}"; Parameters: "/d /c """"{app}\{#MyAppLauncherScript}"""""; WorkingDir: "{app}"; IconFilename: "{sys}\shell32.dll"; IconIndex: 22
Name: "{autodesktop}\{#MyAppName}"; Filename: "{cmd}"; Parameters: "/d /c """"{app}\{#MyAppLauncherScript}"""""; WorkingDir: "{app}"; IconFilename: "{sys}\shell32.dll"; IconIndex: 22; Tasks: desktopicon

[Run]
Filename: "{app}\setup_windows.bat"; Parameters: "auto --skip-shortcut --skip-model-download"; WorkingDir: "{app}"; StatusMsg: "Installing dependencies and preparing the app..."; Flags: waituntilterminated
Filename: "{cmd}"; Parameters: "/d /c """"{app}\{#MyAppLauncherScript}"""""; Description: "Launch {#MyAppName}"; WorkingDir: "{app}"; Flags: postinstall nowait skipifsilent unchecked