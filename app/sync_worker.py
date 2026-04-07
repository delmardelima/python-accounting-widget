"""
Worker de sincronização em background via QThread.

Ciclo:
  1. Push: envia operações pendentes (sync_queue) para a API
  2. Pull: baixa lista completa da API e faz upsert no SQLite
"""
import logging
from datetime import datetime, timezone, timedelta
from PyQt6.QtCore import QThread, pyqtSignal

from app.database import Database
from app.api_client import ApiClient
import requests

logger = logging.getLogger(__name__)


class SyncWorker(QThread):
    """Thread de sincronização API ↔ SQLite."""

    sync_completed = pyqtSignal()        # Sincronização OK
    sync_error = pyqtSignal(str)         # Erro (msg)
    dados_atualizados = pyqtSignal()     # Dados locais mudaram -> UI refresh
    notification_ready = pyqtSignal(str, str) # title, message

    def __init__(self, db: Database, api: ApiClient, intervalo: int = 30):
        super().__init__()
        self.db = db
        self.api = api
        self.intervalo = intervalo  # segundos
        self._rodando = True
        self._notificados_atraso = set() # ids de tarefas atrasadas já notificadas

    # ------------------------------------------------------------------ #
    #  Ciclo principal
    # ------------------------------------------------------------------ #
    def run(self):
        logger.info("SyncWorker iniciado (intervalo=%ds)", self.intervalo)
        while self._rodando:
            try:
                self._push()
                mudou = self._pull()
                if mudou:
                    self.dados_atualizados.emit()
                self.sync_completed.emit()
            except Exception as e:
                logger.error("Erro no ciclo de sync: %s", e, exc_info=True)
                self.sync_error.emit(str(e))

            # Espera interruptível
            for _ in range(self.intervalo * 2):
                if not self._rodando:
                    break
                self.msleep(500)

        logger.info("SyncWorker finalizado.")

    def parar(self):
        self._rodando = False
        self.wait(5000)

    # ------------------------------------------------------------------ #
    #  Push: local → API
    # ------------------------------------------------------------------ #
    def _push(self):
        api_key = self.api._session.headers.get("X-API-Key", "")
        pendencias = self.db.listar_pendencias(api_key)
        if not pendencias:
            return

        logger.info("Push: %d pendências para enviar", len(pendencias))

        for p in pendencias:
            sucesso = False
            descartar = False  # NOVO: Controle para ignorar sem perder prioridade local
            acao = p["acao"]
            payload = p["payload"]
            tarefa_id = p["tarefa_id"]

            try:
                if acao == "update":
                    if not tarefa_id.startswith(("TASK-", "SOL-", "TK-")):
                        logger.debug("Ação 'update' puramente local %s ignorada.", tarefa_id)
                        descartar = True
                    elif "concluida" in payload and payload["concluida"] is True:
                        sucesso = self.api.atualizar_status(tarefa_id, "concluida")
                    else:
                        sucesso = self.api.editar(tarefa_id, payload)
                elif acao == "delete":
                    if not tarefa_id.startswith(("TASK-", "SOL-", "TK-")):
                        descartar = True
                    else:
                        sucesso = self.api.atualizar_status(tarefa_id, "excluida")
                else:
                    descartar = True
            except requests.exceptions.HTTPError as e:
                # O servidor recusou a alteração (4xx).
                logger.warning("Erro HTTP %d ao enviar pendência %d (Tarefa: %s). Será descartada. %s", 
                               e.response.status_code if e.response else 400, p["id"], tarefa_id, e)
                descartar = True

            # LÓGICA DE RESOLUÇÃO SEPARADA
            if sucesso:
                self.db.remover_pendencia(p["id"])
                # Se a API aceitou, podemos desmarcar a flag local
                self.db.limpar_modificada_localmente(tarefa_id)
                logger.debug("Pendência %d resolvida com sucesso (%s)", p["id"], acao)
            elif descartar:
                self.db.remover_pendencia(p["id"])
                # IMPORTANTE: NÃO limpamos a flag 'modificada_localmente'.
                # A pendência sai da fila (destrava), mas o banco local mantém a edição protegida contra o Pull!
                logger.debug("Pendência %d descartada e retida no local (%s)", p["id"], acao)
            else:
                logger.warning("Falha ao enviar pendência %d, tentará novamente", p["id"])
                break  # Para na primeira falha real (ex: sem internet)
            
    # ------------------------------------------------------------------ #
    #  Pull: API → local
    # ------------------------------------------------------------------ #
    def _pull(self) -> bool:
        """Retorna True se houve alterações."""
        dados = self.api.listar() # O _pull agora usa .listar() que na verdade faz GET /sync
        if dados is None:
            return False  # Offline
            
        api_key = self.api._session.headers.get("X-API-Key", "")

        # Tarefas locais antes do upsert
        locais_antes = {t.id: t for t in self.db.listar(api_key)}
        remotos_ids = {d.get("id") for d in dados}

        # Verificação para notificações antes do upsert
        for d in dados:
            tid = d.get("id")
            prioridade = d.get("prioridade", "normal")
            escopo = d.get("escopo", "minha")
            concluida = d.get("concluida", False)
            titulo = d.get("titulo", d.get("nome", ""))

            # 1. Nova tarefa urgente no escritório
            if tid not in locais_antes:
                if prioridade == "alta" and escopo == "escritorio" and not concluida:
                    self.notification_ready.emit(
                        "Nova Tarefa Urgente",
                        f"O escritório possui uma nova tarefa urgente:\n{titulo}"
                    )
            # 2. Tarefa concluída prioritária
            else:
                old_task = locais_antes[tid]
                if not old_task.concluida and concluida and prioridade == "alta":
                    self.notification_ready.emit(
                        "Tarefa Urgente Concluída",
                        f"Tarefa de alta prioridade foi concluída:\n{titulo}"
                    )

        # Upsert
        self.db.upsert_em_lote(dados, api_key)

        # (apenas as que já estavam sincronizadas e não foram modificadas/excluidas localmente)
        local_tasks = self.db.listar_com_excluidas(api_key)
        for tarefa in local_tasks:
            if tarefa.sincronizado and tarefa.id not in remotos_ids:
                if not tarefa.modificada_localmente:
                    # Se foi removida no backend e o usuário não editou localmente.
                    self.db._conn.execute("DELETE FROM tarefas WHERE id=?", (tarefa.id,))
                    self.db._conn.commit()

        locais_depois = {t.id for t in self.db.listar(api_key)}
        mudou = set(locais_antes.keys()) != locais_depois or bool(dados)

        # 3. Verificação de tarefas atrasadas (após upsert)
        now = datetime.now(timezone.utc)
        for tarefa in self.db.listar(api_key):
            if not tarefa.concluida and tarefa.prioridade == "alta":
                try:
                    # fromisoformat não lida bem com "Z", converto se necessário
                    criado_str = tarefa.criado_em.replace("Z", "+00:00")
                    criado_dt = datetime.fromisoformat(criado_str)
                    
                    if now - criado_dt > timedelta(hours=2):
                        if tarefa.id not in self._notificados_atraso:
                            self.notification_ready.emit(
                                "Tarefa Atrasada",
                                f"Atenção: Tarefa prioritária pendente há mais de 2h:\n{tarefa.titulo}"
                            )
                            self._notificados_atraso.add(tarefa.id)
                except Exception as e:
                    logger.warning("Falha ao parsear data %s para verificação de atraso: %s", tarefa.criado_em, e)

        return mudou
