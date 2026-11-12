# Execução do projeto por disciplina

## Produto comum

**Zeladoria Urbana por Foto**: o cidadão registra um problema urbano com foto, categoria informada manualmente e localização aproximada; a ocorrência segue para triagem. A visão computacional sugere buracos quando há pesos instalados, mas a categoria escolhida e a revisão humana continuam valendo.

**Escopo base do MVP:** uma região piloto a definir; categorias escolhidas manualmente entre os valores aceitos no contrato; sem promessa de classificação automática, reparo ou integração municipal até validação.

## Contrato compartilhado entre componentes

O registro principal é a tabela `reports` do SQLite da aplicação, seguindo o contrato da DAG do Joseh: `id` inteiro (o `report_id` compartilhado), `created_at` em UTC, `location`, `latitude`, `longitude`, `description`, `image`, `category`, `status`, `source`, campos opcionais de visão computacional e `service_order`. O `confirm_token` é segredo interno e não deve sair pela API nem pelo pipeline analítico.

Campos usados pela visão computacional: `cv_label`, `cv_confidence`, `cv_model`, `cv_reviewed`. A pessoa pode confirmar ou corrigir a sugestão; a classificação não decide automaticamente se a via é segura.

- API de entrada: `POST /api/reports` com `location`, `description` e `photo`.
- API de consulta: `GET /api/reports`.
- Categorias: `dano_na_pista`, `calcada`, `bueiro`, `lixo`, `iluminacao`, `outro`. Status: `recebido`, `em_triagem`, `encaminhado`, `descartado`. Origem: `cidadao` ou `demo`.
- Dados simulados devem ser marcados como demonstração. Não incluir nome, telefone, rosto ou placa.
- Airflow e UiPath consomem o mesmo `report_id`; não criar cadastros paralelos.

## 1. Generative AI for Engineering

**Componente:** FonteBot responde dúvidas sobre o uso do sistema com base no README/FAQ.

**Entregas:** notebook usado em aula modificado e executado; modelo alterado via API com justificativa; pelo menos três prompts revisados e justificados em Markdown; pelo menos três células novas de experimento; README, requisitos/ambiente e evidências no GitHub.

**Experimentos mínimos:** perguntas novas e caso sem resposta; saída JSON validada; tratamento de erro da API ou resposta inválida.

**Dependência externa:** obter o notebook-base do canal compartilhado da disciplina e configurar a chave de API em variável de ambiente. Nunca publicar segredo.

## 2. Big Data Architecture & Data Integration

**Status:** a implementação canônica é o pacote `zela_bigdata` enviado pelo Joseh e integrado em `disciplinas/02-bigdata/zela_bigdata/` sem alteração dos arquivos originais. O app foi alinhado ao contrato e há um Compose de integração que aponta para `data/zeladoria.db`. O pipeline Python local passou nos testes; a DAG Airflow 2.10.5 foi executada com dados sintéticos, as quatro tarefas terminaram com sucesso e a captura da Graph View foi incluída no PDF e no pacote de evidências. Repositório público: https://github.com/Zoviskgabriel/GenAI-Zeladoria-Urbana-por-Foto.

**Componente:** DAG Airflow que transforma relatos brutos em tabelas analíticas para o piloto.

**Entregas:** DAG reproduzível; diagrama de arquitetura; dicionário de dados; logs/prints ou vídeo de execução; instruções no README.

**MVP de dados:** usar o contrato e o pipeline do Joseh, validar os dados da tabela `reports`, segregar rejeitados e produzir tabelas agregadas por período. Dados de demonstração usam `source=demo`; relatos reais usam `source=cidadao`.

## 3. Business Intelligence & Startup Development

**Responsável:** PH.

**Componente:** hipótese de negócio e pitch com demonstração funcional.

**Entregas:** Lean Canvas consolidado; modelo de negócio com usuário, comprador, canal e hipótese de preço; ficha técnica comum; vídeo de até cinco minutos com todos os integrantes e demo da URL pública.

**Hipótese inicial:** cidadão usa gratuitamente; campus, organização ou prefeitura pode contratar painel e gestão de ocorrências. Validar comprador e processo por conversa; não inventar tração ou preço confirmado.

## 4. Applied Computer Vision

**Componente:** análise de foto de dano na via, inicialmente uma classe: buraco/dano na pista.

**Entregas:** aplicação/URL pública; vídeo de até cinco minutos; documentação das transformações intermediárias e dos dados extraídos; imagens e evidências de execução.

**Critério de honestidade:** usar RDD2022 como ponto de partida, mas avaliar também fotos locais. Mostrar confiança e permitir confirmação humana. Não afirmar que o modelo cobre lixo, bueiros ou toda rua brasileira.

**Implementado neste workspace:** conversor Pascal VOC → YOLO para a classe D40, separação determinística de treino/validação, detector treinado por 30 épocas no RDD2022 e avaliações RDD e local registradas. Também estão prontos o endpoint de prévia e a apresentação da sugestão no formulário. O piloto foi fechado com 20 fotos revisadas (10 com buraco, 10 sem buraco) e 11 caixas confirmadas pela equipe. Veja [vision/README.md](vision/README.md).

## 5. Robotic Process Automation

**Componente:** transformar relato validado em ordem de serviço numa fila de manutenção.

**Entregas:** assessment do processo, business case, BPMN As-Is e To-Be, automação `.xaml`, vídeo de até três minutos e pacote `.zip`.

