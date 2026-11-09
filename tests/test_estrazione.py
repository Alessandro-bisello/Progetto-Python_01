from pathlib import Path

import pytest
from pypdf import PdfWriter

from pdf_rinomina.estrazione import ErrorePdf, leggi_testo_pdf, scegli_codifica
from pdf_rinomina.modello import Campo, Codifica, ErroreCodifica, carica_esempio
from tests.support import scrivi_pdf_testo


def test_legge_il_testo_anche_dalla_seconda_pagina(tmp_path: Path):
    pdf = tmp_path / "due.pdf"
    scrivi_pdf_testo(pdf, ["Prima pagina", "Codice: NELLA-SECONDA"])
    testo = leggi_testo_pdf(pdf)
    assert "NELLA-SECONDA" in testo
    assert Campo("codice", "Codice").estrai(testo) == "NELLA-SECONDA"


def test_pdf_senza_testo(tmp_path: Path):
    pdf = tmp_path / "vuoto.pdf"
    scrivi_pdf_testo(pdf, "   ")
    assert leggi_testo_pdf(pdf).strip() == ""


def test_pdf_protetto_da_password(tmp_path: Path):
    chiaro = tmp_path / "chiaro.pdf"
    segreto = tmp_path / "segreto.pdf"
    scrivi_pdf_testo(chiaro, "Codice: ABC")
    writer = PdfWriter()
    writer.append(str(chiaro))
    writer.encrypt("segreto")
    with segreto.open("wb") as uscita:
        writer.write(uscita)
    with pytest.raises(ErrorePdf, match="password"):
        leggi_testo_pdf(segreto)


def test_sceglie_la_codifica_dal_codice_e_la_riserva():
    codifiche = carica_esempio()
    fattura = "FATTURA\nNumero: 1\nData: 01/01/2026\nCliente: Rossi"
    generico = "Codice: ZZ\nData: 02/02/2026"
    assert scegli_codifica(fattura, codifiche).nome == "Fattura"
    assert scegli_codifica(generico, codifiche).nome == "Documento"
    assert scegli_codifica(generico, codifiche, "Fattura").nome == "Fattura"


def test_piu_codici_chiedono_una_scelta_manuale():
    codifiche = [
        Codifica(nome="A", codice="ALFA", campi=[Campo("n", "Numero")]),
        Codifica(nome="B", codice="BETA", campi=[Campo("n", "Numero")]),
    ]
    with pytest.raises(ErroreCodifica, match="più codifiche"):
        scegli_codifica("ALFA e BETA\nNumero: 1", codifiche)


def test_file_illeggibile(tmp_path: Path):
    pdf = tmp_path / "rotto.pdf"
    pdf.write_bytes(b"non sono un pdf")
    with pytest.raises(ErrorePdf):
        leggi_testo_pdf(pdf)
