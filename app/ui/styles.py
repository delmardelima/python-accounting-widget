"""
Stylesheets temáticos — dark & light, estilo Windows 11 Fluent.
"""

# ================================================================== #
#  PALETAS DE CORES
# ================================================================== #

_DARK = {
    # Superfícies
    "bg_container": "rgba(23, 25, 35, 230)",
    "bg_input": "rgba(0, 0, 0, 40)",
    "bg_input_focus": "rgba(0, 0, 0, 60)",
    "bg_card": "rgba(255, 255, 255, 4)",
    "bg_card_hover": "rgba(255, 255, 255, 8)",
    "bg_btn_hover": "rgba(255, 255, 255, 10)",
    "bg_btn_icon_hover": "rgba(255, 255, 255, 15)",
    "bg_tag": "rgba(255, 255, 255, 8)",
    "bg_tag_hover": "rgba(255, 255, 255, 15)",
    "bg_filter": "rgba(255, 255, 255, 8)",
    "bg_filter_hover": "rgba(255, 255, 255, 15)",
    "bg_scrollbar": "transparent",
    "bg_scrollbar_handle": "rgba(255, 255, 255, 25)",
    "bg_scrollbar_handle_hover": "rgba(255, 255, 255, 45)",
    "bg_slider_groove": "rgba(255, 255, 255, 15)",
    "bg_divider": "rgba(255, 255, 255, 10)",
    "bg_btn_add": "rgba(66, 153, 225, 80)",
    "bg_btn_add_hover": "rgba(66, 153, 225, 120)",
    "bg_btn_add_pressed": "rgba(66, 153, 225, 160)",
    "bg_voltar": "rgba(66, 153, 225, 80)",
    # Accent
    "accent": "#63B3ED",
    "accent_bg": "rgba(66, 153, 225, 30)",
    "accent_bg_tag": "rgba(66, 153, 225, 25)",
    "accent_border": "rgba(66, 153, 225, 50)",
    "accent_input_border": "rgba(66, 153, 225, 60)",
    "accent_icon_bg": "rgba(66, 153, 225, 40)",
    # Texto
    "text_primary": "#E2E8F0",
    "text_secondary": "#A0AEC0",
    "text_muted": "#8896AB",
    "text_disabled": "#6B7A8D",
    "text_input": "white",
    # Bordas
    "border_container": "rgba(255, 255, 255, 20)",
    "border_input": "rgba(255, 255, 255, 12)",
    "border_tag": "rgba(255, 255, 255, 12)",
    "border_filter": "rgba(255, 255, 255, 8)",
    "border_card": "rgba(255, 255, 255, 8)",
    "border_card_hover": "rgba(66, 153, 225, 40)",
    "border_check": "#4A5568",
    # Outros
    "check_green": "#48BB78",
    "grip_color": "rgba(255, 255, 255, 40)",
    "tag_escritorio_bg": "rgba(66, 153, 225, 0.15)",
    "edit_bg": "rgba(0, 0, 0, 60)",
    "expand_bg": "rgba(23, 25, 35, 230)",
    # Config labels
    "text_concluida": "#718096",
    "text_version": "#5A6577",
    # Seletor de tema
    "theme_btn_bg": "rgba(255, 255, 255, 8)",
    "theme_btn_border": "rgba(255, 255, 255, 12)",
    "theme_btn_hover": "rgba(255, 255, 255, 15)",
    "theme_btn_active_bg": "rgba(66, 153, 225, 25)",
    "theme_btn_active_border": "rgba(66, 153, 225, 50)",
    "theme_btn_active_text": "#63B3ED",
}

