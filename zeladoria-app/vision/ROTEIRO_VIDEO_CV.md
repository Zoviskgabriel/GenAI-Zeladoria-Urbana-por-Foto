# Roteiro do vídeo — detector de buracos

**Duração:** até 4min45s

**Formato:** gravação de tela com narração
**URL:** substituir `[URL PÚBLICA DO APP]` pela URL confirmada depois da publicação.

Use uma das 20 fotos revisadas do piloto, sem rostos, placas ou dados pessoais visíveis. Mostre a sugestão do detector como apoio à triagem, não como decisão automática. A avaliação local é pequena e teve desempenho baixo; apresente esse resultado com clareza.

| Tempo | O que mostrar | Narração sugerida |
|---|---|---|
| 0:00–0:20 | Título do projeto e URL pública do app | “Este é o Zela, um protótipo de zeladoria urbana por foto. Nesta demonstração, vou mostrar como o sistema sugere a identificação de buracos e como a decisão final continua com a pessoa.” |
| 0:20–0:55 | Abrir `[URL PÚBLICA DO APP]`; enquadrar o formulário e o aviso de demonstração pública | “O app recebe uma foto e uma localização aproximada. Este ambiente é uma demonstração pública: não devemos enviar dados pessoais. A imagem serve para apoiar a triagem, e não para substituir a revisão humana.” |
| 0:55–1:45 | Escolher uma foto revisada; mostrar as caixas, o rótulo “buraco” e a confiança; confirmar ou corrigir a categoria | “Ao selecionar a foto, o detector analisa a imagem e pode desenhar caixas sobre possíveis buracos. Aqui ele mostra a sugestão e o nível de confiança. Eu confiro a foto e confirmo ou corrijo a categoria.” |
| 1:45–2:15 | Preencher local aproximado e observação curta; enviar; mostrar o protocolo recebido | “Com a categoria revisada, envio o relato. O sistema registra um protocolo para acompanhamento. A sugestão do modelo fica marcada como revisada, mas ainda pode seguir para a triagem humana.” |
| 2:15–2:50 | Mostrar o relato recente na fila; evitar expor detalhes pessoais | “O relato aparece na lista recente deste protótipo. Em um serviço real, seriam necessários controles adicionais de acesso, armazenamento e retenção. Nesta demonstração, usamos somente dados não pessoais.” |
| 2:50–3:35 | Mostrar a transformação dos dados: XML Pascal VOC → caixas YOLO; citar treino e divisão | “Para treinar o detector, usamos o conjunto RDD2022 e filtramos a classe D40, correspondente a buracos neste trabalho. As caixas Pascal VOC foram convertidas para o formato YOLO. A amostra tem cinco mil imagens: 3.711 para treino e 1.289 para validação, divididas por sequência.” |
| 3:35–4:15 | Mostrar métricas RDD e, depois, métricas locais | “Na validação RDD, o modelo alcançou precisão 0,535, recall 0,448 e mAP a 0,5 de 0,471. Nas 20 fotos locais revisadas, a precisão foi 0,088, o recall 0,273 e o mAP a 0,5 foi 0,054. O resultado local é exploratório e mostra que o modelo ainda erra bastante neste território.” |
| 4:15–4:45 | Voltar à tela principal; mostrar aviso de decisão humana | “O protótipo demonstra um fluxo de apoio para buracos. Ele não classifica outros problemas urbanos nem decide sozinho se uma rua está segura. A pessoa pode corrigir a sugestão, e a triagem humana continua necessária.” |

## Conferência antes de gravar

- Atualize a URL no roteiro depois que o serviço estiver publicado.
- Verifique que a URL abre em uma janela sem sessão local e que `/api/cv/status` informa detector disponível.
- Use uma foto revisada e evite enquadrar nomes, contatos, rostos, placas ou endereços residenciais.
- Confirme que o vídeo dura menos de cinco minutos e que as métricas aparecem com vírgula decimal ou explicação oral.
- Inclua o vídeo e este roteiro no pacote final da disciplina.
