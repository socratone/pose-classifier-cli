# 📸 포즈 분류기 (Pose Classifier CLI)

Claude Vision API를 사용해 사진을 사용자 정의 포즈별로 자동 분류하는 CLI 프로그램입니다.

## 설치

### 사전 요구사항

- [Docker](https://docs.docker.com/get-docker/) 설치
- Anthropic API 키

### 이미지 빌드

```bash
docker compose build
# 또는
docker build -t pose-classifier .
```

## 빠른 시작

```bash
# 1. API 키 설정
export ANTHROPIC_API_KEY="sk-ant-..."

# 2. 실행 (포즈 직접 지정)
docker compose run --rm classifier \
  --poses "서있기,앉기,점프,눕기" \
  --input /data/photos \
  --output /data/results.csv

# 3. 대화형 포즈 입력 (포즈 없이 실행, -it 필요)
docker compose run --rm -it classifier \
  --input /data/photos \
  --output /data/results.csv
```

> **참고**: `/data`는 컨테이너 내부에서 프로젝트 루트 디렉토리(현재 디렉토리)를 가리킵니다.  
> 결과 파일을 유지하려면 반드시 `--output /data/...` 형식으로 지정하세요.

## 전체 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--poses` | 쉼표 구분 포즈 목록 | 대화형 입력 |
| `--input` | 이미지 폴더/파일 | 현재 디렉토리 |
| `--output` | 결과 파일 (.csv / .json) | `results.csv` |
| `--extensions` | 처리할 확장자 | jpg,jpeg,png,webp,gif |
| `--confidence` | 신뢰도 점수 포함 | off |
| `--reason` | 분류 이유 포함 | off |
| `--api-key` | API 키 직접 지정 | 환경변수 사용 |

## 사용 예시

### 기본 사용

```bash
docker compose run --rm classifier \
  --poses "standing,sitting,jumping,lying" \
  --input /data/my_photos \
  --output /data/results.csv
```

### 신뢰도 + 이유 포함, JSON 출력

```bash
docker compose run --rm classifier \
  --poses "서있기,앉기,점프,눕기" \
  --input /data/photos \
  --output /data/results.json \
  --confidence \
  --reason
```

### 단일 파일

```bash
docker compose run --rm classifier \
  --poses "서있기,앉기" \
  --input /data/photo.jpg \
  --output /data/results.csv
```

### 대화형 모드 (포즈 입력 없이 실행)

```bash
docker compose run --rm -it classifier \
  --input /data/photos \
  --output /data/results.csv

# 포즈 1: 서있기
# 포즈 2: 앉기
# 포즈 3: 점프
# 포즈 4: (엔터로 완료)
```

### plain Docker로 실행

```bash
docker run --rm \
  -v "$(pwd):/data" \
  -e ANTHROPIC_API_KEY \
  pose-classifier \
  --poses "서있기,앉기" \
  --input /data/photos \
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
  "results": [
    { "file": "photo1.jpg", "pose": "서있기", "confidence": 0.95 }
  ]
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

## 지원 형식

- **입력**: JPG, JPEG, PNG, WEBP, GIF
- **출력**: CSV, JSON