_LIGHT = {
    # Superfícies
    "bg_container": "rgba(245, 247, 250, 245)",
    "bg_input": "rgba(0, 0, 0, 6)",
    "bg_input_focus": "rgba(0, 0, 0, 10)",
    "bg_card": "rgba(0, 0, 0, 3)",
    "bg_card_hover": "rgba(0, 0, 0, 6)",
    "bg_btn_hover": "rgba(0, 0, 0, 6)",
    "bg_btn_icon_hover": "rgba(0, 0, 0, 8)",
    "bg_tag": "rgba(0, 0, 0, 5)",
    "bg_tag_hover": "rgba(0, 0, 0, 8)",
    "bg_filter": "rgba(0, 0, 0, 5)",
    "bg_filter_hover": "rgba(0, 0, 0, 8)",
    "bg_scrollbar": "transparent",
    "bg_scrollbar_handle": "rgba(0, 0, 0, 15)",
    "bg_scrollbar_handle_hover": "rgba(0, 0, 0, 30)",
    "bg_slider_groove": "rgba(0, 0, 0, 12)",
    "bg_divider": "rgba(0, 0, 0, 8)",
    "bg_btn_add": "rgba(49, 130, 206, 200)",
    "bg_btn_add_hover": "rgba(49, 130, 206, 230)",
    "bg_btn_add_pressed": "rgba(49, 130, 206, 255)",
    "bg_voltar": "rgba(49, 130, 206, 200)",
    # Accent
    "accent": "#2B6CB0",
    "accent_bg": "rgba(49, 130, 206, 15)",
    "accent_bg_tag": "rgba(49, 130, 206, 12)",
    "accent_border": "rgba(49, 130, 206, 35)",
    "accent_input_border": "rgba(49, 130, 206, 50)",
    "accent_icon_bg": "rgba(49, 130, 206, 20)",
    # Texto
    "text_primary": "#1A202C",
    "text_secondary": "#4A5568",
    "text_muted": "#718096",
    "text_disabled": "#A0AEC0",
    "text_input": "#1A202C",
    # Bordas
    "border_container": "rgba(0, 0, 0, 10)",
    "border_input": "rgba(0, 0, 0, 12)",
    "border_tag": "rgba(0, 0, 0, 10)",
    "border_filter": "rgba(0, 0, 0, 8)",
    "border_card": "rgba(0, 0, 0, 6)",
    "border_card_hover": "rgba(49, 130, 206, 30)",
    "border_check": "#CBD5E0",
    # Outros
    "check_green": "#38A169",
    "grip_color": "rgba(0, 0, 0, 20)",
    "tag_escritorio_bg": "rgba(49, 130, 206, 0.10)",
    "edit_bg": "rgba(255, 255, 255, 200)",
    "expand_bg": "rgba(245, 247, 250, 240)",
    # Config labels
    "text_concluida": "#A0AEC0",
    "text_version": "#A0AEC0",
    # Seletor de tema
    "theme_btn_bg": "rgba(0, 0, 0, 5)",
    "theme_btn_border": "rgba(0, 0, 0, 10)",
    "theme_btn_hover": "rgba(0, 0, 0, 8)",
    "theme_btn_active_bg": "rgba(49, 130, 206, 12)",
    "theme_btn_active_border": "rgba(49, 130, 206, 35)",
    "theme_btn_active_text": "#2B6CB0",
}


def get_palette(theme: str) -> dict:
    """Retorna o dicionário de cores para o tema especificado."""
    return _LIGHT if theme == "light" else _DARK


# ================================================================== #
#  STYLESHEET GENERATOR
# ================================================================== #

