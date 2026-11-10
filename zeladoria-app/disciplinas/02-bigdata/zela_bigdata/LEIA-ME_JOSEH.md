# Base da parte de Big Data (Zela)

Ponto de partida para a disciplina de Big Data. Pode mudar o que quiser: troque a estrutura, as regras e as ferramentas. Só mantenha o **contrato comum**, porque o app, o painel e o robô dependem dele.

## O que tem aqui

| Caminho | Conteúdo |
| --- | --- |
| `README.md` | Arquitetura (diagrama Mermaid), regras de validação, como rodar e evidências |
| `DICIONARIO_DE_DADOS.md` | Tabela `reports` (origem) e tabelas analíticas (destino) |
| `dags/zela_pipeline.py` | Pipeline extrair → validar → agregar → carregar, só com a biblioteca padrão do Python |
| `dags/zela_relatos_dag.py` | DAG do Airflow 2.10 (`@hourly`, retries, troca de dados por arquivos) |
| `docker-compose.airflow.yml` | Airflow standalone, com a interface só em `127.0.0.1:8080` |
| `tests/test_pipeline.py` | 8 testes do pipeline (pytest) |
| `exemplos/relatos_brutos_exemplo.csv` | 14 linhas "sujas" para mostrar a validação (9 são rejeitadas) |
| `exemplos/reports_demo.csv` | 40 relatos demo exportados do banco da API, **sem** `confirm_token` nem foto |
| `evidencias/` | Logs de duas execuções reais da DAG (`state=success`) e os indicadores |

## Rodar rápido, sem Airflow

```bash
cd dags
python3 zela_pipeline.py --fonte ../exemplos/reports_demo.csv --saida ../saida/teste
```

## Contrato que não pode mudar

- `report_id` = `id` da tabela `reports`. É o mesmo usado pelo robô UiPath. Nada de cadastro paralelo.
- `status`: `recebido`, `em_triagem`, `encaminhado` ou `descartado`.
- `category`: `dano_na_pista`, `calcada`, `bueiro`, `lixo`, `iluminacao` ou `outro`.
- `source`: `cidadao` ou `demo`. Dado simulado sempre marcado como `demo`.
- Nunca ler nem exportar `confirm_token`: é segredo do cidadão.

## Evidências que ainda faltam

Prints da interface do Airflow: grafo da DAG e log de uma tarefa. Para tirar, rode o `docker compose -f docker-compose.airflow.yml up` como está no README.
