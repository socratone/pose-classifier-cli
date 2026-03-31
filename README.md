# 📸 포즈 분류기 (Pose Classifier CLI)

Claude Vision API를 사용해 사진을 사용자 정의 포즈별로 자동 분류하는 CLI 프로그램입니다.

## 설치

### 사전 요구사항

- [Docker](https://docs.docker.com/get-docker/) 설치
- Anthropic API 키

### 폴더 구조

```
pose-classifier-cli/
├── data/                  # 이미지 입력 및 결과 출력 폴더 (컨테이너의 /data로 마운트)
│   ├── photo1.jpg
│   ├── photo2.jpg
│   └── results.csv        # 실행 후 생성됨
├── pose_classifier.py     # 분류 CLI
├── organize_from_csv.py   # CSV 기반 폴더 정리 CLI
├── Dockerfile
├── docker-compose.yml
└── .env
```

`data/` 폴더가 없으면 먼저 생성하세요:

```bash
mkdir data
```

### 이미지 빌드

```bash
docker compose build
```

## 빠른 시작

```bash
# 1. API 키 설정 (.env 파일 또는 export)

# 2. 이미지를 data/ 폴더에 넣고 실행
docker compose run --rm classifier \
  --poses "서있기,앉기,점프,눕기" \
  --input /data \
  --output /data/results.csv
```

> **참고**: 프로젝트의 `data/` 폴더가 컨테이너 내부의 `/data`로 마운트됩니다.  
> 입력 이미지는 `data/` 폴더 안에, 결과 파일도 `--output /data/...` 형식으로 지정하세요.

## 전체 옵션

| 옵션           | 설명                                     | 기본값                |
| -------------- | ---------------------------------------- | --------------------- |
| `--poses`      | 쉼표 구분 포즈 목록                      | 대화형 입력           |
| `--input`      | 이미지 폴더/파일                         | 현재 디렉토리         |
| `--output`     | 결과 파일 (.csv / .json)                 | `results.csv`         |
| `--extensions` | 처리할 확장자                            | jpg,jpeg,png,webp,gif |
| `--confidence` | 신뢰도 점수 포함                         | off                   |
| `--reason`     | 분류 이유 포함                           | off                   |
| `--organize`   | 포즈별 서브폴더로 이미지 복사할 디렉토리 | off                   |
| `--batch-size` | 포즈 자동 발견 시 배치당 이미지 수       | `5`                   |
| `--api-key`    | API 키 직접 지정                         | 환경변수 사용         |

## 사용 예시

### 포즈 자동 발견 (--poses 생략)

```bash
docker compose run --rm classifier \
  --input /data \
  --output /data/results.csv
```

`--poses`를 지정하지 않으면 이미지를 배치로 분석해 포즈를 자동으로 발견합니다:

```
포즈 자동 발견 중...
  [████████████████████] 4/4  배치 4/4
  포즈 목록 통합 중...
  발견된 포즈: 서있기, 앉기, 점프, 눕기
```

### 기본 사용

```bash
docker compose run --rm classifier \
  --poses "서있기,앉기,점프,눕기" \
  --input /data \
  --output /data/results.csv
```

### 신뢰도 + 이유 포함, JSON 출력

```bash
docker compose run --rm classifier \
  --poses "서있기,앉기,점프,눕기" \
  --input /data \
  --output /data/results.json \
  --confidence \
  --reason
```

### 포즈별 폴더 자동 정리

```bash
docker compose run --rm classifier \
  --poses "서있기,앉기,점프,눕기" \
  --input /data \
  --output /data/results.csv \
  --organize /data/organized
```

결과 폴더 구조:

```
organized/
├── 서있기/
│   ├── photo1.jpg
│   └── photo5.jpg
├── 앉기/
│   └── photo2.jpg
├── 점프/
│   └── photo3.jpg
└── 눕기/
    └── photo4.jpg
```

> 원본 파일은 그대로 유지되며, 분류된 파일이 복사됩니다.

### 단일 파일

```bash
docker compose run --rm classifier \
  --poses "서있기,앉기" \
  --input /data/photo.jpg \
  --output /data/results.csv
```

## 출력 형식

### CSV (기본)

```
file,pose,confidence,reason
photo1.jpg,서있기,0.95,두 발로 직립해 있음
photo2.jpg,앉기,0.88,의자에 앉은 자세
```

### JSON (`--output /data/results.json`)

```json
{
  "poses": ["서있기", "앉기", "점프"],
  "total": 3,
  "results": [{ "file": "photo1.jpg", "pose": "서있기", "confidence": 0.95 }]
}
```

## 터미널 출력 예시

```
🤖 포즈 분류기
  포즈: 서있기, 앉기, 점프, 눕기
  이미지: 12장  (/data/photos)
  출력: /data/results.csv

  [████████████░░░░░░░░░░░░░░░░░░] 5/12  photo5.jpg → 서있기

📊 분류 결과 요약
──────────────────────────────────────────────────
  서있기               4장  ████████░░░░░░░░░░░░   33.3%
  앉기                 3장  ██████░░░░░░░░░░░░░░   25.0%
  점프                 3장  ██████░░░░░░░░░░░░░░   25.0%
  눕기                 2장  ████░░░░░░░░░░░░░░░░   16.7%
──────────────────────────────────────────────────
  합계                12장
```

---

## organize_from_csv.py — CSV 기반 폴더 정리

이미 생성된 `results.csv`를 바탕으로 이미지를 포즈별 서브폴더로 복사합니다.  
분류를 다시 실행하지 않아도 됩니다.

### 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--csv` | 분류 결과 CSV 파일 경로 | 필수 |
| `--source` | 원본 이미지 디렉토리 | CSV 파일과 같은 디렉토리 |
| `--output` | 정리된 이미지를 저장할 대상 디렉토리 | 필수 |

### 사용 예시

```bash
# 로컬에서 직접 실행
python organize_from_csv.py --csv data/results.csv --output data/organized

# 소스 디렉토리를 별도로 지정
python organize_from_csv.py --csv data/results.csv --source data/ --output data/organized

# Docker에서 실행
docker compose run --rm --entrypoint python classifier \
  organize_from_csv.py \
  --csv /data/results.csv \
  --output /data/organized
```

결과 폴더 구조:

```
organized/
├── 서있기/
│   ├── photo1.jpg
│   └── photo5.jpg
├── 앉기/
│   └── photo2.jpg
└── 점프/
    └── photo3.jpg
```

> 원본 파일은 그대로 유지되며, 복사본만 생성됩니다.

---

## 지원 형식

- **입력**: JPG, JPEG, PNG, WEBP, GIF
- **출력**: CSV, JSON