def get_stylesheet(theme: str = "dark") -> str:
    """Retorna a stylesheet completa para o tema especificado."""
    c = get_palette(theme)
    return f"""
/* ============================================
   TEMA — WINDOWS 11 FLUENT
   ============================================ */

QWidget {{
    font-family: 'Segoe UI', -apple-system, sans-serif;
    color: {c['text_primary']};
}}

/* --- Container principal translúcido --- */
#MainContainer {{
    background-color: {c['bg_container']};
    border-radius: 16px;
    border: 1px solid {c['border_container']};
}}

/* --- Abas (Pendentes / Concluídas) --- */
QPushButton.TabButton {{
    background-color: transparent; border: none; color: {c['text_secondary']};
    font-weight: 600; font-size: 13px; padding: 6px 10px; border-radius: 8px;
}}
QPushButton.TabButton:hover {{ background-color: {c['bg_btn_hover']}; color: {c['text_primary']}; }}
QPushButton.TabButton.Active {{ background-color: {c['accent_bg']}; color: {c['accent']}; }}

/* --- Botões ícone --- */
QPushButton.IconButton {{
    background-color: transparent; border: none; font-size: 14px;
    border-radius: 6px; padding: 4px;
}}
QPushButton.IconButton:hover {{ background-color: {c['bg_btn_icon_hover']}; }}
QPushButton.IconButton:checked {{ background-color: {c['accent_icon_bg']}; }}

/* --- Toggle Tags (escopo / prioridade) --- */
QPushButton.ToggleTag {{
    background-color: {c['bg_tag']}; color: {c['text_muted']};
    border: 1px solid {c['border_tag']};
    border-radius: 4px; padding: 3px 10px;
    font-size: 11px; font-weight: 500;
}}
QPushButton.ToggleTag:hover {{
    background-color: {c['bg_tag_hover']}; color: {c['text_secondary']};
}}
QPushButton.ToggleTag.Active {{
    background-color: {c['accent_bg_tag']}; color: {c['accent']};
    border: 1px solid {c['accent_border']};
}}

/* --- Filtros (chips) --- */
QPushButton.FilterChip {{
    background-color: {c['bg_filter']}; color: {c['text_muted']};
    border: 1px solid {c['border_filter']};
    border-radius: 12px; padding: 3px 10px; font-size: 11px; font-weight: 500;
}}
QPushButton.FilterChip:hover {{ background-color: {c['bg_filter_hover']}; color: {c['text_secondary']}; }}
QPushButton.FilterChip:checked {{
    background-color: {c['accent_bg_tag']}; color: {c['accent']};
    border: 1px solid {c['accent_border']};
}}

/* --- Input de tarefa --- */
QLineEdit#TaskInput {{
    background-color: {c['bg_input']}; border: 1px solid {c['border_input']};
    border-radius: 8px; padding: 9px 14px; font-size: 13px; color: {c['text_input']};
}}
QLineEdit#TaskInput:focus {{ border: 1px solid {c['accent_input_border']}; background-color: {c['bg_input_focus']}; }}

/* --- Botão Adicionar (dentro do input) --- */
QPushButton#BtnAddTask {{
    background-color: {c['bg_btn_add']}; color: white;
    border: none; border-radius: 6px; font-size: 16px; font-weight: 600;
    padding: 0px;
}}
QPushButton#BtnAddTask:hover {{ background-color: {c['bg_btn_add_hover']}; }}
QPushButton#BtnAddTask:pressed {{ background-color: {c['bg_btn_add_pressed']}; }}

/* --- Lista de tarefas --- */
QListWidget {{ background: transparent; border: none; outline: none; }}
QListWidget::item {{ background: transparent; }}
QListWidget::item:selected {{ background: transparent; }}

/* --- Scrollbar fina --- */
QScrollBar:vertical {{ border: none; background: {c['bg_scrollbar']}; width: 4px; margin: 0px; }}
QScrollBar::handle:vertical {{ background: {c['bg_scrollbar_handle']}; border-radius: 2px; }}
QScrollBar::handle:vertical:hover {{ background: {c['bg_scrollbar_handle_hover']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ border: none; background: none; }}

/* --- Card de tarefa --- */
QFrame.TaskCard {{
    background-color: {c['bg_card']}; border-radius: 10px;
    border: 1px solid {c['border_card']}; margin-bottom: 3px;
}}
QFrame.TaskCard:hover {{
    background-color: {c['bg_card_hover']}; border: 1px solid {c['border_card_hover']};
}}

/* --- Checkbox --- */
QPushButton.CheckButton {{
    background-color: transparent; border: 1.5px solid {c['border_check']}; border-radius: 5px;
}}
QPushButton.CheckButton:hover {{ border-color: {c['accent']}; }}
QPushButton.CheckButton.Checked {{ background-color: {c['check_green']}; border-color: {c['check_green']}; color: white; }}

/* --- Divisória --- */
QFrame#Divider {{
    background-color: {c['bg_divider']};
    max-height: 1px; min-height: 1px;
    border: none;
}}

/* --- Slider --- */
QSlider::groove:horizontal {{
    background: {c['bg_slider_groove']}; height: 4px; border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {c['accent']}; width: 14px; height: 14px; margin: -5px 0;
    border-radius: 7px;
}}

/* --- Seletor de tema --- */
QPushButton.ThemeBtn {{
    background-color: {c['theme_btn_bg']}; color: {c['text_muted']};
    border: 1px solid {c['theme_btn_border']};
    border-radius: 6px; padding: 5px 10px;
    font-size: 11px; font-weight: 500;
}}
QPushButton.ThemeBtn:hover {{
    background-color: {c['theme_btn_hover']}; color: {c['text_secondary']};
}}
QPushButton.ThemeBtn.Active {{
    background-color: {c['theme_btn_active_bg']}; color: {c['theme_btn_active_text']};
    border: 1px solid {c['theme_btn_active_border']};
}}
"""
