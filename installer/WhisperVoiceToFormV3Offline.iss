#define MyAppName "Whisper Voice To Form V3 Offline"
#define MyAppVersion "0.1.1"
#define MyAppPublisher "Bamamana"
#define MyAppSubDir "v3_auto_form_filler"
#define MyAppLauncherScript "windows_launch_v3.pyw"
#ifndef OfflineStageDir
	#error OfflineStageDir compile define is required.
#endif
#define MyAppPythonw "{app}\python-runtime\pythonw.exe"

[Setup]
AppId={{8F6B51E2-5126-4E53-94A8-0B6878F75AE5}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\Whisper Voice To Form V3 Offline
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist\windows-installer-v3-offline
OutputBaseFilename=WhisperVoiceToFormV3OfflineSetup
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
Source: "{#OfflineStageDir}\python-runtime\*"; DestDir: "{app}\python-runtime"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#OfflineStageDir}\tools\ffmpeg\*"; DestDir: "{app}\tools\ffmpeg"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#OfflineStageDir}\redist\VC_redist.x64.exe"; DestDir: "{app}\redist"; Flags: ignoreversion
Source: "{#OfflineStageDir}\{#MyAppSubDir}\*"; DestDir: "{app}\{#MyAppSubDir}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "__pycache__\*,*.pyc"

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{#MyAppPythonw}"; Parameters: """{app}\{#MyAppSubDir}\{#MyAppLauncherScript}"""; WorkingDir: "{app}\{#MyAppSubDir}"; IconFilename: "{sys}\shell32.dll"; IconIndex: 22
Name: "{autodesktop}\{#MyAppName}"; Filename: "{#MyAppPythonw}"; Parameters: """{app}\{#MyAppSubDir}\{#MyAppLauncherScript}"""; WorkingDir: "{app}\{#MyAppSubDir}"; IconFilename: "{sys}\shell32.dll"; IconIndex: 22; Tasks: desktopicon

[Run]
Filename: "{#MyAppPythonw}"; Parameters: """{app}\{#MyAppSubDir}\{#MyAppLauncherScript}"""; Description: "Launch {#MyAppName}"; WorkingDir: "{app}\{#MyAppSubDir}"; Flags: postinstall nowait skipifsilent unchecked

[Code]
function NeedsVCRedist: Boolean;
begin
	Result := not FileExists(ExpandConstant('{sys}\vcruntime140.dll'));
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
	ResultCode: Integer;
begin
	if CurStep <> ssPostInstall then
		exit;

	if not NeedsVCRedist then
		exit;

	if not Exec(ExpandConstant('{app}\redist\VC_redist.x64.exe'), '/install /quiet /norestart', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
		RaiseException('Failed to launch Microsoft Visual C++ Redistributable installer.');

	if (ResultCode <> 0) and (ResultCode <> 3010) and (ResultCode <> 1638) then
		RaiseException(Format('Microsoft Visual C++ Redistributable installer exited with code %d.', [ResultCode]));
end;
