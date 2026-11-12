"""Detector opcional de buracos para o MVP (PyTorch ou ONNX Runtime)."""

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


def _is_onnx(path: Path) -> bool:
    return path.suffix.casefold() == ".onnx"


def status() -> dict[str, Any]:
    path = configured_model_path()
    if not path.is_file():
        return {
            "available": False,
            "message": "Modelo de buracos ainda não instalado. A categoria manual continua disponível.",
        }
    try:
        if _is_onnx(path):
            import onnxruntime  # noqa: F401
        else:
            import ultralytics  # noqa: F401
    except ImportError:
        return {
            "available": False,
            "message": "Instale as dependências necessárias para habilitar a sugestão.",
        }
    return {"available": True, "message": "Detector de buracos disponível."}


def _load_model(path: Path):
    global _MODEL, _MODEL_KEY
    key = (str(path.resolve()), path.stat().st_mtime_ns)
    if _MODEL is None or _MODEL_KEY != key:
        if _is_onnx(path):
            import onnxruntime as ort

            options = ort.SessionOptions()
            options.intra_op_num_threads = 1
            options.inter_op_num_threads = 1
            options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
            options.enable_mem_pattern = False
            _MODEL = ort.InferenceSession(
                str(path), sess_options=options, providers=["CPUExecutionProvider"]
            )
        else:
            from ultralytics import YOLO

            _MODEL = YOLO(str(path))
        _MODEL_KEY = key
    return _MODEL


def _nms(boxes, scores, iou_threshold: float = 0.45, limit: int = 100) -> list[int]:
    import numpy as np

    order = np.argsort(scores)[::-1]
    selected: list[int] = []
    while order.size and len(selected) < limit:
        current = int(order[0])
        selected.append(current)
        remaining = order[1:]
        if not remaining.size:
            break
        x1 = np.maximum(boxes[current, 0], boxes[remaining, 0])
        y1 = np.maximum(boxes[current, 1], boxes[remaining, 1])
        x2 = np.minimum(boxes[current, 2], boxes[remaining, 2])
        y2 = np.minimum(boxes[current, 3], boxes[remaining, 3])
        intersection = np.maximum(0, x2 - x1) * np.maximum(0, y2 - y1)
        area_current = max(0.0, boxes[current, 2] - boxes[current, 0]) * max(
            0.0, boxes[current, 3] - boxes[current, 1]
        )
        area_remaining = np.maximum(0, boxes[remaining, 2] - boxes[remaining, 0]) * np.maximum(
            0, boxes[remaining, 3] - boxes[remaining, 1]
        )
        union = area_current + area_remaining - intersection
        iou = intersection / np.maximum(union, 1e-9)
        order = remaining[iou <= iou_threshold]
    return selected


