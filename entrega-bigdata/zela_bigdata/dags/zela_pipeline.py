"""Pipeline de dados do Zela (Big Data Architecture & Data Integration).

Transforma os relatos brutos da aplicação (tabela `reports`) em tabelas
analíticas do piloto. Só usa a biblioteca padrão do Python, então roda igual
dentro do Airflow, nos testes e na linha de comando.

Etapas (uma tarefa da DAG cada):
    extrair  -> lê SQLite, CSV ou a API (GET /api/reports)
    validar  -> normaliza os campos e separa válidos de rejeitados, com o motivo
    agregar  -> conta relatos por período, categoria, status e origem
    carregar -> grava CSVs e um SQLite analítico (substitui as tabelas a cada execução)

Uso fora do Airflow:
    python zela_pipeline.py --fonte sqlite:///../../.dev/dev.db --saida ../saida
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import unicodedata
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Campos lidos da aplicação. confirm_token e image ficam de fora de propósito:
# o token é segredo do cidadão e a foto não serve para a análise.
CAMPOS = [
    "id", "created_at", "location", "latitude", "longitude", "description",
    "category", "status", "source", "cv_label", "cv_confidence", "cv_model",
    "cv_reviewed", "service_order",
]

CATEGORIAS = {"dano_na_pista", "calcada", "bueiro", "lixo", "iluminacao", "outro"}
STATUS = {"recebido", "em_triagem", "encaminhado", "descartado"}
ORIGENS = {"cidadao", "demo"}

# Sinônimos e valores antigos (versões anteriores da API e digitação livre).
SINONIMOS_CATEGORIA = {
    "buraco": "dano_na_pista", "rachadura": "dano_na_pista", "dano_pista": "dano_na_pista",
    "calcada_quebrada": "calcada", "bueiro_entupido": "bueiro", "boca_de_lobo": "bueiro",
    "entulho": "lixo", "poste": "iluminacao",
}
SINONIMOS_STATUS = {
    "novo": "recebido", "aberto": "recebido", "triagem": "em_triagem",
    "protocolado": "encaminhado", "resolvido": "encaminhado",
    "cancelado": "descartado", "duplicado": "descartado",
}
SINONIMOS_ORIGEM = {"": "cidadao", "real": "cidadao", "simulado": "demo", "demonstracao": "demo"}

INICIO_DO_PILOTO = datetime(2026, 1, 1, tzinfo=timezone.utc)
TOLERANCIA_FUTURO = timedelta(minutes=10)  # relógios de celular adiantados


# ----------------------------------------------------------------- extrair

def extrair(fonte: str) -> list[dict]:
    """Lê os relatos brutos. `fonte`: sqlite:///caminho.db, caminho.csv ou http(s)://.../api/reports."""
    if fonte.startswith("sqlite:///"):
        caminho = fonte.removeprefix("sqlite:///")
        con = sqlite3.connect(f"file:{caminho}?mode=ro", uri=True)  # só leitura
        con.row_factory = sqlite3.Row
        try:
            linhas = con.execute(f"SELECT {', '.join(CAMPOS)} FROM reports ORDER BY id").fetchall()
        finally:
            con.close()
        return [dict(linha) for linha in linhas]
    if fonte.startswith(("http://", "https://")):
        url = fonte if "limit=" in fonte else f"{fonte}{'&' if '?' in fonte else '?'}limit=500"
        with urllib.request.urlopen(url, timeout=30) as resp:  # noqa: S310 (URL vem da configuração)
            return [{c: r.get(c) for c in CAMPOS} for r in json.load(resp)]
    with open(fonte, newline="", encoding="utf-8") as f:
        return [{c: r.get(c) for c in CAMPOS} for r in csv.DictReader(f)]


# ----------------------------------------------------------------- validar

def _chave(texto) -> str:
    """'  Em Triagem ' -> 'em_triagem'; tira acentos e padroniza separadores."""
    t = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
    return "_".join(t.strip().lower().replace("-", " ").split())


def normalizar_categoria(valor) -> str | None:
    k = _chave(valor)
    k = SINONIMOS_CATEGORIA.get(k, k)
    return k if k in CATEGORIAS else None


def normalizar_status(valor) -> str | None:
    k = _chave(valor)
    k = SINONIMOS_STATUS.get(k, k)
    return k if k in STATUS else None


def normalizar_origem(valor) -> str | None:
    k = _chave(valor)
    k = SINONIMOS_ORIGEM.get(k, k)
    return k if k in ORIGENS else None


