"""Extract annotated RDD2022 training images from the official nested archive."""

from __future__ import annotations

import argparse
from pathlib import Path, PurePosixPath
import shutil
from zipfile import BadZipFile, ZipFile


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--archive",
        type=Path,
        default=Path("data/raw/RDD2022_released_through_CRDDC2022.zip"),
    )
    parser.add_argument("--destination", type=Path, default=Path("data/raw/RDD2022"))
    args = parser.parse_args()

    archive_path = args.archive.resolve()
    destination = args.destination.resolve()
    if not archive_path.is_file():
        raise SystemExit(f"Arquivo RDD2022 não encontrado: {archive_path}")
    if destination.exists() and any(destination.iterdir()):
        raise SystemExit(f"A pasta de destino já contém arquivos: {destination}")

    destination.mkdir(parents=True, exist_ok=True)
    image_and_label_extensions = {".jpg", ".jpeg", ".png", ".xml"}
    package_count = 0
    extracted_count = 0

    try:
        with ZipFile(archive_path) as outer:
            packages = [name for name in outer.namelist() if name.lower().endswith(".zip")]
            if not packages:
                raise SystemExit("O ZIP oficial não contém os arquivos ZIP dos países esperados.")

            for package_name in packages:
                with outer.open(package_name) as package_stream, ZipFile(package_stream) as country_zip:
                    entries = [
                        info
                        for info in country_zip.infolist()
                        if "/train/" in f"/{info.filename.strip('/')}"
                        and PurePosixPath(info.filename).suffix.lower() in image_and_label_extensions
                    ]
                    if not entries:
                        continue

                    package_count += 1
                    print(f"Extraindo {package_name}: {len(entries)} imagens/XMLs", flush=True)
                    for info in entries:
                        member = PurePosixPath(info.filename)
                        if member.is_absolute() or ".." in member.parts:
                            continue
                        target = destination.joinpath(*member.parts)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with country_zip.open(info) as source, target.open("wb") as output:
                            shutil.copyfileobj(source, output, length=1024 * 1024)
                        extracted_count += 1
                        if extracted_count % 5000 == 0:
                            print(f"  {extracted_count} arquivos extraídos", flush=True)
    except BadZipFile as exc:
        raise SystemExit(f"Arquivo ZIP inválido: {exc}") from exc

    if not extracted_count:
        raise SystemExit("Nenhuma imagem/XML de treinamento foi extraída.")
    print(
        f"Concluído: {extracted_count} arquivos de {package_count} países em {destination}",
        flush=True,
    )


if __name__ == "__main__":
    main()
