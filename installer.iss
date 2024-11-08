#define MyAppName "TheFixersService"
#define MyAppVersion "0.01"
#define MyAppPublisher "FranciscoOVelazquez99"
#define MyAppURL "https://github.com/FranciscoOVelazquez99/TheFixersServiceAPP-redone"
#define MyAppExeName "TheFixersService.exe"

[Setup]
AppId={{D4A1C3F1-2F7C-4C3B-8E9D-BAC89F1E6A1F}  ;
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
InfoAfterFile=C:\Users\Francisco\Desktop\TheFixersService\README.txt
OutputDir=C:\Users\Francisco\Desktop
OutputBaseFilename={#MyAppName}_Setup
SetupIconFile=C:\Users\Francisco\Desktop\TheFixersService\FixLogo.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
DisableFinishedPage=no
DisableProgramGroupPage=yes
PrivilegesRequired=admin

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
Source: "C:\Users\Francisco\Desktop\TheFixersService\dist\TheFixersService.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\Francisco\Desktop\TheFixersService\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\Francisco\Desktop\TheFixersService\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\Francisco\Desktop\TheFixersService\app\templates\*"; DestDir: "{app}\app\templates"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "C:\Users\Francisco\Desktop\TheFixersService\app\static\*"; DestDir: "{app}\static"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "C:\Users\Francisco\Desktop\TheFixersService\FixLogo.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Iniciar {#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\FixLogo.ico"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\FixLogo.ico"
Name: "{group}\Detener {#MyAppName}"; Filename: "{app}\stop_app.vbs"; IconFilename: "{sys}\shell32.dll"; IconIndex: 131
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

[Dirs]
Name: "{app}\static"
Name: "{app}\static\uploads"
Name: "{app}\static\uploads\avatars"; Permissions: users-modify
Name: "{app}\static\uploads\equipos"; Permissions: users-modify
Name: "{app}\static\PDFs"; Permissions: users-modify

[Code]
procedure CreateStopScript();
var
  StopContent: String;
  StopFilePath: String;
begin
  StopContent := 'Set objWMIService = GetObject("winmgmts:\\.\root\cimv2")' + #13#10 +
                 'Set colProcessList = objWMIService.ExecQuery("Select * from Win32_Process Where Name = ''TheFixersService.exe''")' + #13#10 +
                 'For Each objProcess in colProcessList' + #13#10 +
                 '    objProcess.Terminate()' + #13#10 +
                 'Next';
  
  StopFilePath := ExpandConstant('{app}\stop_app.vbs');
  
  SaveStringToFile(StopFilePath, StopContent, False);
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  UploadDirs: array of string;
  I: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    CreateStopScript();
    
    // Asegurar permisos de escritura en directorios de uploads
    UploadDirs := [
      ExpandConstant('{app}\static\uploads'),
      ExpandConstant('{app}\static\uploads\avatars'),
      ExpandConstant('{app}\static\uploads\equipos'),
      ExpandConstant('{app}\static\PDFs')
    ];
    
    for I := 0 to GetArrayLength(UploadDirs) - 1 do
    begin
      if not DirExists(UploadDirs[I]) then
        CreateDir(UploadDirs[I]);
      // Dar permisos completos a Users
      Exec('icacls.exe', '"' + UploadDirs[I] + '" /grant Users:(OI)(CI)F', '', SW_HIDE, ewWaitUntilTerminated, I);
    end;
  end;
end;

[UninstallDelete]
Type: files; Name: "{app}\stop_app.vbs"
