"""
Widget principal de tarefas — UI reestruturada com suporte a temas e formulário dedicado.
"""
import logging
import re
from datetime import datetime, timedelta

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QStackedWidget, QSlider,
    QListWidgetItem,
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QPropertyAnimation, QRect, QEasingCurve
from PyQt6.QtGui import QColor, QFont, QCursor, QShortcut, QKeySequence
from PyQt6.QtWidgets import QGraphicsDropShadowEffect

from app.models import Tarefa
from app.database import Database
from app.config import Config
from app.ui.styles import get_stylesheet, get_palette
from app.ui.theme import resolver_tema
from app.ui.drag_list import DragListWidget
from app.ui.task_card import TaskCard

logger = logging.getLogger(__name__)

APP_VERSION = "1.0.0"


class WidgetTarefasModerno(QWidget):
    """Janela principal do widget de tarefas."""

    def __init__(self, db: Database, config: Config):
        super().__init__()

        self.db = db
        self.config = config
        self.tarefas: list[dict] = []

        self.opacidade_atual = self.config.getint("window", "opacidade", fallback=95) / 100.0
        self.mostrar_concluidas = False

        # Tema
        self.modo_tema = self.config.get("state", "tema", fallback="sistema")
        self.tema_atual = resolver_tema(self.modo_tema)

        self._setup_window()
        self._init_ui()
        self._restaurar_estado()
        self._carregar_tarefas()

    # ================================================================== #
    #  JANELA
    # ================================================================== #
    def _setup_window(self):
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self.is_collapsed = False
        self.margin = 15
        self.base_expanded_size = QSize(380, 560)
        self.base_collapsed_size = QSize(65, 40)

        self.expanded_size = QSize(
            self.base_expanded_size.width() + self.margin * 2,
            self.base_expanded_size.height() + self.margin * 2,
        )
        self.collapsed_size = QSize(
            self.base_collapsed_size.width() + self.margin * 2,
            self.base_collapsed_size.height() + self.margin * 2,
        )
        self.setFixedSize(self.expanded_size)

        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().availableGeometry()
        pos_x = self.config.getint("window", "pos_x", fallback=-1)
        pos_y = self.config.getint("window", "pos_y", fallback=30)
        if pos_x < 0:
            pos_x = screen.right() - self.expanded_size.width() - 10
        # Garante que o widget fique completamente visível na tela
        pos_x = max(screen.x(), min(pos_x, screen.right() - self.expanded_size.width()))
        pos_y = max(screen.y(), min(pos_y, screen.bottom() - self.expanded_size.height()))
        self.move(pos_x, pos_y)
        self.old_pos = None

    def aplicar_flags_janela(self):
        pos = self.pos()
        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setWindowFlags(flags)
        self.move(pos)
        self.setWindowOpacity(self.opacidade_atual)
        self.show()

    # ================================================================== #
    #  UI
    # ================================================================== #
    def _init_ui(self):
        self.setStyleSheet(get_stylesheet(self.tema_atual))

        self.window_layout = QVBoxLayout(self)
        self.window_layout.setContentsMargins(self.margin, self.margin, self.margin, self.margin)

        # Container principal com sombra
        self.main_container = QFrame()
        self.main_container.setObjectName("MainContainer")

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 5)
        self.main_container.setGraphicsEffect(shadow)
        self.window_layout.addWidget(self.main_container)

        # Botão expandir (estado colapsado)
        self.btn_expand = QPushButton("❮", self)
        self.btn_expand.setFixedSize(self.base_collapsed_size)
        self.btn_expand.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_expand.clicked.connect(self._toggle_collapse)
        self.btn_expand.hide()

        # Layout interno
        self.main_layout = QVBoxLayout(self.main_container)
        self.main_layout.setContentsMargins(16, 14, 16, 14)
        self.main_layout.setSpacing(8)

        # --- CORREÇÃO: Stacked Widget e Criação das 3 Páginas ---
        self.stacked = QStackedWidget()
        self.main_layout.addWidget(self.stacked)

        self.page_tarefas = QWidget()
        self.page_configs = QWidget()
        self.page_form = QWidget()  # Cria a página do formulário

        # Constrói o conteúdo de cada página
        self._build_page_tarefas()
        self._build_page_configs()
        self._build_page_form()     # Chama a construção do formulário

        # Adiciona na ordem correta (0=Lista, 1=Configs, 2=Formulário)
        self.stacked.addWidget(self.page_tarefas)
        self.stacked.addWidget(self.page_configs)
        self.stacked.addWidget(self.page_form)

        # Aplica estilos inline baseados no tema
        self._aplicar_estilos_tema()

    # ------------------------------------------------------------------ #
    #  Página 0: Lista de Tarefas
    # ------------------------------------------------------------------ #
    def _build_page_tarefas(self):
        layout = QVBoxLayout(self.page_tarefas)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # --- Cabeçalho compacto ---
        header = QHBoxLayout()
        header.setSpacing(4)

        self.lbl_logo = QLabel("Tarefas")
        self.lbl_logo.setFont(QFont("Segoe UI", 13, QFont.Weight.DemiBold))

        self.lbl_contador = QLabel("0")
        self.lbl_contador.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_size = 28

        self.btn_config = QPushButton("⛭")
        self.btn_config.setFixedSize(btn_size, btn_size)
        self.btn_config.setFont(QFont("Segoe UI Symbol", 12))
        self.btn_config.setProperty("class", "IconButton")
        self.btn_config.setToolTip("Configurações")
        self.btn_config.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_config.clicked.connect(lambda: self.stacked.setCurrentIndex(1))

        self.btn_collapse = QPushButton("❯")
        self.btn_collapse.setFixedSize(btn_size, btn_size)
        self.btn_collapse.setFont(QFont("Segoe UI", 11))
        self.btn_collapse.setProperty("class", "IconButton")
        self.btn_collapse.setToolTip("Recolher")
        self.btn_collapse.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_collapse.clicked.connect(self._toggle_collapse)

        header.addWidget(self.lbl_logo)
        header.addWidget(self.lbl_contador)
        header.addStretch(1)
        header.addWidget(self.btn_config)
        header.addWidget(self.btn_collapse)
        layout.addLayout(header)

        # --- Abas ---
        tabs = QHBoxLayout()
        tabs.setSpacing(4)
        self.btn_pendentes = QPushButton("Pendentes")
        self.btn_pendentes.setProperty("class", "TabButton Active")
        self.btn_pendentes.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_pendentes.clicked.connect(lambda: self._mudar_aba(False))

        self.btn_concluidas = QPushButton("Concluídas")
        self.btn_concluidas.setProperty("class", "TabButton")
        self.btn_concluidas.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_concluidas.clicked.connect(lambda: self._mudar_aba(True))

        tabs.addWidget(self.btn_pendentes)
        tabs.addWidget(self.btn_concluidas)
        tabs.addStretch()
        layout.addLayout(tabs)

        # --- Barra de Pesquisa e Botão '+' ---
        self.search_container = QWidget()
        search_lay = QHBoxLayout(self.search_container)
        search_lay.setContentsMargins(0, 0, 0, 0)
        search_lay.setSpacing(8)

        self.input_pesquisa = QLineEdit()
        self.input_pesquisa.setObjectName("TaskInput")
        self.input_pesquisa.setPlaceholderText("🔍 Pesquisar tarefas...")
        self.input_pesquisa.textChanged.connect(self._atualizar_lista)

        self.btn_abrir_form = QPushButton("+")
        self.btn_abrir_form.setObjectName("BtnAddTask")
        self.btn_abrir_form.setFixedSize(36, 36)
        self.btn_abrir_form.setFont(QFont("Segoe UI", 16))
        self.btn_abrir_form.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_abrir_form.setToolTip("Criar Nova Tarefa")
        self.btn_abrir_form.clicked.connect(self._mostrar_form_criacao)

        search_lay.addWidget(self.input_pesquisa, stretch=1)
        search_lay.addWidget(self.btn_abrir_form)
        layout.addWidget(self.search_container)

        # NOVO: Atalho de Teclado (Ctrl + N)
        self.atalho_nova_tarefa = QShortcut(QKeySequence("Ctrl+N"), self.page_tarefas)
        self.atalho_nova_tarefa.activated.connect(self._mostrar_form_criacao)
        self.btn_abrir_form.setToolTip("Criar Nova Tarefa (Ctrl+N)") # Atualiza a dica visual

        # --- Divisória ---
        divider = QFrame()
        divider.setObjectName("Divider")
        divider.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(divider)

        # --- Filtros ---
        self.filtros_container = QWidget()
        filtros = QHBoxLayout(self.filtros_container)
        filtros.setContentsMargins(0, 2, 0, 2)
        filtros.setSpacing(4)

        self.filtro_tudo = QPushButton("Todas")
        self.filtro_minhas = QPushButton("Minhas")
        self.filtro_escritorio = QPushButton("Escritório")
        self.filtro_alta = QPushButton("Alta")
        self.filtro_delegadas = QPushButton("Delegadas") # Novo Filtro

        self.botoes_filtro = [
            self.filtro_tudo, self.filtro_minhas,
            self.filtro_escritorio, self.filtro_alta,
            self.filtro_delegadas
        ]

        # Estilização
        self.filtro_tudo.setStyleSheet(self._obter_estilo_botao_legenda("normal"))
        self.filtro_minhas.setStyleSheet(self._obter_estilo_botao_legenda("normal"))
        self.filtro_escritorio.setStyleSheet(self._obter_estilo_botao_legenda("escritorio"))
        self.filtro_alta.setStyleSheet(self._obter_estilo_botao_legenda("alta"))
        self.filtro_delegadas.setStyleSheet(self._obter_estilo_botao_legenda("normal"))

        for btn in self.botoes_filtro:
            btn.setCheckable(True)
            btn.setProperty("class", "FilterChip")
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.clicked.connect(self._tratar_filtro)
            filtros.addWidget(btn)

        self.filtro_tudo.setChecked(True)
        filtros.addStretch()
        layout.addWidget(self.filtros_container)

        # --- Lista ---
        self.lista_tarefas = DragListWidget()
        self.lista_tarefas.order_changed.connect(self._sincronizar_ordem)
        layout.addWidget(self.lista_tarefas)

    # ------------------------------------------------------------------ #
    #  Página 2: Formulário de Criação
    # ------------------------------------------------------------------ #
    def _build_page_form(self):
        layout = QVBoxLayout(self.page_form)
        layout.setSpacing(10)
        
        header = QHBoxLayout()
        btn_voltar_form = QPushButton("❮ Voltar")
        btn_voltar_form.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_voltar_form.setStyleSheet("background: transparent; color: #63B3ED; font-weight: bold; border: none; font-size: 13px;")
        btn_voltar_form.clicked.connect(self._esconder_form_criacao)
        header.addWidget(btn_voltar_form)
        header.addStretch()
        layout.addLayout(header)

        lbl_titulo = QLabel("<b>Nova Tarefa</b>")
        lbl_titulo.setFont(QFont("Segoe UI", 12))
        layout.addWidget(lbl_titulo)

        # Input Principal (Smart Input)
        self.form_titulo = QLineEdit()
        self.form_titulo.setObjectName("TaskInput")
        self.form_titulo.setPlaceholderText("Ex: Pagar guia #urgente @escritorio")
        self.form_titulo.textChanged.connect(self._smart_input_parser)
        self.form_titulo.returnPressed.connect(self._salvar_nova_tarefa_form)
        layout.addWidget(self.form_titulo)

        # Quick Dates
        date_lay = QHBoxLayout()
        self.btn_date_hoje = QPushButton("📅 Hoje")
        self.btn_date_amanha = QPushButton("📅 Amanhã")
        self.btn_date_segunda = QPushButton("📅 Próx Seg")
        self._date_btns = [self.btn_date_hoje, self.btn_date_amanha, self.btn_date_segunda]
        
        for btn in self._date_btns:
            btn.setProperty("class", "ToggleTag")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, b=btn: self._select_date(b))
            date_lay.addWidget(btn)
        layout.addLayout(date_lay)

        # Tags de Configuração
        config_lay = QHBoxLayout()
        self.form_tag_minha = QPushButton("Particular")
        self.form_tag_escritorio = QPushButton("Escritório")
        self.form_tag_normal = QPushButton("Normal")
        self.form_tag_alta = QPushButton("Alta")
        
        # Agrupamentos lógicos
        self._escopo_tags = [self.form_tag_minha, self.form_tag_escritorio]
        self._prior_tags = [self.form_tag_normal, self.form_tag_alta]

        # Estilização
        self.form_tag_minha.setStyleSheet(self._obter_estilo_botao_legenda("normal"))
        self.form_tag_escritorio.setStyleSheet(self._obter_estilo_botao_legenda("escritorio"))
        self.form_tag_normal.setStyleSheet(self._obter_estilo_botao_legenda("normal"))
        self.form_tag_alta.setStyleSheet(self._obter_estilo_botao_legenda("alta"))

        for tag in self._escopo_tags + self._prior_tags:
            tag.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            tag.setProperty("class", "ToggleTag")
            tag.setCheckable(True)

        # Eventos (mesmo sistema de select anterior)
        self.form_tag_minha.clicked.connect(lambda: self._select_tag(self._escopo_tags, self.form_tag_minha))
        self.form_tag_escritorio.clicked.connect(lambda: self._select_tag(self._escopo_tags, self.form_tag_escritorio))
        self.form_tag_normal.clicked.connect(lambda: self._select_tag(self._prior_tags, self.form_tag_normal))
        self.form_tag_alta.clicked.connect(lambda: self._select_tag(self._prior_tags, self.form_tag_alta))

        config_lay.addWidget(self.form_tag_minha)
        config_lay.addWidget(self.form_tag_escritorio)
        config_lay.addSpacing(10)
        config_lay.addWidget(self.form_tag_normal)
        config_lay.addWidget(self.form_tag_alta)
        layout.addLayout(config_lay)

        # Links e Delegação
        self.form_link = QLineEdit()
        self.form_link.setObjectName("TaskInput")
        self.form_link.setPlaceholderText("🔗 Link ou anexo (opcional)")
        self.form_link.returnPressed.connect(self._salvar_nova_tarefa_form)
        layout.addWidget(self.form_link)

        self.form_delegar = QLineEdit()
        self.form_delegar.setObjectName("TaskInput")
        self.form_delegar.setPlaceholderText("👤 Delegar para (nome/setor)")
        self.form_delegar.returnPressed.connect(self._salvar_nova_tarefa_form)
        layout.addWidget(self.form_delegar)

        layout.addStretch()

        # Botão Salvar
        self.btn_salvar_tarefa = QPushButton("Criar Tarefa")
        self.btn_salvar_tarefa.setStyleSheet("background-color: #48BB78; color: white; padding: 10px; border-radius: 8px; font-size: 13px; font-weight: bold;")
        self.btn_salvar_tarefa.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_salvar_tarefa.clicked.connect(self._salvar_nova_tarefa_form)
        layout.addWidget(self.btn_salvar_tarefa)

        # NOVO: Atalho para cancelar/fechar o formulário com a tecla 'Esc'
        self.atalho_fechar_form = QShortcut(QKeySequence("Esc"), self.page_form)
        self.atalho_fechar_form.activated.connect(self._esconder_form_criacao)

    # ------------------------------------------------------------------ #
    #  Página 1: Configurações
    # ------------------------------------------------------------------ #
    def _build_page_configs(self):
        layout = QVBoxLayout(self.page_configs)
        layout.setSpacing(12)

        self.lbl_config_titulo = QLabel("Configurações")
        self.lbl_config_titulo.setFont(QFont("Segoe UI", 14, QFont.Weight.DemiBold))
        layout.addWidget(self.lbl_config_titulo)

        # --- Tema ---
        layout.addWidget(QLabel("Tema:"))
        tema_row = QHBoxLayout()
        tema_row.setSpacing(4)

        self.btn_tema_sistema = QPushButton("🖥 Sistema")
        self.btn_tema_claro = QPushButton("☀ Claro")
        self.btn_tema_escuro = QPushButton("🌙 Escuro")

        self._botoes_tema = [self.btn_tema_sistema, self.btn_tema_claro, self.btn_tema_escuro]
        self._mapa_tema = {
            self.btn_tema_sistema: "sistema",
            self.btn_tema_claro: "claro",
            self.btn_tema_escuro: "escuro",
        }

        for btn in self._botoes_tema:
            btn.setProperty("class", "ThemeBtn")
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.clicked.connect(self._on_tema_clicked)
            tema_row.addWidget(btn)

        tema_row.addStretch()
        layout.addLayout(tema_row)

        # --- Opacidade ---
        layout.addWidget(QLabel("Opacidade:"))
        self.slider_opacidade = QSlider(Qt.Orientation.Horizontal)
        self.slider_opacidade.setMinimum(30)
        self.slider_opacidade.setMaximum(100)
        self.slider_opacidade.setValue(int(self.opacidade_atual * 100))
        self.slider_opacidade.valueChanged.connect(self._mudar_opacidade)
        layout.addWidget(self.slider_opacidade)

        # --- API URL ---
        layout.addWidget(QLabel("API URL:"))
        self.input_api_url = QLineEdit(self.config.get("api", "base_url"))
        self.input_api_url.setObjectName("TaskInput")
        self.input_api_url.editingFinished.connect(self._salvar_api_config)
        layout.addWidget(self.input_api_url)

        # --- API Key ---
        layout.addWidget(QLabel("API Key:"))
        self.input_api_key = QLineEdit(self.config.get("api", "api_key"))
        self.input_api_key.setObjectName("TaskInput")
        self.input_api_key.editingFinished.connect(self._salvar_api_config)
        self.input_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.input_api_key)

        layout.addStretch()

        # --- Sobre ---
        divider = QFrame()
        divider.setObjectName("Divider")
        divider.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(divider)

        self.lbl_versao = QLabel(f"Sagecont Widget v{APP_VERSION}")
        self.lbl_versao.setFont(QFont("Segoe UI", 9))
        self.lbl_versao.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_versao)

        self.lbl_legal = QLabel("© 2026 Sagecont · Todos os direitos reservados")
        self.lbl_legal.setFont(QFont("Segoe UI", 8))
        self.lbl_legal.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_legal)

        # --- Voltar ---
        self.btn_voltar = QPushButton("← Voltar")
        self.btn_voltar.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_voltar.clicked.connect(lambda: self.stacked.setCurrentIndex(0))
        layout.addWidget(self.btn_voltar)

    # ================================================================== #
    #  ESTILOS GERAIS
    # ================================================================== #
    def _obter_estilo_botao_legenda(self, tipo: str) -> str:
        """Gera o estilo CSS dos botões para servir como legenda visual das cores dos cards."""
        if tipo == "alta":
            cor_bg = "rgba(231, 76, 60, 0.15)"
            cor_hover = "rgba(231, 76, 60, 0.25)"
            cor_active = "rgba(231, 76, 60, 0.35)"
            cor_borda = "rgba(231, 76, 60, 0.8)"
        elif tipo == "escritorio":
            cor_bg = "rgba(52, 152, 219, 0.15)"
            cor_hover = "rgba(52, 152, 219, 0.25)"
            cor_active = "rgba(52, 152, 219, 0.35)"
            cor_borda = "rgba(52, 152, 219, 0.8)"
        else:
            cor_bg = "rgba(150, 150, 150, 0.08)"
            cor_hover = "rgba(150, 150, 150, 0.15)"
            cor_active = "rgba(150, 150, 150, 0.25)"
            cor_borda = "rgba(150, 150, 150, 0.6)"

        return f"""
            QPushButton {{
                background-color: {cor_bg};
                border: 1px solid transparent;
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {cor_hover};
                border: 1px solid {cor_bg};
            }}
            QPushButton[class~="Active"], QPushButton:checked {{
                background-color: {cor_active};
                border: 1px solid {cor_borda};
            }}
        """

    def _aplicar_estilos_tema(self):
        """Aplica estilos inline que dependem do tema atual."""
        c = get_palette(self.tema_atual)

        # Header
        self.lbl_logo.setStyleSheet(f"color: {c['text_primary']};")
        self.btn_config.setStyleSheet(f"color: {c['text_secondary']};")
        self.btn_collapse.setStyleSheet(f"font-weight: normal; color: {c['text_secondary']};")

        # Botão expandir (colapsado)
        self.btn_expand.setStyleSheet(
            f"background-color: {c['expand_bg']}; color: {c['text_secondary']};"
            f"border-radius: 8px; font-size: 14px;"
            f"border: 1px solid {c['border_container']};"
        )

        # Botão voltar (configs)
        self.btn_voltar.setStyleSheet(
            f"background-color: {c['bg_voltar']}; color: white;"
            "padding: 8px; border-radius: 8px; font-weight: 500;"
        )

        # Badge do contador
        self.lbl_contador.setStyleSheet(
            "background-color: #E74C3C; color: white; "
            "border-radius: 10px; padding: 2px 7px; "
            "font-size: 11px; font-weight: bold;"
        )

        # Labels de versão / legal
        self.lbl_versao.setStyleSheet(f"color: {c['text_version']};")
        self.lbl_legal.setStyleSheet(f"color: {c['text_version']};")

    def _atualizar_contadores(self):
        """Calcula as tarefas pendentes e atualiza a UI."""
        pendentes = sum(1 for t in self.tarefas if not t.get("concluida", False))
        self.lbl_contador.setText(str(pendentes))
        self.lbl_contador.setVisible(pendentes > 0)
        
        if pendentes > 0:
            self.btn_expand.setText(f"❮   {pendentes}")
        else:
            self.btn_expand.setText("❮")

    # ================================================================== #
    #  LÓGICA DO FORMULÁRIO DE CRIAÇÃO
    # ================================================================== #
    def _mostrar_form_criacao(self):
        # 1. Troca para a página do formulário
        self.stacked.setCurrentIndex(2)
        
        # 2. Usa self.anim para o Python NÃO destruir a animação antes dela terminar!
        self.anim = QPropertyAnimation(self.page_form, b"geometry")
        self.anim.setDuration(250)
        
        # Pega o tamanho atual do container
        geom = self.stacked.geometry()
        
        # Começa com a largura empurrada para a direita (fora da tela) e desliza para o (0, 0)
        self.anim.setStartValue(QRect(geom.width(), 0, geom.width(), geom.height()))
        self.anim.setEndValue(QRect(0, 0, geom.width(), geom.height()))
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Inicia a animação
        self.anim.start()
        
        # Dá foco automático no campo de título para o usuário já sair digitando
        self.form_titulo.setFocus()

    def _esconder_form_criacao(self):
        # Limpa os campos
        self.form_titulo.clear()
        self.form_link.clear()
        self.form_delegar.clear()
        for b in self._date_btns: 
            b.setChecked(False)
            
        # Retorna para a aba de listas sem animação ou com transição instantânea
        self.stacked.setCurrentIndex(0)

    def _smart_input_parser(self, text):
        """Ativa botões automaticamente baseado em texto (#urgente, @escritorio)."""
        if "#urgente" in text.lower() or "#alta" in text.lower():
            self._select_tag(self._prior_tags, self.form_tag_alta)
        
        if "@escritorio" in text.lower():
            self._select_tag(self._escopo_tags, self.form_tag_escritorio)

    def _select_date(self, selected_btn):
        for btn in self._date_btns:
            if btn != selected_btn:
                btn.setChecked(False)

    def _salvar_nova_tarefa_form(self):
        texto = self.form_titulo.text()
        
        # Remove as tags do texto visual
        texto_limpo = re.sub(r'#\w+|@\w+', '', texto).strip()
        if not texto_limpo:
            return

        escopo = "escritorio" if self.form_tag_escritorio.isChecked() else "minha"
        prioridade = "alta" if self.form_tag_alta.isChecked() else "normal"
        link = self.form_link.text().strip()
        delegado = self.form_delegar.text().strip()
        api_key = self.config.get("api", "api_key", fallback="")

        # Lógica das datas (Quick Dates)
        data_venc = ""
        hoje = datetime.now()
        if self.btn_date_hoje.isChecked():
            data_venc = hoje.strftime("%Y-%m-%d")
        elif self.btn_date_amanha.isChecked():
            data_venc = (hoje + timedelta(days=1)).strftime("%Y-%m-%d")
        elif self.btn_date_segunda.isChecked():
            days_ahead = 0 - hoje.weekday() + 7 
            if days_ahead <= 0: days_ahead += 7
            data_venc = (hoje + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

        tarefa = Tarefa(
            titulo=texto_limpo, 
            escopo=escopo, 
            prioridade=prioridade, 
            api_key=api_key,
            data_vencimento=data_venc,
            link_anexo=link,
            delegado_para=delegado
        )
        
        self.db.inserir(tarefa)
        self._esconder_form_criacao()
        self._carregar_tarefas()

    # ================================================================== #
    #  AÇÕES DE DADOS (LISTA/BANCO)
    # ================================================================== #
    def _carregar_tarefas(self):
        api_key = self.config.get("api", "api_key", fallback="")
        lista = self.db.listar(api_key)
        self.tarefas = [t.to_dict() for t in lista]
        self._atualizar_lista()

    def refresh_do_sync(self):
        self._carregar_tarefas()

    def _alterar_status(self, tarefa_id: str, concluida: bool):
        api_key = self.config.get("api", "api_key", fallback="")
        t = self.db.buscar_por_id(tarefa_id, api_key)
        if t:
            t.concluida = concluida
            self.db.atualizar(t)
            self._carregar_tarefas()

    def _editar_tarefa(self, tarefa_id: str, novo_titulo: str):
        api_key = self.config.get("api", "api_key", fallback="")
        t = self.db.buscar_por_id(tarefa_id, api_key)
        if t:
            t.titulo = novo_titulo
            self.db.atualizar(t)

    def _excluir_tarefa(self, tarefa_id: str):
        api_key = self.config.get("api", "api_key", fallback="")
        self.db.excluir(tarefa_id, api_key)
        self._carregar_tarefas()

    # ================================================================== #
    #  TOGGLE TAGS (UI ESTADO)
    # ================================================================== #
    def _select_tag(self, grupo: list, ativo: QPushButton):
        for btn in grupo:
            btn.setProperty("class", "ToggleTag")
            btn.setChecked(False)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            
        ativo.setProperty("class", "ToggleTag Active")
        ativo.setChecked(True)
        ativo.style().unpolish(ativo)
        ativo.style().polish(ativo)

        # Salva a preferência de última escolha
        if grupo == getattr(self, '_escopo_tags', []):
            valor = "escritorio" if ativo == getattr(self, 'form_tag_escritorio', None) else "minha"
            self.config.set("state", "tag_escopo", valor)
        elif grupo == getattr(self, '_prior_tags', []):
            valor = "alta" if ativo == getattr(self, 'form_tag_alta', None) else "normal"
            self.config.set("state", "tag_prioridade", valor)
        self.config.save()

    def _tratar_filtro(self):
        remetente = self.sender()
        if remetente in [self.filtro_tudo, self.filtro_minhas, self.filtro_escritorio]:
            self.filtro_tudo.setChecked(remetente == self.filtro_tudo)
            self.filtro_minhas.setChecked(remetente == self.filtro_minhas)
            self.filtro_escritorio.setChecked(remetente == self.filtro_escritorio)
            if not any(b.isChecked() for b in [self.filtro_tudo, self.filtro_minhas, self.filtro_escritorio]):
                self.filtro_tudo.setChecked(True)
        self._salvar_estado_filtros()
        self._atualizar_lista()

    def _mudar_aba(self, concluidas: bool):
        self.mostrar_concluidas = concluidas
        if concluidas:
            self.btn_concluidas.setProperty("class", "TabButton Active")
            self.btn_pendentes.setProperty("class", "TabButton")
            self.search_container.hide()
            self.filtros_container.hide()
        else:
            self.btn_pendentes.setProperty("class", "TabButton Active")
            self.btn_concluidas.setProperty("class", "TabButton")
            self.search_container.show()
            self.filtros_container.show()

        for btn in [self.btn_pendentes, self.btn_concluidas]:
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        self.config.set("state", "aba_concluidas", str(concluidas).lower())
        self.config.save()
        self._atualizar_lista()

    # ================================================================== #
    #  LISTA E ORDENAÇÃO
    # ================================================================== #
    def _atualizar_lista(self):
        self.lista_tarefas.clear()
        c = get_palette(self.tema_atual)
        filtradas = []
        
        for t in self.tarefas:
            if t.get("concluida", False) != self.mostrar_concluidas:
                continue
            if self.filtro_minhas.isChecked() and t.get("escopo") != "minha":
                continue
            if self.filtro_escritorio.isChecked() and t.get("escopo") != "escritorio":
                continue
            if self.filtro_alta.isChecked() and t.get("prioridade") != "alta":
                continue
            if self.filtro_delegadas.isChecked() and not t.get("delegado_para"):
                continue
                
            termo = self.input_pesquisa.text().lower()
            if termo and termo not in t.get("titulo", "").lower():
                continue
                
            filtradas.append(t)

        if not filtradas:
            item = QListWidgetItem(self.lista_tarefas)
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            msg = "Nenhuma tarefa pendente" if not self.mostrar_concluidas else "Nenhuma tarefa concluída"
            lbl = QLabel(msg)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"color: {c['text_disabled']}; font-size: 12px; font-style: italic; margin-top: 20px;")
            item.setSizeHint(QSize(0, 60))
            self.lista_tarefas.setItemWidget(item, lbl)
        else:
            for tarefa in filtradas:
                card = TaskCard(tarefa, theme=self.tema_atual)
                card.state_changed.connect(self._alterar_status)
                card.delete_requested.connect(self._excluir_tarefa)
                card.edit_requested.connect(self._editar_tarefa)
                
                # Se a emissão do Play/Pause foi configurada no Card:
                if hasattr(card, "progress_changed"):
                    card.progress_changed.connect(self._atualizar_progresso)

                item = QListWidgetItem(self.lista_tarefas)
                item.setData(Qt.ItemDataRole.UserRole, tarefa["id"])
                item.setSizeHint(QSize(0, 48))
                self.lista_tarefas.setItemWidget(item, card)

        self._atualizar_contadores()

    def _atualizar_progresso(self, tarefa_id: str, em_andamento: bool):
        """Salva a mudança de progresso (play/pause)."""
        api_key = self.config.get("api", "api_key", fallback="")
        t = self.db.buscar_por_id(tarefa_id, api_key)
        if t:
            t.em_andamento = em_andamento
            self.db.atualizar(t)
            self._carregar_tarefas()

    def _sincronizar_ordem(self):
        """Mescla persistência no banco com atualização da lista em memória."""
        nova_ordem_ids = []
        for i in range(self.lista_tarefas.count()):
            uid = self.lista_tarefas.item(i).data(Qt.ItemDataRole.UserRole)
            if uid:
                nova_ordem_ids.append(uid)
                self.db._conn.execute(
                    "UPDATE tarefas SET ordem_usuario = ? WHERE id = ?",
                    (i, uid)
                )
        self.db._conn.commit()

        indices_na_memoria = [idx for idx, t in enumerate(self.tarefas) if t["id"] in nova_ordem_ids]
        mapa_objetos = {t["id"]: t for t in self.tarefas if t["id"] in nova_ordem_ids}
        
        for idx, nid in zip(indices_na_memoria, nova_ordem_ids):
            self.tarefas[idx] = mapa_objetos[nid]
            self.tarefas[idx]["ordem_usuario"] = nova_ordem_ids.index(nid)

        self._atualizar_lista()

    # ================================================================== #
    #  TEMA DA JANELA (CONFIGS E MOVIMENTOS)
    # ================================================================== #
    def _on_tema_clicked(self):
        remetente = self.sender()
        modo = self._mapa_tema.get(remetente, "sistema")
        self._mudar_tema(modo)

    def _mudar_tema(self, modo: str):
        self.modo_tema = modo
        self.tema_atual = resolver_tema(modo)
        self.config.set("state", "tema", modo)
        self.config.save()
        self.setStyleSheet(get_stylesheet(self.tema_atual))
        self._aplicar_estilos_tema()
        self._atualizar_seletor_tema()
        self._atualizar_lista()

    def _atualizar_seletor_tema(self):
        mapa_inverso = {v: k for k, v in self._mapa_tema.items()}
        for btn in self._botoes_tema:
            if btn == mapa_inverso.get(self.modo_tema):
                btn.setProperty("class", "ThemeBtn Active")
            else:
                btn.setProperty("class", "ThemeBtn")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _mudar_opacidade(self, valor: int):
        self.opacidade_atual = valor / 100.0
        self.setWindowOpacity(self.opacidade_atual)
        self.config.set("window", "opacidade", valor)
        self.config.save()

    def _salvar_api_config(self):
        url = self.input_api_url.text().strip()
        apikey = self.input_api_key.text().strip()
        if url:
            self.config.set("api", "base_url", url)
        self.config.set("api", "api_key", apikey)
        self.config.save()

    def _toggle_collapse(self):
        self.is_collapsed = not self.is_collapsed
        offset = self.expanded_size.width() - self.collapsed_size.width()

        if self.is_collapsed:
            self.main_container.hide()
            self.setFixedSize(self.collapsed_size)
            self.move(self.x() + offset, self.y())
            self.btn_expand.move(self.margin, self.margin)
            self.btn_expand.show()
        else:
            self.btn_expand.hide()
            self.setFixedSize(self.expanded_size)
            self.move(self.x() - offset, self.y())
            self.main_container.show()

        self.config.set("state", "collapsed", str(self.is_collapsed).lower())
        self.config.save()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if not self.old_pos:
            return
        delta = event.globalPosition().toPoint() - self.old_pos
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.old_pos = None

    def closeEvent(self, event):
        if self.is_collapsed:
            offset = self.expanded_size.width() - self.collapsed_size.width()
            self.config.set("window", "pos_x", self.x() - offset)
        else:
            self.config.set("window", "pos_x", self.x())
        self.config.set("window", "pos_y", self.y())
        self.config.save()
        super().closeEvent(event)

    def _salvar_estado_filtros(self):
        if self.filtro_minhas.isChecked():
            filtro = "minhas"
        elif self.filtro_escritorio.isChecked():
            filtro = "escritorio"
        else:
            filtro = "tudo"
        self.config.set("state", "filtro", filtro)
        self.config.set("state", "filtro_alta", str(self.filtro_alta.isChecked()).lower())
        self.config.set("state", "filtro_delegadas", str(self.filtro_delegadas.isChecked()).lower())
        self.config.save()

    def _restaurar_estado(self):
        self._atualizar_seletor_tema()

        filtro = self.config.get("state", "filtro", fallback="tudo")
        self.filtro_tudo.setChecked(filtro == "tudo")
        self.filtro_minhas.setChecked(filtro == "minhas")
        self.filtro_escritorio.setChecked(filtro == "escritorio")

        filtro_alta = self.config.get("state", "filtro_alta", fallback="false") == "true"
        self.filtro_alta.setChecked(filtro_alta)

        filtro_delegadas = self.config.get("state", "filtro_delegadas", fallback="false") == "true"
        self.filtro_delegadas.setChecked(filtro_delegadas)

        # Tags de Criação 
        tag_escopo = self.config.get("state", "tag_escopo", fallback="minha")
        tag_ativa_escopo = self.form_tag_escritorio if tag_escopo == "escritorio" else self.form_tag_minha
        self._select_tag(self._escopo_tags, tag_ativa_escopo)

        tag_prior = self.config.get("state", "tag_prioridade", fallback="normal")
        tag_ativa_prior = self.form_tag_alta if tag_prior == "alta" else self.form_tag_normal
        self._select_tag(self._prior_tags, tag_ativa_prior)

        aba_concluidas = self.config.get("state", "aba_concluidas", fallback="false") == "true"
        if aba_concluidas:
            self._mudar_aba(True)

        collapsed = self.config.get("state", "collapsed", fallback="false") == "true"
        if collapsed:
            self._toggle_collapse()