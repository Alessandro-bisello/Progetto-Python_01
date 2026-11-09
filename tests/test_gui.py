from pathlib import Path

import pytest

from pdf_rinomina.modello import percorso_esempio
from tests.support import scrivi_pdf_testo

FATTURA = "FATTURA\nNumero: 2026-15\nData: 09/11/2026\nCliente: Rossi Mario\n"
ALTRO = "Codice: PRAT-8\nData: 01/03/2026\n"


@pytest.fixture
def cartella_pdf(tmp_path: Path) -> Path:
    cartella = tmp_path / "documenti"
    cartella.mkdir()
    scrivi_pdf_testo(cartella / "fattura.pdf", FATTURA)
    scrivi_pdf_testo(cartella / "pratica.pdf", ALTRO)
    return cartella


def test_la_finestra_mostra_anteprima_e_copia(cartella_pdf: Path, tmp_path: Path, monkeypatch):
    pytest.importorskip("tkinter")
    import pdf_rinomina.gui as gui

    monkeypatch.setattr(gui.messagebox, "showinfo", lambda *args, **kwargs: None)
    monkeypatch.setattr(gui.messagebox, "showerror", lambda *args, **kwargs: None)
    monkeypatch.setattr(gui, "chiedi_conferma", lambda *args, **kwargs: True)
    codifiche = tmp_path / "codifiche.json"
    codifiche.write_text(percorso_esempio().read_text(encoding="utf-8"), encoding="utf-8")

    app = gui.App(cartella=cartella_pdf, file_codifiche=codifiche)
    try:
        app.update()
        assert app.lista_pdf.size() == 2
        assert app.conteggio.get() == "2 selezionati di 2"
        app._anteprima()
        percorsi = [app.anteprima.item(iid, "values")[3] for iid in app.anteprima.get_children()]
        assert "fatture/2026-15_Rossi_Mario_09-11-2026.pdf" in percorsi
        assert "rinominati/PRAT-8_01-03-2026.pdf" in percorsi

        app.modello.set("{numero}")
        app._anteprima()
        percorsi = [app.anteprima.item(iid, "values")[3] for iid in app.anteprima.get_children()]
        assert "fatture/2026-15.pdf" in percorsi

        app.modello.set("{numero}_{cliente}_{data}")
        app._copia()
    finally:
        app.destroy()

    assert (cartella_pdf / "fatture" / "2026-15_Rossi_Mario_09-11-2026.pdf").is_file()
    assert (cartella_pdf / "rinominati" / "PRAT-8_01-03-2026.pdf").is_file()
    assert (cartella_pdf / "fattura.pdf").is_file()
    assert (cartella_pdf / "pratica.pdf").is_file()
