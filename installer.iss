[Setup]
AppName=Missionfy
AppVersion=1.0
AppPublisher=Missionfy
AppPublisherURL=https://github.com
DefaultDirName={autopf}\Missionfy
DefaultGroupName=Missionfy
OutputDir=installer_output
OutputBaseFilename=Missionfy_Setup
SetupIconFile=money_mission.ico
UninstallDisplayIcon={app}\Missionfy.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest

[Files]
Source: "dist\Missionfy.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "icon.png"; DestDir: "{app}"; Flags: ignoreversion
Source: "money_mission.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "fonts\*.ttf"; DestDir: "{app}\fonts"; Flags: ignoreversion

[Icons]
Name: "{group}\Missionfy"; Filename: "{app}\Missionfy.exe"; IconFilename: "{app}\money_mission.ico"
Name: "{autodesktop}\Missionfy"; Filename: "{app}\Missionfy.exe"; IconFilename: "{app}\money_mission.ico"; Tasks: desktopicon
Name: "{autostartup}\Missionfy"; Filename: "{app}\Missionfy.exe"; Tasks: startupicon

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na Área de Trabalho"; GroupDescription: "Atalhos:"
Name: "startupicon"; Description: "Iniciar com o Windows"; GroupDescription: "Atalhos:"

[Run]
Filename: "{app}\Missionfy.exe"; Description: "Abrir Missionfy agora"; Flags: nowait postinstall skipifsilent
