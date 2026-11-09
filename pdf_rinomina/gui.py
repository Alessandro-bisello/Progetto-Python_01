"""Finestra per scegliere i PDF, leggere il codice e copiarli rinominati."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from pdf_rinomina.estrazione import ErrorePdf, leggi_testo_pdf
from pdf_rinomina.modello import (
    Campo,
    Codifica,
    ErroreCodifica,
    carica_codifiche,
    carica_esempio,
    nome_file,
    percorso_config_predefinito,
    salva_codifiche,
)
from pdf_rinomina.rinomina import PianoFile, descrivi_valori, elenco_pdf, esegui, pianifica

TIPI_VISIBILI = {
    "etichetta": "Etichetta",
    "regex": "Espressione regolare",
}
TIPI_INTERNI = {etichetta: chiave for chiave, etichetta in TIPI_VISIBILI.items()}
AUTOMATICA = "Automatica (in base al codice)"


def avvia(cartella: str | Path | None = None, file_codifiche: str | Path | None = None) -> None:
    app = App(
        cartella=Path(cartella) if cartella else None,
        file_codifiche=Path(file_codifiche) if file_codifiche else None,
    )
    app.mainloop()


class App(tk.Tk):
    def __init__(
        self,
        cartella: Path | None = None,
        file_codifiche: Path | None = None,
    ) -> None:
        super().__init__()
        self.title("Rinomina PDF")
        self.geometry("1280x920")
        self.minsize(1100, 720)
        self._applica_stile()
        self.cartella: Path | None = None
        self.pdf: list[Path] = []
        self.codifiche: list[Codifica] = []
        self._campi: list[Campo] = []
        self._indice: int | None = None
        self._blocco = False
        self._piani: list[PianoFile] = []
        self.percorso_codifiche: Path | None = None
        self._costruisci()
        self._carica_iniziale(file_codifiche)
        if cartella is not None:
            self._imposta_cartella(cartella)

    def _applica_stile(self) -> None:
        stile = ttk.Style(self)
        if "clam" in stile.theme_names():
            stile.theme_use("clam")
        stile.configure("TButton", padding=(8, 4))
        stile.configure("Treeview", rowheight=24)
        stile.configure("Stato.TLabel", padding=(8, 4))

    def _costruisci(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        intro = ttk.Label(
            self,
            padding=(12, 10, 12, 4),
            text=(
                "Apri la cartella, seleziona i PDF e indica il codice da cercare. "
                "Il programma legge i dati e copia i file in una sottocartella, "
                "con il nome composto dalla codifica. Gli originali restano al loro posto."
            ),
            wraplength=1220,
            justify="left",
        )
        intro.grid(row=0, column=0, sticky="ew")

        self.verticale = ttk.Panedwindow(self, orient="vertical")
        self.verticale.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 4))

        alto = ttk.Panedwindow(self.verticale, orient="horizontal")
        basso = ttk.Frame(self.verticale, padding=4)
        self.verticale.add(alto, weight=3)
        self.verticale.add(basso, weight=1)

        sinistra = ttk.Frame(alto, padding=4)
        destra = ttk.Frame(alto, padding=4)
        alto.add(sinistra, weight=2)
        alto.add(destra, weight=3)
        self._costruisci_pdf(sinistra)
        self._costruisci_codifica(destra)
        self._costruisci_anteprima(basso)
        self.after_idle(self._sistema_divisori)

        self.stato = tk.StringVar(value="Apri una cartella per iniziare.")
        ttk.Label(self, textvariable=self.stato, style="Stato.TLabel", anchor="w").grid(
            row=2, column=0, sticky="ew"
        )

    def _costruisci_pdf(self, padre: ttk.Frame) -> None:
        padre.columnconfigure(0, weight=1)
        padre.rowconfigure(1, weight=1)
        barra = ttk.Frame(padre)
        barra.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        barra.columnconfigure(0, weight=1)
        self.percorso_cartella = tk.StringVar()
        ttk.Entry(barra, textvariable=self.percorso_cartella, state="readonly").grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        ttk.Button(barra, text="Apri cartella", command=self._apri_cartella).grid(row=0, column=1)
        ttk.Button(barra, text="Aggiorna", command=self._aggiorna_elenco).grid(row=0, column=2, padx=(6, 0))

        self.riquadro_pdf = ttk.LabelFrame(padre, text="PDF nella cartella", padding=6)
        self.riquadro_pdf.grid(row=1, column=0, sticky="nsew")
        self.riquadro_pdf.columnconfigure(0, weight=1)
        self.riquadro_pdf.rowconfigure(0, weight=1)
        contenitore = ttk.Frame(self.riquadro_pdf)
        contenitore.grid(row=0, column=0, sticky="nsew")
        contenitore.columnconfigure(0, weight=1)
        contenitore.rowconfigure(0, weight=1)
        self.lista_pdf = tk.Listbox(
            contenitore,
            selectmode="extended",
            exportselection=False,
            activestyle="dotbox",
        )
        barra_pdf = ttk.Scrollbar(contenitore, orient="vertical", command=self.lista_pdf.yview)
        self.lista_pdf.configure(yscrollcommand=barra_pdf.set)
        self.lista_pdf.grid(row=0, column=0, sticky="nsew")
        barra_pdf.grid(row=0, column=1, sticky="ns")
        self.lista_pdf.bind("<<ListboxSelect>>", self._su_selezione_pdf)
        self.lista_pdf.bind("<Double-Button-1>", lambda _e: self._mostra_testo())

        azioni = ttk.Frame(self.riquadro_pdf)
        azioni.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        ttk.Button(azioni, text="Seleziona tutti", command=self._seleziona_tutti).grid(row=0, column=0)
        ttk.Button(azioni, text="Nessuno", command=self._deseleziona).grid(row=0, column=1, padx=6)
        ttk.Button(azioni, text="Mostra testo del PDF", command=self._mostra_testo).grid(row=0, column=2)
        self.conteggio = tk.StringVar(value="Nessun PDF")
        ttk.Label(self.riquadro_pdf, textvariable=self.conteggio).grid(
            row=2, column=0, sticky="w", pady=(6, 0)
        )

    def _costruisci_codifica(self, padre: ttk.Frame) -> None:
        padre.columnconfigure(0, weight=1)
        padre.rowconfigure(0, weight=1)
        riquadro = ttk.LabelFrame(padre, text="Codifica del nome", padding=8)
        self.riquadro_codifica = riquadro
        riquadro.grid(row=0, column=0, sticky="nsew")
        riquadro.columnconfigure(0, weight=1)
        riquadro.columnconfigure(1, weight=1)
        riquadro.rowconfigure(1, weight=1)

        scelta = ttk.Frame(riquadro)
        scelta.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        scelta.columnconfigure(1, weight=1)
        ttk.Label(scelta, text="Codifica da usare").grid(row=0, column=0, sticky="w")
        self.scelta_codifica = ttk.Combobox(scelta, state="readonly")
        self.scelta_codifica.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        self.scelta_codifica.set(AUTOMATICA)

        sinistra = ttk.Frame(riquadro)
        destra = ttk.Frame(riquadro)
        sinistra.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        destra.grid(row=1, column=1, sticky="nsew")
        sinistra.columnconfigure(0, weight=1)
        sinistra.rowconfigure(1, weight=1)
        destra.columnconfigure(1, weight=1)

        self.lista_codifiche = tk.Listbox(sinistra, height=4, exportselection=False)
        self.lista_codifiche.grid(row=0, column=0, sticky="ew")
        self.lista_codifiche.bind("<<ListboxSelect>>", self._su_lista_codifiche)
        bottoni_codifica = ttk.Frame(sinistra)
        bottoni_codifica.grid(row=0, column=1, padx=(8, 0), sticky="n")
        ttk.Button(bottoni_codifica, text="Nuova", command=self._nuova_codifica).grid(row=0, column=0, sticky="ew")
        ttk.Button(bottoni_codifica, text="Duplica", command=self._duplica_codifica).grid(
            row=1, column=0, sticky="ew", pady=4
        )
        ttk.Button(bottoni_codifica, text="Elimina", command=self._elimina_codifica).grid(row=2, column=0, sticky="ew")

        self.alberi_campi = ttk.Treeview(
            sinistra,
            columns=("nome", "tipo", "regola"),
            show="headings",
            height=5,
            selectmode="browse",
        )
        for colonna, titolo, larghezza in (
            ("nome", "Nome", 90),
            ("tipo", "Tipo", 130),
            ("regola", "Etichetta o espressione", 180),
        ):
            self.alberi_campi.heading(colonna, text=titolo)
            self.alberi_campi.column(colonna, width=larghezza, anchor="w")
        self.alberi_campi.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(8, 0))
        self.alberi_campi.bind("<Double-Button-1>", lambda _e: self._modifica_campo())
        bottoni_campi = ttk.Frame(sinistra)
        bottoni_campi.grid(row=2, column=0, columnspan=2, sticky="w", pady=(4, 0))
        ttk.Button(bottoni_campi, text="Aggiungi campo", command=self._aggiungi_campo).grid(row=0, column=0)
        ttk.Button(bottoni_campi, text="Modifica campo", command=self._modifica_campo).grid(
            row=0, column=1, padx=6
        )
        ttk.Button(bottoni_campi, text="Rimuovi campo", command=self._rimuovi_campo).grid(row=0, column=2)

        self.nome_codifica = tk.StringVar()
        self.codice = tk.StringVar()
        self.codice_esatto = tk.BooleanVar(value=True)
        self.modello = tk.StringVar()
        self.sottocartella = tk.StringVar()
        self.spazi = tk.BooleanVar(value=False)
        self.hint = tk.StringVar()
        self.origine_codifiche = tk.StringVar()

        self._riga(destra, 0, "Nome codifica", self.nome_codifica)
        self._riga(destra, 1, "Codice nel PDF", self.codice)
        self.codice.trace_add("write", lambda *_: self._aggiorna_hint())
        ttk.Label(
            destra,
            text="Con un codice, la codifica vale solo per i PDF che lo contengono. Vuoto: codifica di riserva.",
            wraplength=360,
            justify="left",
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(4, 0))
        ttk.Checkbutton(
            destra,
            text="Il codice è testo esatto",
            variable=self.codice_esatto,
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(2, 6))
        self._riga(destra, 4, "Nome file", self.modello)
        ttk.Label(destra, textvariable=self.hint, wraplength=360, justify="left").grid(
            row=5, column=0, columnspan=2, sticky="w", pady=(2, 4)
        )
        self._riga(destra, 6, "Sottocartella", self.sottocartella)
        ttk.Checkbutton(
            destra,
            text="Nel nome sostituisci gli spazi con _",
            variable=self.spazi,
        ).grid(row=7, column=0, columnspan=2, sticky="w", pady=(2, 0))

        fondo = ttk.Frame(riquadro)
        fondo.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Button(fondo, text="Apri file", command=self._importa).grid(row=0, column=0)
        ttk.Button(fondo, text="Esporta", command=self._esporta).grid(row=0, column=1, padx=6)
        ttk.Button(fondo, text="Salva", command=self._salva).grid(row=0, column=2)
        ttk.Button(fondo, text="Carica esempio", command=self._carica_esempio).grid(row=0, column=3, padx=(6, 0))
        ttk.Label(fondo, textvariable=self.origine_codifiche, wraplength=640, justify="left").grid(
            row=1, column=0, columnspan=4, sticky="w", pady=(6, 0)
        )

    def _sistema_divisori(self) -> None:
        self.update_idletasks()
        altezza = self.verticale.winfo_height()
        if altezza <= 1:
            return
        richiesto = self.riquadro_codifica.winfo_reqheight() + 20
        spazio_anteprima = max(170, altezza - richiesto)
        try:
            self.verticale.sashpos(0, max(240, altezza - spazio_anteprima))
        except tk.TclError:
            return

    def _costruisci_anteprima(self, padre: ttk.Frame) -> None:
        padre.columnconfigure(0, weight=1)
        padre.rowconfigure(1, weight=1)
        ttk.Label(padre, text="Anteprima").grid(row=0, column=0, sticky="w")
        tabella = ttk.Frame(padre)
        tabella.grid(row=1, column=0, sticky="nsew", pady=4)
        tabella.columnconfigure(0, weight=1)
        tabella.rowconfigure(0, weight=1)
        self.anteprima = ttk.Treeview(
            tabella,
            columns=("file", "codifica", "dati", "destinazione", "stato"),
            show="headings",
            selectmode="browse",
        )
        for colonna, titolo, larghezza in (
            ("file", "File originale", 160),
            ("codifica", "Codifica", 110),
            ("dati", "Dati letti", 240),
            ("destinazione", "Nuovo percorso", 280),
            ("stato", "Stato", 220),
        ):
            self.anteprima.heading(colonna, text=titolo)
            self.anteprima.column(colonna, width=larghezza, anchor="w")
        self.anteprima.tag_configure("ok", foreground="#0b6e4f")
        self.anteprima.tag_configure("errore", foreground="#9b1c1c")
        self.anteprima.bind("<Double-Button-1>", self._dettaglio_anteprima)
        ysb = ttk.Scrollbar(tabella, orient="vertical", command=self.anteprima.yview)
        xsb = ttk.Scrollbar(tabella, orient="horizontal", command=self.anteprima.xview)
        self.anteprima.configure(yscrollcommand=ysb.set, xscrollcommand=xsb.set)
        self.anteprima.grid(row=0, column=0, sticky="nsew")
        ysb.grid(row=0, column=1, sticky="ns")
        xsb.grid(row=1, column=0, sticky="ew")

        azioni = ttk.Frame(padre)
        azioni.grid(row=2, column=0, sticky="w")
        ttk.Button(azioni, text="Aggiorna anteprima", command=self._anteprima).grid(row=0, column=0)
        ttk.Button(azioni, text="Copia nella sottocartella", command=self._copia).grid(
            row=0, column=1, padx=8
        )

    def _riga(self, padre: ttk.LabelFrame, riga: int, etichetta: str, variabile: tk.StringVar) -> None:
        ttk.Label(padre, text=etichetta).grid(row=riga, column=0, sticky="w", pady=2)
        ttk.Entry(padre, textvariable=variabile).grid(row=riga, column=1, sticky="ew", padx=(8, 0), pady=2)

    def _stato(self, testo: str) -> None:
        self.stato.set(testo)

    def _carica_iniziale(self, file_codifiche: Path | None) -> None:
        if file_codifiche is not None:
            try:
                self._imposta_codifiche(carica_codifiche(file_codifiche), file_codifiche)
            except ErroreCodifica as exc:
                messagebox.showerror("Codifiche", str(exc), parent=self)
                self._imposta_codifiche(self._esempio_sicuro(), percorso_config_predefinito())
            return
        predefinito = percorso_config_predefinito()
        if predefinito.is_file():
            try:
                self._imposta_codifiche(carica_codifiche(predefinito), predefinito)
                return
            except ErroreCodifica as exc:
                messagebox.showerror("Codifiche", str(exc), parent=self)
        self._imposta_codifiche(self._esempio_sicuro(), predefinito)

    def _esempio_sicuro(self) -> list[Codifica]:
        try:
            return carica_esempio()
        except ErroreCodifica:
            return [
                Codifica(
                    nome="Documento",
                    campi=[Campo("codice", "Codice")],
                    modello_nome="{codice}",
                    sottocartella="rinominati",
                )
            ]

    def _imposta_codifiche(self, codifiche: list[Codifica], percorso: Path | None) -> None:
        self.codifiche = list(codifiche)
        self.percorso_codifiche = percorso
        if percorso is None:
            self.origine_codifiche.set("Codifiche non ancora salvate.")
        elif percorso.is_file():
            self.origine_codifiche.set(f"File codifiche: {percorso}")
        else:
            self.origine_codifiche.set(f"Salvataggio: {percorso}")
        self._aggiorna_lista(0)

    def _aggiorna_lista(self, seleziona: int) -> None:
        self._blocco = True
        try:
            self.lista_codifiche.delete(0, tk.END)
            for codifica in self.codifiche:
                self.lista_codifiche.insert(tk.END, codifica.nome)
            if self.codifiche:
                seleziona = max(0, min(seleziona, len(self.codifiche) - 1))
                self.lista_codifiche.selection_set(seleziona)
                self.lista_codifiche.activate(seleziona)
                self._indice = seleziona
                self._mostra_codifica(self.codifiche[seleziona])
            else:
                self._indice = None
        finally:
            self._blocco = False
        self._aggiorna_combo()

    def _mostra_codifica(self, codifica: Codifica) -> None:
        self.nome_codifica.set(codifica.nome)
        self.codice.set(codifica.codice)
        self.codice_esatto.set(codifica.codice_esatto)
        self.modello.set(codifica.modello_nome)
        self.sottocartella.set(codifica.sottocartella)
        self.spazi.set(codifica.spazi_underscore)
        self._campi = list(codifica.campi)
        self._disegna_campi()
        self._aggiorna_hint()

    def _disegna_campi(self) -> None:
        self.alberi_campi.delete(*self.alberi_campi.get_children())
        for indice, campo in enumerate(self._campi):
            self.alberi_campi.insert(
                "",
                "end",
                iid=str(indice),
                values=(campo.nome, TIPI_VISIBILI.get(campo.tipo, campo.tipo), campo.regola),
            )

    def _aggiorna_hint(self) -> None:
        nomi = [campo.nome for campo in self._campi]
        esempio_campi = nomi[:3] or ["nome_originale"]
        nomi.append("nome_originale")
        if self.codice.get().strip():
            nomi.append("codice_trovato")
        segnaposto = ", ".join(f"{{{nome}}}" for nome in nomi)
        esempio = "_".join(f"{{{nome}}}" for nome in esempio_campi)
        self.hint.set(f"Segnaposto: {segnaposto}. Esempio: {esempio}")

    def _aggiorna_combo(self) -> None:
        attuale = self.scelta_codifica.get()
        valori = [AUTOMATICA, *[codifica.nome for codifica in self.codifiche]]
        self.scelta_codifica.configure(values=valori)
        self.scelta_codifica.set(attuale if attuale in valori else AUTOMATICA)

    def _leggi_modulo(self) -> Codifica:
        return Codifica(
            nome=self.nome_codifica.get(),
            codice=self.codice.get(),
            codice_esatto=bool(self.codice_esatto.get()),
            campi=list(self._campi),
            modello_nome=self.modello.get(),
            sottocartella=self.sottocartella.get(),
            spazi_underscore=bool(self.spazi.get()),
        )

    def _memorizza_modulo(self) -> None:
        if self._indice is None:
            raise ErroreCodifica("Nessuna codifica selezionata.")
        codifica = self._leggi_modulo()
        nomi = [altra.nome for posizione, altra in enumerate(self.codifiche) if posizione != self._indice]
        if codifica.nome in nomi:
            raise ErroreCodifica(f"Esiste già una codifica chiamata «{codifica.nome}».")
        self.codifiche[self._indice] = codifica
        self._blocco = True
        try:
            self.lista_codifiche.delete(self._indice)
            self.lista_codifiche.insert(self._indice, codifica.nome)
            self.lista_codifiche.selection_clear(0, tk.END)
            self.lista_codifiche.selection_set(self._indice)
            self.lista_codifiche.activate(self._indice)
        finally:
            self._blocco = False
        self._aggiorna_combo()

    def _su_lista_codifiche(self, _event: object = None) -> None:
        if self._blocco:
            return
        selezione = self.lista_codifiche.curselection()
        if not selezione:
            return
        nuovo = int(selezione[0])
        if self._indice is not None and nuovo != self._indice:
            try:
                self._memorizza_modulo()
            except ErroreCodifica as exc:
                self._blocco = True
                try:
                    self.lista_codifiche.selection_clear(0, tk.END)
                    self.lista_codifiche.selection_set(self._indice)
                finally:
                    self._blocco = False
                messagebox.showerror("Codifica non valida", str(exc), parent=self)
                return
            self._blocco = True
            try:
                self.lista_codifiche.selection_clear(0, tk.END)
                self.lista_codifiche.selection_set(nuovo)
                self.lista_codifiche.activate(nuovo)
            finally:
                self._blocco = False
        self._indice = nuovo
        self._mostra_codifica(self.codifiche[nuovo])

    def _nuova_codifica(self) -> None:
        try:
            self._memorizza_modulo()
        except ErroreCodifica as exc:
            messagebox.showerror("Codifica non valida", str(exc), parent=self)
            return
        nome = _nome_libero("Nuova codifica", [codifica.nome for codifica in self.codifiche])
        self.codifiche.append(
            Codifica(
                nome=nome,
                campi=[Campo("codice", "Codice")],
                modello_nome="{codice}",
                sottocartella="rinominati",
            )
        )
        self._aggiorna_lista(len(self.codifiche) - 1)

    def _duplica_codifica(self) -> None:
        try:
            self._memorizza_modulo()
        except ErroreCodifica as exc:
            messagebox.showerror("Codifica non valida", str(exc), parent=self)
            return
        if self._indice is None:
            return
        origine = self.codifiche[self._indice]
        nome = _nome_libero(f"{origine.nome} copia", [codifica.nome for codifica in self.codifiche])
        self.codifiche.append(
            Codifica(
                nome=nome,
                codice=origine.codice,
                codice_esatto=origine.codice_esatto,
                campi=list(origine.campi),
                modello_nome=origine.modello_nome,
                sottocartella=origine.sottocartella,
                spazi_underscore=origine.spazi_underscore,
            )
        )
        self._aggiorna_lista(len(self.codifiche) - 1)

    def _elimina_codifica(self) -> None:
        if len(self.codifiche) <= 1:
            messagebox.showerror("Codifica", "Serve almeno una codifica.", parent=self)
            return
        if self._indice is None:
            return
        del self.codifiche[self._indice]
        self._aggiorna_lista(min(self._indice, len(self.codifiche) - 1))

    def _campo_selezionato(self) -> int | None:
        selezione = self.alberi_campi.selection()
        if not selezione:
            return None
        return int(selezione[0])

    def _aggiungi_campo(self) -> None:
        dialogo = DialogoCampo(self, None, self._testo_prova(), [campo.nome for campo in self._campi])
        self.wait_window(dialogo)
        if dialogo.risultato is None:
            return
        self._campi.append(dialogo.risultato)
        self._disegna_campi()
        self._aggiorna_hint()

    def _modifica_campo(self) -> None:
        indice = self._campo_selezionato()
        if indice is None:
            messagebox.showerror("Campi", "Seleziona un campo da modificare.", parent=self)
            return
        altri = [campo.nome for posizione, campo in enumerate(self._campi) if posizione != indice]
        dialogo = DialogoCampo(self, self._campi[indice], self._testo_prova(), altri)
        self.wait_window(dialogo)
        if dialogo.risultato is None:
            return
        self._campi[indice] = dialogo.risultato
        self._disegna_campi()
        self._aggiorna_hint()

    def _rimuovi_campo(self) -> None:
        indice = self._campo_selezionato()
        if indice is None:
            return
        del self._campi[indice]
        self._disegna_campi()
        self._aggiorna_hint()

    def _testo_prova(self) -> str | None:
        pdf = self._primo_pdf()
        if pdf is None:
            return None
        try:
            return leggi_testo_pdf(pdf)
        except ErrorePdf:
            return None

    def _apri_cartella(self) -> None:
        iniziale = self.cartella or Path.home()
        scelta = filedialog.askdirectory(
            parent=self,
            title="Apri la cartella dei PDF",
            mustexist=True,
            initialdir=str(iniziale),
        )
        if not scelta:
            return
        self._imposta_cartella(Path(scelta))

    def _aggiorna_elenco(self) -> None:
        if self.cartella is None:
            self._apri_cartella()
            return
        self._imposta_cartella(self.cartella)

    def _imposta_cartella(self, cartella: Path) -> None:
        cartella = cartella.expanduser()
        if not cartella.is_dir():
            messagebox.showerror("Cartella", f"La cartella non esiste:\n{cartella}", parent=self)
            return
        self.cartella = cartella
        self.percorso_cartella.set(str(cartella))
        try:
            self.pdf = elenco_pdf(cartella)
        except ErroreCodifica as exc:
            messagebox.showerror("Cartella", str(exc), parent=self)
            return
        self.lista_pdf.delete(0, tk.END)
        for pdf in self.pdf:
            self.lista_pdf.insert(tk.END, pdf.name)
        if self.pdf:
            self.lista_pdf.selection_set(0, tk.END)
        self.riquadro_pdf.configure(text=f"PDF nella cartella ({len(self.pdf)})")
        self._su_selezione_pdf()
        if not self.pdf:
            self._stato("Nella cartella non ci sono file PDF.")
        else:
            self._stato(f"Cartella aperta: {len(self.pdf)} PDF. Aggiorna l'anteprima, poi copia.")

    def _seleziona_tutti(self) -> None:
        if self.pdf:
            self.lista_pdf.selection_set(0, tk.END)
            self._su_selezione_pdf()

    def _deseleziona(self) -> None:
        self.lista_pdf.selection_clear(0, tk.END)
        self._su_selezione_pdf()

    def _su_selezione_pdf(self, _event: object = None) -> None:
        selezionati = len(self.lista_pdf.curselection())
        if not self.pdf:
            self.conteggio.set("Nessun PDF")
        else:
            self.conteggio.set(f"{selezionati} selezionati di {len(self.pdf)}")

    def _pdf_selezionati(self) -> list[Path]:
        return [self.pdf[int(indice)] for indice in self.lista_pdf.curselection()]

    def _primo_pdf(self) -> Path | None:
        selezione = self.lista_pdf.curselection()
        if not selezione:
            return None
        return self.pdf[int(selezione[0])]

    def _forzata(self) -> str | None:
        valore = self.scelta_codifica.get()
        if not valore or valore == AUTOMATICA:
            return None
        return valore

    def _mostra_testo(self) -> None:
        pdf = self._primo_pdf()
        if pdf is None:
            messagebox.showerror("Nessun PDF", "Seleziona un PDF.", parent=self)
            return
        try:
            testo = leggi_testo_pdf(pdf)
        except ErrorePdf as exc:
            messagebox.showerror("PDF", str(exc), parent=self)
            return
        try:
            codifica = self._leggi_modulo()
        except ErroreCodifica:
            codifica = None
        FinestraTesto(self, pdf.name, testo, codifica)

    def _prepara_piani(self) -> list[PianoFile] | None:
        try:
            self._memorizza_modulo()
        except ErroreCodifica as exc:
            messagebox.showerror("Codifica non valida", str(exc), parent=self)
            return None
        if self.cartella is None:
            messagebox.showerror("Cartella", "Apri prima la cartella dei PDF.", parent=self)
            return None
        selezionati = self._pdf_selezionati()
        if not selezionati:
            messagebox.showerror("Nessun PDF", "Seleziona almeno un PDF.", parent=self)
            return None
        self.configure(cursor="watch")
        self._stato("Leggo i PDF…")
        self.update_idletasks()
        try:
            return pianifica(selezionati, self.cartella, self.codifiche, self._forzata())
        finally:
            self.configure(cursor="")

    def _anteprima(self) -> None:
        piani = self._prepara_piani()
        if piani is None:
            return
        self._mostra_piani(piani)

    def _copia(self) -> None:
        piani = self._prepara_piani()
        if piani is None:
            return
        self._mostra_piani(piani)
        pronti = [piano for piano in piani if piano.pronto]
        if not pronti:
            messagebox.showerror(
                "Niente da copiare",
                "Nessun PDF ha tutti i dati richiesti. Controlla l'anteprima.",
                parent=self,
            )
            return
        errori = len(piani) - len(pronti)
        righe = "\n".join(self._relativo(piano.destinazione) for piano in pronti[:8] if piano.destinazione)
        if len(pronti) > 8:
            righe += f"\n… e altri {len(pronti) - 8}"
        messaggio = (
            f"Copio {len(pronti)} PDF nella sottocartella.\n"
            "I file originali restano al loro posto.\n\n"
            f"{righe}"
        )
        if errori:
            messaggio += f"\n\n{errori} file con errore verranno ignorati."
        if not chiedi_conferma(self, "Conferma copia", messaggio):
            self._stato("Copia annullata.")
            return
        esegui(pronti)
        riusciti = [piano for piano in pronti if piano.pronto and piano.destinazione is not None]
        self._mostra_piani(piani)
        if not riusciti:
            messagebox.showerror(
                "Copia non riuscita",
                "\n".join(piano.errore or "Errore sconosciuto" for piano in pronti),
                parent=self,
            )
            return
        elenco = "\n".join(self._relativo(piano.destinazione) for piano in riusciti[:12])
        messagebox.showinfo(
            "File salvati",
            "Ho copiato i PDF qui sotto. Gli originali sono rimasti nella cartella.\n\n" + elenco,
            parent=self,
        )
        self._stato(f"Copiati {len(riusciti)} file. Gli originali non sono stati modificati.")

    def _mostra_piani(self, piani: list[PianoFile]) -> None:
        self._piani = piani
        self.anteprima.delete(*self.anteprima.get_children())
        for indice, piano in enumerate(piani):
            if piano.pronto and piano.destinazione is not None:
                destinazione = self._relativo(piano.destinazione)
                stato = "Pronto"
                tag = "ok"
            else:
                destinazione = ""
                stato = piano.errore or "Errore"
                tag = "errore"
            self.anteprima.insert(
                "",
                "end",
                iid=str(indice),
                values=(
                    piano.origine.name,
                    piano.codifica or "",
                    descrivi_valori(piano.valori),
                    destinazione,
                    stato,
                ),
                tags=(tag,),
            )
        pronti = sum(1 for piano in piani if piano.pronto)
        self._stato(f"Anteprima: {pronti} pronti, {len(piani) - pronti} con errore.")

    def _dettaglio_anteprima(self, _event: object = None) -> None:
        selezione = self.anteprima.selection()
        if not selezione:
            return
        piano = self._piani[int(selezione[0])]
        if piano.pronto and piano.destinazione is not None:
            testo = (
                f"File: {piano.origine.name}\n"
                f"Codifica: {piano.codifica}\n"
                f"Dati: {descrivi_valori(piano.valori)}\n"
                f"Destinazione: {self._relativo(piano.destinazione)}"
            )
        else:
            testo = f"File: {piano.origine.name}\n\n{piano.errore}"
        messagebox.showinfo("Dettaglio", testo, parent=self)

    def _relativo(self, path: Path | None) -> str:
        if path is None:
            return ""
        if self.cartella is None:
            return str(path)
        try:
            return str(path.relative_to(self.cartella))
        except ValueError:
            return str(path)

    def _salva(self) -> None:
        try:
            self._memorizza_modulo()
        except ErroreCodifica as exc:
            messagebox.showerror("Codifica non valida", str(exc), parent=self)
            return
        percorso = self.percorso_codifiche or percorso_config_predefinito()
        try:
            salva_codifiche(percorso, self.codifiche)
        except (ErroreCodifica, OSError) as exc:
            messagebox.showerror("Salvataggio", str(exc), parent=self)
            return
        self.percorso_codifiche = percorso
        self.origine_codifiche.set(f"File codifiche: {percorso}")
        self._stato(f"Codifiche salvate in {percorso}")

    def _importa(self) -> None:
        scelta = filedialog.askopenfilename(
            parent=self,
            title="Apri un file di codifiche",
            filetypes=[("Codifiche JSON", "*.json"), ("Tutti i file", "*.*")],
        )
        if not scelta:
            return
        try:
            codifiche = carica_codifiche(Path(scelta))
        except ErroreCodifica as exc:
            messagebox.showerror("Codifiche", str(exc), parent=self)
            return
        self._imposta_codifiche(codifiche, Path(scelta))
        self._stato(f"Caricate {len(codifiche)} codifiche.")

    def _esporta(self) -> None:
        try:
            self._memorizza_modulo()
        except ErroreCodifica as exc:
            messagebox.showerror("Codifica non valida", str(exc), parent=self)
            return
        scelta = filedialog.asksaveasfilename(
            parent=self,
            title="Esporta le codifiche",
            defaultextension=".json",
            filetypes=[("Codifiche JSON", "*.json")],
        )
        if not scelta:
            return
        percorso = Path(scelta)
        try:
            salva_codifiche(percorso, self.codifiche)
        except (ErroreCodifica, OSError) as exc:
            messagebox.showerror("Esporta", str(exc), parent=self)
            return
        self.percorso_codifiche = percorso
        self.origine_codifiche.set(f"File codifiche: {percorso}")
        self._stato(f"Codifiche esportate in {percorso}")

    def _carica_esempio(self) -> None:
        if not chiedi_conferma(
            self,
            "Esempio",
            "Sostituisco le codifiche aperte con l'esempio Fattura / Documento?",
            pulsante="Carica esempio",
        ):
            return
        self._imposta_codifiche(self._esempio_sicuro(), percorso_config_predefinito())
        self._stato("Ho caricato le codifiche di esempio. Salva se vuoi conservarle.")


class DialogoCampo(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        campo: Campo | None,
        testo: str | None,
        nomi_usati: list[str],
    ) -> None:
        super().__init__(parent)
        self.title("Dato da leggere")
        self.resizable(False, False)
        self.transient(parent)
        self.risultato: Campo | None = None
        self._testo = testo
        self._nomi_usati = set(nomi_usati)
        self.nome = tk.StringVar(value=campo.nome if campo else "")
        self.tipo = tk.StringVar(value=TIPI_VISIBILI.get(campo.tipo, "Etichetta") if campo else "Etichetta")
        self.regola = tk.StringVar(value=campo.regola if campo else "")
        self.messaggio = tk.StringVar()
        self.aiuto = tk.StringVar()

        frame = ttk.Frame(self, padding=12)
        frame.grid(sticky="nsew")
        frame.columnconfigure(1, weight=1)
        ttk.Label(frame, text="Nome nel modello").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.nome, width=42).grid(row=0, column=1, sticky="ew", padx=(8, 0))
        ttk.Label(frame, text="Come lo cerco").grid(row=1, column=0, sticky="w", pady=(6, 0))
        tipo = ttk.Combobox(
            frame,
            textvariable=self.tipo,
            values=list(TIPI_INTERNI),
            state="readonly",
            width=40,
        )
        tipo.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(6, 0))
        tipo.bind("<<ComboboxSelected>>", lambda _e: self._aggiorna_aiuto())
        ttk.Label(frame, text="Regola").grid(row=2, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(frame, textvariable=self.regola, width=42).grid(row=2, column=1, sticky="ew", padx=(8, 0), pady=(6, 0))
        ttk.Label(frame, textvariable=self.aiuto, wraplength=420, justify="left").grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(8, 0)
        )
        ttk.Label(frame, textvariable=self.messaggio, wraplength=420, justify="left").grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(8, 0)
        )
        azioni = ttk.Frame(frame)
        azioni.grid(row=5, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(azioni, text="Prova sul PDF", command=self._prova).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(azioni, text="Annulla", command=self.destroy).grid(row=0, column=1, padx=(0, 6))
        ttk.Button(azioni, text="Usa questo campo", command=self._conferma).grid(row=0, column=2)
        self.bind("<Escape>", lambda _e: self.destroy())
        self._aggiorna_aiuto()
        self.grab_set()
        self.update_idletasks()
        self.geometry(f"+{parent.winfo_rootx() + 70}+{parent.winfo_rooty() + 70}")

    def _aggiorna_aiuto(self) -> None:
        if self.tipo.get() == "Espressione regolare":
            self.aiuto.set(
                "Scrivi un'espressione regolare con una parentesi attorno al valore, "
                "per esempio Codice:\\s*([A-Z0-9-]+)."
            )
        else:
            self.aiuto.set(
                "Nel PDF il dato deve stare su una riga come «Codice: valore» oppure «Codice - valore»."
            )

    def _leggi(self) -> Campo:
        return Campo(
            nome=self.nome.get(),
            tipo=TIPI_INTERNI.get(self.tipo.get(), "etichetta"),
            regola=self.regola.get(),
        )

    def _prova(self) -> None:
        try:
            campo = self._leggi()
        except ErroreCodifica as exc:
            self.messaggio.set(str(exc))
            return
        if not self._testo:
            self.messaggio.set("Seleziona un PDF nella finestra principale, poi riprova.")
            return
        valore = campo.estrai(self._testo)
        if valore is None:
            self.messaggio.set("Nessuna corrispondenza in questo PDF.")
        else:
            self.messaggio.set(f"Valore trovato: {valore}")

    def _conferma(self) -> None:
        try:
            campo = self._leggi()
        except ErroreCodifica as exc:
            self.messaggio.set(str(exc))
            return
        if campo.nome in self._nomi_usati:
            self.messaggio.set(f"Il nome «{campo.nome}» è già usato.")
            return
        self.risultato = campo
        self.destroy()


class FinestraTesto(tk.Toplevel):
    def __init__(self, parent: tk.Misc, nome_file_pdf: str, testo: str, codifica: Codifica | None) -> None:
        super().__init__(parent)
        self.title(f"Testo di {nome_file_pdf}")
        self.geometry("720x420")
        self.transient(parent)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        frame = ttk.Frame(self, padding=8)
        frame.grid(sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        widget = tk.Text(frame, wrap="word")
        barra = ttk.Scrollbar(frame, command=widget.yview)
        widget.configure(yscrollcommand=barra.set)
        widget.grid(row=0, column=0, sticky="nsew")
        barra.grid(row=0, column=1, sticky="ns")
        widget.insert("1.0", testo or "(questo PDF non contiene testo selezionabile)")
        widget.tag_configure("trovato", background="#ffe08a")
        if codifica is not None and testo:
            _evidenzia(widget, testo, codifica)
        widget.configure(state="disabled")
        riepilogo = ttk.Label(frame, text=_riepilogo(testo, codifica), wraplength=720, justify="left")
        riepilogo.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Button(frame, text="Chiudi", command=self.destroy).grid(row=2, column=0, sticky="e", pady=(8, 0))
        self.bind("<Escape>", lambda _e: self.destroy())


def chiedi_conferma(parent: tk.Misc, titolo: str, messaggio: str, pulsante: str = "Copia i file") -> bool:
    dialog = tk.Toplevel(parent)
    dialog.title(titolo)
    dialog.transient(parent)
    dialog.resizable(False, False)
    scelta = {"ok": False}

    def accetta() -> None:
        scelta["ok"] = True
        dialog.destroy()

    frame = ttk.Frame(dialog, padding=16)
    frame.grid(sticky="nsew")
    ttk.Label(frame, text=messaggio, wraplength=480, justify="left").grid(row=0, column=0, sticky="w")
    bottoni = ttk.Frame(frame)
    bottoni.grid(row=1, column=0, sticky="e", pady=(12, 0))
    ttk.Button(bottoni, text="Annulla", command=dialog.destroy).grid(row=0, column=0, padx=(0, 8))
    ttk.Button(bottoni, text=pulsante, command=accetta).grid(row=0, column=1)
    dialog.bind("<Escape>", lambda _e: dialog.destroy())
    dialog.grab_set()
    dialog.update_idletasks()
    dialog.geometry(f"+{parent.winfo_rootx() + 80}+{parent.winfo_rooty() + 80}")
    parent.wait_window(dialog)
    return scelta["ok"]


def _evidenzia(widget: tk.Text, testo: str, codifica: Codifica) -> None:
    match_codice = codifica.cerca_codice(testo)
    if match_codice:
        _marca(widget, match_codice.start(), match_codice.end())
    for campo in codifica.campi:
        match = campo.compilato().search(testo)
        if match:
            _marca(widget, match.start(), match.end())


def _marca(widget: tk.Text, inizio: int, fine: int) -> None:
    widget.tag_add("trovato", f"1.0+{inizio}c", f"1.0+{fine}c")


def _riepilogo(testo: str, codifica: Codifica | None) -> str:
    if codifica is None:
        return "La codifica attuale non è valida, quindi non posso proporti un nome."
    if not testo.strip():
        return "Questo PDF non ha testo selezionabile: se è una scansione non posso leggerlo."
    try:
        valori = codifica.estrai(testo, "documento")
    except ErroreCodifica as exc:
        return str(exc)
    righe = [f"{chiave}: {valore}" for chiave, valore in valori.items() if chiave != "nome_originale"]
    try:
        nuovo = nome_file(codifica.modello_nome, valori, ".pdf", codifica.spazi_underscore)
    except ErroreCodifica as exc:
        return str(exc)
    return "Dati letti — " + " · ".join(righe) + f"\nNome file: {nuovo}"


def _nome_libero(base: str, nomi: list[str]) -> str:
    if base not in nomi:
        return base
    numero = 2
    while f"{base} {numero}" in nomi:
        numero += 1
    return f"{base} {numero}"