**Prova curta antes de investir:** confirmar acesso autorizado, campos, autenticação e viabilidade do portal municipal. Se não funcionar no prazo, automatizar um portal de demonstração funcional e declarar a limitação. Comparar RPA com API.

**Execução demonstrada:** como o workspace não identifica município, portal, URL ou autorização, foi criado o fallback local em `disciplinas/05-rpa/`, com triagem humana, relatos `source=demo`, vínculo por `report_id`, business case, BPMNs e workflow UiPath. O vídeo de 11/11 mostra aprovação humana dos relatos 1–3, execução do robô para criar as três primeiras OS, aprovação humana do relato 4 e uma segunda execução que cria a quarta OS. O MP4 integral (2min12s) foi incluído no pacote ZIP. A integração com portal municipal permanece condicionada a acesso, mapeamento dos campos e autorização do órgão.

## 6. Secure DevOps Tools & Cloud Computing

**Componente:** publicar o mesmo MVP com build repetível, segurança e observabilidade.

**Entregas:** Dockerfile enxuto e usuário não-root; Compose; Terraform e estado/variáveis protegidos; GitHub Actions com build, Gitleaks, Semgrep e Trivy; deploy; métricas e alerta; documentação de custos e dados pessoais.

**Condição:** não expor portas administrativas ao público nem salvar segredos no repositório.

## 7. Project-Based Maker Lab

**Componente:** placa acessível com QR code que abre o formulário de relato no território piloto.

**Entregas:** diagnóstico com foto, medidas e pessoas afetadas; CAD do original e redesign; pelo menos uma peça cortada a laser e uma impressa em 3D; fotos antes/depois; publicação no MakerWorld e PDF organizado.

**Validação:** testar leitura do QR, legibilidade e estabilidade do suporte. Não instalar em espaço público sem autorização.

## Ordem de execução

1. **Fundação compartilhada:** escolher território e objeto; confirmar critérios com os professores; fixar contrato de dados e repositório.
2. **MVP e CV:** fechar envio, consulta e confirmação; testar modelo em imagens locais.
3. **Trilhas paralelas:** Airflow, notebook GenAI, BPMN/UiPath e CAD/fabricação.
4. **Integração:** Airflow e UiPath usam o `report_id` da mesma aplicação; publicar e observar o MVP.
5. **Evidências:** cada disciplina gera seus próprios PDFs/vídeos/prints, todos apontando para a mesma URL, repositório e ficha técnica.

## Situação atual

- [x] Base web do MVP: formulário, upload, protocolo e fila simples.
- [x] Estrutura inicial por disciplina e contrato comum definidos.
- [ ] Território, fotos locais e validação com cidadãos.
- [x] Integração opcional de CV no MVP e scripts para preparar, treinar e avaliar o detector de buracos.
- [x] Baixar e verificar o RDD2022; preparar amostra D40 de 5.000 imagens, treinar 30 épocas e registrar a validação RDD.
- [x] Fechar o piloto com as 20 fotos revisadas, confirmar 11 caixas e executar a avaliação local exploratória.
- [x] Equipe revisou e confirmou as 11 caixas das 20 fotos locais; avaliação local registrada como exploratória.
- [x] Preparar roteiro de vídeo de até cinco minutos para Visão Computacional.
- [x] Publicar o app em https://zela-gs26-buraco-demo.onrender.com; `/api/cv/status` respondeu HTTP 200 com detector disponível em 12/11/2026.
- [x] Confirmar no painel Render que o Compute Plan do serviço está como Free (12/11/2026).
- [ ] Gravar e publicar o vídeo de até cinco minutos com a participação de todos os integrantes.
- [ ] Notebook-base de GenAI e API.
- [x] Integrado o pacote Big Data do Joseh sem editar os arquivos originais; criado Compose local adaptado à estrutura do app.
- [x] Alinhado o app ao contrato comum: `id` inteiro/`report_id`, categorias, status, origem e campos opcionais; token de confirmação excluído da API.
- [x] Executado o pipeline Python com CSV demo (40 válidos, 0 rejeitados) e registrados banco/CSVs/JSON de saída.
- [x] Executar a DAG na UI Airflow via Docker Compose com CSV sintético; captura e logs registrados. A conexão com SQLite/API deve ser validada quando houver relatos reais do MVP.
- [x] Publicar o repositório e incluir evidências próprias da execução local e do Airflow.
- [x] Assessment inicial, business case, BPMN As-Is/To-Be e código do portal local de demonstração preparados; fluxo restrito a `source=demo` e aprovação humana.
- [x] Workflow UiPath `.xaml` preparado para criar uma ordem por `report_id` aprovado na demo.
- [x] Portal local respondendo HTTP 200; três relatos fictícios sem PII criados, e `report_id=1` aprovado. Evidência em `disciplinas/05-rpa/evidencias/`.
- [x] Demonstrar no vídeo o lote UiPath para os relatos 1–3 e a segunda execução para o relato 4; quatro OS demo aparecem registradas.
- [x] Guardar a captura histórica do portal com três ordens de demonstração.
- [x] Aprovar manualmente o `report_id=4`, gravar a segunda execução do UiPath e incluí-la em vídeo de até três minutos no ZIP final.
- [x] Incluir relatório PDF com integrantes/RMs, resultado da análise do processo e Business Case; deixar no ZIP somente os entregáveis e arquivos necessários do projeto.
- [ ] Validar portal municipal, campos, autenticação e autorização quando o município fornecer o acesso.
- [ ] Protótipo físico, cloud/DevSecOps, vídeos e entregas dos portais.
