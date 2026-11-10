# Zeladoria Urbana por Foto

MVP acadêmico: envio de foto, localização aproximada e categoria, armazenamento local em SQLite e painel de relatos. O esquema da tabela `reports` está alinhado ao contrato da entrega Big Data. O item de visão computacional agora tem integração opcional e um fluxo reproduzível para preparar e treinar um detector de buracos; os pesos ainda precisam ser treinados e instalados.

## Executar

Requer Python 3.10+; o servidor básico não usa dependências externas.

```powershell
python app.py
```

Abra http://127.0.0.1:8000. Os arquivos enviados ficam em `uploads/` e os registros em `data/zeladoria.db`.

Para habilitar a sugestão de visão computacional, prepare o conjunto RDD2022, instale `requirements-cv.txt`, treine o modelo e aponte `CV_MODEL_PATH` para `best.pt`. O roteiro completo está em [vision/README.md](vision/README.md). Sem pesos, o envio e a classificação manual continuam funcionando.

## Escopo atual

- O detector opcional cobre apenas buracos (classe RDD2022 D40). O cidadão escolhe a categoria final e pode revisar a sugestão.
- Categorias aceitas pela API: `dano_na_pista`, `calcada`, `bueiro`, `lixo`, `iluminacao`, `outro`.
- Foto JPG, PNG ou WebP, limite de 8 MB.
- Local aproximado e observação opcional; sem cadastro de cidadão.
- Fila simples; status `recebido` e origem `cidadao` seguem o contrato compartilhado.
- `reports.id` é inteiro e também é retornado como `report_id`; data/hora em UTC ISO 8601.
- A API retorna caixas, classe e confiança da inferência; a lista pública de relatos mantém `cv_label`, `cv_confidence`, `cv_model` e `cv_reviewed`, sem expor `confirm_token`.
- Interface responsiva e acessível por teclado.

## Lacunas planejadas

- Treinamento e avaliação em fotos locais do território piloto; o modelo RDD2022 não foi treinado neste workspace.
- Autenticação do painel de manutenção e atualização do status.
- Integração do pacote Airflow canônico do Joseh, integração UiPath e deploy público.
- Notebook de GenAI executado conforme a atividade da disciplina.
- Protótipo físico da placa QR no Maker Lab.

Não publique este servidor de demonstração como serviço aberto: ele ainda não tem autenticação operacional nem política de retenção de imagens. Não envie fotos com rostos, placas ou dados pessoais.

## Plano de execução

A divisão por disciplina e o contrato de dados compartilhado estão em [PLANO_POR_DISCIPLINA.md](PLANO_POR_DISCIPLINA.md). A entrega Big Data integrada está em [disciplinas/02-bigdata](disciplinas/02-bigdata/README.md); o pacote original de Joseh foi copiado sem alterações e recebeu uma configuração Compose externa para este app.

O PDF técnico da disciplina está em [Entrega_Big_Data_Zeladoria.pdf](../output/pdf/Entrega_Big_Data_Zeladoria.pdf). Repositório público: https://github.com/Zoviskgabriel/GenAI-Zeladoria-Urbana-por-Foto. A DAG `zela_relatos` foi executada com sucesso no Airflow 2.10.5; os logs das quatro tarefas e os arquivos de saída estão em `disciplinas/02-bigdata/zela_bigdata/evidencias/execucao_airflow/`. A captura da Graph View está incluída em `disciplinas/02-bigdata/zela_bigdata/evidencias/execucao_airflow/airflow_graph_view_2026-11-10.png`.

