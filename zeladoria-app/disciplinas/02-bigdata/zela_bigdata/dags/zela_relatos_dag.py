"""DAG do Airflow: relatos brutos do Zela -> tabelas analíticas do piloto.

extrair -> validar -> agregar -> carregar

As tarefas trocam dados por arquivos JSON numa pasta de trabalho da execução
(o XCom leva só o caminho), para não guardar dados no banco de metadados do Airflow.

Configuração (variáveis de ambiente do Airflow, ou parâmetros ao disparar a DAG):
    ZELA_FONTE  sqlite:///caminho.db | caminho.csv | http(s)://host/api/reports
    ZELA_SAIDA  pasta onde ficam os CSVs e o zela_analitico.db
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from airflow.decorators import dag, task
from airflow.models.param import Param

import zela_pipeline as zp

FONTE_PADRAO = os.getenv("ZELA_FONTE", "sqlite:////opt/zela/app/dev.db")
SAIDA_PADRAO = os.getenv("ZELA_SAIDA", "/opt/zela/saida")


def _pasta_trabalho(run_id: str) -> Path:
    seguro = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in run_id)
    pasta = Path(SAIDA_PADRAO) / "_trabalho" / seguro
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def _salvar(pasta: Path, nome: str, dados) -> str:
    caminho = pasta / f"{nome}.json"
    caminho.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    return str(caminho)


def _ler(caminho: str):
    return json.loads(Path(caminho).read_text(encoding="utf-8"))


@dag(
    dag_id="zela_relatos",
    description="Relatos do Zela: validação, normalização e agregação por período, categoria e status",
    schedule="@hourly",
    start_date=datetime(2026, 11, 1),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=2)},
    params={
        "fonte": Param(FONTE_PADRAO, type="string", description="sqlite:///..., caminho .csv ou URL da API"),
        "saida": Param(SAIDA_PADRAO, type="string", description="pasta de saída"),
    },
    tags=["zela", "gs2026"],
    doc_md=__doc__,
)
def zela_relatos():
    @task
    def extrair(params=None, run_id=None) -> str:
        brutos = zp.extrair(params["fonte"])
        print(f"{len(brutos)} relatos lidos de {params['fonte']}")
        return _salvar(_pasta_trabalho(run_id), "brutos", brutos)

    @task
    def validar(caminho_brutos: str, run_id=None) -> dict:
        validos, rejeitados = zp.validar(_ler(caminho_brutos))
        print(f"válidos: {len(validos)} | rejeitados: {len(rejeitados)}")
        for r in rejeitados:
            print(f"  rejeitado id={r.get('id')!r}: {r['motivos']}")
        pasta = _pasta_trabalho(run_id)
        return {"validos": _salvar(pasta, "validos", validos), "rejeitados": _salvar(pasta, "rejeitados", rejeitados)}

    @task
    def agregar(caminhos: dict, run_id=None) -> str:
        agregado = zp.agregar(_ler(caminhos["validos"]))
        print(f"{len(agregado)} linhas agregadas (dia, semana e mês)")
        return _salvar(_pasta_trabalho(run_id), "agregado", agregado)

    @task
    def carregar(caminhos: dict, caminho_agregado: str, params=None, run_id=None) -> dict:
        validos, rejeitados = _ler(caminhos["validos"]), _ler(caminhos["rejeitados"])
        ind = zp.indicadores(validos, rejeitados)
        zp.carregar(Path(params["saida"]), validos, rejeitados, _ler(caminho_agregado),
                    {"run_id": run_id, "fonte": params["fonte"], "indicadores": ind})
        print(json.dumps(ind, ensure_ascii=False, indent=2))
        return ind

    caminhos = validar(extrair())
    carregar(caminhos, agregar(caminhos))


zela_relatos()
