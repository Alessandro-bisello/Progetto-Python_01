"""PDF minimi con testo, usati dai test."""

from __future__ import annotations

from pathlib import Path


def scrivi_pdf_testo(path: Path, testo: str | list[str]) -> None:
    pagine = [testo] if isinstance(testo, str) else list(testo)
    if not pagine:
        pagine = [""]

    def flusso(testo_pagina: str) -> bytes:
        def escape(valore: str) -> str:
            return valore.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

        linee = testo_pagina.splitlines() or [""]
        comandi = ["BT", "/F1 12 Tf", "72 740 Td", "16 TL"]
        for indice, linea in enumerate(linee):
            if indice:
                comandi.append("T*")
            comandi.append(f"({escape(linea)}) Tj")
        comandi.append("ET")
        return "\n".join(comandi).encode("latin-1", errors="replace")

    font_id = 3
    next_id = 4
    pagine_oggetti: list[tuple[int, bytes]] = []
    kids: list[int] = []
    for testo_pagina in pagine:
        page_id = next_id
        content_id = next_id + 1
        next_id += 2
        kids.append(page_id)
        stream = flusso(testo_pagina)
        pagine_oggetti.append(
            (
                page_id,
                (
                    f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                    f"/Contents {content_id} 0 R /Resources << /Font << /F1 {font_id} 0 R >> >> >>"
                ).encode(),
            )
        )
        pagine_oggetti.append(
            (
                content_id,
                b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
            )
        )

    oggetti = [b""] * next_id
    oggetti[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    kids_ref = " ".join(f"{kid} 0 R" for kid in kids)
    oggetti[2] = f"<< /Type /Pages /Kids [{kids_ref}] /Count {len(kids)} >>".encode()
    oggetti[3] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    for oggetto_id, corpo in pagine_oggetti:
        oggetti[oggetto_id] = corpo

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0] * next_id
    for indice in range(1, next_id):
        offsets[indice] = len(out)
        out.extend(f"{indice} 0 obj\n".encode())
        out.extend(oggetti[indice])
        out.extend(b"\nendobj\n")
    xref = len(out)
    out.extend(f"xref\n0 {next_id}\n".encode())
    out.extend(b"0000000000 65535 f \n")
    for indice in range(1, next_id):
        out.extend(f"{offsets[indice]:010d} 00000 n \n".encode())
    out.extend(
        f"trailer\n<< /Size {next_id} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    path.write_bytes(bytes(out))
