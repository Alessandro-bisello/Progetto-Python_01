"""Piano di rinomina e copia dei PDF nella sottocartella."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

from pdf_rinomina.estrazione import ErrorePdf, leggi_testo_pdf, scegli_codifica
from pdf_rinomina.modello import (
    Codifica,
    ErroreCodifica,
    nome_file,
    nome_sottocartella,
)


@dataclass
class PianoFile:
    origine: Path
    codifica: str | None = None
    valori: dict[str, str] = field(default_factory=dict)
    destinazione: Path | None = None
    errore: str | None = None

    @property
    def pronto(self) -> bool:
        return self.errore is None and self.destinazione is not None


def elenco_pdf(cartella: Path) -> list[Path]:
    if not cartella.is_dir():
        raise ErroreCodifica(f"La cartella non esiste: {cartella}")
    return sorted(
        (path for path in cartella.iterdir() if path.is_file() and path.suffix.lower() == ".pdf"),
        key=lambda path: path.name.casefold(),
    )


def _dentro(cartella: Path, destinazione: Path) -> bool:
    try:
        destinazione.resolve().relative_to(cartella.resolve())
    except ValueError:
        return False
    return True


def _percorso_univoco(destinazione: Path, riservati: set[Path]) -> Path:
    candidato = destinazione
    numero = 2
    while candidato in riservati or candidato.exists():
        candidato = destinazione.with_name(f"{destinazione.stem}_{numero}{destinazione.suffix}")
        numero += 1
        if numero > 9999:
            raise ErroreCodifica("Troppi file produrrebbero lo stesso nome.")
    riservati.add(candidato)
    return candidato


def pianifica(
    file_pdf: list[Path],
    cartella: Path,
    codifiche: list[Codifica],
    forzata: str | None = None,
) -> list[PianoFile]:
    riservati: set[Path] = set()
    piani: list[PianoFile] = []
    for pdf in file_pdf:
        piani.append(_pianifica_uno(pdf, cartella, codifiche, forzata, riservati))
    return piani


def _pianifica_uno(
    pdf: Path,
    cartella: Path,
    codifiche: list[Codifica],
    forzata: str | None,
    riservati: set[Path],
) -> PianoFile:
    try:
        if not pdf.is_file():
            raise ErrorePdf(f"File non trovato: {pdf.name}")
        if pdf.suffix.lower() != ".pdf":
            raise ErrorePdf(f"«{pdf.name}» non è un PDF.")
        testo = leggi_testo_pdf(pdf)
        if not testo.strip():
            raise ErrorePdf(
                "Il PDF non contiene testo selezionabile. "
                "Se è una scansione, il programma non può leggerlo."
            )
        codifica = scegli_codifica(testo, codifiche, forzata)
        valori = codifica.estrai(testo, pdf.stem)
        nome = nome_file(
            codifica.modello_nome,
            valori,
            pdf.suffix or ".pdf",
            codifica.spazi_underscore,
        )
        sottocartella = nome_sottocartella(
            codifica.sottocartella,
            valori,
            codifica.spazi_underscore,
        )
        destinazione = cartella / sottocartella / nome
        if not _dentro(cartella, destinazione):
            raise ErroreCodifica("La destinazione esce dalla cartella scelta.")
        if destinazione.resolve() == pdf.resolve():
            raise ErroreCodifica("Il nuovo nome coincide con il file originale.")
        destinazione = _percorso_univoco(destinazione, riservati)
        return PianoFile(pdf, codifica.nome, valori, destinazione, None)
    except (ErrorePdf, ErroreCodifica) as exc:
        return PianoFile(pdf, errore=str(exc))


def salva_copia(origine: Path, destinazione: Path) -> None:
    destinazione.parent.mkdir(parents=True, exist_ok=True)
    with origine.open("rb") as sorgente, destinazione.open("xb") as destinazione_file:
        shutil.copyfileobj(sorgente, destinazione_file)
    try:
        shutil.copystat(origine, destinazione)
    except OSError:
        pass


def esegui(piani: list[PianoFile]) -> list[PianoFile]:
    for piano in piani:
        if not piano.pronto or piano.destinazione is None:
            continue
        try:
            salva_copia(piano.origine, piano.destinazione)
        except OSError as exc:
            piano.errore = f"Copia non riuscita: {exc}"
            piano.destinazione = None
    return piani


def descrivi_valori(valori: dict[str, str]) -> str:
    return ", ".join(
        f"{chiave}={valore}"
        for chiave, valore in valori.items()
        if chiave != "nome_originale"
    )
