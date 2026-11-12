from datetime import datetime, timezone
from email.parser import BytesParser
from email.policy import default
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import json
import mimetypes
import os
import sqlite3
import uuid

try:
    from vision.inference import predict_image, status as cv_status
except Exception as exc:
    # The RPA demo uses only the local triage and order routes. Keep those
    # routes runnable even when optional computer-vision dependencies are not
    # installed in the evaluator's environment.
    _CV_IMPORT_ERROR = exc

    def predict_image(_image):
        raise RuntimeError("Detector de visão computacional indisponível.") from _CV_IMPORT_ERROR

    def cv_status():
        return {
            "available": False,
            "message": "Detector indisponível; a categoria manual e a triagem humana continuam disponíveis.",
        }

ROOT = Path(__file__).parent
DB = ROOT / "data" / "zeladoria.db"
UP = ROOT / "uploads"
STATIC = ROOT / "static"
MAX = 8 * 1024 * 1024
CATEGORIES = {"dano_na_pista", "calcada", "bueiro", "lixo", "iluminacao", "outro"}
STATUSES = {"recebido", "em_triagem", "encaminhado", "descartado"}


def connect():
    DB.parent.mkdir(exist_ok=True)
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.execute(
        """CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            location TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            description TEXT NOT NULL DEFAULT '',
            image TEXT NOT NULL,
            category TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'recebido',
            source TEXT NOT NULL DEFAULT 'cidadao',
            cv_label TEXT,
            cv_confidence REAL,
            cv_model TEXT,
            cv_reviewed INTEGER NOT NULL DEFAULT 0,
            service_order TEXT,
            confirm_token TEXT NOT NULL
        )"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS rpa_demo_approvals (
            report_id INTEGER PRIMARY KEY,
            approved_at TEXT NOT NULL,
            approved_by TEXT NOT NULL DEFAULT 'triagem-demo'
        )"""
    )
    return c


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def render_rpa_demo():
    with connect() as c:
        pending = [dict(row) for row in c.execute(
            """SELECT r.id, r.created_at, r.location, r.category, r.description
               FROM reports r
               LEFT JOIN rpa_demo_approvals a ON a.report_id = r.id
               WHERE r.source = 'demo' AND r.status IN ('recebido', 'em_triagem')
                 AND r.service_order IS NULL AND a.report_id IS NULL
               ORDER BY r.created_at, r.id"""
        )]
        approved = [dict(row) for row in c.execute(
            """SELECT r.id, r.created_at, r.location, r.category, r.description, a.approved_at
               FROM reports r JOIN rpa_demo_approvals a ON a.report_id = r.id
               WHERE r.source = 'demo' AND r.status = 'em_triagem'
                 AND r.service_order IS NULL
               ORDER BY a.approved_at, r.id"""
        )]
        completed = [dict(row) for row in c.execute(
            """SELECT id, location, category, service_order, created_at
               FROM reports WHERE source = 'demo' AND service_order IS NOT NULL
               ORDER BY id DESC LIMIT 10"""
        )]

    def rows(items, mode):
        if not items:
            return '<p class="empty">Nenhum relato nesta etapa.</p>'
        rendered = []
        for item in items:
            rid = int(item["id"])
            loc = escape(item["location"] or "")
            category = escape(item["category"] or "")
            description = escape(item.get("description") or "")
            if mode == "pending":
                action = (
                    f'<form method="post" action="/rpa-demo/approve">'
                    f'<input type="hidden" name="report_id" value="{rid}">'
                    f'<button class="secondary" type="submit">Validar para ordem</button></form>'
                )
            elif mode == "approved":
                action = (
                    f'<form method="post" action="/rpa-demo/orders">'
                    f'<input type="hidden" name="report_id" value="{rid}">'
                    f'<button data-testid="create-order-{rid}" type="submit">Criar ordem para relato {rid}</button></form>'
                )
            else:
                action = (
                    f'<span id="service-order-{rid}" class="order">'
                    f'{escape(item["service_order"] or "")}</span>'
                )
            rendered.append(
                f'<article class="item" data-report-id="{rid}"><div><b>Relato {rid}</b>'
                f'<span>{category} · {loc}</span><small>{description}</small></div>{action}</article>'
            )
        return "".join(rendered)

    return f'''<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Portal de manutenção · Demonstração</title><style>
:root{{--ink:#191922;--pink:#d41464;--line:#e3dfe4;--muted:#686a74}}*{{box-sizing:border-box}}
body{{margin:0;background:#f6f4f5;color:var(--ink);font:16px/1.5 system-ui,Segoe UI,Arial,sans-serif}}
header{{background:#1b1b22;color:white;padding:24px max(calc((100vw - 1000px)/2),24px)}}header b{{color:#ff6fa7}}
main{{max-width:1000px;margin:auto;padding:28px 24px}}.warning{{background:#fff2f7;border:1px solid #f4bfd3;border-radius:10px;padding:13px 16px;margin-bottom:18px}}
.panel{{background:white;border:1px solid var(--line);border-radius:12px;padding:20px;margin:14px 0}}h1{{margin:0;font-size:1.45rem}}h2{{margin:0 0 10px;font-size:1.12rem}}
.item{{display:flex;justify-content:space-between;align-items:center;gap:20px;border-top:1px solid var(--line);padding:14px 0}}.item span,.item small{{display:block}}.item small{{color:var(--muted);margin-top:4px}}
button{{background:var(--pink);color:white;border:0;border-radius:8px;padding:10px 14px;font:inherit;font-weight:700;cursor:pointer;white-space:nowrap}}
button.secondary{{background:#34333a}}.order{{font-weight:800;color:#125b37}}.empty{{color:var(--muted)}}footer{{text-align:center;color:var(--muted);font-size:.83rem;padding:18px}}
@media(max-width:650px){{.item{{align-items:flex-start;flex-direction:column}}}}
</style></head><body><header><b>ZELA · PORTAL DE MANUTENÇÃO</b></header><main>
<h1>Fila de ordens de serviço</h1>
<p class="warning"><strong>Ambiente acadêmico de demonstração.</strong> Os registros usam <code>source=demo</code> e não são enviados a uma prefeitura.</p>
<section class="panel"><h2>1 · Triagem humana</h2><p>Confira os campos e libere apenas relatos válidos para a automação.</p>{rows(pending, "pending")}</section>
<section class="panel"><h2>2 · Aprovados para automação</h2><p>O robô UiPath usa o botão de cada relato para registrar a ordem.</p>{rows(approved, "approved")}</section>
<section class="panel"><h2>3 · Ordens registradas</h2>{rows(completed, "completed")}</section>
</main><footer>Demo local · dados fictícios · acesso sem autenticação</footer></body></html>'''


