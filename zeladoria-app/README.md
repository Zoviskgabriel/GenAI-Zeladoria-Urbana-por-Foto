# Aplicação Zela

Aplicação demonstrativa para registrar ocorrências urbanas. Para iniciar localmente, use Python 3.10 ou superior:

```powershell
python app.py
```

Abra `http://127.0.0.1:8000`. A documentação específica da entrega de Big Data está na pasta [`entrega-bigdata/`](../entrega-bigdata/).

## Visão computacional

O detector de buracos foi treinado inicialmente com uma amostra anotada do RDD2022 e seus pesos estão em `models/best.pt`. A avaliação RDD e as instruções para as fotos do território piloto estão em [vision/README.md](vision/README.md). Inicie o app pelo ambiente local com `.venv\Scripts\python.exe app.py`; a sugestão de buraco aparece ao escolher uma foto e continua sujeita à decisão humana.

O piloto local está fechado com 20 fotos revisadas (10 com buraco, 10 sem buraco) e 11 caixas confirmadas pela equipe. A avaliação está em `evidence/cv_local/validation/`; com essa amostra pequena e o desempenho observado, apresente-a como exploratória. Veja o [guia e a avaliação](data/local_pilot/README.md). Fotos locais e rótulos reais ficam fora do Git por padrão.

A configuração em [`../render.yaml`](../render.yaml) solicita o plano Render Free e usa ONNX Runtime em CPU. A URL pública [zela-gs26-buraco-demo.onrender.com](https://zela-gs26-buraco-demo.onrender.com) está ativa; `GET /api/cv/status` respondeu HTTP 200 com o detector disponível em 12/11/2026. No plano gratuito, a instância dorme após 15 minutos sem acesso e desperta na próxima visita; a primeira abertura pode levar cerca de um minuto. Relatos do SQLite podem ser apagados ao reiniciar. O plano Compute Free foi confirmado pela equipe no painel Render em 12/11/2026.

