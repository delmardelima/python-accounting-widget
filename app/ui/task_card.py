"""
Card individual de tarefa — ícones clean estilo Windows 11.
Suporta temas dark/light via paleta de cores.
"""
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMenu
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor, QFont

from app.ui.styles import get_palette

class TaskCard(QFrame):
    """Widget que representa uma tarefa na lista."""

    state_changed = pyqtSignal(str, bool)
    delete_requested = pyqtSignal(str)
    #edit_requested = pyqtSignal(str, str)
    edit_requested = pyqtSignal(str)
    view_requested = pyqtSignal(str)

    def __init__(self, tarefa: dict, theme: str = "dark"):
        super().__init__()
        self.tarefa = tarefa
        self.edit_mode = False
        self.theme = theme
        self.c = get_palette(theme)

        self.setObjectName("TaskCard")
        self.setProperty("class", "TaskCard")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(8)

        # Grip (drag handle)
        self.lbl_grip = QLabel("⠿")
        self.lbl_grip.setStyleSheet(
            f"color: {self.c['grip_color']}; font-size: 14px; padding: 0; margin-right: 2px;"
        )
        self.lbl_grip.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))

        # Checkbox
        self.btn_check = QPushButton("✓" if tarefa.get("concluida") else "")
        self.btn_check.setFixedSize(20, 20)
        self.btn_check.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.btn_check.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_check.setProperty(
            "class", "CheckButton Checked" if tarefa.get("concluida") else "CheckButton"
        )
        self.btn_check.clicked.connect(self._toggle_check)

        # Título (editável)
        titulo_text = tarefa["titulo"]
        if tarefa.get("link_anexo"):
            titulo_text = "🔗 " + titulo_text
            
        self.edit_titulo = QLineEdit(titulo_text)
        self._estilizar_leitura()
        self.edit_titulo.returnPressed.connect(self._finalizar_edicao)
        self.edit_titulo.editingFinished.connect(self._finalizar_edicao)

        # Botão Menu (3 pontos) substitui os antigos Editar/Excluir/Play
        self.btn_menu = QPushButton("⋮")
        self.btn_menu.setFixedSize(24, 24)
        self.btn_menu.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.btn_menu.setStyleSheet(f"color: {self.c['text_secondary']}; border: none; background: transparent; padding-bottom: 4px;")
        self.btn_menu.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_menu.setToolTip("Opções")
        self.btn_menu.clicked.connect(self._mostrar_menu)

        # Montagem Super Limpa
        lay.addWidget(self.lbl_grip)
        lay.addWidget(self.btn_check)
        lay.addWidget(self.edit_titulo, stretch=1)
        lay.addWidget(self.btn_menu)

        self._aplicar_cor_fundo()

    # ---------- menu de contexto ----------
    def _mostrar_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {self.c['bg_container']};
                color: {self.c['text_primary']};
                border: 1px solid {self.c['border_container']};
                border-radius: 6px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 24px 6px 8px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {self.c['bg_btn_hover']};
            }}
        """)
        
        acao_visualizar = menu.addAction("👁 Visualizar / Detalhes")
        acao_editar = menu.addAction("✏️ Editar Título")
        acao_excluir = menu.addAction("❌ Excluir Tarefa")
        
        # Abre o menu na posição do mouse
        acao = menu.exec(QCursor.pos())
        
        if acao == acao_visualizar:
            self.view_requested.emit(self.tarefa["id"])
        elif acao == acao_editar:
            #self._iniciar_edicao()
            self.edit_requested.emit(self.tarefa["id"])
        elif acao == acao_excluir:
            self.delete_requested.emit(self.tarefa["id"])

    # ---------- estilos ----------
    def _aplicar_cor_fundo(self):
        if self.tarefa.get("concluida"):
            bg_color = "transparent"
            border = "1px solid transparent"
        elif self.tarefa.get("prioridade") == "alta":
            bg_color = "rgba(231, 76, 60, 0.15)"
            border = "1px solid rgba(231, 76, 60, 0.4)"
        elif self.tarefa.get("escopo") == "escritorio":
            bg_color = "rgba(52, 152, 219, 0.15)"
            border = "1px solid rgba(52, 152, 219, 0.4)"
        else:
            bg_color = "rgba(150, 150, 150, 0.08)"
            border = "1px solid transparent"

        # Indicativo sutil se estiver em andamento (Opcional)
        if self.tarefa.get("em_andamento") and not self.tarefa.get("concluida"):
            border = "1px dashed #E74C3C"

        self.setStyleSheet(f"""
            #TaskCard {{
                background-color: {bg_color};
                border: {border};
                border-radius: 6px;
            }}
        """)

    def _estilizar_leitura(self):
        self.edit_titulo.setReadOnly(True)
        self.edit_titulo.setCursorPosition(0)
        self.edit_titulo.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        if self.tarefa.get("concluida"):
            # Aplica o riscado (line-through) e reduz a opacidade da cor
            self.edit_titulo.setStyleSheet(
                "background: transparent; border: none;"
                f"color: {self.c['text_concluida']}; "
                "text-decoration: line-through; " # O efeito de riscado
                "font-size: 12px;"
            )
        else:
            self.edit_titulo.setStyleSheet(
                "background: transparent; border: none;"
                f"color: {self.c['text_primary']}; font-weight: 500; font-size: 12px;"
            )

    # ---------- edição ----------
    def _iniciar_edicao(self):
        self.edit_mode = True
        self.edit_titulo.setReadOnly(False)
        self.edit_titulo.setStyleSheet(
            f"background: {self.c['edit_bg']}; border: 1px solid {self.c['accent_input_border']};"
            f"color: {self.c['text_input']}; border-radius: 4px; padding: 2px; font-size: 12px;"
        )
        self.edit_titulo.setFocus()
        self.edit_titulo.selectAll()

    def _finalizar_edicao(self):
        if not self.edit_mode:
            return
        self.edit_mode = False
        self._estilizar_leitura()
        self.edit_titulo.clearFocus()
        novo = self.edit_titulo.text().strip()
        if novo and novo != self.tarefa["titulo"]:
            self.tarefa["titulo"] = novo
            self.edit_requested.emit(self.tarefa["id"], novo)

    # ---------- check ----------
    def _toggle_check(self):
        self.state_changed.emit(self.tarefa["id"], not self.tarefa["concluida"])

    