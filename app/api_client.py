"""
Cliente HTTP para a API de tarefas do servidor principal.
"""
import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# Timeout padrão para requisições (connect, read) em segundos
_TIMEOUT = (5, 10)


class ApiClient:
    """Consome endpoints REST do servidor de tarefas."""

    def __init__(self, base_url: str, api_key: str = ""):
        self.base_url = base_url.rstrip("/")
        self._session = requests.Session()
        self._session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-API-Key": api_key,
        })

    # ------------------------------------------------------------------ #
    #  Verificação
    # ------------------------------------------------------------------ #
    def verificar_conexao(self) -> bool:
        try:
            r = self._session.get(
                f"{self.base_url}/tarefas/api/widget/sync",
                timeout=_TIMEOUT,
            )
            return r.status_code == 200
        except Exception:
            return False

    # ------------------------------------------------------------------ #
    #  Sync e CRUD
    # ------------------------------------------------------------------ #
    def listar(self) -> Optional[list[dict]]:
        """Sincronização geral de demandas."""
        try:
            r = self._session.get(
                f"{self.base_url}/tarefas/api/widget/sync",
                timeout=_TIMEOUT,
            )
            r.raise_for_status()
            dados = r.json()
            if dados.get("success"):
                return dados.get("tasks", [])
            else:
                logger.warning("API erro em listar: %s", dados.get("message"))
                return None
        except Exception as e:
            logger.warning("API indisponível (listar): %s", e)
            return None

    def editar(self, tarefa_id: str, tarefa_dict: dict) -> bool:
        """Editar informações (apenas TASK-)."""
        payload = {}
        for chave in ["nome", "titulo", "descricao", "prioridade"]:
            if chave in tarefa_dict:
                nova_chave = "nome" if chave == "titulo" else chave
                payload[nova_chave] = tarefa_dict[chave]

        try:
            r = self._session.put(
                f"{self.base_url}/tarefas/api/widget/task/{tarefa_id}/edit",
                json=payload,
                timeout=_TIMEOUT,
            )
            r.raise_for_status()
            dados = r.json()
            return dados.get("success", False)
        except requests.exceptions.HTTPError as e:
            if e.response is not None and 400 <= e.response.status_code < 500:
                raise e
            logger.warning("API erro HTTP (editar): %s", e)
            return False
        except Exception as e:
            logger.warning("API indisponível (editar): %s", e)
            return False

    def atualizar_status(self, tarefa_id: str, status: str) -> bool:
        """Atualiza o status para concluida ou excluida."""
        try:
            r = self._session.post(
                f"{self.base_url}/tarefas/api/widget/task/{tarefa_id}/status",
                json={"status": status},
                timeout=_TIMEOUT,
            )
            r.raise_for_status()
            dados = r.json()
            return dados.get("success", False)
        except requests.exceptions.HTTPError as e:
            if e.response is not None and 400 <= e.response.status_code < 500:
                raise e  # OBRIGATÓRIO: Repassa o 400 para o Worker identificar e descartar
            logger.warning("API erro HTTP (atualizar_status): %s", e)
            return False
        except requests.exceptions.RequestException as e: # <--- Trocar 'Exception' por 'RequestException'
            logger.warning("API indisponível (atualizar_status): %s", e)
            return False
