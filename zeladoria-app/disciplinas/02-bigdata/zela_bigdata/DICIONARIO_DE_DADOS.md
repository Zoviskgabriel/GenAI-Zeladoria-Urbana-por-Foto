# Dicionário de dados

## Origem: `reports` (banco da aplicação)

É a tabela comum a todas as disciplinas. Cada linha é um relato, e o `id` é o `report_id` usado pelo Airflow e pelo UiPath.

| Campo | Tipo | Nulo? | Domínio / regra | Descrição |
| --- | --- | --- | --- | --- |
| `id` | inteiro | não | Sequencial | `report_id`, também é o número do protocolo mostrado ao cidadão |
| `created_at` | data e hora (UTC) | não | | Momento do envio |
| `location` | texto (3 a 200) | não | | Endereço aproximado ou ponto de referência digitado pelo cidadão |
| `latitude` | real | sim | −90 a 90 | GPS do celular, se a pessoa autorizar |
| `longitude` | real | sim | −180 a 180 | Idem |
| `description` | texto (até 500) | não (pode ser vazio) | | Descrição livre. Os demos começam com "[demonstração]" |
| `image` | texto | não | | Nome do arquivo gerado pela API. **Não é extraído pela DAG** |
| `category` | texto | não | `dano_na_pista`, `calcada`, `bueiro`, `lixo`, `iluminacao`, `outro` | Categoria final: a sugestão aceita ou a escolha do cidadão |
| `status` | texto | não | `recebido`, `em_triagem`, `encaminhado`, `descartado` | Situação do relato |
| `source` | texto | não | `cidadao`, `demo` | `demo` = dado simulado |
| `cv_label` | texto | sim | `dano_na_pista`, `sem_deteccao` | Sugestão da visão. Nulo quando o modelo não estava disponível |
| `cv_confidence` | real | sim | 0 a 1 | Maior confiança entre as detecções válidas |
| `cv_model` | texto | sim | | Modelo que gerou a sugestão |
| `cv_reviewed` | booleano | não | | O cidadão confirmou ou corrigiu a categoria |
| `service_order` | texto | sim | | Número da ordem de serviço gravado pelo robô |
| `confirm_token` | texto | não | | Segredo para a confirmação. **Nunca é extraído pela DAG** |

## Destino: `zela_analitico.db`

### `relatos_limpos`

Uma linha por relato válido, já normalizado.

| Campo | Tipo | Descrição |
| --- | --- | --- |
| `id` | inteiro | `report_id` |
| `created_at` | texto ISO 8601 com fuso UTC | Data de envio normalizada |
| `dia` | texto `AAAA-MM-DD` | Dia (UTC) |
| `semana` | texto `AAAA-Snn` | Semana ISO |
| `mes` | texto `AAAA-MM` | Mês |
| `location` | texto | Local sem espaços repetidos |
| `latitude`, `longitude` | real ou nulo | Nulos quando o par veio incompleto ou fora da faixa |
| `category`, `status`, `source` | texto | Valores canônicos do contrato |
| `cv_label`, `cv_confidence`, `cv_model` | | Copiados da origem |
| `cv_reviewed` | 0 ou 1 | |
| `has_service_order` | 0 ou 1 | Se o robô já gravou a ordem de serviço. O número em si não é copiado |

### `relatos_rejeitados`

Os campos da origem (sem `image` e `confirm_token`) mais:

| Campo | Tipo | Descrição |
| --- | --- | --- |
| `motivos` | texto | Lista separada por `;` com todos os problemas encontrados |

### `agregado_periodo`

Uma linha por (`periodo_tipo`, `periodo`, `category`, `status`, `source`).

| Campo | Tipo | Descrição |
| --- | --- | --- |
| `periodo_tipo` | `dia`, `semana` ou `mes` | Granularidade |
| `periodo` | texto | Valor do período no formato da coluna correspondente |
| `category`, `status`, `source` | texto | Dimensões |
| `total` | inteiro | Relatos no grupo |
| `confirmados_pelo_cidadao` | inteiro | Com `cv_reviewed = 1` |
| `visao_sugeriu_dano` | inteiro | Com `cv_label = dano_na_pista` |
| `visao_concordou` | inteiro | Revisados em que a sugestão (dano ou não) bate com a categoria final |
| `com_ordem_de_servico` | inteiro | Já encaminhados pelo robô |

`source` é uma dimensão para os dados simulados nunca se misturarem com os reais sem aviso. A soma de `total` em um mesmo `periodo_tipo` é igual ao número de relatos válidos.

### `execucoes`

Uma linha por execução da DAG. As outras tabelas são recriadas a cada execução, e esta só recebe novas linhas.

| Campo | Descrição |
| --- | --- |
| `executado_em` | Data e hora UTC da carga |
| `run_id` | `run_id` do Airflow |
| `fonte` | Fonte lida |
| `indicadores_json` | `relatos_lidos`, `relatos_validos`, `relatos_rejeitados`, `relatos_demo`, `taxa_confirmacao_cidadao`, `taxa_concordancia_visao`, `taxa_encaminhamento` |
