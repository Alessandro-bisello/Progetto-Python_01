# Progetto-Python_01

Quaderno è un programma Python da riga di comando per annotare testi in un file JSON locale.

Non ha dipendenze esterne. Richiede Python 3.11 o successivo.

## Avvio

Dalla radice del repository:

```bash
PYTHONPATH=src python3 -m quaderno aggiungi "Comprare il latte"
PYTHONPATH=src python3 -m quaderno elenco
PYTHONPATH=src python3 -m quaderno cerca latte
PYTHONPATH=src python3 -m quaderno elimina 1
```

Le note finiscono in `~/.quaderno/note.json`. Il file tiene l'elenco e il prossimo id, che non viene riassegnato dopo un'eliminazione. Un altro file si indica con `--file`:

```bash
PYTHONPATH=src python3 -m quaderno --file ./note.json elenco
```

Installazione opzionale del comando `quaderno`:

```bash
pip install -e .
quaderno elenco
```

## Comandi

| Comando | Effetto |
| --- | --- |
| `aggiungi TESTO` | Crea una nota e stampa il suo id |
| `elenco` | Mostra tutte le note |
| `cerca QUERY` | Mostra le note che contengono il testo, senza distinguere maiuscole e minuscole |
| `elimina ID` | Elimina la nota con quell'id |

Un testo fatto solo di spazi viene rifiutato. Se l'id da eliminare non esiste, il programma esce con codice 1.

## Test

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```
