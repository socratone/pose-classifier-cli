import argparse
import base64
import csv
import json
import os
import shutil
import sys
from pathlib import Path

import anthropic
from rich.console import Console
from rich.progress import BarColumn, Progress, TaskProgressColumn, TextColumn, TimeRemainingColumn

MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}

console = Console()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Claude Vision API를 사용해 사진을 포즈별로 분류합니다."
    )
    parser.add_argument("--poses", help="쉼표 구분 포즈 목록 (예: 서있기,앉기,점프)")
    parser.add_argument("--input", default=".", help="이미지 폴더 또는 파일 경로 (기본값: 현재 디렉토리)")
    parser.add_argument("--output", default="results.csv", help="결과 파일 경로 (.csv 또는 .json, 기본값: results.csv)")
    parser.add_argument("--extensions", default="jpg,jpeg,png,webp,gif", help="처리할 확장자 (기본값: jpg,jpeg,png,webp,gif)")
    parser.add_argument("--confidence", action="store_true", help="신뢰도 점수 포함")
    parser.add_argument("--reason", action="store_true", help="분류 이유 포함")
    parser.add_argument("--api-key", help="Anthropic API 키 (기본값: ANTHROPIC_API_KEY 환경변수)")
    parser.add_argument("--organize", metavar="DIR", help="분류된 이미지를 포즈별 서브폴더로 복사할 디렉토리")
    return parser.parse_args()


