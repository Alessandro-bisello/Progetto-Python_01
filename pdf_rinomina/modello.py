"""Codifiche: quali dati leggere dal PDF e come comporre il nuovo nome."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

NOME_CAMPO = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
SEGNA_POSTO = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
CARATTERI_VIETATI = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
NOMI_RISERVATI = {"CON", "PRN", "AUX", "NUL"}
NOMI_RISERVATI.update(f"COM{i}" for i in range(1, 10))
NOMI_RISERVATI.update(f"LPT{i}" for i in range(1, 10))
CAMPI_IMPLICITI = {"nome_originale", "codice_trovato"}


class ErroreCodifica(ValueError):
    """La codifica o il modello del nome non sono utilizzabili."""


class CampoMancante(ErroreCodifica):
    """Uno o più dati previsti dalla codifica non sono nel PDF."""

    def __init__(self, campi: list[str]):
        self.campi = list(campi)
        elenco = ", ".join(self.campi)
        super().__init__(f"Dati non trovati nel PDF: {elenco}.")


def percorso_esempio() -> Path:
    return Path(__file__).with_name("codifiche.example.json")


def percorso_config_predefinito() -> Path:
    base = Path.home() / ".config" / "pdf_rinomina"
    return base / "codifiche.json"


def prepara_testo(testo: str) -> str:
    return testo.replace("\xa0", " ").replace("\u200b", "")


def normalizza_valore(valore: str) -> str:
    valore = prepara_testo(valore)
    valore = re.sub(r"[ \t]+", " ", valore)
    return valore.strip(" \t;")


def pattern_da_etichetta(etichetta: str) -> str:
    """Cerca una riga «Etichetta: valore» oppure «Etichetta - valore»."""
    return rf"(?im)(?<!\w){re.escape(etichetta)}\s*[:–—-]\s*([^\n\r]+)"


def sanitizza_componente(valore: str, spazi_underscore: bool = False) -> str:
    pulito = CARATTERI_VIETATI.sub("-", valore)
    pulito = re.sub(r"\s+", " ", pulito).strip(" .")
    if spazi_underscore:
        pulito = pulito.replace(" ", "_")
    pulito = re.sub(r"-{2,}", "-", pulito)
    pulito = re.sub(r"_{2,}", "_", pulito)
    return pulito or "vuoto"


def _controlla_parentesi(modello: str, dove: str) -> None:
    senza = SEGNA_POSTO.sub("", modello)
    if "{" in senza or "}" in senza:
        raise ErroreCodifica(
            f"In {dove} resta una parentesi graffa. "
            "I dati si inseriscono così: {codice}."
        )


@dataclass(frozen=True)
class Campo:
    nome: str
    regola: str
    tipo: str = "etichetta"

    def __post_init__(self) -> None:
        nome = self.nome.strip()
        regola = self.regola.strip()
        tipo = self.tipo.strip().lower()
        object.__setattr__(self, "nome", nome)
        object.__setattr__(self, "regola", regola)
        object.__setattr__(self, "tipo", tipo)
        if not NOME_CAMPO.fullmatch(nome):
            raise ErroreCodifica(
                "Il nome del campo deve iniziare con una lettera "
                "e contenere solo lettere, numeri e _."
            )
        if nome in CAMPI_IMPLICITI:
            raise ErroreCodifica(f"Il nome «{nome}» è riservato.")
        if tipo not in {"etichetta", "regex"}:
            raise ErroreCodifica("Il tipo del campo deve essere «etichetta» o «regex».")
        if not regola:
            raise ErroreCodifica(f"Il campo «{nome}» non ha una regola.")
        self.compilato()

    def compilato(self) -> re.Pattern[str]:
        sorgente = self.regola if self.tipo == "regex" else pattern_da_etichetta(self.regola)
        try:
            return re.compile(sorgente)
        except re.error as exc:
            raise ErroreCodifica(
                f"Espressione non valida per «{self.nome}»: {exc}"
            ) from exc

    def estrai(self, testo: str) -> str | None:
        match = self.compilato().search(prepara_testo(testo))
        if not match:
            return None
        valore = match.group(1) if match.re.groups else match.group(0)
        valore = normalizza_valore(valore)
        return valore or None

    def to_dict(self) -> dict[str, str]:
        return {"nome": self.nome, "tipo": self.tipo, "regola": self.regola}

    @classmethod
    def from_dict(cls, data: object) -> Campo:
        if not isinstance(data, dict):
            raise ErroreCodifica("Ogni campo della codifica deve essere un oggetto JSON.")
        return cls(
            nome=str(data.get("nome", "")),
            tipo=str(data.get("tipo", "etichetta")),
            regola=str(data.get("regola", "")),
        )


@dataclass(frozen=True)
class Codifica:
    nome: str
    codice: str = ""
    codice_esatto: bool = True
    campi: list[Campo] = field(default_factory=list)
    modello_nome: str = "{nome_originale}"
    sottocartella: str = "rinominati"
    spazi_underscore: bool = False

    def __post_init__(self) -> None:
        nome = self.nome.strip()
        codice = self.codice.strip()
        modello_nome = self.modello_nome.strip()
        sottocartella = self.sottocartella.strip()
        object.__setattr__(self, "nome", nome)
        object.__setattr__(self, "codice", codice)
        object.__setattr__(self, "modello_nome", modello_nome)
        object.__setattr__(self, "sottocartella", sottocartella)
        if not nome:
            raise ErroreCodifica("Ogni codifica deve avere un nome.")
        if not modello_nome:
            raise ErroreCodifica(f"La codifica «{nome}» non ha un modello per il nome file.")
        if not sottocartella:
            raise ErroreCodifica(f"La codifica «{nome}» non ha il nome della sottocartella.")
        nomi = [campo.nome for campo in self.campi]
        if len(nomi) != len(set(nomi)):
            raise ErroreCodifica(f"La codifica «{nome}» ha due campi con lo stesso nome.")
        if codice and not self.codice_esatto:
            try:
                re.compile(codice)
            except re.error as exc:
                raise ErroreCodifica(
                    f"Il codice identificativo di «{nome}» non è un'espressione valida: {exc}"
                ) from exc
        _controlla_parentesi(modello_nome, f"il nome file di «{nome}»")
        _controlla_parentesi(sottocartella, f"la sottocartella di «{nome}»")
        noti = {campo.nome for campo in self.campi} | {"nome_originale"}
        if codice:
            noti.add("codice_trovato")
        for modello in (modello_nome, sottocartella):
            for segnaposto in SEGNA_POSTO.findall(modello):
                if segnaposto not in noti:
                    raise ErroreCodifica(
                        f"«{segnaposto}» è nel modello ma non esiste tra i campi di «{nome}»."
                    )

    def segnaposto(self) -> set[str]:
        return set(SEGNA_POSTO.findall(self.modello_nome) + SEGNA_POSTO.findall(self.sottocartella))

    def cerca_codice(self, testo: str) -> re.Match[str] | None:
        if not self.codice:
            return None
        testo = prepara_testo(testo)
        if self.codice_esatto:
            return re.search(re.escape(self.codice), testo, re.IGNORECASE)
        return re.search(self.codice, testo)

    def contiene_codice(self, testo: str) -> bool:
        if not self.codice:
            return True
        return self.cerca_codice(testo) is not None

    def estrai(self, testo: str, nome_originale: str) -> dict[str, str]:
        testo = prepara_testo(testo)
        valori = {"nome_originale": nome_originale}
        mancanti: list[str] = []
        for campo in self.campi:
            valore = campo.estrai(testo)
            if valore is None:
                mancanti.append(campo.nome)
            else:
                valori[campo.nome] = valore
        if self.codice:
            match = self.cerca_codice(testo)
            if match:
                valori["codice_trovato"] = normalizza_valore(match.group(0))
            elif "codice_trovato" in self.segnaposto():
                mancanti.append("codice_trovato")
        if mancanti:
            raise CampoMancante(mancanti)
        return valori

    def to_dict(self) -> dict[str, object]:
        return {
            "nome": self.nome,
            "codice": self.codice,
            "codice_esatto": self.codice_esatto,
            "campi": [campo.to_dict() for campo in self.campi],
            "modello_nome": self.modello_nome,
            "sottocartella": self.sottocartella,
            "spazi_underscore": self.spazi_underscore,
        }

    @classmethod
    def from_dict(cls, data: object) -> Codifica:
        if not isinstance(data, dict):
            raise ErroreCodifica("Ogni codifica nel file deve essere un oggetto JSON.")
        campi_raw = data.get("campi", [])
        if not isinstance(campi_raw, list):
            raise ErroreCodifica("L'elenco dei campi non è valido.")
        return cls(
            nome=str(data.get("nome", "")),
            codice=str(data.get("codice", "")),
            codice_esatto=bool(data.get("codice_esatto", True)),
            campi=[Campo.from_dict(campo) for campo in campi_raw],
            modello_nome=str(data.get("modello_nome", "{nome_originale}")),
            sottocartella=str(data.get("sottocartella", "rinominati")),
            spazi_underscore=bool(data.get("spazi_underscore", False)),
        )


def controlla_nomi_unici(codifiche: list[Codifica]) -> None:
    nomi = [codifica.nome for codifica in codifiche]
    if len(nomi) != len(set(nomi)):
        raise ErroreCodifica("Due codifiche non possono avere lo stesso nome.")
    if not codifiche:
        raise ErroreCodifica("Serve almeno una codifica.")


def carica_codifiche(path: Path) -> list[Codifica]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ErroreCodifica(f"Il file delle codifiche non è un JSON valido: {exc}") from exc
    except OSError as exc:
        raise ErroreCodifica(f"Impossibile leggere le codifiche: {exc}") from exc
    if isinstance(data, dict):
        elementi = data.get("codifiche", [])
    elif isinstance(data, list):
        elementi = data
    else:
        raise ErroreCodifica("Il file delle codifiche non ha il formato atteso.")
    if not isinstance(elementi, list):
        raise ErroreCodifica("Il file delle codifiche non ha il formato atteso.")
    codifiche = [Codifica.from_dict(elemento) for elemento in elementi]
    controlla_nomi_unici(codifiche)
    return codifiche


def salva_codifiche(path: Path, codifiche: list[Codifica]) -> None:
    controlla_nomi_unici(codifiche)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"codifiche": [codifica.to_dict() for codifica in codifiche]}
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def carica_esempio() -> list[Codifica]:
    return carica_codifiche(percorso_esempio())


def applica_modello(modello: str, valori: dict[str, str], spazi_underscore: bool = False) -> str:
    def sostituisci(match: re.Match[str]) -> str:
        chiave = match.group(1)
        if chiave not in valori:
            raise CampoMancante([chiave])
        return sanitizza_componente(valori[chiave], spazi_underscore)

    compilato = SEGNA_POSTO.sub(sostituisci, modello)
    compilato = CARATTERI_VIETATI.sub("-", compilato)
    compilato = re.sub(r"\s+", " ", compilato).strip(" .")
    if spazi_underscore:
        compilato = compilato.replace(" ", "_")
    compilato = re.sub(r"-{2,}", "-", compilato)
    compilato = re.sub(r"_{2,}", "_", compilato)
    if compilato in {"", ".", ".."} or ".." in compilato.split("-"):
        raise ErroreCodifica("Il nome prodotto dal modello non è valido.")
    return compilato


def nome_file(modello: str, valori: dict[str, str], suffisso: str, spazi_underscore: bool = False) -> str:
    if not suffisso.startswith("."):
        suffisso = f".{suffisso}" if suffisso else ".pdf"
    suffisso = suffisso.lower()
    nome = applica_modello(modello, valori, spazi_underscore)
    if nome.lower().endswith(suffisso):
        base = nome[: -len(suffisso)] + suffisso
    else:
        base = f"{nome}{suffisso}"
    if Path(base).stem.upper() in NOMI_RISERVATI:
        base = f"_{base}"
    if len(base) > 180:
        massimo = 180 - len(suffisso)
        stem = base[: -len(suffisso)].rstrip(" ._")
        base = f"{stem[:massimo].rstrip(' ._')}{suffisso}"
    return base


def nome_sottocartella(modello: str, valori: dict[str, str], spazi_underscore: bool = False) -> str:
    nome = applica_modello(modello, valori, spazi_underscore)
    if nome in {".", ".."}:
        raise ErroreCodifica("Il nome della sottocartella non è valido.")
    return nome
