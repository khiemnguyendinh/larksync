; ─────────────────────────────────────────────────────────────────────
; LarkSync — Windows installer (Inno Setup 6.3+)
;   python build_windows.py
;   iscc /DMyAppVersion=1.1.0 installer\windows\LarkSync.iss
; Output: dist\LarkSync-Setup-<version>.exe
; Per-user install (no administrator rights needed): LarkSync keeps its data in
; %APPDATA% and its "launch at login" entry in HKCU, so nothing is machine-wide.
; ─────────────────────────────────────────────────────────────────────
#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif
#define MyAppName "LarkSync"
#define MyAppExe  "LarkSync.exe"

[Setup]
AppId={{7B0C9E5A-3C1D-4F5B-9A57-4C4B1C0A1F11}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher=Kstudy Academy
AppPublisherURL=https://www.kstudy.edu.vn
AppSupportURL=https://github.com/khiemnguyendinh/larksync/issues
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\..\dist
OutputBaseFilename=LarkSync-Setup-{#MyAppVersion}
SetupIconFile=..\..\assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExe}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; Flags: unchecked
Name: "startup";     Description: "Start LarkSync when I &sign in to Windows"; Flags: unchecked

[Files]
Source: "..\..\dist\LarkSync\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"
Name: "{autodesktop}\{#MyAppName}";  Filename: "{app}\{#MyAppExe}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; \
  ValueName: "{#MyAppName}"; ValueData: """{app}\{#MyAppExe}"""; Tasks: startup; Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#MyAppExe}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
// The user may have switched "Launch at Login" on from LarkSync's own Settings;
// remove that entry too so uninstalling leaves nothing pointing at a missing exe.
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
    RegDeleteValue(HKEY_CURRENT_USER, 'Software\Microsoft\Windows\CurrentVersion\Run', '{#MyAppName}');
end;
