"""
Gerenciamento de configurações via arquivo INI.
"""
import configparser
import os
import sys
import logging

logger = logging.getLogger(__name__)

_DEFAULTS = {
    "window": {
        "opacidade": "95",
        "pos_x": "-1",
        "pos_y": "30",
    },
    "api": {
        "base_url": "http://localhost:5000",
        "sync_interval_seconds": "30",
        "api_key": "",
    },
    "state": {
        "collapsed": "false",
        "aba_concluidas": "false",
        "filtro": "tudo",
        "filtro_alta": "false",
        "tag_escopo": "minha",
        "tag_prioridade": "normal",
        "tema": "sistema",
    },
}

if getattr(sys, 'frozen', False):
    app_data_path = os.path.join(os.getenv('APPDATA'), "Sagecont-Win")
else:
    app_data_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONFIG_PATH = os.path.join(app_data_path, "config.ini")

class Config:
    """Lê e salva configurações em config.ini."""

    def __init__(self, path: str = CONFIG_PATH):
        self.path = path
        self._parser = configparser.ConfigParser()
        self._carregar()

    # ---------- público ----------
    def get(self, section: str, key: str, fallback: str = "") -> str:
        return self._parser.get(section, key, fallback=fallback)

    def getint(self, section: str, key: str, fallback: int = 0) -> int:
        return self._parser.getint(section, key, fallback=fallback)

    def set(self, section: str, key: str, value):
        if not self._parser.has_section(section):
            self._parser.add_section(section)
        self._parser.set(section, key, str(value))

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                self._parser.write(f)
        except OSError as e:
            logger.error("Erro ao salvar config.ini: %s", e)

    # ---------- privado ----------
    def _carregar(self):
        if os.path.exists(self.path):
            self._parser.read(self.path, encoding="utf-8")
            logger.info("Config carregada de %s", self.path)
        else:
            logger.info("config.ini não encontrado, criando com defaults.")

        # Preenche valores ausentes com defaults
        for section, keys in _DEFAULTS.items():
            if not self._parser.has_section(section):
                self._parser.add_section(section)
            for key, val in keys.items():
                if not self._parser.has_option(section, key):
                    self._parser.set(section, key, val)

        self.save()
