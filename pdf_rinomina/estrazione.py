"""Testo dei PDF e scelta della codifica in base al codice trovato."""

from __future__ import annotations

from pathlib import Path

from pdf_rinomina.modello import Codifica, ErroreCodifica, prepara_testo

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover - dipende dall'ambiente
    PdfReader = None


class ErrorePdf(Exception):
    """Il PDF non si può leggere o non contiene testo."""


def leggi_testo_pdf(path: Path) -> str:
    if PdfReader is None:
        raise ErrorePdf(
            "Manca la libreria pypdf. Installala con: pip install -r requirements.txt"
        )
    try:
        reader = PdfReader(str(path))
    except Exception as exc:
        raise ErrorePdf(f"Impossibile aprire «{path.name}»: {exc}") from exc
    if reader.is_encrypted:
        try:
            esito = reader.decrypt("")
        except Exception as exc:
            raise ErrorePdf(f"«{path.name}» è protetto da password.") from exc
        if esito == 0:
            raise ErrorePdf(f"«{path.name}» è protetto da password.")
    parti: list[str] = []
    for indice, pagina in enumerate(reader.pages, start=1):
        try:
            testo = pagina.extract_text() or ""
        except Exception as exc:
            raise ErrorePdf(
                f"Errore nel leggere la pagina {indice} di «{path.name}»: {exc}"
            ) from exc
        parti.append(testo)
    return prepara_testo("\n".join(parti))


def scegli_codifica(
    testo: str,
    codifiche: list[Codifica],
    forzata: str | None = None,
) -> Codifica:
    if not codifiche:
        raise ErroreCodifica("Non c'è nessuna codifica configurata.")
    if forzata:
        for codifica in codifiche:
            if codifica.nome == forzata:
                return codifica
        raise ErroreCodifica(f"Codifica «{forzata}» non trovata.")
    specifiche = [codifica for codifica in codifiche if codifica.codice and codifica.contiene_codice(testo)]
    if len(specifiche) == 1:
        return specifiche[0]
    if len(specifiche) > 1:
        nomi = ", ".join(codifica.nome for codifica in specifiche)
        raise ErroreCodifica(
            f"Il PDF corrisponde a più codifiche ({nomi}). Selezionane una nella finestra."
        )
    generiche = [codifica for codifica in codifiche if not codifica.codice]
    if len(generiche) == 1:
        return generiche[0]
    if len(generiche) > 1:
        raise ErroreCodifica(
            "Nessun codice identificativo trovato e ci sono più codifiche senza codice. "
            "Selezionane una nella finestra."
        )
    raise ErroreCodifica("Nessuna codifica corrisponde al codice presente nel PDF.")
