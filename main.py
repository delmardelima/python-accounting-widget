"""
SageCont-Win — Widget de Tarefas para Escritório de Contabilidade.
Entry point da aplicação.
"""
import sys
import logging

# --- Configuração de Logs ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


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
        logger.critical("Erro fatal: %s", e, exc_info=True)