class App(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def send(self, code, body, typ="application/json; charset=utf-8"):
        b = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", typ)
        self.send_header("Content-Length", str(len(b)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        p = urlparse(self.path).path
        if p == "/rpa-demo":
            return self.send(200, render_rpa_demo(), "text/html; charset=utf-8")
        if p == "/":
            return self.send(200, (STATIC / "index.html").read_bytes(), "text/html; charset=utf-8")
        if p in ["/app.css", "/app.js"]:
            f = STATIC / p[1:]
            return self.send(200, f.read_bytes(), (mimetypes.guess_type(f.name)[0] or "text/plain") + "; charset=utf-8")
        if p == "/api/reports":
            # Never expose confirm_token; the Airflow pipeline also excludes it.
            public_fields = "id, created_at, location, latitude, longitude, description, image, category, status, source, cv_label, cv_confidence, cv_model, cv_reviewed, service_order"
            with connect() as c:
                rows = [dict(x) for x in c.execute(f"SELECT {public_fields} FROM reports ORDER BY created_at DESC")]
            for row in rows:
                row["report_id"] = row["id"]
            return self.send(200, json.dumps(rows, ensure_ascii=False))
        if p == "/api/cv/status":
            return self.send(200, json.dumps(cv_status(), ensure_ascii=False))
        if p.startswith("/uploads/"):
            name = Path(p).name
            f = UP / name
            if f.exists():
                return self.send(200, f.read_bytes(), mimetypes.guess_type(name)[0] or "application/octet-stream")
        return self.send(404, "{}")

    def do_POST(self):
        endpoint = urlparse(self.path).path
        if endpoint in ("/rpa-demo/approve", "/rpa-demo/orders"):
            return self.handle_rpa_demo(endpoint)
        if endpoint not in ("/api/reports", "/api/cv/predict"):
            return self.send(404, "{}")
        try:
            n = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            n = 0
        if n <= 0 or n > MAX + 20000:
            return self.send(413, json.dumps({"error": "Arquivo vazio ou maior que 8 MB."}))
        raw = self.rfile.read(n)
        msg = BytesParser(policy=default).parsebytes(
            b"Content-Type: " + self.headers.get("Content-Type", "").encode() + b"\r\nMIME-Version: 1.0\r\n\r\n" + raw
        )
        fields = {}
        image = None
        mime = ""
        for part in msg.iter_parts():
            name = part.get_param("name", header="content-disposition")
            data = part.get_payload(decode=True) or b""
            if name == "photo":
                image, mime = data, part.get_content_type()
            elif name in ("location", "description", "category", "cv_reviewed"):
                fields[name] = data.decode("utf-8", "replace").strip()

        if endpoint == "/api/cv/predict":
            if not image or mime not in ("image/jpeg", "image/png", "image/webp"):
                return self.send(400, json.dumps({"error": "Envie uma imagem JPG, PNG ou WebP."}, ensure_ascii=False))
            if len(image) > MAX:
                return self.send(413, json.dumps({"error": "A imagem deve ter no máximo 8 MB."}, ensure_ascii=False))
            try:
                prediction = predict_image(image)
            except ValueError as exc:
                return self.send(400, json.dumps({"error": str(exc)}, ensure_ascii=False))
            except Exception as exc:
                print(f"Falha na inferência CV: {type(exc).__name__}: {exc}")
                prediction = {"available": False, "message": "Não foi possível executar o detector. A categoria manual continua disponível."}
            return self.send(200, json.dumps(prediction, ensure_ascii=False))

        category = fields.get("category", "dano_na_pista")
        if not image or mime not in ("image/jpeg", "image/png", "image/webp") or not fields.get("location"):
            return self.send(400, json.dumps({"error": "Informe o local e envie uma imagem JPG, PNG ou WebP."}))
        if len(image) > MAX:
            return self.send(413, json.dumps({"error": "A imagem deve ter no máximo 8 MB."}))
        if category not in CATEGORIES:
            return self.send(400, json.dumps({"error": "Categoria inválida."}))

        ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}[mime]
        filename = uuid.uuid4().hex + ext
        UP.mkdir(exist_ok=True)
        (UP / filename).write_bytes(image)
        try:
            prediction = predict_image(image)
        except Exception as exc:
            print(f"Falha na inferência CV; relato seguirá por triagem manual: {type(exc).__name__}: {exc}")
            prediction = {"available": False}
        now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        token = uuid.uuid4().hex
        cv_label = prediction.get("label") if prediction.get("available") else None
        cv_conf = prediction.get("confidence") if prediction.get("available") else None
        cv_model = prediction.get("model") if prediction.get("available") else None
        cv_reviewed = int(bool(prediction.get("available")) and fields.get("cv_reviewed") == "1")
        with connect() as c:
            cur = c.execute(
                """INSERT INTO reports
                   (created_at, location, description, image, category, status, source,
                    cv_label, cv_confidence, cv_model, cv_reviewed, confirm_token)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (now, fields["location"][:160], fields.get("description", "")[:500], filename,
                 category, "recebido", "cidadao", cv_label, cv_conf, cv_model, cv_reviewed, token),
            )
            report_id = cur.lastrowid
        if cv_label:
            message = "Relato recebido. A sugestão de buraco foi salva para revisão humana."
        elif prediction.get("available"):
            message = "Relato recebido. O detector não encontrou buraco acima do limiar; a triagem continua manual."
        else:
            message = "Relato recebido. O detector ainda não está disponível; a triagem continua manual."
        return self.send(201, json.dumps({
            "id": report_id,
            "report_id": report_id,
            "message": message,
            "cv_label": cv_label,
            "cv_confidence": cv_conf,
            "cv_reviewed": cv_reviewed,
        }, ensure_ascii=False))

    def handle_rpa_demo(self, endpoint):
        try:
            n = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            n = 0
        if n <= 0 or n > 4096:
            return self.send(400, "Requisição inválida.", "text/plain; charset=utf-8")
        fields = parse_qs(self.rfile.read(n).decode("utf-8", "replace"))
        try:
            report_id = int(fields.get("report_id", [""])[0])
        except (TypeError, ValueError):
            return self.send(400, "report_id inválido.", "text/plain; charset=utf-8")

        with connect() as c:
            row = c.execute(
                "SELECT id, created_at, location, category, status, source, service_order "
                "FROM reports WHERE id = ?",
                (report_id,),
            ).fetchone()
            if not row or row["source"] != "demo" or row["service_order"]:
                return self.send(409, "Relato indisponível para esta demonstração.", "text/plain; charset=utf-8")
            if not (row["location"] or "").strip() or row["category"] not in CATEGORIES:
                return self.send(409, "Localização ou categoria inválida para abertura de ordem.", "text/plain; charset=utf-8")

            if endpoint == "/rpa-demo/approve":
                if row["status"] not in ("recebido", "em_triagem"):
                    return self.send(409, "O relato não está aguardando triagem.", "text/plain; charset=utf-8")
                c.execute("UPDATE reports SET status = 'em_triagem' WHERE id = ?", (report_id,))
                c.execute(
                    "INSERT OR IGNORE INTO rpa_demo_approvals (report_id, approved_at) VALUES (?, ?)",
                    (report_id, utc_now()),
                )
            else:
                approved = c.execute(
                    "SELECT 1 FROM rpa_demo_approvals WHERE report_id = ?", (report_id,)
                ).fetchone()
                if not approved or row["status"] != "em_triagem":
                    return self.send(409, "O relato ainda não foi validado para automação.", "text/plain; charset=utf-8")
                created_at = row["created_at"] or ""
                year = created_at[:4] if len(created_at) >= 4 and created_at[:4].isdigit() else utc_now()[:4]
                order_id = f"DEMO-OS-{year}-{report_id:06d}"
                updated = c.execute(
                    "UPDATE reports SET service_order = ?, status = 'encaminhado' "
                    "WHERE id = ? AND source = 'demo' AND service_order IS NULL",
                    (order_id, report_id),
                )
                if updated.rowcount != 1:
                    return self.send(409, "A ordem já foi criada ou o relato mudou.", "text/plain; charset=utf-8")
                c.execute("DELETE FROM rpa_demo_approvals WHERE report_id = ?", (report_id,))

        self.send_response(303)
        self.send_header("Location", "/rpa-demo")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    print(f"Zeladoria Urbana por Foto: http://{host}:{port}")
    class DemoHTTPServer(ThreadingHTTPServer):
        daemon_threads = True
        request_queue_size = 32

    DemoHTTPServer((host, port), App).serve_forever(poll_interval=0.5)
