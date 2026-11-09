from pathlib import Path

from pdf_rinomina.modello import carica_esempio
from pdf_rinomina.rinomina import esegui, pianifica
from tests.support import scrivi_pdf_testo

FATTURA = "FATTURA\nNumero: 2026-15\nData: 09/11/2026\nCliente: Rossi Mario\n"
ALTRO = "Codice: PRAT-8\nData: 01/03/2026\n"
SENZA_DATI = "Questo documento non ha i campi attesi.\n"


def test_copia_nella_sottocartella_e_lascia_gli_originali(tmp_path: Path):
    prima = tmp_path / "prima.pdf"
    seconda = tmp_path / "seconda.pdf"
    terza = tmp_path / "terza.pdf"
    scrivi_pdf_testo(prima, FATTURA)
    scrivi_pdf_testo(seconda, ALTRO)
    scrivi_pdf_testo(terza, SENZA_DATI)
    originale = prima.read_bytes()

    piani = pianifica([prima, seconda, terza], tmp_path, carica_esempio())
    esegui(piani)

    assert piani[0].pronto
    assert piani[0].destinazione == tmp_path / "fatture" / "2026-15_Rossi_Mario_09-11-2026.pdf"
    assert piani[0].destinazione.is_file()
    assert piani[1].destinazione == tmp_path / "rinominati" / "PRAT-8_01-03-2026.pdf"
    assert piani[2].errore is not None
    assert not piani[2].pronto
    assert prima.read_bytes() == originale
    assert sorted(path.name for path in tmp_path.glob("*.pdf")) == ["prima.pdf", "seconda.pdf", "terza.pdf"]


def test_due_pdf_con_gli_stessi_dati_non_si_sovrascrivono(tmp_path: Path):
    uno = tmp_path / "uno.pdf"
    due = tmp_path / "due.pdf"
    scrivi_pdf_testo(uno, ALTRO)
    scrivi_pdf_testo(due, ALTRO)
    piani = pianifica([uno, due], tmp_path, carica_esempio())
    esegui(piani)
    assert piani[0].destinazione is not None and piani[1].destinazione is not None
    assert piani[0].destinazione != piani[1].destinazione
    assert piani[0].destinazione.is_file()
    assert piani[1].destinazione.is_file()
    assert piani[1].destinazione.name == "PRAT-8_01-03-2026_2.pdf"


def test_anteprima_non_scrive(tmp_path: Path):
    pdf = tmp_path / "doc.pdf"
    scrivi_pdf_testo(pdf, ALTRO)
    piani = pianifica([pdf], tmp_path, carica_esempio())
    assert piani[0].destinazione is not None
    assert not piani[0].destinazione.exists()
