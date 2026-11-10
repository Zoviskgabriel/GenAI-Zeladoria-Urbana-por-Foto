# Applied Computer Vision — detector de buracos

Este componente usa **uma classe**: buraco (`D40`, nome padronizado como `pothole`). Ele não classifica lixo, calçadas, bueiros ou iluminação. A sugestão serve para triagem; a categoria escolhida pela pessoa e a revisão humana continuam valendo.

## Estado

- Integração opcional com o MVP e desenho das caixas na prévia: pronta.
- Conversão do RDD2022 Pascal VOC para YOLO, treino e avaliação: prontos para executar.
- Pesos treinados, métricas e avaliação em fotos brasileiras: ainda pendentes. Este workspace não contém o RDD2022 nem fotos locais, então não há resultado de modelo a apresentar ainda.

## Dados e origem

Use o conjunto RDD2022 disponibilizado pelos organizadores do CRDDC'2022. O treino oficial inclui imagens e anotações Pascal VOC; o teste oficial não tem rótulos públicos. Para evitar misturar quadros quase adjacentes entre treino e validação, o conversor agrupa nomes no padrão RDD por sequência antes de separar 80/20. O resultado é uma divisão didática própria, não o split oficial do desafio.

O código mantém imagens sem caixas D40 como exemplos negativos e descarta caixas de outras categorias. A transformação é:

1. ler XML Pascal VOC e dimensões da imagem;
2. selecionar somente `D40`;
3. limitar coordenadas às bordas da imagem e descartar caixas inválidas;
4. converter `xmin,ymin,xmax,ymax` em `class x_center y_center width height`, normalizado entre 0 e 1;
5. separar por sequência em `train` e `val`, com seed registrada;
6. gravar o inventário em `data/processed/rdd2022_pothole/manifest.json`.

Os organizadores descrevem RDD2022 como imagens de seis países, com caixas e quatro classes do desafio (D00, D10, D20, D40); o conjunto de teste é disponibilizado sem anotações. Fontes: [página oficial de dados CRDDC'2022](https://crddc2022.sekilab.global/data/) e [repositório oficial RoadDamageDetector](https://github.com/sekilab/RoadDamageDetector).

## Preparar dados

Baixe e extraia uma parte do RDD2022 fora do Git. O conversor aceita a pasta extraída, procura XMLs e imagens por nome e copia o resultado para `data/processed/` sem editar a origem.

```powershell
python vision/prepare_rdd2022.py --source "C:\dados\RDD2022" --max-images 5000
```

`--max-images 5000` cria uma amostra menor para começar. Para converter todas as imagens anotadas, remova `--max-images` ou passe `--max-images 0`. A saída precisa de espaço adicional porque as imagens são copiadas.

## Treinar e avaliar

```powershell
python -m pip install -r requirements-cv.txt
python vision/train.py --epochs 30 --batch 8
python vision/evaluate.py --model "runs\detect\rdd2022-pothole\weights\best.pt"
```

O treino grava pesos, gráficos de treino e um manifesto com versão do Python, PyTorch, Ultralytics, hiperparâmetros e caminho do conjunto. A avaliação salva precisão, recall, mAP@0.5 e mAP@0.5:0.95 em `metrics.json`, junto dos gráficos. Reduza `--batch` se faltar memória; use `--device 0` para a primeira GPU NVIDIA ou `--device cpu` para CPU.

Gere evidências visuais das caixas convertidas e de uma inferência:

```powershell
python vision/preview_dataset.py --split val --limit 12
python vision/predict_file.py --image "C:\fotos\buraco.jpg" --model "runs\detect\rdd2022-pothole\weights\best.pt"
```

As imagens e os JSONs serão salvos em `evidence/generated/`; copie para a pasta de entrega apenas as evidências revisadas e autorizadas.

Para repetir com exatamente o mesmo ambiente, registrem a versão instalada de Ultralytics e PyTorch no README da entrega. O ponto de partida `yolo11n.pt` é o modelo nano oficial; ele é inicializado com pesos públicos e ajustado para a única classe `pothole`. O guia oficial documenta o formato YOLO e o fluxo de ajuste fino: [YOLO11](https://docs.ultralytics.com/models/yolo11), [detecção e treino](https://docs.ultralytics.com/tasks/detect/) e [formato do conjunto](https://docs.ultralytics.com/datasets/detect/).

## Ligar os pesos ao MVP

Copie ou mantenha `best.pt` localmente e inicie o servidor com:

```powershell
$env:CV_MODEL_PATH = "C:\caminho\para\best.pt"
$env:CV_CONFIDENCE = "0.35"
python app.py
```

O formulário chama `POST /api/cv/predict` quando a foto é escolhida. A resposta inclui classe, confiança, caixas `x1,y1,x2,y2` em pixels da imagem original e tamanho da imagem. Na criação do relato, o servidor executa a inferência novamente e salva a sugestão em `cv_label`, `cv_confidence` e `cv_model`. A escolha do cidadão fica em `category`; a marcação de revisão fica em `cv_reviewed`. `GET /api/cv/status` informa se os pesos estão disponíveis.

Se não houver pesos, se o arquivo não identificar `pothole`/`buraco` ou se a inferência falhar, a interface preserva o envio manual. Uma ausência de detecção não significa que a rua esteja sem danos.

## Evidências para a entrega

Guardar, depois de executar o fluxo:

- `manifest.json` do conjunto convertido;
- imagens com caixas de rótulos convertidos, geradas por `vision/preview_dataset.py`;
- `training_manifest.json`, curvas de treino e `metrics.json`;
- exemplos de caixas D40 convertidas e fotos locais anonimizadas, com rótulo humano;
- imagem de uma inferência com caixas, confiança e confirmação/correção humana;
- vídeo curto mostrando foto → sugestão → decisão humana → relato no painel;
- comparação separada entre validação RDD2022 e fotos locais. Não apresentar a métrica de um conjunto como resultado do outro.

Não usar rostos, placas ou outros dados pessoais nas evidências. O servidor básico foi pensado para demonstração local e ainda não tem autenticação do painel nem política de retenção para implantação pública.

## Licença do framework

Ultralytics declara o uso acadêmico sob AGPL-3.0 e exige licença Enterprise para certos usos fechados/comerciais. Como a entrega da equipe será pública, confirmem com o grupo que o código correspondente será publicado com os avisos e a licença aplicáveis. A página oficial descreve os termos: [Ultralytics License](https://www.ultralytics.com/license).
