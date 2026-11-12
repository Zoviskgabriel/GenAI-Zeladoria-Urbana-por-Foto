"""Exporta os pesos treinados para ONNX para inferência leve em CPU."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", type=Path, default=Path("models/best.pt"))
    parser.add_argument("--output", type=Path, default=Path("models/best.onnx"))
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--opset", type=int, default=17)
    args = parser.parse_args()
    source = args.weights.resolve()
    target = args.output.resolve()
    if not source.is_file():
        raise SystemExit(f"Pesos não encontrados: {source}")
    from ultralytics import YOLO

    exported = Path(YOLO(str(source)).export(
        format="onnx", imgsz=args.imgsz, opset=args.opset,
        simplify=False, dynamic=False, half=False,
    ))
    if exported.resolve() != target:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(exported, target)
    print(f"Modelo ONNX: {target}")


if __name__ == "__main__":
    main()
