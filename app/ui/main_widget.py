"""
Widget principal de tarefas — UI reestruturada com suporte a temas.
"""
import logging

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QStackedWidget, QSlider,
    QListWidgetItem,
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QCursor
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
        self.base_collapsed_size = QSize(40, 40)

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

        # Stacked: tarefas | configs
        self.stacked = QStackedWidget()
        self.main_layout.addWidget(self.stacked)

        self.page_tarefas = QWidget()
        self.page_configs = QWidget()
        self._build_page_tarefas()
        self._build_page_configs()
        self.stacked.addWidget(self.page_tarefas)
        self.stacked.addWidget(self.page_configs)

        # Aplica estilos inline baseados no tema
        self._aplicar_estilos_tema()

    # ------------------------------------------------------------------ #
    #  Página de tarefas
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

        header.addWidget(self.lbl_logo, stretch=1)
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

        # --- Bloco de criação ---
        self.input_container = QWidget()
        input_v = QVBoxLayout(self.input_container)
        input_v.setContentsMargins(0, 0, 0, 0)
        input_v.setSpacing(6)

        # Input + botão "+"
        input_row = QHBoxLayout()
        input_row.setSpacing(6)
        self.input_tarefa = QLineEdit()
        self.input_tarefa.setObjectName("TaskInput")
        self.input_tarefa.setPlaceholderText("Nova tarefa...")
        self.input_tarefa.returnPressed.connect(self._adicionar_tarefa)

        self.btn_add = QPushButton("+")
        self.btn_add.setObjectName("BtnAddTask")
        self.btn_add.setFixedSize(34, 34)
        self.btn_add.setFont(QFont("Segoe UI", 15, QFont.Weight.Normal))
        self.btn_add.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_add.setToolTip("Adicionar tarefa")
        self.btn_add.clicked.connect(self._adicionar_tarefa)

        input_row.addWidget(self.input_tarefa, stretch=1)
        input_row.addWidget(self.btn_add)
        input_v.addLayout(input_row)

        # Toggle tags (escopo + prioridade)
        tags_row = QHBoxLayout()
        tags_row.setSpacing(4)

        self.tag_minha = QPushButton("Particular")
        self.tag_escritorio = QPushButton("Escritório")
        self.tag_normal = QPushButton("Normal")
        self.tag_alta = QPushButton("Alta ⚡")

        self._escopo_tags = [self.tag_minha, self.tag_escritorio]
        self._prior_tags = [self.tag_normal, self.tag_alta]

        for tag in self._escopo_tags + self._prior_tags:
            tag.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            tag.setProperty("class", "ToggleTag")

        # Defaults activos (serão sobrescritos por _restaurar_estado)
        self.tag_minha.setProperty("class", "ToggleTag Active")
        self.tag_normal.setProperty("class", "ToggleTag Active")

        self.tag_minha.clicked.connect(lambda: self._select_tag(self._escopo_tags, self.tag_minha))
        self.tag_escritorio.clicked.connect(lambda: self._select_tag(self._escopo_tags, self.tag_escritorio))
        self.tag_normal.clicked.connect(lambda: self._select_tag(self._prior_tags, self.tag_normal))
        self.tag_alta.clicked.connect(lambda: self._select_tag(self._prior_tags, self.tag_alta))

        tags_row.addWidget(self.tag_minha)
        tags_row.addWidget(self.tag_escritorio)
        tags_row.addSpacing(8)
        tags_row.addWidget(self.tag_normal)
        tags_row.addWidget(self.tag_alta)
        tags_row.addStretch()

        input_v.addLayout(tags_row)
        layout.addWidget(self.input_container)

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
        self.filtro_alta = QPushButton("Alta ⚡")

        self.botoes_filtro = [
            self.filtro_tudo, self.filtro_minhas,
            self.filtro_escritorio, self.filtro_alta,
        ]
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
    #  Página de configurações
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
    #  TEMA
    # ================================================================== #
    def _on_tema_clicked(self):
        """Callback dos botões de tema."""
        remetente = self.sender()
        modo = self._mapa_tema.get(remetente, "sistema")
        self._mudar_tema(modo)

    def _mudar_tema(self, modo: str):
        """Aplica e persiste o modo de tema escolhido."""
        self.modo_tema = modo
        self.tema_atual = resolver_tema(modo)

        # Salvar
        self.config.set("state", "tema", modo)
        self.config.save()

        # Aplicar
        self.setStyleSheet(get_stylesheet(self.tema_atual))
        self._aplicar_estilos_tema()
        self._atualizar_seletor_tema()
        self._atualizar_lista()

    def _atualizar_seletor_tema(self):
        """Destaca o botão do tema ativo."""
        mapa_inverso = {v: k for k, v in self._mapa_tema.items()}
        for btn in self._botoes_tema:
            if btn == mapa_inverso.get(self.modo_tema):
                btn.setProperty("class", "ThemeBtn Active")
            else:
                btn.setProperty("class", "ThemeBtn")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

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

        # Labels de versão / legal
        self.lbl_versao.setStyleSheet(f"color: {c['text_version']};")
        self.lbl_legal.setStyleSheet(f"color: {c['text_version']};")

    # ================================================================== #
    #  DADOS
    # ================================================================== #
    def _carregar_tarefas(self):
        """Carrega tarefas do SQLite e popula a lista."""
        api_key = self.config.get("api", "api_key", fallback="")
        lista = self.db.listar(api_key)
        self.tarefas = [t.to_dict() for t in lista]
        self._atualizar_lista()

    def refresh_do_sync(self):
        """Chamado pelo SyncWorker quando há dados novos da API."""
        self._carregar_tarefas()

    # ================================================================== #
    #  AÇÕES
    # ================================================================== #
    def _adicionar_tarefa(self):
        texto = self.input_tarefa.text().strip()
        if not texto:
            return

        escopo = "escritorio" if "Active" in (self.tag_escritorio.property("class") or "") else "minha"
        prioridade = "alta" if "Active" in (self.tag_alta.property("class") or "") else "normal"
        api_key = self.config.get("api", "api_key", fallback="")

        tarefa = Tarefa(titulo=texto, escopo=escopo, prioridade=prioridade, api_key=api_key)
        self.db.inserir(tarefa)

        self.input_tarefa.clear()
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
    #  TOGGLE TAGS
    # ================================================================== #
    def _select_tag(self, grupo: list, ativo: QPushButton):
        for btn in grupo:
            btn.setProperty("class", "ToggleTag")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        ativo.setProperty("class", "ToggleTag Active")
        ativo.style().unpolish(ativo)
        ativo.style().polish(ativo)

        # Persistir tags de criação
        if grupo == self._escopo_tags:
            valor = "escritorio" if ativo == self.tag_escritorio else "minha"
            self.config.set("state", "tag_escopo", valor)
        elif grupo == self._prior_tags:
            valor = "alta" if ativo == self.tag_alta else "normal"
            self.config.set("state", "tag_prioridade", valor)
        self.config.save()

    # ================================================================== #
    #  FILTROS / ABAS
    # ================================================================== #
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
            self.input_container.hide()
            self.filtros_container.hide()
        else:
            self.btn_pendentes.setProperty("class", "TabButton Active")
            self.btn_concluidas.setProperty("class", "TabButton")
            self.input_container.show()
            self.filtros_container.show()

        for btn in [self.btn_pendentes, self.btn_concluidas]:
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        self.config.set("state", "aba_concluidas", str(concluidas).lower())
        self.config.save()
        self._atualizar_lista()

    # ================================================================== #
    #  LISTA
    # ================================================================== #
    def _atualizar_lista(self):
        self.lista_tarefas.clear()
        c = get_palette(self.tema_atual)
        filtradas = []
        for t in self.tarefas:
            if t["concluida"] != self.mostrar_concluidas:
                continue
            if self.filtro_minhas.isChecked() and t.get("escopo") != "minha":
                continue
            if self.filtro_escritorio.isChecked() and t.get("escopo") != "escritorio":
                continue
            if self.filtro_alta.isChecked() and t.get("prioridade") != "alta":
                continue
            filtradas.append(t)

        if not filtradas:
            item = QListWidgetItem(self.lista_tarefas)
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            msg = "Nenhuma tarefa pendente" if not self.mostrar_concluidas else "Nenhuma tarefa concluída"
            lbl = QLabel(msg)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(
                f"color: {c['text_disabled']}; font-size: 12px; font-style: italic; margin-top: 20px;"
            )
            item.setSizeHint(QSize(0, 60))
            self.lista_tarefas.setItemWidget(item, lbl)
            return

        for tarefa in filtradas:
            card = TaskCard(tarefa, theme=self.tema_atual)
            card.state_changed.connect(self._alterar_status)
            card.delete_requested.connect(self._excluir_tarefa)
            card.edit_requested.connect(self._editar_tarefa)

            item = QListWidgetItem(self.lista_tarefas)
            item.setData(Qt.ItemDataRole.UserRole, tarefa["id"])
            item.setSizeHint(QSize(0, 48))
            self.lista_tarefas.setItemWidget(item, card)

    def _sincronizar_ordem(self):
        """Mescla persistência no banco com atualização da lista em memória."""
        nova_ordem_ids = []
        
        # 1. Identificar a nova ordem visual e persistir no SQLite
        for i in range(self.lista_tarefas.count()):
            uid = self.lista_tarefas.item(i).data(Qt.ItemDataRole.UserRole)
            if uid:
                nova_ordem_ids.append(uid)
                # Atualiza a coluna ordem_usuario no banco de dados local
                self.db._conn.execute(
                    "UPDATE tarefas SET ordem_usuario = ? WHERE id = ?",
                    (i, uid)
                )
        
        self.db._conn.commit()
        logger.info("Ordem do usuário persistida no SQLite local.")

        # 2. Mesclar na lista interna self.tarefas (Lógica da Versão 1)
        indices_na_memoria = []
        for idx, t in enumerate(self.tarefas):
            if t["id"] in nova_ordem_ids:
                indices_na_memoria.append(idx)

        # Cria um mapa dos objetos atuais para reposicioná-los
        mapa_objetos = {t["id"]: t for t in self.tarefas if t["id"] in nova_ordem_ids}
        
        # Reorganiza apenas os itens que estavam visíveis, mantendo os outros nos seus lugares
        for idx, nid in zip(indices_na_memoria, nova_ordem_ids):
            self.tarefas[idx] = mapa_objetos[nid]
            # Atualiza o campo no dicionário da memória para consistência
            self.tarefas[idx]["ordem_usuario"] = nova_ordem_ids.index(nid)

        # 3. Atualiza a UI sem precisar recarregar tudo do banco
        self._atualizar_lista()

    # ================================================================== #
    #  CONFIGURAÇÕES
    # ================================================================== #
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

    # ================================================================== #
    #  COLAPSAR / EXPANDIR
    # ================================================================== #
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

    # ================================================================== #
    #  ARRASTAR JANELA
    # ================================================================== #
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

    # ================================================================== #
    #  SALVAR POSIÇÃO AO FECHAR
    # ================================================================== #
    def closeEvent(self, event):
        # Salvar posição real (expandida) mesmo se colapsado
        if self.is_collapsed:
            offset = self.expanded_size.width() - self.collapsed_size.width()
            self.config.set("window", "pos_x", self.x() - offset)
        else:
            self.config.set("window", "pos_x", self.x())
        self.config.set("window", "pos_y", self.y())
        self.config.save()
        super().closeEvent(event)

    # ================================================================== #
    #  PERSISTÊNCIA DE ESTADO
    # ================================================================== #
    def _salvar_estado_filtros(self):
        """Salva o estado atual dos filtros no config.ini."""
        if self.filtro_minhas.isChecked():
            filtro = "minhas"
        elif self.filtro_escritorio.isChecked():
            filtro = "escritorio"
        else:
            filtro = "tudo"
        self.config.set("state", "filtro", filtro)
        self.config.set("state", "filtro_alta", str(self.filtro_alta.isChecked()).lower())
        self.config.save()

    def _restaurar_estado(self):
        """Restaura o estado salvo da UI a partir do config.ini."""
        # --- Tema ---
        self._atualizar_seletor_tema()

        # --- Filtros ---
        filtro = self.config.get("state", "filtro", fallback="tudo")
        self.filtro_tudo.setChecked(filtro == "tudo")
        self.filtro_minhas.setChecked(filtro == "minhas")
        self.filtro_escritorio.setChecked(filtro == "escritorio")

        filtro_alta = self.config.get("state", "filtro_alta", fallback="false") == "true"
        self.filtro_alta.setChecked(filtro_alta)

        # --- Tags de criação ---
        tag_escopo = self.config.get("state", "tag_escopo", fallback="minha")
        tag_ativa_escopo = self.tag_escritorio if tag_escopo == "escritorio" else self.tag_minha
        self._select_tag(self._escopo_tags, tag_ativa_escopo)

        tag_prior = self.config.get("state", "tag_prioridade", fallback="normal")
        tag_ativa_prior = self.tag_alta if tag_prior == "alta" else self.tag_normal
        self._select_tag(self._prior_tags, tag_ativa_prior)

        # --- Aba ativa ---
        aba_concluidas = self.config.get("state", "aba_concluidas", fallback="false") == "true"
        if aba_concluidas:
            self._mudar_aba(True)

        # --- Colapsado (restaurar por último para posição correta) ---
        collapsed = self.config.get("state", "collapsed", fallback="false") == "true"
        if collapsed:
            self._toggle_collapse()
