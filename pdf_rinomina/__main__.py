"""Avvio della finestra oppure anteprima ed esecuzione da terminale."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pdf_rinomina.modello import (
    ErroreCodifica,
    carica_codifiche,
    carica_esempio,
    percorso_config_predefinito,
)
from pdf_rinomina.rinomina import elenco_pdf, esegui, pianifica


def costruisci_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rinomina-pdf",
        description=(
            "Legge un codice e altri dati dai PDF e li copia in una sottocartella "
            "con un nome costruito dalla codifica."
        ),
    )
    parser.add_argument("--cartella", help="Cartella che contiene i PDF e che riceve la sottocartella.")
    parser.add_argument("--codifiche", help="File JSON con le codifiche. Se manca, usa quelle salvate o l'esempio.")
    parser.add_argument("--codifica", help="Nome della codifica da forzare, invece della ricerca automatica del codice.")
    parser.add_argument(
        "--esegui",
        action="store_true",
        help="Copia i file. Senza questa opzione, se chiedi l'anteprima, i file non vengono scritti.",
    )
    parser.add_argument(
        "--anteprima",
        action="store_true",
        help="Mostra nel terminale il nuovo nome, senza copiare.",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Apre la finestra anche se sono indicati dei PDF.",
    )
    parser.add_argument("pdf", nargs="*", help="PDF da elaborare. Se mancano, usa tutti i PDF della cartella.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = costruisci_parser()
    args = parser.parse_args(argv)
    usa_terminale = not args.gui and (args.esegui or args.anteprima or bool(args.pdf))
    if usa_terminale:
        if not args.cartella:
            parser.error("Per lavorare dal terminale indica --cartella.")
        try:
            return esegui_terminale(args)
        except ErroreCodifica as exc:
            print(str(exc), file=sys.stderr)
            return 1
    from pdf_rinomina.gui import avvia

    avvia(cartella=args.cartella, file_codifiche=args.codifiche)
    return 0


def esegui_terminale(args: argparse.Namespace) -> int:
    cartella = Path(args.cartella).expanduser().resolve()
    if args.codifiche:
        codifiche = carica_codifiche(Path(args.codifiche).expanduser())
    else:
        predefinito = percorso_config_predefinito()
        codifiche = carica_codifiche(predefinito) if predefinito.is_file() else carica_esempio()
    if args.pdf:
        file_pdf: list[Path] = []
        for nome in args.pdf:
            path = Path(nome).expanduser()
            if not path.is_file():
                path = cartella / nome
            file_pdf.append(path)
    else:
        file_pdf = elenco_pdf(cartella)
    if not file_pdf:
        print("Nessun PDF da elaborare.", file=sys.stderr)
        return 1
    piani = pianifica(file_pdf, cartella, codifiche, args.codifica)
    if args.esegui:
        esegui(piani)
    errori = 0
    for piano in piani:
        if piano.pronto and piano.destinazione is not None:
            azione = "copiato" if args.esegui else "pronto"
            print(f"{piano.origine.name} -> {piano.destinazione.relative_to(cartella)} [{azione}]")
        else:
            errori += 1
            print(f"{piano.origine.name} ERRORE: {piano.errore}", file=sys.stderr)
    return 1 if errori else 0


if __name__ == "__main__":
    raise SystemExit(main())
