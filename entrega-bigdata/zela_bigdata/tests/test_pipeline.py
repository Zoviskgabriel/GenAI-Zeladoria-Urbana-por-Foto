import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent / "dags"))

import zela_pipeline as zp  # noqa: E402

EXEMPLO = AQUI.parent / "exemplos" / "relatos_brutos_exemplo.csv"
AGORA = datetime(2026, 11, 10, tzinfo=timezone.utc)


def processar():
    return zp.validar(zp.extrair(str(EXEMPLO)), agora=AGORA)


def test_separa_validos_e_rejeitados():
    validos, rejeitados = processar()
    assert [r["id"] for r in validos] == [1, 2, 3, 4, 5]
    motivos = {str(r["id"]): r["motivos"] for r in rejeitados}
    assert "local vazio" in motivos["6"]
    assert "categoria desconhecida" in motivos["7"]
    assert motivos["8"] == "data no futuro"
    assert "data ausente ou inválida" in motivos["9"]
    assert "status desconhecido" in motivos["10"]
    assert "id duplicado" in motivos["2"]
    assert "id ausente" in motivos["abc"]
    assert motivos["13"] == "data anterior ao piloto"
    assert "origem desconhecida" in motivos["14"]


def test_normaliza_status_categoria_origem_e_texto():
    v = {r["id"]: r for r in processar()[0]}
    assert (v[2]["category"], v[2]["status"]) == ("dano_na_pista", "em_triagem")
    assert (v[3]["category"], v[3]["location"]) == ("calcada", "Travessa do Mercado, 45")
    assert (v[4]["category"], v[4]["status"], v[4]["source"]) == ("bueiro", "recebido", "demo")
    assert v[5]["status"] == "encaminhado"  # "protocolado" da API antiga


def test_datas_em_utc_e_periodos():
    v = {r["id"]: r for r in processar()[0]}
    assert v[2]["created_at"] == "2026-11-02T14:00:00+00:00"  # sem fuso = UTC
    assert (v[3]["dia"], v[3]["semana"], v[3]["mes"]) == ("2026-11-03", "2026-S45", "2026-11")


def test_coordenada_incompleta_e_descartada_sem_perder_relato():
    v = {r["id"]: r for r in processar()[0]}
    assert (v[4]["latitude"], v[4]["longitude"]) == (None, None)
    assert (v[1]["latitude"], v[1]["longitude"]) == (-23.55, -46.63)


def test_agregado_soma_o_total_de_validos_por_tipo_de_periodo():
    validos, _ = processar()
    ag = zp.agregar(validos)
    for tipo in ("dia", "semana", "mes"):
        assert sum(l["total"] for l in ag if l["periodo_tipo"] == tipo) == len(validos)
    nov = [l for l in ag if l["periodo_tipo"] == "mes" and l["category"] == "dano_na_pista"]
    assert sum(l["total"] for l in nov) == 3


def test_indicadores():
    validos, rejeitados = processar()
    ind = zp.indicadores(validos, rejeitados)
    assert (ind["relatos_lidos"], ind["relatos_validos"], ind["relatos_rejeitados"]) == (14, 5, 9)
    assert ind["relatos_demo"] == 5
    # revisados com sugestão: 1, 2 e 3 -> todos concordam com a categoria final
    assert ind["taxa_concordancia_visao"] == 1.0


def test_nao_extrai_token_nem_foto(tmp_path):
    db = tmp_path / "app.db"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE reports (id, created_at, location, latitude, longitude, description, image, category,"
                " status, source, cv_label, cv_confidence, cv_model, cv_reviewed, service_order, confirm_token)")
    con.execute("INSERT INTO reports VALUES (1, '2026-11-02T10:00:00', 'Rua A, 1', NULL, NULL, '', 'x.png',"
                " 'dano_na_pista', 'recebido', 'cidadao', NULL, NULL, NULL, 0, NULL, 'SEGREDO')")
    con.commit()
    con.close()
    brutos = zp.extrair(f"sqlite:///{db}")
    assert "confirm_token" not in brutos[0] and "image" not in brutos[0]


def test_carregar_e_idempotente(tmp_path):
    validos, rejeitados = processar()
    ag = zp.agregar(validos)
    info = {"run_id": "t", "fonte": "teste", "indicadores": zp.indicadores(validos, rejeitados)}
    zp.carregar(tmp_path, validos, rejeitados, ag, info)
    zp.carregar(tmp_path, validos, rejeitados, ag, info)
    con = sqlite3.connect(tmp_path / "zela_analitico.db")
    assert con.execute("SELECT COUNT(*) FROM relatos_limpos").fetchone()[0] == 5
    assert con.execute("SELECT COUNT(*) FROM relatos_rejeitados").fetchone()[0] == 9
    assert con.execute("SELECT COUNT(*) FROM execucoes").fetchone()[0] == 2
    assert (tmp_path / "agregado_periodo.csv").read_text(encoding="utf-8").startswith("periodo_tipo,")
