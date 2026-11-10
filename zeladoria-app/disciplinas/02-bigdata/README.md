# Big Data & Data Integration — Zela

Esta é a entrega de Big Data integrada ao MVP. A pasta `zela_bigdata/` foi copiada do pacote de Joseh sem edição; ela contém a DAG, o pipeline, dicionário, exemplos, testes e evidências recebidas. O contrato do app foi alinhado para a tabela `reports` descrita no dicionário.

## Executar o pipeline local

Requer Python 3.10+ e não precisa de dependências externas:

```powershell
python zela_bigdata\dags\zela_pipeline.py --fonte zela_bigdata\exemplos\reports_demo.csv --saida zela_bigdata\evidencias\execucao_local
```

O conjunto é sintético e vem marcado como `source=demo`. A execução gera o banco analítico e arquivos CSV/JSON na pasta indicada. Evidência gerada nesta cópia: [execucao_pipeline_local.log](zela_bigdata/evidencias/execucao_pipeline_local.log).

Para executar a suíte incluída no pacote: `python -m pip install -r requirements-test.txt` e depois `python -m pytest zela_bigdata/tests -q`. Resultado verificado nesta cópia em 10/11/2026: 8 testes passaram.

## Executar Airflow sobre o banco do MVP

Suba o app primeiro para inicializar `zeladoria-app/data/zeladoria.db`. Depois, nesta pasta (`disciplinas/02-bigdata`), execute:

```powershell
docker compose -f docker-compose.workspace.yml up
```

Abra `http://localhost:8080`, obtenha a senha inicial nos logs do serviço `airflow`, habilite `zela_relatos` e clique em **Trigger DAG**. A configuração local monta o banco em modo somente leitura e limita a interface administrativa a `127.0.0.1`. A saída analítica fica em `saida/`, ignorada pelo Git.

Para repetir a evidência com os dados sintéticos, no PowerShell defina `$env:ZELA_FONTE="/opt/zela/exemplos/reports_demo.csv"` antes de subir o Compose. Para ler o banco do MVP, mantenha o padrão SQLite; o banco precisa existir em `zeladoria-app/data/zeladoria.db`. Para usar a API em vez do SQLite, configure `ZELA_FONTE` com a URL do endpoint `/api/reports`; o host precisa ser alcançável de dentro do contêiner.

## Contrato e privacidade

- A chave compartilhada é `reports.id` / `report_id`; o pipeline lê `id`.
- `status`, `category` e `source` usam os domínios documentados em `zela_bigdata/DICIONARIO_DE_DADOS.md`.
- A DAG não extrai `confirm_token` nem o nome da imagem. A camada analítica também não guarda localização detalhada ou descrição livre.
- Todos os indicadores dos exemplos são sintéticos; não representam resultados de campo.

## Evidências e estado da entrega

Os logs recebidos em `zela_bigdata/evidencias/` vieram no pacote do Joseh. A execução local e a execução via Airflow foram feitas nesta cópia com o CSV sintético. O run `manual__entrega_bigdata_20261110` terminou em `success`; as quatro tarefas `extrair`, `validar`, `agregar` e `carregar` também terminaram em `success`. Os logs de cada tarefa e as saídas CSV/JSON estão em `zela_bigdata/evidencias/execucao_airflow/`. A captura da interface Airflow (Graph View) está incluída em `zela_bigdata/evidencias/execucao_airflow/airflow_graph_view_2026-11-10.png` e também na página 5 do PDF técnico.

O PDF de entrega técnica está em `../../../output/pdf/Entrega_Big_Data_Zeladoria.pdf` a partir desta pasta.
