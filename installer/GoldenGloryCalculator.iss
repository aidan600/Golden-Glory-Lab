; Inno Setup 7.0.2 script for Golden Glory Calculator.
;
; Packages the already-built portable one-file executable
; (release/GoldenGloryCalculator.exe) into a per-user Windows installer,
; GoldenGloryCalculator-Setup.exe. Build the portable EXE first with
; scripts/build_calculator_exe.py, or run scripts/build_release.ps1 to do
; both steps and compile this script in one command.
;
; Compile directly with:
;   ISCC.exe installer\GoldenGloryCalculator.iss
;
; Deliberately excluded: administrator requirement, services, startup tasks,
; file associations, PATH changes, network access, and an updater.

#define MyAppName "Golden Glory Calculator"
#ifndef MyAppVersion
  #define MyAppVersion "0.1.0"
#endif
#define MyAppPublisher "Golden Glory Lab"
#define MyAppURL "https://github.com/aidan600/Golden-Glory-Lab"
#define MyAppExeName "GoldenGloryCalculator.exe"
#ifndef SourceExePath
  #define SourceExePath "..\release\GoldenGloryCalculator.exe"
#endif
#ifndef OutputDirPath
  #define OutputDirPath "..\release"
#endif

[Setup]
AppId={{8C2DFEEF-1ED9-4084-B7AF-F32A8F5A2300}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
; Per-user install, no administrator requirement. With PrivilegesRequired set
; to lowest, {autopf} resolves to the per-user Programs folder instead of
; Program Files.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DefaultDirName={autopf}\Golden Glory Calculator
DefaultGroupName=Golden Glory Calculator
DisableProgramGroupPage=yes
OutputDir={#OutputDirPath}
OutputBaseFilename=GoldenGloryCalculator-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesInstallIn64BitMode=x64compatible
; No components/tasks beyond the optional desktop shortcut below; no
; services, no scheduled task, no file association, no PATH change.
DisableWelcomePage=no
SetupLogging=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "{#SourceExePath}"; DestDir: "{app}"; DestName: "{#MyAppExeName}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
