"""Evaluate trained weights and save a compact metrics record."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True, help="Caminho para best.pt")
    parser.add_argument("--data", type=Path, default=Path("data/processed/rdd2022_buraco/data.yaml"))
    parser.add_argument(
        "--project",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "evidence" / "cv",
    )
    args = parser.parse_args()

    if not args.model.is_file():
        raise SystemExit(f"Pesos não encontrados: {args.model}")
    if not args.data.is_file():
        raise SystemExit(f"Dataset YAML não encontrado: {args.data}")
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise SystemExit("Instale requirements-cv.txt antes de avaliar.") from exc

    model = YOLO(str(args.model.resolve()))
    project_path = args.project
    if not project_path.is_absolute():
        project_path = Path(__file__).resolve().parent.parent / project_path
    results = model.val(
        data=str(args.data.resolve()),
        plots=True,
        save_json=True,
        project=str(project_path.resolve()),
        name="validation",
        exist_ok=True,
    )
    metrics = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "weights": str(args.model.resolve()),
        "dataset_yaml": str(args.data.resolve()),
        "class_names": {str(k): v for k, v in model.names.items()} if isinstance(model.names, dict) else list(model.names),
        "precision": float(results.box.mp),
        "recall": float(results.box.mr),
        "map50": float(results.box.map50),
        "map50_95": float(results.box.map),
        "per_class_map50_95": [float(v) for v in results.box.maps],
        "plots_directory": str(Path(results.save_dir).resolve()),
    }
    output = Path(results.save_dir) / "metrics.json"
    output.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    print(f"Métricas salvas em: {output.resolve()}")


if __name__ == "__main__":
    main()
