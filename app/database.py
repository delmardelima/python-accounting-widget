"""
Repositório SQLite local — espelho da API.
"""
import sqlite3
import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from app.models import Tarefa

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sagecont.db")


class Database:
    """CRUD de tarefas + fila de sincronização."""

    def __init__(self, path: str = DB_PATH):
        self.path = path
        self._conn: Optional[sqlite3.Connection] = None
        self._conectar()
        self._criar_tabelas()

    # ------------------------------------------------------------------ #
    #  Conexão
    # ------------------------------------------------------------------ #
    def _conectar(self):
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL;")
        logger.info("SQLite conectado: %s", self.path)

    def _criar_tabelas(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS tarefas (
                id            TEXT PRIMARY KEY,
                titulo        TEXT NOT NULL,
                concluida     INTEGER DEFAULT 0,
                escopo        TEXT DEFAULT 'minha',
                prioridade    TEXT DEFAULT 'normal',
                criado_em     TEXT,
                atualizado_em TEXT,
                sincronizado  INTEGER DEFAULT 0,
                api_key       TEXT DEFAULT '',
                excluida      INTEGER DEFAULT 0,
                modificada_localmente INTEGER DEFAULT 0,
                ordem_usuario INTEGER DEFAULT 99999,
                em_andamento  INTEGER DEFAULT 0,
                data_vencimento TEXT DEFAULT '',
                link_anexo    TEXT DEFAULT '',
                delegado_para TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS sync_queue (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                acao       TEXT NOT NULL,
                tarefa_id  TEXT NOT NULL,
                payload    TEXT,
                criado_em  TEXT,
                api_key    TEXT DEFAULT ''
            );
        """)
        self._conn.commit()

        # Tenta aplicar a migração de esquema de forma segura para quem já tem a V1 compilada
        try:
            self._conn.execute("ALTER TABLE tarefas ADD COLUMN api_key TEXT DEFAULT ''")
            self._conn.execute("ALTER TABLE sync_queue ADD COLUMN api_key TEXT DEFAULT ''")
            self._conn.commit()
        except sqlite3.OperationalError:
            pass  # As colunas já existem
            
        try:
            self._conn.execute("ALTER TABLE tarefas ADD COLUMN excluida INTEGER DEFAULT 0")
            self._conn.execute("ALTER TABLE tarefas ADD COLUMN modificada_localmente INTEGER DEFAULT 0")
            self._conn.commit()
        except sqlite3.OperationalError:
            pass  # As colunas já existem

        try:
            self._conn.execute("ALTER TABLE tarefas ADD COLUMN ordem_usuario INTEGER DEFAULT 99999")
            self._conn.commit()
        except sqlite3.OperationalError:
            pass

        novas_colunas = {
            "em_andamento": "INTEGER DEFAULT 0",
            "data_vencimento": "TEXT DEFAULT ''",
            "link_anexo": "TEXT DEFAULT ''",
            "delegado_para": "TEXT DEFAULT ''"
        }
        for col, tipo in novas_colunas.items():
            try:
                self._conn.execute(f"ALTER TABLE tarefas ADD COLUMN {col} {tipo}")
                self._conn.commit()
            except sqlite3.OperationalError:
                pass

    # ------------------------------------------------------------------ #
    #  CRUD Tarefas
    # ------------------------------------------------------------------ #
    def inserir(self, tarefa: Tarefa, enfileirar: bool = True):
        modificada = 1 if enfileirar else int(tarefa.modificada_localmente)
        self._conn.execute("""
            INSERT OR REPLACE INTO tarefas
                (id, titulo, concluida, escopo, prioridade, criado_em, atualizado_em, 
                 sincronizado, api_key, excluida, modificada_localmente, 
                 ordem_usuario, em_andamento, data_vencimento, link_anexo, delegado_para)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            tarefa.id, tarefa.titulo, int(tarefa.concluida),
            tarefa.escopo, tarefa.prioridade,
            tarefa.criado_em, tarefa.atualizado_em,
            int(tarefa.sincronizado), tarefa.api_key,
            int(tarefa.excluida), modificada,
            tarefa.ordem_usuario, int(tarefa.em_andamento),
            tarefa.data_vencimento, tarefa.link_anexo, tarefa.delegado_para
        ))
        self._conn.commit()
        if enfileirar:
            self.adicionar_pendencia("create", tarefa.id, tarefa.api_key, tarefa.to_dict())

    def atualizar(self, tarefa: Tarefa, enfileirar: bool = True):
        tarefa.touch()
        modificada = 1 if enfileirar else int(tarefa.modificada_localmente)
        tarefa.modificada_localmente = bool(modificada)
        self._conn.execute("""
            UPDATE tarefas
            SET titulo=?, concluida=?, escopo=?, prioridade=?,
                atualizado_em=?, sincronizado=?, api_key=?,
                excluida=?, modificada_localmente=?, 
                em_andamento=?, data_vencimento=?, link_anexo=?, delegado_para=?
            WHERE id=?
        """, (
            tarefa.titulo, int(tarefa.concluida), tarefa.escopo,
            tarefa.prioridade, tarefa.atualizado_em,
            int(tarefa.sincronizado), tarefa.api_key, 
            int(tarefa.excluida), modificada, 
            int(tarefa.em_andamento), tarefa.data_vencimento, 
            tarefa.link_anexo, tarefa.delegado_para, tarefa.id
        ))
        self._conn.commit()
        if enfileirar:
            self.adicionar_pendencia("update", tarefa.id, tarefa.api_key, tarefa.to_dict())

    def excluir(self, tarefa_id: str, api_key: str = "", enfileirar: bool = True):
        self._conn.execute("UPDATE tarefas SET excluida=1, modificada_localmente=1 WHERE id=?", (tarefa_id,))
        self._conn.commit()

        if enfileirar:
            self.adicionar_pendencia("delete", tarefa_id, api_key)

    def listar(self, api_key: str = "") -> list[Tarefa]:
        # Ordenação conforme sua solicitação
        query = """
            SELECT * FROM tarefas 
            WHERE api_key=? AND excluida=0 
            ORDER BY 
                ordem_usuario ASC,
                CASE WHEN escopo='escritorio' THEN 0 ELSE 1 END,
                CASE WHEN prioridade='alta' THEN 0 ELSE 1 END, 
                criado_em DESC
        """
        rows = self._conn.execute(query, (api_key,)).fetchall()
        return [self._row_to_tarefa(r) for r in rows]

    def listar_com_excluidas(self, api_key: str = "") -> list[Tarefa]:
        rows = self._conn.execute(
            "SELECT * FROM tarefas WHERE api_key=? ORDER BY "
            "CASE WHEN prioridade='alta' THEN 0 ELSE 1 END, criado_em DESC",
            (api_key,)
        ).fetchall()
        return [self._row_to_tarefa(r) for r in rows]

    def buscar_por_id(self, tarefa_id: str, api_key: str = "") -> Optional[Tarefa]:
        row = self._conn.execute(
            "SELECT * FROM tarefas WHERE id=? AND api_key=?", (tarefa_id, api_key)
        ).fetchone()
        return self._row_to_tarefa(row) if row else None

    # ------------------------------------------------------------------ #
    #  Sync Queue
    # ------------------------------------------------------------------ #
    def adicionar_pendencia(self, acao: str, tarefa_id: str, api_key: str, payload: dict = None):
        self._conn.execute("""
            INSERT INTO sync_queue (acao, tarefa_id, payload, criado_em, api_key)
            VALUES (?, ?, ?, ?, ?)
        """, (
            acao, tarefa_id,
            json.dumps(payload) if payload else None,
            datetime.now(timezone.utc).isoformat(),
            api_key
        ))
        self._conn.commit()

    def listar_pendencias(self, api_key: str = "") -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM sync_queue WHERE api_key=? ORDER BY id ASC",
            (api_key,)
        ).fetchall()
        resultado = []
        for r in rows:
            resultado.append({
                "id": r["id"],
                "acao": r["acao"],
                "tarefa_id": r["tarefa_id"],
                "payload": json.loads(r["payload"]) if r["payload"] else None,
                "criado_em": r["criado_em"],
                "api_key": r["api_key"],
            })
        return resultado

    def remover_pendencia(self, pendencia_id: int):
        self._conn.execute("DELETE FROM sync_queue WHERE id=?", (pendencia_id,))
        self._conn.commit()

    def limpar_modificada_localmente(self, tarefa_id: str):
        self._conn.execute("UPDATE tarefas SET modificada_localmente=0 WHERE id=?", (tarefa_id,))
        self._conn.commit()

    # ------------------------------------------------------------------ #
    #  Sync Bulk
    # ------------------------------------------------------------------ #
    def upsert_em_lote(self, tarefas: list[dict], api_key: str = ""):
        """Recebe lista de dicts da API e faz upsert no banco local sem sobreescrever modificados locais."""
        locais = {t.id: t for t in self.listar_com_excluidas(api_key)}
        for data in tarefas:
            data["sincronizado"] = True
            data["api_key"] = api_key
            
            if "nome" in data and "titulo" not in data:
                data["titulo"] = data.pop("nome")
                
            tarefa_api = Tarefa.from_dict(data)
            
            # Prioridade para dados locais.
            local_obj = locais.get(tarefa_api.id)
            if local_obj and (local_obj.excluida or local_obj.modificada_localmente):
                # Se sofreu edição local/exclusão (mesmo que com erro de push), o local prevalece.
                continue

            self._conn.execute("""
                INSERT INTO tarefas
                    (id, titulo, concluida, escopo, prioridade, criado_em, atualizado_em, sincronizado, api_key, excluida, modificada_localmente)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, 0, 0)
                ON CONFLICT(id) DO UPDATE SET
                    titulo=excluded.titulo,
                    concluida=excluded.concluida,
                    escopo=excluded.escopo,
                    prioridade=excluded.prioridade,
                    atualizado_em=excluded.atualizado_em,
                    api_key=excluded.api_key,
                    sincronizado=1,
                    excluida=0,
                    modificada_localmente=0
            """, (
                tarefa_api.id, tarefa_api.titulo, int(tarefa_api.concluida),
                tarefa_api.escopo, tarefa_api.prioridade,
                tarefa_api.criado_em, tarefa_api.atualizado_em, tarefa_api.api_key
            ))
        self._conn.commit()

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _row_to_tarefa(row) -> Tarefa:
        # Armazenamos as chaves disponíveis na linha atual
        keys = row.keys()
        
        return Tarefa(
            id=row["id"],
            titulo=row["titulo"],
            concluida=bool(row["concluida"]),
            escopo=row["escopo"],
            prioridade=row["prioridade"],
            criado_em=row["criado_em"],
            atualizado_em=row["atualizado_em"],
            sincronizado=bool(row["sincronizado"]),
            
            # Checagens seguras (sem usar .get)
            api_key=row["api_key"] if "api_key" in keys else "",
            excluida=bool(row["excluida"]) if "excluida" in keys else False,
            modificada_localmente=bool(row["modificada_localmente"]) if "modificada_localmente" in keys else False,
            ordem_usuario=row["ordem_usuario"] if "ordem_usuario" in keys else 99999,
            
            # Novos campos MVP (verificação segura caso a migração do SQLite atrase)
            em_andamento=bool(row["em_andamento"]) if "em_andamento" in keys else False,
            data_vencimento=row["data_vencimento"] if "data_vencimento" in keys else "",
            link_anexo=row["link_anexo"] if "link_anexo" in keys else "",
            delegado_para=row["delegado_para"] if "delegado_para" in keys else ""
        )

    def fechar(self):
        if self._conn:
            self._conn.close()
