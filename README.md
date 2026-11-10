# Zeladoria Urbana por Foto

Projeto CitizenTech 2026.2: MVP acadêmico para registrar problemas urbanos com foto, categoria manual e localização aproximada, mantendo o mesmo identificador de relato entre app, dados e automação.

Repositório público da equipe: [GenAI-Zeladoria-Urbana-por-Foto](https://github.com/Zoviskgabriel/GenAI-Zeladoria-Urbana-por-Foto).

Integrantes: Joseh Gabriel Trimboli Agra (RM 553094) e Pedro Henrique de Assuncao Lima (RM 5527476).

## Rodar o app

```powershell
cd zeladoria-app
python app.py
```

Abra `http://127.0.0.1:8000`. O servidor básico usa a biblioteca padrão do Python. A integração opcional de visão computacional e os scripts para preparar, treinar e avaliar o detector estão em `zeladoria-app/vision/`; o modelo treinado e a validação em fotos locais ainda faltam. O protótipo não deve ser publicado como serviço aberto.

## Entrega de Big Data & Data Integration

O pacote-base Big Data recebido de Joseh está em `zeladoria-app/disciplinas/02-bigdata/zela_bigdata/`. O pacote original foi preservado; a integração acrescenta instruções e uma configuração Docker Compose compatível com o banco do MVP.

Para reproduzir a transformação local com os dados de demonstração:

```powershell
python zeladoria-app\disciplinas\02-bigdata\zela_bigdata\dags\zela_pipeline.py `
  --fonte zeladoria-app\disciplinas\02-bigdata\zela_bigdata\exemplos\reports_demo.csv `
  --saida zeladoria-app\disciplinas\02-bigdata\zela_bigdata\evidencias\execucao_local
```

Os dados são sintéticos. A execução registrada nesta cópia leu 40 relatos, aceitou 40, rejeitou 0 e produziu 74 linhas agregadas. Logs que vieram no ZIP do Joseh estão identificados como evidências recebidas; a execução local tem log e saídas próprios.

O documento técnico está em [`output/pdf/Entrega_Big_Data_Zeladoria.pdf`](output/pdf/Entrega_Big_Data_Zeladoria.pdf). A DAG foi executada em Airflow 2.10.5 com sucesso: as tarefas extrair, validar, agregar e carregar terminaram. Os logs e saídas estão no pacote. A captura da Graph View está incluída no PDF e em `zeladoria-app/disciplinas/02-bigdata/zela_bigdata/evidencias/execucao_airflow/airflow_graph_view_2026-11-10.png`. A URL pública do repositório da equipe está no link acima; o pacote ZIP contém a versão completa da entrega Big Data.

## Referências internas

- [App e execução](zeladoria-app/README.md)
- [Plano por disciplina e contrato comum](zeladoria-app/PLANO_POR_DISCIPLINA.md)
- [Instruções da entrega de Big Data](zeladoria-app/disciplinas/02-bigdata/README.md)
