"""Archivio di note su file JSON."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class Nota:
    id: int
    testo: str
    creata_il: str


class Quaderno:
    """Elenco di note persistito in un unico file JSON."""

    def __init__(self, percorso: Path) -> None:
        self.percorso = Path(percorso)

    def aggiungi(self, testo: str) -> Nota:
        pulito = testo.strip()
        if not pulito:
            raise ValueError("Il testo della nota non può essere vuoto.")
        note, prossimo_id = self._carica()
        nota = Nota(id=prossimo_id, testo=pulito, creata_il=_adesso())
        note.append(nota)
        self._salva(note, prossimo_id + 1)
        return nota

    def elenco(self) -> list[Nota]:
        note, _prossimo_id = self._carica()
        return note

    def cerca(self, query: str) -> list[Nota]:
        termine = query.strip().casefold()
        if not termine:
            return []
        return [nota for nota in self.elenco() if termine in nota.testo.casefold()]

    def elimina(self, id_nota: int) -> bool:
        note, prossimo_id = self._carica()
        rimaste = [nota for nota in note if nota.id != id_nota]
        if len(rimaste) == len(note):
            return False
        self._salva(rimaste, prossimo_id)
        return True

    def _carica(self) -> tuple[list[Nota], int]:
        if not self.percorso.exists():
            return [], 1
        try:
            dati = json.loads(self.percorso.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"File note non valido: {self.percorso}") from exc
        if not isinstance(dati, dict):
            raise ValueError(f"File note non valido: {self.percorso}")
        note_grezze = dati.get("note")
        prossimo_id = dati.get("prossimo_id")
        if not isinstance(note_grezze, list) or not _intero_positivo(prossimo_id):
            raise ValueError(f"File note non valido: {self.percorso}")
        return [_nota_da_dizionario(elemento) for elemento in note_grezze], prossimo_id

    def _salva(self, note: list[Nota], prossimo_id: int) -> None:
        self.percorso.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "prossimo_id": prossimo_id,
            "note": [asdict(nota) for nota in note],
        }
        contenuto = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        self.percorso.write_text(contenuto, encoding="utf-8")


def percorso_predefinito() -> Path:
    return Path.home() / ".quaderno" / "note.json"


def _adesso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _intero_positivo(valore: object) -> bool:
    return isinstance(valore, int) and not isinstance(valore, bool) and valore >= 1


def _nota_da_dizionario(elemento: object) -> Nota:
    if not isinstance(elemento, dict):
        raise ValueError("File note non valido: ogni voce deve essere un oggetto.")
    try:
        id_nota = elemento["id"]
        testo = elemento["testo"]
        creata_il = elemento["creata_il"]
    except KeyError as exc:
        raise ValueError("File note non valido: manca un campo obbligatorio.") from exc
    if isinstance(id_nota, bool) or not isinstance(id_nota, int):
        raise ValueError("File note non valido: id non numerico.")
    if not isinstance(testo, str) or not isinstance(creata_il, str):
        raise ValueError("File note non valido: campi di tipo errato.")
    return Nota(id=id_nota, testo=testo, creata_il=creata_il)