def ler_data(valor) -> datetime | None:
    """Aceita ISO 8601 com ou sem fuso (sem fuso = UTC, como a API grava)."""
    if valor in (None, ""):
        return None
    try:
        d = datetime.fromisoformat(str(valor).strip().replace("Z", "+00:00").replace(" ", "T", 1))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _numero(valor) -> float | None:
    try:
        return None if valor in (None, "") else float(valor)
    except (TypeError, ValueError):
        return None


def _booleano(valor) -> bool:
    return _chave(valor) in {"1", "true", "sim", "t", "yes"}


def validar(brutos: list[dict], agora: datetime | None = None) -> tuple[list[dict], list[dict]]:
    """Devolve (válidos normalizados, rejeitados com `motivos`)."""
    agora = agora or datetime.now(timezone.utc)
    validos, rejeitados, vistos = [], [], set()
    for bruto in brutos:
        motivos = []

        try:
            rid = int(str(bruto.get("id")).strip())
        except (TypeError, ValueError):
            rid = None
            motivos.append("id ausente ou não numérico")
        if rid is not None and rid in vistos:
            motivos.append("id duplicado")

        local = " ".join(str(bruto.get("location") or "").split())
        if len(local) < 3:
            motivos.append("local vazio ou curto demais")

        categoria = normalizar_categoria(bruto.get("category"))
        if categoria is None:
            motivos.append(f"categoria desconhecida: {bruto.get('category')!r}")

        status = normalizar_status(bruto.get("status"))
        if status is None:
            motivos.append(f"status desconhecido: {bruto.get('status')!r}")

        origem = normalizar_origem(bruto.get("source"))
        if origem is None:
            motivos.append(f"origem desconhecida: {bruto.get('source')!r}")

        criado = ler_data(bruto.get("created_at"))
        if criado is None:
            motivos.append("data ausente ou inválida")
        elif criado > agora + TOLERANCIA_FUTURO:
            motivos.append("data no futuro")
        elif criado < INICIO_DO_PILOTO:
            motivos.append("data anterior ao piloto")

        lat, lon = _numero(bruto.get("latitude")), _numero(bruto.get("longitude"))
        if (lat is None) != (lon is None) or (lat is not None and not (-90 <= lat <= 90 and -180 <= lon <= 180)):
            lat = lon = None  # coordenada opcional: descarta só ela, não o relato

        if motivos:
            rejeitados.append({**{c: bruto.get(c) for c in CAMPOS}, "motivos": "; ".join(motivos)})
            continue

        vistos.add(rid)
        semana = criado.isocalendar()
        validos.append({
            "id": rid,
            "created_at": criado.astimezone(timezone.utc).isoformat(),
            "dia": criado.astimezone(timezone.utc).date().isoformat(),
            "semana": f"{semana.year}-S{semana.week:02d}",
            "mes": criado.astimezone(timezone.utc).strftime("%Y-%m"),
            "location": local,
            "latitude": lat,
            "longitude": lon,
            "category": categoria,
            "status": status,
            "source": origem,
            "cv_label": _chave(bruto.get("cv_label")) or None,
            "cv_confidence": _numero(bruto.get("cv_confidence")),
            "cv_model": (str(bruto.get("cv_model")).strip() or None) if bruto.get("cv_model") else None,
            "cv_reviewed": _booleano(bruto.get("cv_reviewed")),
            "has_service_order": bool(str(bruto.get("service_order") or "").strip()),
        })
    return validos, rejeitados


# ----------------------------------------------------------------- agregar

def agregar(validos: list[dict]) -> list[dict]:
    """Uma linha por (tipo de período, período, categoria, status, origem)."""
    grupos: dict[tuple, Counter] = defaultdict(Counter)
    for r in validos:
        for tipo in ("dia", "semana", "mes"):
            g = grupos[(tipo, r[tipo], r["category"], r["status"], r["source"])]
            g["total"] += 1
            g["confirmados_pelo_cidadao"] += r["cv_reviewed"]
            g["visao_sugeriu_dano"] += r["cv_label"] == "dano_na_pista"
            # A sugestão "acertou" quando bate com a categoria final escolhida pelo cidadão.
            g["visao_concordou"] += r["cv_reviewed"] and (
                (r["cv_label"] == "dano_na_pista") == (r["category"] == "dano_na_pista")
            ) and r["cv_label"] is not None
            g["com_ordem_de_servico"] += r["has_service_order"]
    return [
        {"periodo_tipo": k[0], "periodo": k[1], "category": k[2], "status": k[3], "source": k[4], **dict(v)}
        for k, v in sorted(grupos.items())
    ]