def get_poses(args):
    if args.poses:
        poses = [p.strip() for p in args.poses.split(",") if p.strip()]
        if poses:
            return poses

    console.print("\n[bold]포즈를 입력하세요[/bold] (빈 줄로 완료):")
    poses = []
    i = 1
    while True:
        try:
            pose = input(f"  포즈 {i}: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not pose:
            break
        poses.append(pose)
        i += 1

    if not poses:
        console.print("[red]포즈를 최소 1개 입력해야 합니다.[/red]", file=sys.stderr)
        sys.exit(1)

    return poses


def collect_images(input_path: str, extensions: list) -> list:
    p = Path(input_path)
    if p.is_file():
        return [p] if p.suffix.lower() in extensions else []
    if not p.is_dir():
        console.print(f"[red]경로를 찾을 수 없습니다: {input_path}[/red]", file=sys.stderr)
        sys.exit(1)
    return sorted(f for f in p.iterdir() if f.is_file() and f.suffix.lower() in extensions)


def encode_image(path: Path):
    media_type = MEDIA_TYPES[path.suffix.lower()]
    with open(path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode("utf-8")
    return data, media_type


def classify_image(client, image_path: Path, poses: list, include_confidence: bool, include_reason: bool) -> dict:
    data, media_type = encode_image(image_path)

    if len(data) > 6_900_000:
        console.print(f"[yellow]경고: {image_path.name} 파일이 너무 큽니다 (5MB 초과). API 오류가 발생할 수 있습니다.[/yellow]")

    pose_list = "\n".join(f"- {p}" for p in poses)
    fields = ['"pose": "<exact pose name from list>"']
    if include_confidence:
        fields.append('"confidence": <float 0.0-1.0>')
    if include_reason:
        fields.append('"reason": "<brief explanation>"')
    json_template = "{\n  " + ",\n  ".join(fields) + "\n}"

    prompt = f"""Classify the pose shown in this image. Choose exactly one pose from the following list:

{pose_list}

Respond with only valid JSON in this exact format:
{json_template}

The "pose" value must be exactly one of the strings listed above."""

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=256,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": data,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    result = json.loads(raw)

    if result.get("pose") not in poses:
        result["pose"] = poses[0]

    return result


def write_csv(results: list, output_path: str, include_confidence: bool, include_reason: bool):
    fieldnames = ["file", "pose"]
    if include_confidence:
        fieldnames.append("confidence")
    if include_reason:
        fieldnames.append("reason")

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)


def write_json(results: list, poses: list, output_path: str, include_confidence: bool, include_reason: bool):
    keep_keys = ["file", "pose"]
    if include_confidence:
        keep_keys.append("confidence")
    if include_reason:
        keep_keys.append("reason")

    filtered = [{k: r.get(k) for k in keep_keys} for r in results]

    output = {
        "poses": poses,
        "total": len(results),
        "results": filtered,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)


def organize_files(results: list, images: list, organize_dir: str):
    base = Path(organize_dir)
    img_map = {p.name: p for p in images}

    copied = 0
    errors = 0
    for r in results:
        pose = r.get("pose")
        filename = r.get("file")
        if not pose or pose == "ERROR" or filename not in img_map:
            continue
        dest_dir = base / pose
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / filename
        # 같은 이름 파일이 이미 있으면 _1, _2 ... 붙이기
        if dest.exists():
            stem, suffix = dest.stem, dest.suffix
            n = 1
            while dest.exists():
                dest = dest_dir / f"{stem}_{n}{suffix}"
                n += 1
        try:
            shutil.copy2(img_map[filename], dest)
            copied += 1
        except Exception as e:
            console.print(f"[red]복사 오류 {filename}: {e}[/red]")
            errors += 1

    console.print(f"\n폴더 정리 완료: [bold]{organize_dir}[/bold]")
    console.print(f"  복사됨: {copied}장" + (f"  오류: {errors}장" if errors else ""))

    # 생성된 폴더 목록 출력
    for pose_dir in sorted(base.iterdir()):
        if pose_dir.is_dir():
            count = sum(1 for f in pose_dir.iterdir() if f.is_file())
            console.print(f"  [cyan]{pose_dir.name}/[/cyan]  {count}장")


def print_summary(results: list, poses: list):
    counts = {pose: 0 for pose in poses}
    error_count = 0
    for r in results:
        p = r.get("pose", "")
        if p in counts:
            counts[p] += 1
        elif p == "ERROR":
            error_count += 1

    total = len(results)
    max_bar = 20

    console.print("\n[bold]📊 분류 결과 요약[/bold]")
    console.print("─" * 50)

    for pose in poses:
        count = counts[pose]
        pct = count / total * 100 if total > 0 else 0
        filled = int(pct / 100 * max_bar)
        bar = "█" * filled + "░" * (max_bar - filled)
        console.print(f"  {pose:<20} {count:>4}장  {bar}  {pct:>5.1f}%")

    if error_count:
        console.print(f"  [red]{'오류':<20} {error_count:>4}장[/red]")

    console.print("─" * 50)
    console.print(f"  {'합계':<20} {total:>4}장")


def main():
    args = parse_args()
    poses = get_poses(args)

    api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        console.print("[red]오류: API 키가 없습니다. ANTHROPIC_API_KEY 환경변수를 설정하거나 --api-key를 사용하세요.[/red]", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    extensions = [f".{e.strip().lower()}" for e in args.extensions.split(",")]
    images = collect_images(args.input, extensions)

    if not images:
        console.print(f"[red]이미지를 찾을 수 없습니다: {args.input}[/red]", file=sys.stderr)
        sys.exit(1)

    console.print(f"\n[bold]🤖 포즈 분류기[/bold]")
    console.print(f"  포즈: {', '.join(poses)}")
    console.print(f"  이미지: {len(images)}장  ({args.input})")
    console.print(f"  출력: {args.output}")
    if args.organize:
        console.print(f"  폴더 정리: {args.organize}")
    console.print()

    results = []

    with Progress(
        TextColumn("  "),
        BarColumn(),
        TaskProgressColumn(),
        TextColumn("[cyan]{task.fields[filename]}"),
        TextColumn("[green]{task.fields[last_result]}"),
        TimeRemainingColumn(),
    ) as progress:
        task = progress.add_task(
            "Classifying", total=len(images), filename="", last_result=""
        )
        for img_path in images:
            progress.update(task, filename=img_path.name, last_result="")
            try:
                result = classify_image(client, img_path, poses, args.confidence, args.reason)
                result["file"] = img_path.name
                results.append(result)
                progress.update(task, advance=1, last_result=f"→ {result['pose']}")
            except Exception as e:
                results.append({"file": img_path.name, "pose": "ERROR", "error": str(e)})
                progress.update(task, advance=1, last_result="→ [red]오류[/red]")

    output = args.output
    if output.endswith(".json"):
        write_json(results, poses, output, args.confidence, args.reason)
    else:
        write_csv(results, output, args.confidence, args.reason)

    console.print(f"\n결과 저장됨: [bold]{output}[/bold]")
    print_summary(results, poses)

    if args.organize:
        organize_files(results, images, args.organize)


if __name__ == "__main__":
    main()
