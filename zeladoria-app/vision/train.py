"""Ajuste um detector Ultralytics para identificar buracos nas fotos."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import shutil


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data/processed/rdd2022_buraco/data.yaml"))
    parser.add_argument(
        "--model",
        default="data/raw/yolo11n.pt",
        help="Checkpoint base; default is the downloaded official nano model",
    )
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--device", default="", help="Use 0 for the first CUDA GPU or cpu")
    parser.add_argument(
        "--workers",
        type=int,
        default=0 if platform.system() == "Windows" else 8,
        help="Number of data-loader worker processes (defaults to 0 on Windows)",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--name", default="rdd2022-buraco")
    args = parser.parse_args()

    data_path = args.data.resolve()
    if not data_path.is_file():
        raise SystemExit(f"Dataset YAML não encontrado: {data_path}. Rode prepare_rdd2022.py primeiro.")
    try:
        import torch
        import ultralytics
        from ultralytics import YOLO
    except ImportError as exc:
        raise SystemExit("Instale requirements-cv.txt antes de treinar: python -m pip install -r requirements-cv.txt") from exc

    model = YOLO(args.model)
    options = {
        "data": str(data_path),
        "epochs": args.epochs,
        "imgsz": args.imgsz,
        "batch": args.batch,
        "workers": args.workers,
        "seed": args.seed,
        "project": str(Path(__file__).resolve().parent / "runs" / "detect"),
        "name": args.name,
        "exist_ok": True,
        "patience": 8,
        "plots": True,
        "save_json": True,
        "verbose": True,
    }
    if args.device:
        options["device"] = args.device
    result = model.train(**options)
    run_dir = Path(result.save_dir)
    best = run_dir / "weights" / "best.pt"
    if not best.is_file():
        raise SystemExit(f"O treino terminou sem gerar os pesos esperados: {best}")
    deploy_model = Path("models/best.pt").resolve()
    deploy_model.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(best, deploy_model)
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dataset_yaml": str(data_path),
        "base_model": args.model,
        "best_weights": str(best.resolve()),
        "app_model": str(deploy_model),
        "epochs_requested": args.epochs,
        "image_size": args.imgsz,
        "batch": args.batch,
        "workers": args.workers,
        "seed": args.seed,
        "device": args.device or "auto",
        "python": platform.python_version(),
        "torch": torch.__version__,
        "ultralytics": ultralytics.__version__,
        "cuda_available": torch.cuda.is_available(),
        "run_directory": str(run_dir.resolve()),
    }
    (run_dir / "training_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Pesos finais: {best.resolve()}")
    print(f"Modelo pronto para o app: {deploy_model}")
    print(f"Manifesto da execução: {(run_dir / 'training_manifest.json').resolve()}")


if __name__ == "__main__":
    main()
