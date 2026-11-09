import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from quaderno.cli import main
from quaderno.note import Quaderno


class TestQuaderno(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.percorso = Path(self.tmp.name) / "note.json"
        self.quaderno = Quaderno(self.percorso)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_aggiungi_e_elenco(self) -> None:
        nota = self.quaderno.aggiungi("  Prima nota  ")
        self.assertEqual(nota.id, 1)
        self.assertEqual(nota.testo, "Prima nota")
        self.assertTrue(nota.creata_il.endswith("+00:00"))

        seconda = self.quaderno.aggiungi("Seconda")
        self.assertEqual(seconda.id, 2)
        testi = [n.testo for n in self.quaderno.elenco()]
        self.assertEqual(testi, ["Prima nota", "Seconda"])

    def test_rifiuta_testo_vuoto(self) -> None:
        with self.assertRaises(ValueError):
            self.quaderno.aggiungi("   ")
        self.assertFalse(self.percorso.exists())

    def test_cerca_ignora_maiuscole(self) -> None:
        self.quaderno.aggiungi("Latte e pane")
        self.quaderno.aggiungi("Caffè")
        trovate = self.quaderno.cerca("LATTE")
        self.assertEqual([n.testo for n in trovate], ["Latte e pane"])
        self.assertEqual(self.quaderno.cerca("   "), [])

    def test_elimina(self) -> None:
        self.quaderno.aggiungi("Da togliere")
        self.quaderno.aggiungi("Da tenere")
        self.assertTrue(self.quaderno.elimina(1))
        self.assertFalse(self.quaderno.elimina(1))
        self.assertEqual([n.testo for n in self.quaderno.elenco()], ["Da tenere"])

    def test_id_non_viene_riusato(self) -> None:
        self.quaderno.aggiungi("Uno")
        self.quaderno.elimina(1)
        self.assertEqual(self.quaderno.aggiungi("Due").id, 2)

    def test_file_json_non_valido(self) -> None:
        self.percorso.write_text("{", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.quaderno.elenco()

    def test_salva_caratteri_unicode(self) -> None:
        self.quaderno.aggiungi("città — già")
        dati = json.loads(self.percorso.read_text(encoding="utf-8"))
        self.assertEqual(dati["note"][0]["testo"], "città — già")
        self.assertEqual(dati["prossimo_id"], 2)


class TestCli(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.percorso = str(Path(self.tmp.name) / "note.json")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _run(self, *args: str) -> tuple[int, str, str]:
        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(["--file", self.percorso, *args])
        return code, out.getvalue(), err.getvalue()

    def test_flusso_comandi(self) -> None:
        code, out, _err = self._run("aggiungi", "Comprare il latte")
        self.assertEqual(code, 0)
        self.assertIn("Nota 1 aggiunta.", out)

        code, out, _err = self._run("elenco")
        self.assertEqual(code, 0)
        self.assertIn("Comprare il latte", out)

        code, out, _err = self._run("cerca", "latte")
        self.assertIn("#1", out)

        code, out, err = self._run("elimina", "9")
        self.assertEqual(code, 1)
        self.assertIn("non trovata", err)

        code, out, _err = self._run("elimina", "1")
        self.assertEqual(code, 0)
        self.assertIn("eliminata", out)

        code, out, _err = self._run("elenco")
        self.assertIn("Nessuna nota.", out)

    def test_aggiungi_vuoto(self) -> None:
        code, _out, err = self._run("aggiungi", "  ")
        self.assertEqual(code, 1)
        self.assertIn("vuoto", err)


if __name__ == "__main__":
    unittest.main()