def _predict_onnx(path: Path, image) -> dict[str, Any]:
    import numpy as np
    from PIL import Image

    session = _load_model(path)
    input_meta = session.get_inputs()[0]
    input_name = input_meta.name
    input_shape = input_meta.shape
    size = int(input_shape[-1]) if isinstance(input_shape[-1], int) else 640
    original_width, original_height = image.size
    scale = min(size / original_width, size / original_height)
    resized_width = max(1, int(round(original_width * scale)))
    resized_height = max(1, int(round(original_height * scale)))
    resized = image.resize((resized_width, resized_height), Image.Resampling.BILINEAR)
    pad_x = (size - resized_width) / 2
    pad_y = (size - resized_height) / 2
    left, top = int(round(pad_x - 0.1)), int(round(pad_y - 0.1))
    canvas = Image.new("RGB", (size, size), (114, 114, 114))
    canvas.paste(resized, (left, top))
    tensor = np.asarray(canvas, dtype=np.float32).transpose(2, 0, 1)[None, ...] / 255.0
    output = session.run(None, {input_name: tensor})[0]
    predictions = np.asarray(output).squeeze()
    if predictions.ndim != 2:
        raise ValueError("A saída do detector ONNX tem formato inesperado.")
    if predictions.shape[0] <= 64 and predictions.shape[0] < predictions.shape[1]:
        predictions = predictions.T
    if predictions.shape[1] < 5:
        raise ValueError("O modelo ONNX não contém as coordenadas e a confiança esperadas.")

    class_scores = predictions[:, 4:]
    class_ids = class_scores.argmax(axis=1)
    scores = class_scores.max(axis=1)
    mask = (class_ids == 0) & (scores >= confidence_threshold())
    rows = predictions[mask]
    scores = scores[mask]
    if not len(rows):
        detections: list[dict[str, Any]] = []
    else:
        boxes = np.empty((len(rows), 4), dtype=np.float32)
        boxes[:, 0] = rows[:, 0] - rows[:, 2] / 2
        boxes[:, 1] = rows[:, 1] - rows[:, 3] / 2
        boxes[:, 2] = rows[:, 0] + rows[:, 2] / 2
        boxes[:, 3] = rows[:, 1] + rows[:, 3] / 2
        valid = (boxes[:, 2] > boxes[:, 0]) & (boxes[:, 3] > boxes[:, 1])
        boxes, scores = boxes[valid], scores[valid]
        kept = _nms(boxes, scores)
        detections = []
        for index in kept:
            box = boxes[index]
            x1 = min(max((float(box[0]) - left) / scale, 0.0), float(original_width))
            y1 = min(max((float(box[1]) - top) / scale, 0.0), float(original_height))
            x2 = min(max((float(box[2]) - left) / scale, 0.0), float(original_width))
            y2 = min(max((float(box[3]) - top) / scale, 0.0), float(original_height))
            if x2 <= x1 or y2 <= y1:
                continue
            detections.append({
                "label": "buraco",
                "confidence": round(float(scores[index]), 4),
                "box": {"x1": round(x1, 1), "y1": round(y1, 1),
                        "x2": round(x2, 1), "y2": round(y2, 1)},
            })
        detections.sort(key=lambda row: row["confidence"], reverse=True)

    best = detections[0] if detections else None
    return {
        "available": True,
        "model": path.name,
        "image_size": {"width": original_width, "height": original_height},
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


def predict_image(image_bytes: bytes) -> dict[str, Any]:
    """Executa o modelo configurado para detectar buracos."""
    path = configured_model_path()
    if not path.is_file():
        return {"available": False, "message": status()["message"]}

    try:
        from PIL import Image

        image = Image.open(BytesIO(image_bytes)).convert("RGB")
    except Exception as exc:
        raise ValueError("Não foi possível ler a imagem enviada.") from exc

    if _is_onnx(path):
        try:
            return _predict_onnx(path, image)
        except ImportError as exc:
            raise RuntimeError("Instale onnxruntime e numpy para usar o modelo ONNX.") from exc

    model = _load_model(path)
    names = model.names
    if isinstance(names, dict):
        names = {int(index): str(name) for index, name in names.items()}
    else:
        names = {index: str(name) for index, name in enumerate(names)}
    target_ids = {
        index for index, name in names.items()
        if name.strip().casefold() in {"buraco", "dano_na_pista", "road_damage"}
    }
    if not target_ids:
        return {"available": False, "message": "O arquivo configurado não identifica a classe de buraco."}

    result = model.predict(source=image, conf=confidence_threshold(), imgsz=640, verbose=False)[0]
    detections: list[dict[str, Any]] = []
    if result.boxes is not None:
        xyxy = result.boxes.xyxy.cpu().tolist()
        scores = result.boxes.conf.cpu().tolist()
        class_ids = result.boxes.cls.cpu().tolist()
        for box, score, class_id in zip(xyxy, scores, class_ids):
            if int(class_id) not in target_ids:
                continue
            detections.append({
                "label": "buraco",
                "confidence": round(float(score), 4),
                "box": {"x1": round(float(box[0]), 1), "y1": round(float(box[1]), 1),
                        "x2": round(float(box[2]), 1), "y2": round(float(box[3]), 1)},
            })
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
