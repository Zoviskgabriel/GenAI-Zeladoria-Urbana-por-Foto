# Big Data & Data Integration — Zela

**Equipe**

- Joseh Gabriel Trimboli Agra — RM 553094
- Pedro Henrique de Assuncao Lima — RM 552746

## Objetivo

Construir um pipeline reproduzível que recebe relatos urbanos, valida e normaliza os registros, separa dados rejeitados e gera agregações por período, categoria, status e origem. O identificador `reports.id` é preservado como identificador do relato.

## Arquitetura

![Diagrama da arquitetura](docs/arquitetura_pipeline.svg)

A DAG `zela_relatos` orquestra quatro tarefas: `extrair` → `validar` → `agregar` → `carregar`. As fontes aceitas são a tabela SQLite `reports`, uma URL da API ou CSV. As saídas são `relatos_limpos`, `relatos_rejeitados`, `agregado_periodo`, `execucoes` e arquivos CSV/JSON. O dicionário completo está em [DICIONARIO_DE_DADOS.md](DICIONARIO_DE_DADOS.md).

## Ambiente

- Python 3.10 ou superior para executar o pipeline local e os testes.
- Docker Desktop com virtualização habilitada para a execução Airflow. O Compose usa `apache/airflow:2.10.5-python3.12`.
- O pipeline local usa apenas a biblioteca padrão do Python. `requirements.txt` contém `pytest` para a suíte de testes. Instale com `python -m pip install -r requirements.txt`.

## Executar localmente

Na raiz desta pasta:

```powershell
python -m pip install -r requirements.txt
python zela_bigdata\dags\zela_pipeline.py --fonte zela_bigdata\exemplos\reports_demo.csv --saida saida\execucao_local
python -m pytest zela_bigdata\tests -q
```

Resultado verificado: **8 testes aprovados**. O CSV de demonstração contém 40 registros sintéticos.

## Executar a DAG no Airflow

```powershell
docker compose up -d
docker compose logs airflow
```

A senha inicial do usuário `admin` aparece nos logs. Acesse `http://localhost:8080`, habilite `zela_relatos` e use **Trigger DAG**. A fonte padrão é `reports_demo.csv`; a saída fica em `saida/`. Para encerrar: `docker compose down`.

## Evidência da execução

A execução registrada em 10/11/2026 usa o run `manual__entrega_bigdata_20261110`. A DAG e as tarefas `extrair`, `validar`, `agregar` e `carregar` terminaram em `success`. Foram lidos 40 registros, com 40 válidos e nenhum rejeitado. A captura da Graph View, os logs de cada tarefa e os arquivos resultantes estão em [evidencias/execucao_airflow](evidencias/execucao_airflow/). O relatório em PDF reúne arquitetura, dicionário e evidências.

## Limitações e privacidade

Os registros e indicadores apresentados são sintéticos e servem para demonstrar o processamento; não representam dados de campo. A carga recria as tabelas analíticas a cada execução, adequada ao volume de demonstração. O pipeline não extrai o token de confirmação nem o nome da imagem e não copia a descrição livre para a camada analítica.
