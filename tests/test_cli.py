from pathlib import Path

from pdf_rinomina.__main__ import main
from pdf_rinomina.modello import percorso_esempio
from tests.support import scrivi_pdf_testo


def test_anteprima_non_crea_file_ed_esecuzione_si(tmp_path: Path, capsys):
    pdf = tmp_path / "doc.pdf"
    scrivi_pdf_testo(pdf, "Codice: ALFA\nData: 02/02/2026\n")
    codice = main(
        ["--cartella", str(tmp_path), "--codifiche", str(percorso_esempio()), "--anteprima"]
    )
    assert codice == 0
    assert "rinominati/ALFA_02-02-2026.pdf [pronto]" in capsys.readouterr().out
    assert not (tmp_path / "rinominati").exists()

    codice = main(
        ["--cartella", str(tmp_path), "--codifiche", str(percorso_esempio()), "--esegui", "doc.pdf"]
    )
    assert codice == 0
    assert (tmp_path / "rinominati" / "ALFA_02-02-2026.pdf").is_file()
    assert pdf.is_file()


def test_errore_di_lettura_ha_codice_di_uscita(tmp_path: Path, capsys):
    scrivi_pdf_testo(tmp_path / "vuoto.pdf", "senza campi\n")
    codice = main(
        ["--cartella", str(tmp_path), "--codifiche", str(percorso_esempio()), "--anteprima"]
    )
    catturato = capsys.readouterr()
    assert codice == 1
    assert "ERRORE" in catturato.err
