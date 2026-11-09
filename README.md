# Rinomina PDF

Programma per leggere un codice e altri dati da PDF con testo selezionabile, poi copiarli in una sottocartella con un nome che componi tu.

Gli originali restano nella cartella di partenza.

## Avvio

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python rinomina_pdf.py
```

1. Apri la cartella che contiene i PDF.
2. Seleziona i file da elaborare.
3. Controlla la codifica: il codice da cercare nel PDF, i dati da leggere e il modello del nuovo nome.
4. Aggiorna l'anteprima.
5. Copia nella sottocartella.

Puoi anche aprire subito una cartella:

```bash
python rinomina_pdf.py --cartella /percorso/dei/pdf
```

## Come si scrive una codifica

Una codifica ha:

- **Codice nel PDF**: testo che deve comparire nel documento, per esempio `FATTURA`. Se lo lasci vuoto, la codifica è di riserva e si usa quando nessun codice specifico combacia. Con «testo esatto» il punto e gli altri caratteri non sono speciali.
- **Dati da leggere**:
  - *Etichetta*: nel PDF serve una riga come `Numero: 2026-15` oppure `Numero - 2026-15`.
  - *Espressione regolare*: metti il valore da tenere tra parentesi, per esempio `Numero:\s*([A-Z0-9-]+)`.
- **Nome file**: usa i dati tra graffe, per esempio `{numero}_{cliente}_{data}`. Sono sempre disponibili `{nome_originale}` e, se hai indicato un codice, `{codice_trovato}`.
- **Sottocartella**: un solo livello dentro la cartella aperta, per esempio `fatture`. Può contenere anch'essa dei segnaposto.

Le barre e gli altri caratteri non ammessi in un nome file vengono sostituiti: una data `09/11/2026` diventa `09-11-2026`.

L'esempio già pronto riconosce una fattura che contiene la parola `FATTURA` e le righe `Numero`, `Data` e `Cliente`. Gli altri PDF usano la codifica `Documento`, che cerca `Codice` e `Data`. Aprilo con **Carica esempio**.

Per vedere se la regola funziona, seleziona un PDF e usa **Mostra testo del PDF** oppure **Prova sul PDF** mentre aggiungi un campo.

Le codifiche si salvano in JSON. All'avvio il programma riapre `~/.config/pdf_rinomina/codifiche.json`, se esiste.

## Terminale

L'anteprima non scrive nulla:

```bash
python rinomina_pdf.py --cartella ./documenti --codifiche pdf_rinomina/codifiche.example.json --anteprima
```

La copia usa gli stessi controlli:

```bash
python rinomina_pdf.py --cartella ./documenti --codifiche pdf_rinomina/codifiche.example.json --esegui
```

`--codifica Fattura` forza una codifica e non cerca il codice. Puoi anche elencare solo alcuni file: `--esegui uno.pdf due.pdf`.

## Limite

Il programma legge il testo già presente nel PDF. Una scansione senza testo selezionabile viene segnalata e non viene copiata.
