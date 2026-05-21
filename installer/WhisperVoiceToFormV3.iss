#define MyAppName "Whisper Voice To Form V3"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "Bamamana"
#define MyAppSubDir "v3_auto_form_filler"
#define MyAppLauncherScript "windows_launch_v3.pyw"
#define MyAppPythonw "{app}\v3_auto_form_filler\.venv\Scripts\pythonw.exe"

[Setup]
AppId={{6E308780-8C1B-4AE0-8B60-FA7348F31734}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\Whisper Voice To Form V3
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist\windows-installer-v3
OutputBaseFilename=WhisperVoiceToFormV3Setup
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
Source: "..\{#MyAppSubDir}\*"; DestDir: "{app}\{#MyAppSubDir}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: ".venv\*,model-cache\*,templates\*,__pycache__\*,.gemini-api-key,*.pyc"

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{#MyAppPythonw}"; Parameters: """{app}\{#MyAppSubDir}\{#MyAppLauncherScript}"""; WorkingDir: "{app}\{#MyAppSubDir}"; IconFilename: "{sys}\shell32.dll"; IconIndex: 22
Name: "{autodesktop}\{#MyAppName}"; Filename: "{#MyAppPythonw}"; Parameters: """{app}\{#MyAppSubDir}\{#MyAppLauncherScript}"""; WorkingDir: "{app}\{#MyAppSubDir}"; IconFilename: "{sys}\shell32.dll"; IconIndex: 22; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppSubDir}\install_windows_v3.bat"; WorkingDir: "{app}\{#MyAppSubDir}"; StatusMsg: "Installing dependencies and preparing the V3 app..."; Flags: waituntilterminated
Filename: "{#MyAppPythonw}"; Parameters: """{app}\{#MyAppSubDir}\{#MyAppLauncherScript}"""; Description: "Launch {#MyAppName}"; WorkingDir: "{app}\{#MyAppSubDir}"; Flags: postinstall nowait skipifsilent unchecked
