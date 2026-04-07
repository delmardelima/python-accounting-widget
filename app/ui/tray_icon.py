"""
Componente do ícone na bandeja do sistema (System Tray).
"""
import logging
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QStyle
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QIcon
import os

logger = logging.getLogger(__name__)

class AppTrayIcon(QSystemTrayIcon):
    def __init__(self, main_widget, app, parent=None):
        super().__init__(parent)
        self.main_widget = main_widget
        self.app = app
        
        current_dir = os.path.dirname(__file__)
        root_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))
        icon_path = os.path.join(root_dir, "imgs", "sagecont-win.ico")

        if not os.path.exists(icon_path):
            print(f"ERRO: Ícone ainda não encontrado em: {icon_path}")
        else:
            icon = QIcon(icon_path)
            self.setIcon(icon)
        
        self.setToolTip("Sagecont Widget Tarefas")

        # Configurar menu de contexto
        menu = QMenu()

        self.action_exibir = menu.addAction("Exibir Widget")
        self.action_ocultar = menu.addAction("Ocultar Widget")
        menu.addSeparator()
        action_sair = menu.addAction("Sair do Sagecont")

        self.action_exibir.triggered.connect(self._exibir_widget)
        self.action_ocultar.triggered.connect(self._ocultar_widget)
        action_sair.triggered.connect(self._sair_app)

        self.setContextMenu(menu)
        self.activated.connect(self._on_activated)

        # Atualizar visibilidade das ações
        self._atualizar_acoes()

    def _exibir_widget(self):
        self.main_widget.show()
        self.main_widget.activateWindow()
        self.main_widget.raise_()
        self._atualizar_acoes()

    def _ocultar_widget(self):
        self.main_widget.hide()
        self._atualizar_acoes()

    def _sair_app(self):
        logger.info("Encerrando via System Tray.")
        self.app.quit()

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger or reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            # Toggle de exibição
            if self.main_widget.isHidden():
                self._exibir_widget()
            else:
                self._ocultar_widget()

    def _atualizar_acoes(self):
        is_hidden = self.main_widget.isHidden()
        self.action_exibir.setVisible(is_hidden)
        self.action_ocultar.setVisible(not is_hidden)

    def mostrar_notificacao(self, titulo: str, mensagem: str):
        """Dispara uma notificação nativa do Windows."""
        self.showMessage(
            titulo,
            mensagem,
            QSystemTrayIcon.MessageIcon.Information,
            5000  # 5 segundos
        )
