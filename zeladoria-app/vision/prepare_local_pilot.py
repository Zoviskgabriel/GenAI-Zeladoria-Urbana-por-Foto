"""Convert human-reviewed local photos and pixel boxes to a YOLO val set."""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import csv
import json
from pathlib import Path
import shutil

from PIL import Image


def parse_yes(value: str) -> bool:
    normalized = value.strip().casefold()
    if normalized in {"sim", "yes", "true", "1"}:
        return True
    if normalized in {"não", "nao", "no", "false", "0"}:
        return False
    raise ValueError(f"has_buraco deve ser sim/não; recebido: {value!r}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", type=Path, default=Path("data/local_pilot/images"))
    parser.add_argument("--annotations", type=Path, default=Path("data/local_pilot/annotations.csv"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/local_pilot"))
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    if not args.images.is_dir():
        raise SystemExit(f"Pasta de fotos não encontrada: {args.images}")
    if not args.annotations.is_file():
        raise SystemExit(f"Anotações não encontradas: {args.annotations}. Revise as fotos e crie o CSV a partir do template.")
    if args.output.exists() and any(args.output.iterdir()) and not args.overwrite:
        raise SystemExit(f"A saída já existe e não está vazia: {args.output} (use --overwrite para refazer)")
    if args.output.exists() and args.overwrite:
        shutil.rmtree(args.output)

    grouped: dict[str, dict] = defaultdict(lambda: {"has_buraco": None, "boxes": []})
    required = {"image", "has_buraco", "xmin_px", "ymin_px", "xmax_px", "ymax_px"}
    with args.annotations.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise SystemExit("O CSV precisa ter as colunas image, has_buraco, xmin_px, ymin_px, xmax_px e ymax_px.")
        for line_number, row in enumerate(reader, start=2):
            filename = (row.get("image") or "").strip()
            if not filename or Path(filename).name != filename:
                raise SystemExit(f"Linha {line_number}: use apenas o nome do arquivo, sem caminho.")
            image_path = args.images / filename
            if not image_path.is_file():
                raise SystemExit(f"Linha {line_number}: foto não encontrada: {image_path}")
            try:
                has_buraco = parse_yes(row.get("has_buraco") or "")
            except ValueError as exc:
                raise SystemExit(f"Linha {line_number}: {exc}") from exc

            record = grouped[filename]
            if record["has_buraco"] is not None and record["has_buraco"] != has_buraco:
                raise SystemExit(f"Linha {line_number}: {filename} não pode estar marcada com e sem buraco.")
            record["has_buraco"] = has_buraco
            coordinates = [row.get(key, "").strip() for key in ("xmin_px", "ymin_px", "xmax_px", "ymax_px")]
            if has_buraco:
                if any(value == "" for value in coordinates):
                    raise SystemExit(f"Linha {line_number}: informe a caixa em pixels para cada buraco.")
                try:
                    record["boxes"].append(tuple(float(value) for value in coordinates))
                except ValueError as exc:
                    raise SystemExit(f"Linha {line_number}: coordenadas devem ser números.") from exc
            elif any(coordinates):
                raise SystemExit(f"Linha {line_number}: deixe a caixa vazia quando has_buraco=nao.")

    if not grouped:
        raise SystemExit("O CSV não contém fotos rotuladas.")

    output = args.output.resolve()
    (output / "images" / "val").mkdir(parents=True, exist_ok=True)
    (output / "labels" / "val").mkdir(parents=True, exist_ok=True)
    positives = negatives = box_count = 0
    seen_stems: set[str] = set()
    for filename, record in sorted(grouped.items()):
        source = args.images / filename
        stem = source.stem.casefold()
        if stem in seen_stems:
            raise SystemExit(f"Nomes de arquivos com a mesma raiz não podem ser usados juntos: {filename}")
        seen_stems.add(stem)
        try:
            with Image.open(source) as image:
                width, height = image.size
                image.verify()
        except Exception as exc:
            raise SystemExit(f"Imagem inválida: {source}: {exc}") from exc
        if width <= 0 or height <= 0:
            raise SystemExit(f"Dimensões inválidas: {source}")

        label_lines = []
        for xmin, ymin, xmax, ymax in record["boxes"]:
            if not (0 <= xmin < xmax <= width and 0 <= ymin < ymax <= height):
                raise SystemExit(f"Caixa fora da imagem em {filename}; dimensões: {width}x{height}.")
            xc = ((xmin + xmax) / 2) / width
            yc = ((ymin + ymax) / 2) / height
            bw = (xmax - xmin) / width
            bh = (ymax - ymin) / height
            label_lines.append(f"0 {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}")
        if record["has_buraco"] and not label_lines:
            raise SystemExit(f"{filename} está marcada com buraco, mas não tem nenhuma caixa.")

        shutil.copy2(source, output / "images" / "val" / source.name)
        label_file = output / "labels" / "val" / f"{source.stem}.txt"
        label_file.write_text("\n".join(label_lines) + ("\n" if label_lines else ""), encoding="utf-8")
        positives += int(record["has_buraco"])
        negatives += int(not record["has_buraco"])
        box_count += len(label_lines)

    output_posix = output.as_posix().replace('"', '\\"')
    (output / "data.yaml").write_text(
        f'path: "{output_posix}"\ntrain: images/val\nval: images/val\nnames:\n  0: buraco\n',
        encoding="utf-8",
    )
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "rótulos de pasta fornecidos pelo usuário; caixas marcadas inicialmente pelo assistente e revisadas e confirmadas pela equipe, conforme informado pelo usuário",
        "image_count": len(grouped),
        "positive_images": positives,
        "negative_images": negatives,
        "buraco_boxes": box_count,
        "split": "validation only; these images must not be used for training",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"Conjunto local preparado: {output}")


if __name__ == "__main__":
    main()