def indicadores(validos: list[dict], rejeitados: list[dict]) -> dict:
    total = len(validos)
    revisados = [r for r in validos if r["cv_reviewed"] and r["cv_label"] is not None]
    concordou = sum((r["cv_label"] == "dano_na_pista") == (r["category"] == "dano_na_pista") for r in revisados)
    return {
        "relatos_lidos": total + len(rejeitados),
        "relatos_validos": total,
        "relatos_rejeitados": len(rejeitados),
        "relatos_demo": sum(r["source"] == "demo" for r in validos),
        "taxa_confirmacao_cidadao": round(sum(r["cv_reviewed"] for r in validos) / total, 3) if total else None,
        "taxa_concordancia_visao": round(concordou / len(revisados), 3) if revisados else None,
        "taxa_encaminhamento": round(sum(r["status"] == "encaminhado" for r in validos) / total, 3) if total else None,
    }


# ----------------------------------------------------------------- carregar

def _escrever_csv(caminho: Path, linhas: list[dict], campos: list[str]) -> None:
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
        w.writeheader()
        w.writerows(linhas)


def _substituir_tabela(con: sqlite3.Connection, nome: str, linhas: list[dict], campos: list[str]) -> None:
    con.execute(f'DROP TABLE IF EXISTS "{nome}"')
    con.execute(f'CREATE TABLE "{nome}" ({", ".join(f'"{c}"' for c in campos)})')
    con.executemany(
        f'INSERT INTO "{nome}" VALUES ({", ".join("?" for _ in campos)})',
        [[linha.get(c) for c in campos] for linha in linhas],
    )


CAMPOS_LIMPOS = ["id", "created_at", "dia", "semana", "mes", "location", "latitude", "longitude", "category",
                 "status", "source", "cv_label", "cv_confidence", "cv_model", "cv_reviewed", "has_service_order"]
CAMPOS_REJEITADOS = [*CAMPOS, "motivos"]
CAMPOS_AGREGADO = ["periodo_tipo", "periodo", "category", "status", "source", "total", "confirmados_pelo_cidadao",
                   "visao_sugeriu_dano", "visao_concordou", "com_ordem_de_servico"]


def carregar(saida: Path, validos, rejeitados, agregado, info: dict) -> dict:
    """Grava CSVs e o SQLite analítico. As tabelas são recriadas a cada execução (idempotente)."""
    saida.mkdir(parents=True, exist_ok=True)
    _escrever_csv(saida / "relatos_limpos.csv", validos, CAMPOS_LIMPOS)
    _escrever_csv(saida / "relatos_rejeitados.csv", rejeitados, CAMPOS_REJEITADOS)
    _escrever_csv(saida / "agregado_periodo.csv", agregado, CAMPOS_AGREGADO)

    con = sqlite3.connect(saida / "zela_analitico.db")
    try:
        with con:
            _substituir_tabela(con, "relatos_limpos", validos, CAMPOS_LIMPOS)
            _substituir_tabela(con, "relatos_rejeitados", rejeitados, CAMPOS_REJEITADOS)
            _substituir_tabela(con, "agregado_periodo", agregado, CAMPOS_AGREGADO)
            con.execute("CREATE TABLE IF NOT EXISTS execucoes (executado_em, run_id, fonte, indicadores_json)")
            con.execute("INSERT INTO execucoes VALUES (?, ?, ?, ?)", (
                datetime.now(timezone.utc).isoformat(), info.get("run_id"), info.get("fonte"),
                json.dumps(info.get("indicadores"), ensure_ascii=False),
            ))
    finally:
        con.close()
    (saida / "indicadores.json").write_text(json.dumps(info.get("indicadores"), ensure_ascii=False, indent=2), encoding="utf-8")
    return {"saida": str(saida), "tabelas": ["relatos_limpos", "relatos_rejeitados", "agregado_periodo", "execucoes"]}


# ----------------------------------------------------------------- linha de comando

def executar(fonte: str, saida: Path, run_id: str = "manual") -> dict:
    brutos = extrair(fonte)
    validos, rejeitados = validar(brutos)
    agregado = agregar(validos)
    ind = indicadores(validos, rejeitados)
    carregar(saida, validos, rejeitados, agregado, {"run_id": run_id, "fonte": fonte, "indicadores": ind})
    return ind


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--fonte", required=True)
    p.add_argument("--saida", type=Path, default=Path("saida"))
    a = p.parse_args()
    print(json.dumps(executar(a.fonte, a.saida), ensure_ascii=False, indent=2))
