from __future__ import annotations

import html
import json
import subprocess
import textwrap
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "evidencia" / "sprint-12"
LOGS_DIR = EVIDENCE_DIR / "logs"


def fetch_json(url: str) -> object:
    with urllib.request.urlopen(url) as response:
        return json.loads(response.read().decode("utf-8"))


def run_command(command: list[str]) -> str:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout


def render_svg_lines(
    title: str,
    lines: list[str],
    output_path: Path,
    *,
    width: int = 1600,
    line_height: int = 24,
    font_size: int = 16,
    background: str = "#0f172a",
    foreground: str = "#e2e8f0",
) -> None:
    title_lines = textwrap.wrap(title, width=90) or [title]
    wrapped_lines: list[str] = []
    for line in lines:
        wrapped_lines.extend(textwrap.wrap(line, width=120) or [""])

    total_lines = len(title_lines) + len(wrapped_lines) + 3
    height = max(320, total_lines * line_height + 40)

    y = 36
    content: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        f'<rect width="100%" height="100%" fill="{background}" />',
    ]
    for title_line in title_lines:
        content.append(
            f'<text x="24" y="{y}" fill="#93c5fd" font-family="Consolas, monospace" font-size="{font_size + 2}">{html.escape(title_line)}</text>'
        )
        y += line_height

    y += 10
    for line in wrapped_lines:
        content.append(
            f'<text x="24" y="{y}" fill="{foreground}" font-family="Consolas, monospace" font-size="{font_size}">{html.escape(line)}</text>'
        )
        y += line_height

    content.append("</svg>")
    output_path.write_text("\n".join(content), encoding="utf-8")


def build_db_table_lines(rows: list[dict[str, object]]) -> list[str]:
    headers = [
        "id",
        "created_at",
        "endpoint",
        "interaction_type",
        "status",
        "confidence_label",
        "latency_total_ms",
        "top_score",
    ]
    lines = [
        " | ".join(headers),
        "-" * 150,
    ]
    for row in rows:
        values = [str(row.get(header, "")) for header in headers]
        lines.append(" | ".join(values))
    return lines


def extract_code_snippet() -> str:
    middleware_lines = (ROOT / "app" / "middleware" / "audit_middleware.py").read_text(
        encoding="utf-8"
    ).splitlines()
    service_lines = (ROOT / "app" / "services" / "audit_service.py").read_text(
        encoding="utf-8"
    ).splitlines()

    selected = ["# Middleware", *middleware_lines[:60], "", "# Servicio", *service_lines[:90]]
    return "\n".join(selected)


def main() -> None:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    summary = fetch_json("http://localhost:8000/auditoria/resumen")
    records = fetch_json("http://localhost:8000/auditoria/registros?limit=30")
    db_rows = [
        row
        for row in records
        if row.get("endpoint") not in {"/health", "/auditoria/registros", "/auditoria/resumen"}
    ][:8]
    if not db_rows:
        db_rows = records[:8]
    api_logs = run_command(["docker", "compose", "logs", "api", "--tail=120"])

    (EVIDENCE_DIR / "auditoria-resumen.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (EVIDENCE_DIR / "auditoria-registros.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (EVIDENCE_DIR / "tabla-auditoria-db.json").write_text(
        json.dumps(db_rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (LOGS_DIR / "auditoria-api.log").write_text(api_logs, encoding="utf-8")

    snippet = extract_code_snippet()
    (EVIDENCE_DIR / "codigo-auditoria.txt").write_text(snippet, encoding="utf-8")

    render_svg_lines(
        "Sprint 12 - Tabla de auditoría exportada desde SQLite (/data/audit.db)",
        build_db_table_lines(db_rows),
        EVIDENCE_DIR / "01-tabla-auditoria-db.svg",
    )
    render_svg_lines(
        "Sprint 12 - Código fuente del sistema de logging y monitoreo",
        snippet.splitlines(),
        EVIDENCE_DIR / "02-codigo-auditoria.svg",
        width=1700,
    )

    readme = textwrap.dedent(
        """
        # Evidencia Sprint 12

        Meta validada: cada interacción genera un registro persistente con latencia, estado, score y metadatos de auditoría.

        Archivos principales:

        - `01-tabla-auditoria-db.svg`: vista visual de los últimos registros guardados en SQLite.
        - `02-codigo-auditoria.svg`: fragmento visual del middleware y servicio de auditoría.
        - `auditoria-resumen.json`: resumen agregado del módulo de auditoría.
        - `auditoria-registros.json`: respuesta del endpoint `/auditoria/registros`.
        - `tabla-auditoria-db.json`: export de los últimos registros persistidos en la base de auditoría.
        - `codigo-auditoria.txt`: extracto del código de logging/monitoreo implementado.
        - `logs/auditoria-api.log`: logs reales del backend con latencias y alertas.
        """
    ).strip()
    (EVIDENCE_DIR / "README.md").write_text(readme + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
