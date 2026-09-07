#define MyAppName "Jalaram CNC"
#ifndef MyAppVersion
  #define MyAppVersion "1.1.0"
#endif
#define MyAppPublisher "Jalaram CNC Art & Craft"
#define MyAppExeName "JalaramCNC.exe"
#define MyServiceExeName "JalaramCNCService.exe"

[Setup]
AppId={{B0C97A31-49E9-4F38-9377-31969E8D0F0E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Jalaram CNC
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
PrivilegesRequired=admin
OutputDir=output
OutputBaseFilename=JalaramCNC-Setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
SetupLogging=yes
UsePreviousAppDir=yes
CloseApplications=yes
RestartApplications=no
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}

[Dirs]
Name: "{commonappdata}\JalaramCNC"; Permissions: users-modify
Name: "{commonappdata}\JalaramCNC\logs"; Permissions: users-modify
Name: "{commonappdata}\JalaramCNC\backups\daily"; Permissions: users-modify
Name: "{commonappdata}\JalaramCNC\backups\monthly"; Permissions: users-modify
Name: "{commonappdata}\JalaramCNC\media"; Permissions: users-modify

[Files]
Source: "..\dist\JalaramCNC\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "C:\JalaramCNC\db.sqlite3"; DestDir: "{commonappdata}\JalaramCNC"; DestName: "db.sqlite3"; Flags: external skipifsourcedoesntexist onlyifdoesntexist uninsneveruninstall

[INI]
Filename: "{app}\Jalaram CNC.url"; Section: "InternetShortcut"; Key: "URL"; String: "http://127.0.0.1:8000"

[Icons]
Name: "{commondesktop}\Jalaram CNC"; Filename: "{app}\Jalaram CNC.url"; WorkingDir: "{app}"
Name: "{group}\Jalaram CNC"; Filename: "{app}\Jalaram CNC.url"; WorkingDir: "{app}"
Name: "{group}\Uninstall Jalaram CNC"; Filename: "{uninstallexe}"

[Run]
Filename: "http://127.0.0.1:8000"; Description: "Open Jalaram CNC"; Flags: shellexec postinstall skipifsilent nowait

[UninstallRun]
Filename: "{app}\{#MyServiceExeName}"; Parameters: "stop"; Flags: runhidden waituntilterminated skipifdoesntexist; RunOnceId: "StopService"
Filename: "{app}\{#MyServiceExeName}"; Parameters: "uninstall"; Flags: runhidden waituntilterminated skipifdoesntexist; RunOnceId: "RemoveService"
Filename: "{sys}\schtasks.exe"; Parameters: "/Delete /F /TN ""JalaramCNC_DailyBackup"""; Flags: runhidden waituntilterminated; RunOnceId: "RemoveBackupTask"
Filename: "{sys}\schtasks.exe"; Parameters: "/Delete /F /TN ""JalaramCNC_StartupBackup"""; Flags: runhidden waituntilterminated; RunOnceId: "RemoveLegacyStartupTask"

[Code]
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
  ExistingApp: String;
begin
  Exec(ExpandConstant('{sys}\sc.exe'), 'stop JalaramCNCService', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  ExistingApp := ExpandConstant('{app}\{#MyAppExeName}');
  if FileExists(ExistingApp) then
  begin
    if (not Exec(ExistingApp, 'backup', '', SW_HIDE, ewWaitUntilTerminated, ResultCode)) or (ResultCode <> 0) then
    begin
      Result := 'The existing database could not be backed up. Installation was cancelled to protect your data.';
      exit;
    end;
  end;
  Exec(ExpandConstant('{sys}\sc.exe'), 'delete JalaramCNCService', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec(ExpandConstant('{sys}\schtasks.exe'), '/Delete /F /TN "JalaramCNC_DailyBackup"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec(ExpandConstant('{sys}\schtasks.exe'), '/Delete /F /TN "JalaramCNC_StartupBackup"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := '';
end;

procedure RunRequired(const FileName, Parameters, StatusText: String);
var
  ResultCode: Integer;
begin
  WizardForm.StatusLabel.Caption := StatusText;
  if (not Exec(FileName, Parameters, '', SW_HIDE, ewWaitUntilTerminated, ResultCode)) or (ResultCode <> 0) then
    RaiseException(Format('%s failed with exit code %d.', [StatusText, ResultCode]));
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  AppExe: String;
  ServiceExe: String;
begin
  if CurStep <> ssPostInstall then
    exit;

  AppExe := ExpandConstant('{app}\{#MyAppExeName}');
  ServiceExe := ExpandConstant('{app}\{#MyServiceExeName}');

  RunRequired(AppExe, 'init', 'Preparing the Jalaram CNC database');
  RunRequired(AppExe, 'backup', 'Creating the initial verified backup');
  RunRequired(ServiceExe, 'install', 'Installing the automatic Windows service');
  RunRequired(ExpandConstant('{sys}\sc.exe'), 'config JalaramCNCService start= auto', 'Configuring automatic startup');
  RunRequired(ExpandConstant('{sys}\sc.exe'), 'failure JalaramCNCService reset= 3600 actions= restart/5000/restart/15000/restart/30000', 'Configuring service recovery');
  RunRequired(ServiceExe, 'start', 'Starting Jalaram CNC');
  RunRequired(AppExe, 'wait-ready', 'Verifying Jalaram CNC is ready');
end;