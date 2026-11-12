# Zeladoria Urbana por Foto

**Equipe:**
- Joseh Gabriel Trimboli Agra (RM 553094)
- Pedro Henrique de Assuncao Lima (RM 552746)

> Projeto CitizenTech da Global Solution FIAP 2026.2: uma aplicação para registrar ocorrências urbanas por foto e apoiar a análise dos relatos.

## Visão geral

O **Zela** conecta o registro de uma ocorrência urbana a ferramentas de visão computacional e análise de dados. A pessoa informa a localização, descreve o problema e envia uma foto. Quando o detector está disponível, a aplicação sugere possíveis buracos na pista; a sugestão pode ser confirmada ou corrigida antes do envio.

O projeto também inclui um pipeline de dados que valida, organiza e agrega relatos para produzir indicadores de zeladoria urbana.

## Demonstração pública

- **Aplicação:** [zela-gs26-buraco-demo.onrender.com](https://zela-gs26-buraco-demo.onrender.com)
- **Disponibilidade do detector:** [GET /api/cv/status](https://zela-gs26-buraco-demo.onrender.com/api/cv/status)
- **Código, modelo ONNX e evidências de visão computacional:** [branch de implantação codex/cv-public-deploy](https://github.com/Zoviskgabriel/Zeladoria-Urbana-por-Foto/tree/codex/cv-public-deploy)

A hospedagem usa o plano gratuito do Render. Após um período sem acessos, a instância pode suspender temporariamente e levar cerca de um minuto para responder à primeira visita. O endereço público permanece o mesmo.

## O que o sistema faz

- Registra uma ocorrência com foto, localização, descrição e categoria informadas pela pessoa.
- Analisa a imagem e sugere caixas delimitadoras para a classe **buraco**.
- Retorna a classe, a confiança, as coordenadas das caixas e a quantidade de detecções.
- Mantém a pessoa responsável pela confirmação ou correção da categoria.
- Disponibiliza relatos para o pipeline de Big Data, que gera dados limpos e indicadores agregados.

O detector foi treinado para uma única classe: **D40 do RDD2022**, apresentada como “buraco” na interface. Ele não identifica lixo, calçadas, bueiros ou iluminação.

## Visão computacional

O conjunto de treinamento foi preparado a partir de uma amostra de 5.000 imagens anotadas do RDD2022. As anotações Pascal VOC foram convertidas para YOLO, filtrando a classe D40. As caixas em pixels foram normalizadas como centro x, centro y, largura e altura. A divisão própria de treino e validação foi feita por sequência para reduzir a mistura de quadros vizinhos.

| Avaliação | Imagens | Precisão | Recall | mAP@0,5 | mAP@0,5:0,95 |
|---|---:|---:|---:|---:|---:|
| Validação RDD2022 | 1.289 | 0,535 | 0,448 | 0,471 | 0,199 |
| Piloto local revisado | 20 | 0,088 | 0,273 | 0,054 | 0,017 |

O piloto local contém 20 fotos revisadas (10 com buraco e 10 sem buraco) e 11 caixas confirmadas pela equipe. O resultado local é **exploratório**: a amostra é pequena e as métricas são baixas. Ele não demonstra generalização para outras ruas ou cidades. As fotos locais e o arquivo de anotações não são publicados no repositório.

Na aplicação, a imagem é redimensionada proporcionalmente para a entrada de 640 × 640 pixels, com preenchimento, e os pixels são normalizados. As caixas de saída são convertidas de volta para as coordenadas da imagem original. Na implantação, o modelo ONNX é executado em CPU com limiar de confiança 0,35.

A documentação detalhada de preparação, treinamento, avaliação e inferência está em [zeladoria-app/vision/README.md](zeladoria-app/vision/README.md).

## Dados retornados pela inferência

| Campo | Significado |
|---|---|
| label | Classe sugerida pelo detector: buraco. |
| confidence | Confiança associada à detecção, entre 0 e 1. |
| box.x1, y1, x2, y2 | Limites da caixa em pixels da imagem original; origem no canto superior esquerdo. |
| detection_count | Número de caixas aprovadas pelo limiar de confiança e pela supressão de caixas redundantes. |
| Localização, descrição e categoria final | Dados informados ou revisados pela pessoa; não são extraídos automaticamente da foto. |

## API principal

| Método e rota | Uso |
|---|---|
| GET /api/cv/status | Informa se o modelo de visão computacional está disponível. |
| POST /api/cv/predict | Recebe uma imagem e retorna as detecções sugeridas. |
| GET /api/reports | Fornece os relatos disponíveis para integração de dados. |
| POST /api/reports | Registra um novo relato. |

## Executar a aplicação localmente

Para usar o modelo ONNX já preparado, clone o branch de implantação:

~~~powershell
git clone --single-branch --branch codex/cv-public-deploy https://github.com/Zoviskgabriel/Zeladoria-Urbana-por-Foto.git
Set-Location Zeladoria-Urbana-por-Foto\zeladoria-app

python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-deploy.txt
.\.venv\Scripts\python.exe app.py
~~~

Acesse [http://127.0.0.1:8000](http://127.0.0.1:8000). O ambiente de inferência usa ONNX Runtime, NumPy e Pillow. Para preparar dados, treinar ou avaliar o modelo PyTorch, consulte os procedimentos e dependências de desenvolvimento no [guia de visão computacional](zeladoria-app/vision/README.md).

## Pipeline de Big Data

A pasta [entrega-bigdata/](entrega-bigdata/) contém um pipeline em Python e uma DAG Airflow. O fluxo extrai relatos, valida e normaliza campos, separa registros rejeitados, agrega indicadores por período e carrega os resultados.

Execução local com os registros sintéticos incluídos:

~~~powershell
Set-Location entrega-bigdata
python zela_bigdata\dags\zela_pipeline.py --fonte zela_bigdata\exemplos\reports_demo.csv --saida saida\execucao_local
~~~

O conjunto de demonstração é sintético; não representa ocorrências reais. O guia com instruções de Docker e Airflow está no [README de Big Data](entrega-bigdata/README.md), e a definição dos campos está no [dicionário de dados](entrega-bigdata/DICIONARIO_DE_DADOS.md).

## Estrutura do repositório

~~~text
.
├── entrega-bigdata/       Pipeline, DAG Airflow, dicionário, exemplos e evidências
├── zeladoria-app/         Aplicação web, API e componentes de visão computacional
│   ├── static/            Interface web
│   ├── vision/            Preparação de dados, treino, avaliação e inferência
│   ├── models/            Pesos publicados no branch de implantação
│   └── evidence/          Métricas, curvas e imagens intermediárias
├── render.yaml            Configuração de publicação no Render
└── output/pdf/            Relatório PDF da entrega de Big Data
~~~

## Documentação e evidências

- [Guia técnico de visão computacional](zeladoria-app/vision/README.md)
- [Roteiro para o vídeo de demonstração](https://github.com/Zoviskgabriel/Zeladoria-Urbana-por-Foto/blob/codex/cv-public-deploy/zeladoria-app/vision/ROTEIRO_VIDEO_CV.md)
- [Guia do pipeline de Big Data](entrega-bigdata/README.md)
- [Dicionário de dados](entrega-bigdata/DICIONARIO_DE_DADOS.md)
- [Relatório PDF de Big Data](entrega-bigdata/Relatorio_Big_Data_Zeladoria.pdf)
- [Manifesto do conjunto RDD2022](https://github.com/Zoviskgabriel/Zeladoria-Urbana-por-Foto/blob/codex/cv-public-deploy/zeladoria-app/evidence/cv/training/dataset_manifest.json)
- [Métricas da validação RDD2022](https://github.com/Zoviskgabriel/Zeladoria-Urbana-por-Foto/blob/codex/cv-public-deploy/zeladoria-app/evidence/cv/validation/metrics.json)
- [Métricas agregadas do piloto local](https://github.com/Zoviskgabriel/Zeladoria-Urbana-por-Foto/blob/codex/cv-public-deploy/zeladoria-app/evidence/cv_local/validation/metrics.json)
- [Imagem de predições intermediárias](https://github.com/Zoviskgabriel/Zeladoria-Urbana-por-Foto/blob/codex/cv-public-deploy/zeladoria-app/evidence/cv/validation/val_batch0_pred.jpg)

## Privacidade e limitações

As fotos e anotações originais do piloto local permanecem fora do repositório. Os exemplos de Big Data são sintéticos. A aplicação é demonstrativa e não substitui a avaliação humana nem um sistema municipal de atendimento com autenticação, segurança operacional e política de retenção de dados.
