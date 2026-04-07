"""
Detecção do tema do sistema operacional Windows.
"""
import logging

logger = logging.getLogger(__name__)


def detectar_tema_sistema() -> str:
    """Retorna 'dark' ou 'light' baseado no tema do Windows."""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        return "light" if value == 1 else "dark"
    except Exception as e:
        logger.warning("Não foi possível detectar tema do sistema: %s", e)
        return "dark"


def resolver_tema(modo: str) -> str:
    """Converte modo ('sistema', 'escuro', 'claro') para tema efetivo ('dark'/'light')."""
    if modo == "claro":
        return "light"
    if modo == "escuro":
        return "dark"
    return detectar_tema_sistema()
