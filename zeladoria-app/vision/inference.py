"""Optional one-class pothole detector used by the MVP API."""

from __future__ import annotations

from io import BytesIO
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = ROOT / "models" / "best.pt"
_MODEL: Any = None
_MODEL_KEY: tuple[str, int] | None = None


def configured_model_path() -> Path:
    return Path(os.getenv("CV_MODEL_PATH", str(DEFAULT_MODEL))).expanduser()


def confidence_threshold() -> float:
    try:
        value = float(os.getenv("CV_CONFIDENCE", "0.35"))
    except ValueError:
        value = 0.35
    return min(max(value, 0.01), 0.99)


def status() -> dict[str, Any]:
    path = configured_model_path()
    if not path.is_file():
        return {
            "available": False,
            "message": "Modelo de buracos ainda não instalado. A categoria manual continua disponível.",
        }
    try:
        import ultralytics  # noqa: F401
    except ImportError:
        return {
            "available": False,
            "message": "Instale as dependências de visão computacional para habilitar a sugestão.",
        }
    return {"available": True, "message": "Detector de buracos disponível."}


def _load_model(path: Path):
    global _MODEL, _MODEL_KEY
    key = (str(path.resolve()), path.stat().st_mtime_ns)
    if _MODEL is None or _MODEL_KEY != key:
        from ultralytics import YOLO

        _MODEL = YOLO(str(path))
        _MODEL_KEY = key
    return _MODEL


def _class_names(model: Any) -> dict[int, str]:
    names = model.names
    if isinstance(names, dict):
        return {int(index): str(name) for index, name in names.items()}
    return {index: str(name) for index, name in enumerate(names)}


def predict_image(image_bytes: bytes) -> dict[str, Any]:
    """Run the configured pothole model; never substitutes a generic model."""
    path = configured_model_path()
    if not path.is_file():
        return {"available": False, "message": status()["message"]}

    try:
        from PIL import Image

        image = Image.open(BytesIO(image_bytes)).convert("RGB")
    except Exception as exc:
        raise ValueError("Não foi possível ler a imagem enviada.") from exc

    model = _load_model(path)
    names = _class_names(model)
    target_ids = {
        index
        for index, name in names.items()
        if name.strip().casefold() in {"pothole", "buraco", "dano_na_pista", "road_damage"}
    }
    if not target_ids:
        return {
            "available": False,
            "message": "O arquivo configurado não identifica a classe pothole/buraco.",
        }

    result = model.predict(
        source=image,
        conf=confidence_threshold(),
        imgsz=640,
        verbose=False,
    )[0]
    detections: list[dict[str, Any]] = []
    if result.boxes is not None:
        xyxy = result.boxes.xyxy.cpu().tolist()
        scores = result.boxes.conf.cpu().tolist()
        class_ids = result.boxes.cls.cpu().tolist()
        for box, score, class_id in zip(xyxy, scores, class_ids):
            class_id = int(class_id)
            if class_id not in target_ids:
                continue
            detections.append(
                {
                    "label": names[class_id],
                    "confidence": round(float(score), 4),
                    "box": {"x1": round(float(box[0]), 1), "y1": round(float(box[1]), 1),
                            "x2": round(float(box[2]), 1), "y2": round(float(box[3]), 1)},
                }
            )
    detections.sort(key=lambda row: row["confidence"], reverse=True)
    best = detections[0] if detections else None
    return {
        "available": True,
        "model": path.name,
        "image_size": {"width": image.width, "height": image.height},
        "suggestion_category": "dano_na_pista" if best else None,
        "label": best["label"] if best else None,
        "confidence": best["confidence"] if best else None,
        "detection_count": len(detections),
        "detections": detections[:20],
        "message": (
            "Sugestão de buraco encontrada; confirme ou corrija a categoria."
            if best
            else "O detector não encontrou buraco acima do limiar. Isso não prova que a via esteja sem danos."
        ),
    }
