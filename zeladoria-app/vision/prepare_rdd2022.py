"""Converte anotações Pascal VOC do RDD2022 para um conjunto YOLO de buracos.

The script keeps all labeled images (including images without D40 annotations)
and retains only D40 (buraco) boxes. It copies source images and never edits the
downloaded dataset.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
import random
import re
import shutil
from pathlib import Path
import xml.etree.ElementTree as ET

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png")


def find_images(root: Path) -> dict[str, list[Path]]:
    images: dict[str, list[Path]] = {}
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
            images.setdefault(path.stem.casefold(), []).append(path)
    return images


def match_image(annotation: Path, root: Path, images: dict[str, list[Path]]) -> Path | None:
    try:
        tree = ET.parse(annotation)
    except ET.ParseError:
        return None
    named = tree.getroot().findtext("filename")
    stem = Path(named).stem if named else annotation.stem
    candidates = images.get(stem.casefold(), [])
    if not candidates:
        candidates = images.get(annotation.stem.casefold(), [])
    if len(candidates) <= 1:
        return candidates[0] if candidates else None

    relative_annotation = annotation.relative_to(root)
    normalized_parts = [part.casefold() for part in relative_annotation.parts]
    parent_parts = [part for part in normalized_parts[:-1] if part not in {"annotations", "annotation"}]
    for candidate in candidates:
        relative_image = candidate.relative_to(root)
        image_parts = [part.casefold() for part in relative_image.parts]
        image_parent = [part for part in image_parts[:-1] if part not in {"jpegimages", "images"}]
        if parent_parts[-1:] == image_parent[-1:]:
            return candidate
    raise ValueError(f"Nome de imagem ambíguo para {annotation}: {candidates}")


def sequence_group(stem: str) -> str:
    # RDD-style names often end in a six-digit frame number; keep frames from
    # the same three-digit sequence together when creating the validation split.
    match = re.match(r"^(.*?[_-]\d{3})\d{3}$", stem)
    return match.group(1).casefold() if match else stem.casefold()


def annotation_record(xml_path: Path) -> tuple[list[tuple[float, float, float, float]], int, int]:
    root = ET.parse(xml_path).getroot()
    size = root.find("size")
    if size is None:
        raise ValueError(f"A anotação não tem dimensões: {xml_path}")
    width, height = int(size.findtext("width", "0")), int(size.findtext("height", "0"))
    if width <= 0 or height <= 0:
        raise ValueError(f"Dimensões inválidas na anotação: {xml_path}")

    boxes = []
    for obj in root.findall("object"):
        name = (obj.findtext("name") or "").strip().upper()
        if name != "D40":
            continue
        bounds = obj.find("bndbox")
        if bounds is None:
            continue
        xmin = max(0.0, min(float(bounds.findtext("xmin", "0")), width))
        ymin = max(0.0, min(float(bounds.findtext("ymin", "0")), height))
        xmax = max(0.0, min(float(bounds.findtext("xmax", "0")), width))
        ymax = max(0.0, min(float(bounds.findtext("ymax", "0")), height))
        if xmax <= xmin or ymax <= ymin:
            continue
        x_center = ((xmin + xmax) / 2) / width
        y_center = ((ymin + ymax) / 2) / height
        box_width = (xmax - xmin) / width
        box_height = (ymax - ymin) / height
        boxes.append((x_center, y_center, box_width, box_height))
    return boxes, width, height


def split_records(records: list[dict], fraction: float, seed: int) -> tuple[list[dict], list[dict]]:
    groups = sorted({row["group"] for row in records})
    random.Random(seed).shuffle(groups)
    if len(groups) < 2:
        # Tiny subsets cannot support a group-level holdout; make that limitation
        # visible in the generated manifest and split by image instead.
        groups = []
        rows = records[:]
        random.Random(seed).shuffle(rows)
        cut = max(1, min(len(rows) - 1, round(len(rows) * fraction)))
        return rows[cut:], rows[:cut]
    val_group_count = max(1, min(len(groups) - 1, round(len(groups) * fraction)))
    val_groups = set(groups[:val_group_count])
    train = [row for row in records if row["group"] not in val_groups]
    val = [row for row in records if row["group"] in val_groups]
    return train, val


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path, help="Pasta extraída do RDD2022")
    parser.add_argument("--output", type=Path, default=Path("data/processed/rdd2022_buraco"))
    parser.add_argument("--val-fraction", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-images", type=int, default=0, help="Limite opcional; 0 usa todas as imagens anotadas")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    source = args.source.resolve()
    output = args.output.resolve()
    if not source.is_dir():
        raise SystemExit(f"Pasta de dados não encontrada: {source}")
    if not 0.05 <= args.val_fraction <= 0.5:
        raise SystemExit("--val-fraction deve ficar entre 0.05 e 0.5")
    if output.exists() and any(output.iterdir()) and not args.overwrite:
        raise SystemExit(f"A saída já existe e não está vazia: {output} (use --overwrite para refazer)")
    if output.exists() and args.overwrite:
        shutil.rmtree(output)

    image_index = find_images(source)
    records = []
    missing = []
    for xml_path in sorted(source.rglob("*.xml")):
        image_path = match_image(xml_path, source, image_index)
        if image_path is None:
            missing.append(str(xml_path.relative_to(source)))
            continue
        try:
            boxes, width, height = annotation_record(xml_path)
        except (ET.ParseError, ValueError) as exc:
            print(f"Anotação ignorada: {xml_path}: {exc}")
            continue
        records.append({
            "xml": xml_path,
            "image": image_path,
            "boxes": boxes,
            "width": width,
            "height": height,
            "group": sequence_group(image_path.stem),
        })
    if not records:
        raise SystemExit("Nenhum par imagem/XML foi encontrado. Confira a estrutura extraída do RDD2022.")

    if args.max_images > 0 and len(records) > args.max_images:
        positives = [row for row in records if row["boxes"]]
        negatives = [row for row in records if not row["boxes"]]
        rng = random.Random(args.seed)
        rng.shuffle(positives)
        rng.shuffle(negatives)
        positive_limit = min(len(positives), max(1, round(args.max_images * 0.8)))
        chosen = positives[:positive_limit] + negatives[:max(0, args.max_images - positive_limit)]
        if len(chosen) < args.max_images:
            chosen += positives[positive_limit:positive_limit + args.max_images - len(chosen)]
        records = sorted(chosen, key=lambda row: row["image"].as_posix().casefold())

    train_rows, val_rows = split_records(records, args.val_fraction, args.seed)
    output.mkdir(parents=True, exist_ok=True)
    instance_counts = {"train": 0, "val": 0}
    positive_counts = {"train": 0, "val": 0}
    for split, rows in (("train", train_rows), ("val", val_rows)):
        (output / "images" / split).mkdir(parents=True, exist_ok=True)
        (output / "labels" / split).mkdir(parents=True, exist_ok=True)
        for row in rows:
            target_name = f"{row['image'].stem}{row['image'].suffix.lower()}"
            shutil.copy2(row["image"], output / "images" / split / target_name)
            label_path = output / "labels" / split / f"{row['image'].stem}.txt"
            label_lines = ["0 " + " ".join(f"{part:.6f}" for part in box) for box in row["boxes"]]
            label_path.write_text("\n".join(label_lines) + ("\n" if label_lines else ""), encoding="utf-8")
            instance_counts[split] += len(row["boxes"])
            positive_counts[split] += bool(row["boxes"])

    yaml_root = output.as_posix().replace('"', '\\"')
    (output / "data.yaml").write_text(
        f'path: "{yaml_root}"\ntrain: images/train\nval: images/val\nnames:\n  0: buraco\n',
        encoding="utf-8",
    )
    manifest = {
        "source": "RDD2022 official Pascal VOC training annotations",
        "source_directory": str(source),
        "target_class": "D40 / buraco",
        "source_annotations": "Pascal VOC XML; all non-D40 boxes discarded",
        "training_format": "YOLO normalized xywh (class x_center y_center width height)",
        "split_strategy": "deterministic 80/20 group split by RDD-style sequence prefix; image-level fallback if fewer than two groups exist",
        "seed": args.seed,
        "requested_validation_fraction": args.val_fraction,
        "image_count": {"train": len(train_rows), "val": len(val_rows)},
        "positive_image_count": positive_counts,
        "buraco_instance_count": instance_counts,
        "unpaired_annotation_count": len(missing),
        "unpaired_annotations_sample": missing[:20],
        "max_images": args.max_images,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in ("image_count", "positive_image_count", "buraco_instance_count", "unpaired_annotation_count")}, indent=2))
    print(f"Dataset YAML: {output / 'data.yaml'}")


if __name__ == "__main__":
    main()
