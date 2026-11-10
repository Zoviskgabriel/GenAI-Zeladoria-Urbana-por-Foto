"""Save one annotated image and JSON record as computer-vision evidence."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from inference import predict_image


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("evidence/generated/prediction"))
    args = parser.parse_args()
    if not args.image.is_file():
        raise SystemExit(f"Imagem não encontrada: {args.image}")
    if not args.model.is_file():
        raise SystemExit(f"Pesos não encontrados: {args.model}")
    os.environ["CV_MODEL_PATH"] = str(args.model.resolve())

    image_bytes = args.image.read_bytes()
    prediction = predict_image(image_bytes)
    if not prediction.get("available"):
        raise SystemExit(prediction.get("message", "Modelo indisponível."))

    image = Image.open(args.image).convert("RGB")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    for item in prediction["detections"]:
        box = item["box"]
        coords = (box["x1"], box["y1"], box["x2"], box["y2"])
        draw.rectangle(coords, outline="#ff2879", width=max(2, image.width // 500))
        text = f"Buraco {item['confidence']:.0%}"
        draw.text((box["x1"] + 4, max(0, box["y1"] - 14)), text, fill="white", stroke_width=2, stroke_fill="#920d43", font=font)

    args.output.mkdir(parents=True, exist_ok=True)
    annotated = args.output / f"{args.image.stem}_prediction.jpg"
    record = args.output / f"{args.image.stem}_prediction.json"
    image.save(annotated, quality=92)
    record.write_text(json.dumps({"image": args.image.name, **prediction}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(annotated.resolve())
    print(record.resolve())


if __name__ == "__main__":
    main()
