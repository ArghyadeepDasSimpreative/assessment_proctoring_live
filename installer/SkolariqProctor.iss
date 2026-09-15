[Setup]
AppName=Skolariq Proctor
AppVersion=1.0.0

DefaultDirName={autopf}\Skolariq Proctor
DefaultGroupName=Skolariq Proctor

OutputDir=output
OutputBaseFilename=SkolariqProctorSetup

SetupIconFile=assets\main-icon.ico

PrivilegesRequired=admin

Compression=lzma2
SolidCompression=yes

WizardStyle=modern

UninstallDisplayIcon={app}\SkolariqProctor.exe

ChangesAssociations=yes


[Files]
Source: "..\dist\SkolariqProctor\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs


[Icons]
Name: "{group}\Skolariq Proctor"; Filename: "{app}\SkolariqProctor.exe"

Name: "{autodesktop}\Skolariq Proctor"; Filename: "{app}\SkolariqProctor.exe"


[Registry]

; ---------------------------------------------------------
; Register custom protocol:
;
; skolariq-proctor://launch?token=...
;
; This allows the browser/frontend to launch the
; installed Skolariq Proctor application.
; ---------------------------------------------------------

Root: HKCR; \
Subkey: "skolariq-proctor"; \
ValueType: string; \
ValueName: ""; \
ValueData: "URL:Skolariq Proctor Protocol"; \
Flags: uninsdeletekey

Root: HKCR; \
Subkey: "skolariq-proctor"; \
ValueType: string; \
ValueName: "URL Protocol"; \
ValueData: ""

Root: HKCR; \
Subkey: "skolariq-proctor\DefaultIcon"; \
ValueType: string; \
ValueName: ""; \
ValueData: """{app}\SkolariqProctor.exe"",0"

Root: HKCR; \
Subkey: "skolariq-proctor\shell"; \
ValueType: string; \
ValueName: ""; \
ValueData: ""

Root: HKCR; \
Subkey: "skolariq-proctor\shell\open"; \
ValueType: string; \
ValueName: ""; \
ValueData: ""

Root: HKCR; \
Subkey: "skolariq-proctor\shell\open\command"; \
ValueType: string; \
ValueName: ""; \
ValueData: """{app}\SkolariqProctor.exe"" ""%1"""


[Run]
Filename: "{app}\SkolariqProctor.exe"; \
Description: "Launch Skolariq Proctor"; \
Flags: nowait postinstall skipifsilent