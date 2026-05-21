#define MyAppName "Whisper Voice To Form V2"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "Bamamana"
#define MyAppSubDir "v2_gemini_form_filler"
#define MyAppLauncherScript "windows_launch_v2.pyw"
#define MyAppPythonw "{app}\v2_gemini_form_filler\.venv\Scripts\pythonw.exe"

[Setup]
AppId={{49B6A3F7-7CB6-4BB7-8CE3-5C7754656CC4}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\Whisper Voice To Form V2
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist\windows-installer-v2
OutputBaseFilename=WhisperVoiceToFormV2Setup
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
Source: "..\{#MyAppSubDir}\*"; DestDir: "{app}\{#MyAppSubDir}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: ".venv\*,model-cache\*,__pycache__\*,.gemini-api-key,*.pyc"

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{#MyAppPythonw}"; Parameters: """{app}\{#MyAppSubDir}\{#MyAppLauncherScript}"""; WorkingDir: "{app}\{#MyAppSubDir}"; IconFilename: "{sys}\shell32.dll"; IconIndex: 22
Name: "{autodesktop}\{#MyAppName}"; Filename: "{#MyAppPythonw}"; Parameters: """{app}\{#MyAppSubDir}\{#MyAppLauncherScript}"""; WorkingDir: "{app}\{#MyAppSubDir}"; IconFilename: "{sys}\shell32.dll"; IconIndex: 22; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppSubDir}\install_windows_v2.bat"; WorkingDir: "{app}\{#MyAppSubDir}"; StatusMsg: "Installing dependencies and preparing the V2 app..."; Flags: waituntilterminated
Filename: "{#MyAppPythonw}"; Parameters: """{app}\{#MyAppSubDir}\{#MyAppLauncherScript}"""; Description: "Launch {#MyAppName}"; WorkingDir: "{app}\{#MyAppSubDir}"; Flags: postinstall nowait skipifsilent unchecked
