"""
Modelos de dados do SageCont-Win.
"""
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone


@dataclass
class Tarefa:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    titulo: str = ""
    concluida: bool = False
    escopo: str = "minha"        # "minha" | "escritorio"
    prioridade: str = "normal"   # "normal" | "alta"
    criado_em: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    atualizado_em: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    sincronizado: bool = False
    api_key: str = ""
    excluida: bool = False
    modificada_localmente: bool = False
    ordem_usuario: int = 99999

    # ---------- serialização ----------
    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Tarefa":
        campos_validos = {f.name for f in cls.__dataclass_fields__.values()}
        filtrado = {k: v for k, v in data.items() if k in campos_validos}
        return cls(**filtrado)

    # ---------- helpers ----------
    def touch(self):
        """Atualiza timestamp de modificação."""
        self.atualizado_em = datetime.now(timezone.utc).isoformat()
