# Fotos do território piloto

Foram copiadas 20 imagens das pastas `Downloads/buraco` e `Downloads/sem buraco`: 10 de cada grupo. As cópias estão em `images/`; os originais em Downloads foram preservados. As extensões das cópias foram normalizadas para corresponder ao formato real, sem recompressão: cinco `.jfif` para `.jpg` e três imagens PNG que estavam nomeadas como `.jpg` para `.png`. As imagens `.webp` também são aceitas pelo fluxo.

Comecem com cerca de 20–30 imagens variadas, incluindo vias com buracos e trechos sem buracos. Esse conjunto é uma conferência inicial, não uma avaliação estatística conclusiva.

O arquivo `annotations.csv` contém os rótulos de imagem (`sim` ou `nao`) indicados pelas pastas de origem e 11 caixas nas imagens positivas. A equipe revisou e confirmou as caixas. O piloto fica fechado com estas 20 fotos; não serão adicionadas outras. Evitem incluir rostos, placas e outros dados pessoais nas imagens.

A avaliação gerou precisão 0,088, recall 0,273, mAP@0.5 0,054 e mAP@0.5:0.95 0,017 em 20 imagens revisadas. Consulte os gráficos em `evidence/cv_local/validation/`. Como a amostra é pequena e o desempenho é baixo, apresente o resultado como exploratório e discuta a limitação.

As colunas do CSV são `image,has_buraco,xmin_px,ymin_px,xmax_px,ymax_px`. A origem `(0,0)` fica no canto superior esquerdo da foto. Se houver mais de um buraco na imagem, dupliquem a linha com uma caixa diferente. Para as imagens `nao`, deixem as coordenadas vazias. O template vazio está em `annotations_template.csv`; o CSV preenchido e as imagens locais ficam fora do Git por padrão.

Exemplo de formato:

```csv
image,has_buraco,xmin_px,ymin_px,xmax_px,ymax_px
foto_001.jpg,sim,115,203,301,362
foto_002.jpg,nao,,,,
```

As coordenadas são pixels da imagem original, começando no canto superior esquerdo. Se houver dois buracos em uma foto, adicione duas linhas `sim` com caixas diferentes.

Depois da revisão, prepare o conjunto local para validação:

```powershell
.venv\Scripts\python.exe vision/prepare_local_pilot.py
.venv\Scripts\python.exe vision/evaluate.py --model "models\best.pt" --data "data\processed\local_pilot\data.yaml" --project "evidence\cv_local"
```

As fotos locais devem ficar separadas do conjunto de treino. Assim, a métrica local mede como o modelo se sai no território piloto, em vez de repetir imagens que ele já viu durante o treino.
