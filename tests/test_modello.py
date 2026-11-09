from pathlib import Path

import pytest

from pdf_rinomina.modello import (
    Campo,
    CampoMancante,
    Codifica,
    ErroreCodifica,
    applica_modello,
    carica_codifiche,
    carica_esempio,
    nome_file,
    nome_sottocartella,
    salva_codifiche,
)


def test_etichetta_legge_il_valore_dopo_i_due_punti():
    campo = Campo("codice", "Codice")
    assert campo.estrai("Nota\nCodice: ABC-123\nFine") == "ABC-123"


def test_etichetta_non_cattura_un_altra_voce_che_inizia_con_la_stessa_parola():
    campo = Campo("data", "Data")
    testo = "Data di nascita: 01/01/1990\nDatazione: ignota\nData: 09/11/2026"
    assert campo.estrai(testo) == "09/11/2026"


def test_regex_usa_il_primo_gruppo():
    campo = Campo("codice", r"Codice:\s*([A-Z0-9-]+)", "regex")
    assert campo.estrai("Codice: ZX-9 altro") == "ZX-9"


def test_nome_campo_riservato_e_regex_non_valida():
    with pytest.raises(ErroreCodifica):
        Campo("nome_originale", "Codice")
    with pytest.raises(ErroreCodifica):
        Campo("codice", r"[", "regex")


def test_segnaposto_sconosciuto():
    with pytest.raises(ErroreCodifica, match="cliente"):
        Codifica(
            nome="Doc",
            campi=[Campo("codice", "Codice")],
            modello_nome="{codice}_{cliente}",
        )


def test_codice_esatto_non_interpreta_il_punto():
    codifica = Codifica(nome="Esplode", codice="FATTURA.", codice_esatto=True, campi=[Campo("n", "Numero")])
    assert codifica.contiene_codice("FATTURA\nNumero: 1") is False
    assert codifica.contiene_codice("Tipo: FATTURA.\nNumero: 1") is True


def test_codice_trovato_mantiene_il_testo_del_pdf():
    codifica = Codifica(
        nome="Fattura",
        codice="FATTURA",
        campi=[Campo("numero", "Numero")],
        modello_nome="{codice_trovato}_{numero}",
    )
    valori = codifica.estrai("fattura\nNumero: 15", "origine")
    assert valori["codice_trovato"] == "fattura"
    assert nome_file(codifica.modello_nome, valori, ".pdf") == "fattura_15.pdf"


def test_data_con_barre_diventa_un_nome_lecito():
    valori = {"codice": "A/B", "data": "09/11/2026", "nome_originale": "scan"}
    assert nome_file("{codice}_{data}", valori, ".PDF") == "A-B_09-11-2026.pdf"


def test_spazi_diventano_underscore_solo_se_richiesto():
    valori = {"cliente": "Rossi Mario"}
    assert nome_file("{cliente}", valori, ".pdf", spazi_underscore=True) == "Rossi_Mario.pdf"
    assert nome_file("{cliente}", valori, ".pdf") == "Rossi Mario.pdf"


def test_nome_riservato_di_windows_viene_prefissato():
    assert nome_file("{codice}", {"codice": "CON"}, ".pdf").upper().startswith("_CON")


def test_parentesi_graffa_spaiata():
    with pytest.raises(ErroreCodifica):
        Codifica(nome="Doc", campi=[Campo("codice", "Codice")], modello_nome="{codice")


def test_dato_mancante():
    codifica = Codifica(nome="Doc", campi=[Campo("codice", "Codice"), Campo("data", "Data")])
    with pytest.raises(CampoMancante) as exc:
        codifica.estrai("Codice: ABC", "file")
    assert exc.value.campi == ["data"]


def test_sottocartella_con_dato():
    assert nome_sottocartella("archivio_{codice}", {"codice": "Q/1"}) == "archivio_Q-1"


def test_salvataggio_e_modello_non_valido(tmp_path: Path):
    codifiche = carica_esempio()
    assert {codifica.nome for codifica in codifiche} == {"Fattura", "Documento"}
    destinazione = tmp_path / "codifiche.json"
    salva_codifiche(destinazione, codifiche)
    assert carica_codifiche(destinazione)[0].nome == "Fattura"
    destinazione.write_text("{", encoding="utf-8")
    with pytest.raises(ErroreCodifica):
        carica_codifiche(destinazione)


def test_applica_modello_rifiuta_il_nome_vuoto():
    with pytest.raises(ErroreCodifica):
        applica_modello("..", {})
