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
from PyQt6.QtCore import Qt, QUrl, QSize, pyqtSignal, QPropertyAnimation, QRect, QEasingCurve
from PyQt6.QtGui import QColor, QFont, QCursor, QShortcut, QKeySequence
from PyQt6.QtWidgets import QGraphicsDropShadowEffect
from PyQt6.QtMultimedia import QSoundEffect

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
        self._tarefa_em_edicao_id = None

        self.opacidade_atual = self.config.getint("window", "opacidade", fallback=95) / 100.0
        self.mostrar_concluidas = False

        self.som_conclusao = QSoundEffect()
        self.som_conclusao.setSource(QUrl.fromLocalFile("assets/success.wav"))
        self.som_conclusao.setVolume(0.25)

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

        # --- CORREÇÃO: Stacked Widget e Criação das 4 Páginas ---
        self.stacked = QStackedWidget()
        self.main_layout.addWidget(self.stacked)

        self.page_tarefas = QWidget()
        self.page_configs = QWidget()
        self.page_form = QWidget()
        self.page_view = QWidget()  # NOVA PÁGINA

        self._build_page_tarefas()
        self._build_page_configs()
        self._build_page_form()
        self._build_page_view()     # CONSTROI A NOVA PÁGINA

        self.stacked.addWidget(self.page_tarefas)
        self.stacked.addWidget(self.page_configs)
        self.stacked.addWidget(self.page_form)
        self.stacked.addWidget(self.page_view) # ÍNDICE 3

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
        self.btn_abrir_form.clicked.connect(self._mostrar_form_criacao)

        search_lay.addWidget(self.input_pesquisa, stretch=1)
        search_lay.addWidget(self.btn_abrir_form)
        layout.addWidget(self.search_container)

        # NOVO: Atalho de Teclado (Ctrl + N)
        self.atalho_nova_tarefa = QShortcut(QKeySequence("Ctrl+N"), self.page_tarefas)
        self.atalho_nova_tarefa.activated.connect(self._mostrar_form_criacao)
        self.btn_abrir_form.setToolTip("Criar Nova Tarefa (Ctrl+N)")

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
        self.filtro_delegadas = QPushButton("Delegadas")

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

        self.lbl_titulo_form = QLabel("<b>Nova Tarefa</b>")
        self.lbl_titulo_form.setFont(QFont("Segoe UI", 12))
        layout.addWidget(self.lbl_titulo_form)

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

        # Eventos
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

        self.atalho_fechar_form = QShortcut(QKeySequence("Esc"), self.page_form)
        self.atalho_fechar_form.activated.connect(self._esconder_form_criacao)

    # ------------------------------------------------------------------ #
    #  Página 3: Formulário de Detalhes (Visualização)
    # ------------------------------------------------------------------ #
    def _build_page_view(self):
        layout = QVBoxLayout(self.page_view)
        layout.setSpacing(10)
        
        header = QHBoxLayout()
        btn_voltar = QPushButton("❮ Voltar")
        btn_voltar.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_voltar.setStyleSheet("background: transparent; color: #63B3ED; font-weight: bold; border: none; font-size: 13px;")
        btn_voltar.clicked.connect(self._esconder_form_visualizacao)
        header.addWidget(btn_voltar)
        header.addStretch()
        layout.addLayout(header)

        self.view_titulo = QLabel()
        self.view_titulo.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.view_titulo.setWordWrap(True)
        layout.addWidget(self.view_titulo)

        self.view_detalhes = QLabel()
        self.view_detalhes.setWordWrap(True)
        self.view_detalhes.setStyleSheet("font-size: 13px; line-height: 1.6;")
        layout.addWidget(self.view_detalhes)
        
        layout.addStretch()

        self.btn_view_play = QPushButton()
        self.btn_view_play.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_view_play.clicked.connect(self._toggle_play_from_view)
        layout.addWidget(self.btn_view_play)
        
        self.view_tarefa_atual_id = None
        
        self.atalho_fechar_view = QShortcut(QKeySequence("Esc"), self.page_view)
        self.atalho_fechar_view.activated.connect(self._esconder_form_visualizacao)

    def _mostrar_form_visualizacao(self, tarefa_id: str):
        api_key = self.config.get("api", "api_key", fallback="")
        t = self.db.buscar_por_id(tarefa_id, api_key)
        if not t:
            return

        self.view_tarefa_atual_id = tarefa_id
        self.view_titulo.setText(t.titulo)
        
        status = "✅ Concluída" if t.concluida else "⏳ Pendente"
        prioridade = "Alta ⚡" if t.prioridade == "alta" else "Normal"
        escopo = "🏢 Escritório" if t.escopo == "escritorio" else "👤 Particular"
        
        detalhes = f"<b>Status:</b> {status}<br><br>"
        detalhes += f"<b>Prioridade:</b> {prioridade}<br><br>"
        detalhes += f"<b>Origem:</b> {escopo}<br><br>"
        
        if getattr(t, 'data_vencimento', ''):
            detalhes += f"<b>Vencimento:</b> {t.data_vencimento}<br><br>"
        
        if getattr(t, 'link_anexo', ''):
            detalhes += f"<b>Anexo/Link:</b> <a href='{t.link_anexo}' style='color: #63B3ED;'>{t.link_anexo}</a><br><br>"
            
        if getattr(t, 'delegado_para', ''):
            detalhes += f"<b>Delegado para:</b> {t.delegado_para}<br><br>"

        self.view_detalhes.setText(detalhes)
        self.view_detalhes.setOpenExternalLinks(True)
        
        is_playing = getattr(t, 'em_andamento', False)
        self._atualizar_btn_play_view(is_playing)

        self.stacked.setCurrentIndex(3)
        
        self.anim_view = QPropertyAnimation(self.page_view, b"geometry")
        self.anim_view.setDuration(250)
        geom = self.stacked.geometry()
        self.anim_view.setStartValue(QRect(geom.width(), 0, geom.width(), geom.height()))
        self.anim_view.setEndValue(QRect(0, 0, geom.width(), geom.height()))
        self.anim_view.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim_view.start()

    def _esconder_form_visualizacao(self):
        self.stacked.setCurrentIndex(0)
        
    def _atualizar_btn_play_view(self, is_playing: bool):
        if is_playing:
            self.btn_view_play.setText("⏸ Pausar Tarefa (Em andamento)")
            self.btn_view_play.setStyleSheet("background-color: #E74C3C; color: white; padding: 12px; border-radius: 8px; font-weight: bold; font-size: 13px;")
        else:
            self.btn_view_play.setText("▶ Iniciar Tarefa (Dar play)")
            self.btn_view_play.setStyleSheet("background-color: #3182CE; color: white; padding: 12px; border-radius: 8px; font-weight: bold; font-size: 13px;")

    def _toggle_play_from_view(self):
        if not self.view_tarefa_atual_id:
            return
        api_key = self.config.get("api", "api_key", fallback="")
        t = self.db.buscar_por_id(self.view_tarefa_atual_id, api_key)
        if t:
            novo_estado = not getattr(t, 'em_andamento', False)
            t.em_andamento = novo_estado
            self.db.atualizar(t)
            self._atualizar_btn_play_view(novo_estado)
            self._carregar_tarefas()

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
        c = get_palette(self.tema_atual)
        self.lbl_logo.setStyleSheet(f"color: {c['text_primary']};")
        self.btn_config.setStyleSheet(f"color: {c['text_secondary']};")
        self.btn_collapse.setStyleSheet(f"font-weight: normal; color: {c['text_secondary']};")

        self.btn_expand.setStyleSheet(
            f"background-color: {c['expand_bg']}; color: {c['text_secondary']};"
            f"border-radius: 8px; font-size: 14px;"
            f"border: 1px solid {c['border_container']};"
        )

        self.btn_voltar.setStyleSheet(
            f"background-color: {c['bg_voltar']}; color: white;"
            "padding: 8px; border-radius: 8px; font-weight: 500;"
        )

        self.lbl_contador.setStyleSheet(
            "background-color: #E74C3C; color: white; "
            "border-radius: 10px; padding: 2px 7px; "
            "font-size: 11px; font-weight: bold;"
        )

        self.lbl_versao.setStyleSheet(f"color: {c['text_version']};")
        self.lbl_legal.setStyleSheet(f"color: {c['text_version']};")

    def _atualizar_contadores(self):
        pendentes = sum(1 for t in self.tarefas if not t.get("concluida", False))
        self.lbl_contador.setText(str(pendentes))
        self.lbl_contador.setVisible(pendentes > 0)
        
        if pendentes > 0:
            self.btn_expand.setText(f"❮   {pendentes}")
        else:
            self.btn_expand.setText("❮")

    # ================================================================== #
    #  AÇÕES DO FORMULÁRIO DE CRIAÇÃO
    # ================================================================== #
    def _mostrar_form_criacao(self):
        self._tarefa_em_edicao_id = None  # Modo Criação
        self.btn_salvar_tarefa.setText("Criar Tarefa")
        self.lbl_titulo_form.setText("<b>Nova Tarefa</b>") # Adicione um name no QLabel se necessário

        self.stacked.setCurrentIndex(2)
        
        self._limpar_form()

        self.anim = QPropertyAnimation(self.page_form, b"geometry")
        self.anim.setDuration(250)
        geom = self.stacked.geometry()
        self.anim.setStartValue(QRect(geom.width(), 0, geom.width(), geom.height()))
        self.anim.setEndValue(QRect(0, 0, geom.width(), geom.height()))
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.start()
        
        # Correção: Seleciona "Hoje" por padrão ao abrir
        self._select_date(self.btn_date_hoje)
        self.form_titulo.setFocus()

    def _esconder_form_criacao(self):
        self.stacked.setCurrentIndex(0)
        self.form_titulo.clear()
        self.form_link.clear()
        self.form_delegar.clear()
        for b in self._date_btns: 
            b.setChecked(False)

    def _smart_input_parser(self, text):
        if "#urgente" in text.lower() or "#alta" in text.lower():
            self._select_tag(self._prior_tags, self.form_tag_alta)
        
        if "@escritorio" in text.lower():
            self._select_tag(self._escopo_tags, self.form_tag_escritorio)

    def _select_date(self, selected_btn):
        for btn in self._date_btns:
            # Força o estado True apenas no botão clicado
            is_active = (btn == selected_btn)
            btn.setChecked(is_active)
            
            # Atualiza a classe CSS para mudar a cor
            btn.setProperty("class", "ToggleTag Active" if is_active else "ToggleTag")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _editar_tarefa(self, tarefa_id: str):
        """Preenche o formulário com dados existentes para edição."""
        api_key = self.config.get("api", "api_key", fallback="")
        t = self.db.buscar_por_id(tarefa_id, api_key)
        if not t: 
            return

        self._tarefa_em_edicao_id = tarefa_id
        self.btn_salvar_tarefa.setText("Salvar Alterações")
        self.lbl_titulo_form.setText("<b>Editar Tarefa</b>")
        
        # Preenche os campos de texto
        self.form_titulo.setText(t.titulo)
        self.form_link.setText(t.link_anexo if t.link_anexo else "")
        self.form_delegar.setText(t.delegado_para if t.delegado_para else "")
        
        # Seleciona as tags de Escopo
        tag_escopo = self.form_tag_escritorio if t.escopo == "escritorio" else self.form_tag_minha
        self._select_tag(self._escopo_tags, tag_escopo)
        
        # Seleciona as tags de Prioridade
        tag_prior = self.form_tag_alta if t.prioridade == "alta" else self.form_tag_normal
        self._select_tag(self._prior_tags, tag_prior)

        # Reseta botões de data (seleção manual se necessário)
        for btn in self._date_btns: 
            btn.setChecked(False)
            btn.setProperty("class", "ToggleTag")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        self.stacked.setCurrentIndex(2)
        self._animar_pagina(self.page_form)
        self.form_titulo.setFocus()

    def _animar_pagina(self, pagina):
        """Executa a animação de deslize lateral para as páginas do formulário."""
        self.anim_geral = QPropertyAnimation(pagina, b"geometry")
        self.anim_geral.setDuration(250)
        geom = self.stacked.geometry()
        self.anim_geral.setStartValue(QRect(geom.width(), 0, geom.width(), geom.height()))
        self.anim_geral.setEndValue(QRect(0, 0, geom.width(), geom.height()))
        self.anim_geral.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim_geral.start()

    def _salvar_nova_tarefa_form(self):
        texto = self.form_titulo.text()
        texto_limpo = re.sub(r'#\w+|@\w+', '', texto).strip()
        if not texto_limpo: return

        api_key = self.config.get("api", "api_key", fallback="")
        
        # Se estiver editando, busca a tarefa original; senão cria uma nova
        if self._tarefa_em_edicao_id:
            tarefa = self.db.buscar_por_id(self._tarefa_em_edicao_id, api_key)
            tarefa.titulo = texto_limpo
        else:
            tarefa = Tarefa(titulo=texto_limpo, api_key=api_key)

        # Atualiza os demais campos
        tarefa.escopo = "escritorio" if self.form_tag_escritorio.isChecked() else "minha"
        tarefa.prioridade = "alta" if self.form_tag_alta.isChecked() else "normal"
        tarefa.link_anexo = self.form_link.text().strip()
        tarefa.delegado_para = self.form_delegar.text().strip()
        
        # Lógica de Data
        hoje = datetime.now()
        if self.btn_date_hoje.isChecked():
            tarefa.data_vencimento = hoje.strftime("%Y-%m-%d")
        elif self.btn_date_amanha.isChecked():
            tarefa.data_vencimento = (hoje + timedelta(days=1)).strftime("%Y-%m-%d")

        # Persiste no banco
        if self._tarefa_em_edicao_id:
            self.db.atualizar(tarefa)
        else:
            self.db.inserir(tarefa)

        self._esconder_form_criacao()
        self._carregar_tarefas()

    def _limpar_form(self):
        self.form_titulo.clear()
        self.form_link.clear()
        self.form_delegar.clear()

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

            # Se a tarefa acabou de ser concluída, toca o som de sucesso
            if concluida:
                self.som_conclusao.play()

            self._carregar_tarefas()

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
                card.view_requested.connect(self._mostrar_form_visualizacao)

                item = QListWidgetItem(self.lista_tarefas)
                item.setData(Qt.ItemDataRole.UserRole, tarefa["id"])
                item.setSizeHint(QSize(0, 48))
                self.lista_tarefas.setItemWidget(item, card)

        self._atualizar_contadores()

    def _sincronizar_ordem(self):
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