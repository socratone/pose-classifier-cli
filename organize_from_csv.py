#!/usr/bin/env python3
"""CSV 결과 파일을 바탕으로 이미지를 포즈별 폴더로 복사하는 CLI."""

import argparse
import csv
import shutil
import sys
from pathlib import Path

from rich.console import Console

console = Console()


def parse_args():
    parser = argparse.ArgumentParser(
        description="results.csv를 바탕으로 이미지를 포즈별 서브폴더로 복사합니다."
    )
    parser.add_argument("--csv", required=True, metavar="FILE", help="분류 결과 CSV 파일 경로")
    parser.add_argument(
        "--source",
        metavar="DIR",
        help="원본 이미지 디렉토리 (기본값: CSV 파일과 같은 디렉토리)",
    )
    parser.add_argument("--output", required=True, metavar="DIR", help="정리된 이미지를 저장할 대상 디렉토리")
    return parser.parse_args()


def read_csv(csv_path: str) -> list[dict]:
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def organize(rows: list[dict], source_dir: Path, output_dir: Path):
    copied = 0
    errors = 0
    skipped = 0

    for row in rows:
        filename = row.get("file", "").strip()
        pose = row.get("pose", "").strip()

        if not filename or not pose or pose.upper() == "ERROR":
            skipped += 1
            continue

        src = source_dir / filename
        if not src.exists():
            console.print(f"[yellow]파일 없음: {filename}[/yellow]")
            skipped += 1
            continue

        dest_dir = output_dir / pose
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / filename

        if dest.exists():
            stem, suffix = dest.stem, dest.suffix
            n = 1
            while dest.exists():
                dest = dest_dir / f"{stem}_{n}{suffix}"
                n += 1

        try:
            shutil.copy2(src, dest)
            copied += 1
        except Exception as e:
            console.print(f"[red]복사 오류 {filename}: {e}[/red]")
            errors += 1

    console.print(f"\n폴더 정리 완료: [bold]{output_dir}[/bold]")
    console.print(
        f"  복사됨: {copied}장"
        + (f"  건너뜀: {skipped}장" if skipped else "")
        + (f"  오류: {errors}장" if errors else "")
    )

    for pose_dir in sorted(output_dir.iterdir()):
        if pose_dir.is_dir():
            count = sum(1 for f in pose_dir.iterdir() if f.is_file())
            console.print(f"  [cyan]{pose_dir.name}/[/cyan]  {count}장")


def main():
    args = parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        console.print(f"[red]오류: CSV 파일을 찾을 수 없습니다: {args.csv}[/red]")
        sys.exit(1)

    source_dir = Path(args.source) if args.source else csv_path.parent
    if not source_dir.is_dir():
        console.print(f"[red]오류: 소스 디렉토리가 존재하지 않습니다: {source_dir}[/red]")
        sys.exit(1)

    output_dir = Path(args.output)

    rows = read_csv(str(csv_path))
    if not rows:
        console.print("[red]오류: CSV 파일이 비어 있습니다.[/red]")
        sys.exit(1)

    console.print(f"\n[bold]📁 CSV 기반 이미지 정리[/bold]")
    console.print(f"  CSV:    {csv_path}")
    console.print(f"  소스:   {source_dir}")
    console.print(f"  대상:   {output_dir}")
    console.print(f"  항목:   {len(rows)}개\n")

    organize(rows, source_dir, output_dir)


if __name__ == "__main__":
    main()
