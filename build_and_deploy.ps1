<#
.SYNOPSIS
    Script de Build e Deploy do projeto Accounting Widget.
.DESCRIPTION
    Este script automatiza a criação do executável via PyInstaller, 
    a geração do instalador via Inno Setup, o commit do código e a 
    criação de uma Release no GitHub com os arquivos compilados.
#>

#----------------------------------------------------------------#
#               CONFIGURAÇÕES (ALTERE SE NECESSÁRIO)             #
#----------------------------------------------------------------#

# Caminho do compilador do Inno Setup
$innoSetupCompiler = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

# Caminhos dos arquivos de configuração e saída
$pyInstallerScript = "main.py"
$appName = "AccountingWidget"
$iconPath = "imgs\sagecont-win.ico"
$innoScript = "instalador.iss"

# Pastas padrão onde os artefatos são gerados (verifique seu .iss)
$pyInstallerOutputDir = "dist\$appName"
$installerOutputDir = "Output"

#----------------------------------------------------------------#
#                           FUNÇÕES                              #
#----------------------------------------------------------------#

function Compile-PyInstaller {
    Write-Host "`n[1/4] Iniciando PyInstaller..." -ForegroundColor Cyan
    try {
        # Comando padrão para gerar interface gráfica (sem console), em uma pasta e com ícone
        pyinstaller --noconfirm --onedir --windowed --icon $iconPath --name $appName $pyInstallerScript
        
        if (Test-Path "$pyInstallerOutputDir\$appName.exe") {
            Write-Host "✅ Executável gerado com sucesso em $pyInstallerOutputDir" -ForegroundColor Green
            return $true
        } else {
            Write-Host "❌ Erro: O executável não foi encontrado." -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "❌ Erro ao rodar o PyInstaller: $_" -ForegroundColor Red
        return $false
    }
}

function Compile-InnoSetup {
    Write-Host "`n[2/4] Iniciando Inno Setup..." -ForegroundColor Cyan
    if (-Not (Test-Path $innoSetupCompiler)) {
        Write-Host "❌ Erro: Inno Setup não encontrado em $innoSetupCompiler" -ForegroundColor Red
        return $false
    }

    try {
        # Executa o Inno Setup silenciosamente
        $process = Start-Process -FilePath $innoSetupCompiler -ArgumentList "`"$innoScript`"" -Wait -NoNewWindow -PassThru
        
        if ($process.ExitCode -eq 0) {
            Write-Host "✅ Instalador gerado com sucesso na pasta $installerOutputDir" -ForegroundColor Green
            return $true
        } else {
            Write-Host "❌ Erro ao compilar Inno Setup." -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "❌ Erro: $_" -ForegroundColor Red
        return $false
    }
}

function Push-SourceCode {
    param([string]$version)
    Write-Host "`n[3/4] Enviando código fonte para o GitHub..." -ForegroundColor Cyan
    try {
        git add .
        git commit -m "Release da versão $version"
        git push origin main # Altere 'main' para o nome da sua branch principal se necessário
        Write-Host "✅ Código fonte enviado com sucesso!" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "❌ Falha ao enviar código para o GitHub. (Verifique se não há mudanças pendentes ou conflitos)." -ForegroundColor Yellow
        return $false
    }
}

function Create-GitHubRelease {
    param([string]$version)
    Write-Host "`n[4/4] Criando Release no GitHub e anexando arquivos..." -ForegroundColor Cyan
    
    # Procura o arquivo gerado pelo Inno Setup (Ex: AccountingWidget_Setup.exe)
    # Adapte o filtro conforme o nome configurado no seu instalador.iss
    $installerFile = Get-ChildItem -Path $installerOutputDir -Filter "*.exe" | Select-Object -First 1
    
    if (-Not $installerFile) {
        Write-Host "❌ Erro: Instalador não encontrado na pasta Output." -ForegroundColor Red
        return $false
    }

    try {
        # Usa o GitHub CLI para criar a release e fazer upload do instalador
        gh release create $version $installerFile.FullName --title "Versão $version" --notes "Atualização gerada automaticamente. Baixe o arquivo .exe abaixo para instalar."
        
        Write-Host "✅ Release criada com sucesso! Verifique seu repositório no GitHub." -ForegroundColor Green
        return $true
    } catch {
        Write-Host "❌ Erro ao criar Release no GitHub. Verifique se o GitHub CLI (gh) está instalado e autenticado (gh auth login)." -ForegroundColor Red
        return $false
    }
}

#----------------------------------------------------------------#
#                           MENU PRINCIPAL                       #
#----------------------------------------------------------------#

Clear-Host
Write-Host "=========================================" -ForegroundColor Magenta
Write-Host "  BUILD & DEPLOY - ACCOUNTING WIDGET     " -ForegroundColor Magenta
Write-Host "=========================================" -ForegroundColor Magenta
Write-Host "1. Gerar Apenas o Executável (.exe)"
Write-Host "2. Gerar Executável + Instalador"
Write-Host "3. Fluxo Completo (Build + Commit + GitHub Release)"
Write-Host "q. Sair"
Write-Host "-----------------------------------------"

$choice = Read-Host "Escolha uma opção"

switch ($choice) {
    "1" {
        Compile-PyInstaller
    }
    "2" {
        if (Compile-PyInstaller) {
            Compile-InnoSetup
        }
    }
    "3" {
        $version = Read-Host "Digite a tag da versão (Ex: v1.0.0)"
        if ([string]::IsNullOrWhiteSpace($version)) {
            Write-Host "Operação cancelada. A versão é obrigatória para o GitHub Release." -ForegroundColor Yellow
            exit
        }

        if (Compile-PyInstaller) {
            if (Compile-InnoSetup) {
                Push-SourceCode -version $version
                Create-GitHubRelease -version $version
            }
        }
    }
    "q" {
        Write-Host "Saindo..."
        exit
    }
    default {
        Write-Host "Opção inválida." -ForegroundColor Red
    }
}

Write-Host "`nProcesso finalizado. Pressione Enter para fechar."
Read-Host