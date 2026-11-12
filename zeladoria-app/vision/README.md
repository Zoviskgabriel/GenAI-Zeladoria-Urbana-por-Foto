# Applied Computer Vision — detector de buracos

Este componente detecta **uma classe**: buraco (`D40` no conjunto RDD2022). Ele não classifica lixo, calçadas, bueiros ou iluminação. A sugestão serve para triagem; a categoria escolhida pela pessoa e a revisão humana continuam valendo.

## Estado

- Integração opcional com o MVP e desenho das caixas na prévia: pronta.
- Conversão do RDD2022 Pascal VOC para YOLO, treino inicial e avaliação RDD: concluídos.
- 20 fotos locais revisadas e preparadas (10 positivas, 10 negativas), com 11 caixas conferidas e confirmadas pela equipe.
- Pesos em `models/best.pt`; avaliação RDD2022 em `evidence/cv/validation/metrics.json`.
- Avaliação local em `evidence/cv_local/validation/metrics.json`: precisão 0,088, recall 0,273, mAP@0.5 0,054 e mAP@0.5:0.95 0,017. As caixas foram revisadas; por usar apenas 20 fotos e apresentar desempenho baixo, o resultado deve ser descrito como avaliação exploratória do piloto.

O arquivo oficial do RDD2022 foi baixado e teve tamanho (13.264.172.619 bytes) e MD5 (`b62bd51d2ffcfaa76c60f234f0cc2bb3`) conferidos. Foi preparada uma amostra de 5.000 imagens anotadas de treino, filtrada para a classe `D40`: 3.711 imagens para treino e 1.289 para validação, em divisão própria por sequência. Após 30 épocas, a validação RDD registrou precisão 0,535, recall 0,448, mAP@0.5 0,471 e mAP@0.5:0.95 0,199. Esses números são uma referência inicial do conjunto RDD; não medem o desempenho no território piloto.

## Dados e origem

Use o conjunto RDD2022 disponibilizado pelos organizadores do CRDDC'2022. O treino oficial inclui imagens e anotações Pascal VOC; o teste oficial não tem rótulos públicos. Para evitar misturar quadros quase adjacentes entre treino e validação, o conversor agrupa nomes no padrão RDD por sequência antes de separar 80/20. O resultado é uma divisão didática própria, não o split oficial do desafio.

O código mantém imagens sem caixas D40 como exemplos negativos e descarta caixas de outras categorias. A transformação é:

1. ler XML Pascal VOC e dimensões da imagem;
2. selecionar somente `D40`;
3. limitar coordenadas às bordas da imagem e descartar caixas inválidas;
4. converter `xmin,ymin,xmax,ymax` em `class x_center y_center width height`, normalizado entre 0 e 1;
5. separar por sequência em `train` e `val`, com seed registrada;
6. gravar o inventário em `data/processed/rdd2022_buraco/manifest.json`.

