"""
Card individual de tarefa — ícones clean estilo Windows 11.
Suporta temas dark/light via paleta de cores.
"""
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor, QFont

from app.ui.styles import get_palette


class TaskCard(QFrame):
    """Widget que representa uma tarefa na lista."""

    state_changed = pyqtSignal(str, bool)
    delete_requested = pyqtSignal(str)
    edit_requested = pyqtSignal(str, str)
    progress_changed = pyqtSignal(str, bool)

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
        self.btn_check = QPushButton("✓" if tarefa["concluida"] else "")
        self.btn_check.setFixedSize(20, 20)
        self.btn_check.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.btn_check.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_check.setProperty(
            "class", "CheckButton Checked" if tarefa["concluida"] else "CheckButton"
        )
        self.btn_check.clicked.connect(self._toggle_check)

        # Botão Play/Pause (Em Andamento)
        is_playing = tarefa.get("em_andamento", False)
        self.btn_play = QPushButton("⏸" if is_playing else "▶")
        self.btn_play.setFixedSize(22, 22)
        self.btn_play.setFont(QFont("Segoe UI", 10))
        self.btn_play.setStyleSheet(f"color: {'#E74C3C' if is_playing else self.c['text_secondary']}; border: none; background: transparent;")
        self.btn_play.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_play.setToolTip("Pausar" if is_playing else "Iniciar Tarefa")
        self.btn_play.clicked.connect(self._toggle_play)

        # Título (editável)
        self.edit_titulo = QLineEdit(tarefa["titulo"])
        self._estilizar_leitura()
        self.edit_titulo.returnPressed.connect(self._finalizar_edicao)
        self.edit_titulo.editingFinished.connect(self._finalizar_edicao)

        # Botão editar
        self._icon_edit = "✏️"
        self._icon_save = "✓"
        self.btn_edit = QPushButton(self._icon_edit)
        self.btn_edit.setFixedSize(24, 24)
        self.btn_edit.setFont(QFont("Segoe UI", 11))
        self.btn_edit.setStyleSheet(f"color: {self.c['text_secondary']};")
        self.btn_edit.setProperty("class", "IconButton")
        self.btn_edit.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_edit.setToolTip("Editar")
        self.btn_edit.clicked.connect(self._toggle_edicao)

        # Botão excluir
        self.btn_delete = QPushButton("❌")
        self.btn_delete.setFixedSize(24, 24)
        self.btn_delete.setFont(QFont("Segoe UI", 10))
        self.btn_delete.setStyleSheet(f"color: {self.c['text_secondary']};")
        self.btn_delete.setProperty("class", "IconButton")
        self.btn_delete.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_delete.setToolTip("Excluir")
        self.btn_delete.clicked.connect(
            lambda: self.delete_requested.emit(self.tarefa["id"])
        )

        # Montagem
        lay.addWidget(self.lbl_grip)
        lay.addWidget(self.btn_check)
        if not tarefa.get("concluida"):
            lay.addWidget(self.btn_play)
        lay.addWidget(self.edit_titulo, stretch=1)
        lay.addWidget(self.btn_edit)
        lay.addWidget(self.btn_delete)

        self._aplicar_cor_fundo()

    # ---------- estilos ----------
    def _aplicar_cor_fundo(self):
        """Define a cor de fundo do card baseada na prioridade e escopo."""
        # Se estiver concluída, fica transparente para não chamar atenção
        if self.tarefa["concluida"]:
            bg_color = "transparent"
            border = "1px solid transparent"
        
        # 1. Prioridade Máxima: Alta
        elif self.tarefa.get("prioridade") == "alta":
            # Fundo avermelhado/laranja suave
            bg_color = "rgba(231, 76, 60, 0.15)"
            border = "1px solid rgba(231, 76, 60, 0.4)"
            
        # 2. Prioridade Secundária: Escritório
        elif self.tarefa.get("escopo") == "escritorio":
            # Fundo azulado suave
            bg_color = "rgba(52, 152, 219, 0.15)"
            border = "1px solid rgba(52, 152, 219, 0.4)"
            
        # 3. Padrão: Tarefa Particular / Normal
        else:
            # Fundo neutro/cinza
            bg_color = "rgba(150, 150, 150, 0.08)"
            border = "1px solid transparent"

        # Aplica o estilo focando apenas no QFrame principal usando o ObjectName
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
        if self.tarefa["concluida"]:
            self.edit_titulo.setStyleSheet(
                "background: transparent; border: none;"
                f"color: {self.c['text_concluida']}; text-decoration: line-through; font-size: 12px;"
            )
        else:
            self.edit_titulo.setStyleSheet(
                "background: transparent; border: none;"
                f"color: {self.c['text_primary']}; font-weight: 500; font-size: 12px;"
            )

    # ---------- edição ----------
    def _toggle_edicao(self):
        if self.edit_mode:
            self._finalizar_edicao()
        else:
            self._iniciar_edicao()

    def _iniciar_edicao(self):
        self.edit_mode = True
        self.btn_edit.setText(self._icon_save)
        self.btn_edit.setStyleSheet(f"color: {self.c['check_green']};")
        self.btn_edit.setToolTip("Salvar")
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
        self.btn_edit.setText(self._icon_edit)
        self.btn_edit.setStyleSheet(f"color: {self.c['text_secondary']};")
        self.btn_edit.setToolTip("Editar")
        self._estilizar_leitura()
        self.edit_titulo.clearFocus()
        novo = self.edit_titulo.text().strip()
        if novo and novo != self.tarefa["titulo"]:
            self.tarefa["titulo"] = novo
            self.edit_requested.emit(self.tarefa["id"], novo)

    # ---------- check ----------
    def _toggle_check(self):
        self.state_changed.emit(self.tarefa["id"], not self.tarefa["concluida"])

    # ---------- play/pause ----------
    def _toggle_play(self):
        novo_estado = not self.tarefa.get("em_andamento", False)
        self.tarefa["em_andamento"] = novo_estado
        
        # Atualiza visual do botão
        if novo_estado:
            self.btn_play.setText("⏸")
            self.btn_play.setStyleSheet(f"color: #E74C3C; border: none; background: transparent;")
            self.btn_play.setToolTip("Pausar Tarefa")
        else:
            self.btn_play.setText("▶")
            self.btn_play.setStyleSheet(f"color: {self.c['text_secondary']}; border: none; background: transparent;")
            self.btn_play.setToolTip("Iniciar Tarefa")
            
        # Opcional: Mudar cor do card sutilmente quando em andamento
        self._aplicar_cor_fundo()
        
        self.progress_changed.emit(self.tarefa["id"], novo_estado)
