#define MyAppName "ASCII-Vibes-Visualizer"
#define MyAppVersion "1.0.0"
#define SourceDir "..\dist\ASCII-Vibes-Visualizer"

[Setup]
AppId={{7D45E108-C10C-4C55-B790-B102AA2A2B87}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
UninstallDisplayIcon={app}\ASCII-Vibes-Visualizer.exe
SetupIconFile=..\ASCII-Vibes-Visualizer.ico
WizardImageFile=wizard-logo.bmp
WizardSmallImageFile=wizard-logo-small.bmp
OutputDir=..\dist\installer
OutputBaseFilename=ASCII-Vibes-Visualizer-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\ASCII-Vibes-Visualizer.exe"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\ASCII-Vibes-Visualizer.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\ASCII-Vibes-Visualizer.exe"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
