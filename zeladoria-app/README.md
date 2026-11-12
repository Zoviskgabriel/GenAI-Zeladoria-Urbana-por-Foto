# Aplicação Zela

Aplicação demonstrativa para registrar ocorrências urbanas. Para iniciar localmente, use Python 3.10 ou superior:

```powershell
python app.py
```

Abra `http://127.0.0.1:8000`. A documentação específica da entrega de Big Data está na pasta [`entrega-bigdata/`](../entrega-bigdata/).

## Visão computacional

O detector de buracos foi treinado inicialmente com uma amostra anotada do RDD2022 e seus pesos estão em `models/best.pt`. A avaliação RDD e as instruções para as fotos do território piloto estão em [vision/README.md](vision/README.md). Inicie o app pelo ambiente local com `.venv\Scripts\python.exe app.py`; a sugestão de buraco aparece ao escolher uma foto e continua sujeita à decisão humana.

O piloto local está fechado com 20 fotos revisadas (10 com buraco, 10 sem buraco) e 11 caixas confirmadas pela equipe. A avaliação está em `evidence/cv_local/validation/`; com essa amostra pequena e o desempenho observado, apresente-a como exploratória. Veja o [guia e a avaliação](data/local_pilot/README.md). Fotos locais e rótulos reais ficam fora do Git por padrão.

A configuração gratuita está em [`../render.yaml`](../render.yaml) e usa ONNX Runtime em CPU para caber no plano Render Free (512 MB). O endereço previsto é `https://zela-gs26-buraco-demo.onrender.com`, ainda pendente de criação no Render. No plano gratuito, o serviço pode dormir após 15 minutos sem acesso e os relatos do SQLite podem ser apagados ao reiniciar. Nenhum plano pago é necessário para a demonstração.

## Robotic Process Automation

O assessment, business case, BPMNs, portal local de demonstração, seed fictício e workflow UiPath estão em [disciplinas/05-rpa/](disciplinas/05-rpa/). O portal oficial não foi acessado porque o workspace não informa município, URL ou autorização; a demo só processa `source=demo` e exige validação humana.
