"""Render a small visual audit of converted YOLO pothole labels."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path("data/processed/rdd2022_pothole"))
    parser.add_argument("--split", choices=("train", "val"), default="val")
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--output", type=Path, default=Path("evidence/generated/conversion_preview"))
    args = parser.parse_args()

    images_dir = args.data_root / "images" / args.split
    labels_dir = args.data_root / "labels" / args.split
    if not images_dir.is_dir():
        raise SystemExit(f"Pasta de imagens não encontrada: {images_dir}")
    files = sorted(path for path in images_dir.iterdir() if path.suffix.lower() in {".jpg", ".jpeg", ".png"})
    if not files:
        raise SystemExit(f"Nenhuma imagem no split {args.split}.")
    args.output.mkdir(parents=True, exist_ok=True)
    font = ImageFont.load_default()

    for index, path in enumerate(files[: max(1, args.limit)], 1):
        image = Image.open(path).convert("RGB")
        draw = ImageDraw.Draw(image)
        label_path = labels_dir / f"{path.stem}.txt"
        boxes = 0
        if label_path.is_file():
            for line in label_path.read_text(encoding="utf-8").splitlines():
                fields = line.split()
                if len(fields) != 5:
                    continue
                _, xc, yc, bw, bh = map(float, fields)
                x1 = (xc - bw / 2) * image.width
                y1 = (yc - bh / 2) * image.height
                x2 = (xc + bw / 2) * image.width
                y2 = (yc + bh / 2) * image.height
                draw.rectangle((x1, y1, x2, y2), outline="#ff2879", width=max(2, image.width // 500))
                draw.text((x1 + 3, max(0, y1 - 14)), "D40 pothole", fill="white", stroke_width=2, stroke_fill="#920d43", font=font)
                boxes += 1
        banner = f"{args.split.upper()} · {boxes} pothole box(es)"
        draw.rectangle((0, 0, image.width, 24), fill="#181a20")
        draw.text((8, 5), banner, fill="white", font=font)
        output_path = args.output / f"{args.split}_{index:03d}_{path.stem}.jpg"
        image.save(output_path, quality=90)
        print(output_path.resolve())


if __name__ == "__main__":
    main()
