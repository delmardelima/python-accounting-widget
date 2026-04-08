"""
SageCont-Win — Widget de Tarefas para Escritório de Contabilidade.
Entry point da aplicação.
"""
import sys
import logging
import os
import winreg

# --- Configuração de Caminhos Profissional ---
if getattr(sys, 'frozen', False):
    app_data_path = os.path.join(os.getenv('APPDATA'), "Sagecont-Win")
else:
    app_data_path = os.path.dirname(os.path.abspath(__file__))

# Garante que a pasta exista antes de tentar criar o arquivo
if not os.path.exists(app_data_path):
    os.makedirs(app_data_path)

log_file = os.path.join(app_data_path, "sagecont_error.log")

formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s — %(message)s")

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
root_logger.addHandler(console_handler)

file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setLevel(logging.CRITICAL)
file_handler.setFormatter(formatter)
root_logger.addHandler(file_handler)

logger = logging.getLogger(__name__)

def configurar_inicializacao_automatica():
    """Garante que o executável esteja na chave de 'Run' do Registro do Windows."""
    if not getattr(sys, 'frozen', False):
        return

    app_name = "Sagecont-Win"
    exe_path = f'"{sys.executable}"'
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"

    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
        
        try:
            valor_atual, _ = winreg.QueryValueEx(key, app_name)
        except FileNotFoundError:
            valor_atual = None

        if valor_atual != exe_path:
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, exe_path)
            logger.info("Inicialização automática configurada no Registro.")
        
        winreg.CloseKey(key)
    except Exception as e:
        logger.error(f"Não foi possível configurar inicialização automática: {e}")

def main():
    from PyQt6.QtWidgets import QApplication

    from app.config import Config
    from app.database import Database
    from app.api_client import ApiClient
    from app.sync_worker import SyncWorker
    from app.ui.main_widget import WidgetTarefasModerno
    from app.ui.tray_icon import AppTrayIcon

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Mantém aberto ao fechar janela principal

    # Infraestrutura
    config = Config()
    configurar_inicializacao_automatica()
    db = Database()
    api = ApiClient(
        base_url=config.get("api", "base_url"),
        api_key=config.get("api", "api_key")
    )

    # Widget principal
    widget = WidgetTarefasModerno(db, config)
    widget.aplicar_flags_janela()

    # Tray Icon
    tray_icon = AppTrayIcon(widget, app)
    tray_icon.show()

    # Sincronização em background
    intervalo = config.getint("api", "sync_interval_seconds", fallback=30)
    sync = SyncWorker(db, api, intervalo)
    sync.dados_atualizados.connect(widget.refresh_do_sync)
    # Suporte futuro a notificações emitidas pelo SyncWorker
    if hasattr(sync, "notification_ready"):
        sync.notification_ready.connect(tray_icon.mostrar_notificacao)
    sync.start()

    logger.info("Widget iniciado com sucesso.")
    codigo = app.exec()

    # Encerramento limpo
    sync.parar()
    db.fechar()
    logger.info("Aplicação encerrada.")
    sys.exit(codigo)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        #logger.critical("Erro fatal: %s", e, exc_info=True)
        logger.critical("ERRO FATAL NA INICIALIZAÇÃO: %s", e, exc_info=True)
        
        try:
            from PyQt6.QtWidgets import QApplication, QMessageBox
            temp_app = QApplication.instance() or QApplication(sys.argv)
            QMessageBox.critical(None, "Erro de Inicialização", 
                               f"O aplicativo não pôde ser iniciado.\n\nErro: {e}\n\nVerifique o arquivo sagecont_debug.log")
        except:
            pass
        sys.exit(1)