Os organizadores descrevem RDD2022 como imagens de seis países, com caixas e quatro classes do desafio (D00, D10, D20, D40); o conjunto de teste é disponibilizado sem anotações. Fontes: [página oficial de dados CRDDC'2022](https://crddc2022.sekilab.global/data/) e [repositório oficial RoadDamageDetector](https://github.com/sekilab/RoadDamageDetector).

O arquivo oficial pode ser baixado pela [ficha RDD2022 no Figshare](https://doi.org/10.6084/m9.figshare.21431547.v1), sob licença CC BY 4.0. O ZIP contém ZIPs aninhados por país; `vision/extract_rdd2022.py` extrai apenas imagens e XMLs anotados das pastas `train/`, sem desempacotar imagens de teste sem rótulos.

## Preparar dados

Baixe e extraia uma parte do RDD2022 fora do Git. O conversor aceita a pasta extraída, procura XMLs e imagens por nome e copia o resultado para `data/processed/` sem editar a origem.

```powershell
.venv\Scripts\python.exe vision/extract_rdd2022.py
.venv\Scripts\python.exe vision/prepare_rdd2022.py --source "data\raw\RDD2022" --max-images 5000
```

`--max-images 5000` cria uma amostra menor para começar. Para converter todas as imagens anotadas, remova `--max-images` ou passe `--max-images 0`. A saída precisa de espaço adicional porque as imagens são copiadas.

## Treinar e avaliar

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-cv.txt
.venv\Scripts\python.exe -m pip install torch==2.11.0 torchvision==0.26.0 --index-url https://download.pytorch.org/whl/cu126
.venv\Scripts\python.exe vision/train.py --epochs 30 --batch 8 --device 0
.venv\Scripts\python.exe vision/evaluate.py --model "models\best.pt"
```

O ambiente deste workspace já está configurado para a RTX 2060, e o checkpoint base fica em `data/raw/yolo11n.pt`. A linha de instalação do PyTorch só é necessária ao montar o ambiente em outra máquina; o índice CUDA 12.6 segue a instalação oficial do [PyTorch para Windows](https://pytorch.org/get-started/previous-versions/).

O treino copia o melhor peso para `models/best.pt` e grava gráficos e manifesto da execução. A avaliação salva precisão, recall, mAP@0.5 e mAP@0.5:0.95 em `metrics.json`, junto dos gráficos. Reduza `--batch` se faltar memória; use `--device 0` para a primeira GPU NVIDIA ou `--device cpu` para CPU. No Windows, o script usa zero processos auxiliares do carregador de imagens.

Gere evidências visuais das caixas convertidas e de uma inferência:

```powershell
.venv\Scripts\python.exe vision/preview_dataset.py --split val --limit 12
.venv\Scripts\python.exe vision/predict_file.py --image "C:\fotos\buraco.jpg" --model "models\best.pt"
```

As imagens e os JSONs serão salvos em `evidence/generated/`; copie para a pasta de entrega apenas as evidências revisadas e autorizadas.

Para repetir com exatamente o mesmo ambiente, registrem a versão instalada de Ultralytics e PyTorch no README da entrega. O ponto de partida `yolo11n.pt` é o modelo nano oficial; ele é inicializado com pesos públicos e ajustado para detectar buracos. O guia oficial documenta o formato YOLO e o fluxo de ajuste fino: [YOLO11](https://docs.ultralytics.com/models/yolo11), [detecção e treino](https://docs.ultralytics.com/tasks/detect/) e [formato do conjunto](https://docs.ultralytics.com/datasets/detect/).

## Exportar ONNX para hospedagem gratuita

A versão PyTorch `models/best.pt` é mantida para treino e avaliação. Para o serviço Render Free, a inferência usa `models/best.onnx` e ONNX Runtime, sem carregar PyTorch no servidor. Exporte localmente com:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-export.txt
.venv\Scripts\python.exe vision\export_onnx.py
```

A API aceita os dois formatos. O Render usa `requirements-deploy.txt` com ONNX Runtime, NumPy e Pillow. O plano gratuito oferece 512 MB de RAM e dorme após 15 minutos sem tráfego; a mesma URL desperta o serviço na próxima visita, podendo levar cerca de um minuto. Relatos no disco local são temporários.

## Ligar os pesos ao MVP

Copie ou mantenha `best.pt` localmente e inicie o servidor com:

```powershell
$env:CV_MODEL_PATH = "C:\caminho\para\best.pt"
$env:CV_CONFIDENCE = "0.35"
.venv\Scripts\python.exe app.py
```

Depois do treino, os pesos são copiados automaticamente para `models/best.pt`; nesse caso, basta executar `.venv\Scripts\python.exe app.py` sem definir `CV_MODEL_PATH`.

O formulário chama `POST /api/cv/predict` quando a foto é escolhida. A resposta inclui classe, confiança, caixas `x1,y1,x2,y2` em pixels da imagem original e tamanho da imagem. Na criação do relato, o servidor executa a inferência novamente e salva a sugestão em `cv_label`, `cv_confidence` e `cv_model`. A escolha do cidadão fica em `category`; a marcação de revisão fica em `cv_reviewed`. `GET /api/cv/status` informa se os pesos estão disponíveis.

Se não houver pesos, se o arquivo não identificar a classe de buraco ou se a inferência falhar, a interface preserva o envio manual. Uma ausência de detecção não significa que a rua esteja sem danos.

## Evidências para a entrega

Guardar, depois de executar o fluxo:

- `manifest.json` do conjunto convertido;
- imagens com caixas de rótulos convertidos, geradas por `vision/preview_dataset.py`;
- `training_manifest.json`, curvas de treino e `metrics.json`;
- exemplos de caixas D40 convertidas e fotos locais anonimizadas, com rótulo humano;
- imagem de uma inferência com caixas, confiança e confirmação/correção humana;
- vídeo curto mostrando foto → sugestão → decisão humana → relato no painel;
- comparação separada entre validação RDD2022 e fotos locais. Não apresentar a métrica de um conjunto como resultado do outro.

As fotos do território piloto entram em `data/local_pilot/images/`; instruções e o CSV modelo estão em `data/local_pilot/README.md` e `data/local_pilot/annotations_template.csv`. Depois da revisão humana, `vision/prepare_local_pilot.py` converte caixas em pixels para o mesmo formato YOLO e cria uma validação local separada. Não use essas fotos na etapa de treino se pretende reportá-las como avaliação local.

Não usar rostos, placas ou outros dados pessoais nas evidências. O servidor básico foi pensado para demonstração local e ainda não tem autenticação do painel nem política de retenção para implantação pública.

## Licença do framework

Ultralytics declara o uso acadêmico sob AGPL-3.0 e exige licença Enterprise para certos usos fechados/comerciais. Como a entrega da equipe será pública, confirmem com o grupo que o código correspondente será publicado com os avisos e a licença aplicáveis. A página oficial descreve os termos: [Ultralytics License](https://www.ultralytics.com/license).
