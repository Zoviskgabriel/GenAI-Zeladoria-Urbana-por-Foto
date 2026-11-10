from datetime import datetime, timezone
from email.parser import BytesParser
from email.policy import default
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse
import json
import mimetypes
import sqlite3
import uuid

from vision.inference import predict_image, status as cv_status

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
    return c


class App(BaseHTTPRequestHandler):
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

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print("Zeladoria Urbana por Foto: http://127.0.0.1:8000")
    HTTPServer(("127.0.0.1", 8000), App).serve_forever()
