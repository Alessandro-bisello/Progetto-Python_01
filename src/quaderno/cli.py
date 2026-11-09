"""Interfaccia a riga di comando di Quaderno."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from quaderno.note import Nota, Quaderno, percorso_predefinito


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    quaderno = Quaderno(Path(args.file))
    try:
        return _esegui(quaderno, args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1


def esegui() -> None:
    raise SystemExit(main())


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="quaderno",
        description="Salva, cerca ed elimina note in un file JSON locale.",
    )
    parser.add_argument(
        "--file",
        default=str(percorso_predefinito()),
        help="Percorso del file JSON (predefinito: ~/.quaderno/note.json)",
    )
    comandi = parser.add_subparsers(dest="comando", required=True)

    aggiungi = comandi.add_parser("aggiungi", help="Aggiunge una nota")
    aggiungi.add_argument("testo", help="Testo della nota")

    comandi.add_parser("elenco", help="Mostra tutte le note")

    cerca = comandi.add_parser("cerca", help="Cerca una parola nel testo")
    cerca.add_argument("query", help="Testo da cercare")

    elimina = comandi.add_parser("elimina", help="Elimina una nota per id")
    elimina.add_argument("id", type=int, help="Identificativo della nota")
    return parser


def _esegui(quaderno: Quaderno, args: argparse.Namespace) -> int:
    if args.comando == "aggiungi":
        nota = quaderno.aggiungi(args.testo)
        print(f"Nota {nota.id} aggiunta.")
        return 0
    if args.comando == "elenco":
        return _stampa_note(quaderno.elenco(), vuoto="Nessuna nota.")
    if args.comando == "cerca":
        return _stampa_note(quaderno.cerca(args.query), vuoto="Nessun risultato.")
    if args.comando == "elimina":
        if quaderno.elimina(args.id):
            print(f"Nota {args.id} eliminata.")
            return 0
        print(f"Nota {args.id} non trovata.", file=sys.stderr)
        return 1
    print(f"Comando sconosciuto: {args.comando}", file=sys.stderr)
    return 2


def _stampa_note(note: list[Nota], vuoto: str) -> int:
    if not note:
        print(vuoto)
        return 0
    for nota in note:
        print(f"#{nota.id}  {nota.creata_il}")
        print(nota.testo)
        print()
    return 0
