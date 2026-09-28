# 단색 배경 제거 → Lottie JSON or GIF 변환 프로그램 (Video-to-Lottie or GIF)

10초 이하의 짧은 동영상 파일(.mp4, .mov)을 입력받아 **단색 배경을 자동으로 감지 및 제거**하고, 전경 객체의 외곽선을 벡터 Path로 추출하여 **투명 배경의 Lottie JSON** 애니메이션 파일로 변환하는 Python 프로그램입니다.

> [!IMPORTANT]
> **본 프로그램은 AI/머신러닝 모델을 일체 사용하지 않습니다.**  
> OpenCV 및 NumPy 기반의 이미지 처리 및 컴퓨터 비전 알고리즘만으로 배경 검출, 마스크 추출, 외곽선 단순화 및 Lottie JSON 생성을 수행합니다.

---

## 📑 주요 특징

* **배경색 자동 검출**: 사용자의 배경색 직접 입력 없이 영상의 4개 모서리(3%~5% 영역)를 다중 샘플링하여 CIELAB / HSV 색상 공간에서 최다 배경색을 자동 감지.
* **다중 프레임 배경 검증**: 0%, 25%, 50%, 75%, 100% 프레임 시점을 검사하여 배경 일관성을 확인하고 변경 시 경고 출력.
* **투명 배경 Lottie 생성**: 전경 객체의 외곽선을 Lottie 규격의 벡터 Shape Path(`v`, `i`, `o`, `c`) 및 프레임별 Hold Keyframe(`h: 1`)으로 변환.
* **JSON 파일 용량 최적화**: 
  * `cv2.approxPolyDP`를 활용한 외곽선 좌표 단순화 (프레임당 100~300 포인트 목표).
  * 좌표 소수점 정밀도 제한 (기본 2자리).
  * 연속 프레임 간 변형이 적은 키프레임 자동 생략.
* **제한 사항**: 최대 10초 이하 동영상 지원 (10초 초과 시 오류 메시지 출력 후 종료).

---

## 🛠️ 개발 및 실행 환경

* **Python 3.11 이상**
* **필수 라이브러리**:
  * `opencv-python >= 4.8.0`
  * `numpy >= 1.24.0`

---

## 📂 프로젝트 구조

```text
video-to-lottie/
│
├── main.py                # CLI 실행 메인 스크립트
├── config.py              # 기본 설정 및 하이퍼파라미터
├── requirements.txt       # 의존성 패키지 목록
├── README.md              # 프로젝트 안내 문서
├── test.html              # Lottie Web 애니메이션 확인용 HTML 파일
│
├── video/                 # 비디오 읽기 및 메타데이터 추출 모듈
│   ├── __init__.py
│   ├── reader.py
│   └── frame_processor.py
│
├── background/            # 배경색 자동 검출 모듈
│   ├── __init__.py
│   └── detector.py
│
├── mask/                  # 색상 거리 마스크 및 모놀로지 후처리 모듈
│   ├── __init__.py
│   └── processor.py
│
├── contour/               # 외곽선 추출 및 approxPolyDP 단순화 모듈
│   ├── __init__.py
│   └── extractor.py
│
├── lottie/                # Lottie Path 변환 및 JSON 생성 모듈
│   ├── __init__.py
│   ├── path.py
│   └── writer.py
│
├── tests/                 # 단계별 검증 테스트 스크립트
│   ├── test_phase1_2.py
│   └── test_phase3_5.py
│
├── input/                 # 입력 영상 저장 디렉토리
├── lottie-output/         # 생성된 Lottie JSON 저장 디렉토리
└── debug/                 # 디버그 마스크/외곽선 이미지 저장 디렉토리
```

---

## 🚀 설치 및 실행 방법

### 1. 의존성 패키지 설치

```bash
pip install -r requirements.txt
```

### 2. macOS 전용 더블클릭 실행 🍎 (Apple Silicon M1/M2/M3/M4 & Intel Mac)

1. `mac_run.command` 파일에 실행 권한 부여 (터미널 최초 1회):
   ```bash
   chmod +x mac_run.command
   ```
2. Finder(파인더)에서 **`mac_run.command`**를 **더블클릭**하면 자동으로 파이썬 가상환경 생성 및 필요한 라이브러리를 설치한 후 GUI 프로그램이 실행됩니다.

#### macOS 독립 실행형 앱 번들(`.app`) 빌드:
```bash
python build_mac_app.py
```
빌드가 완료되면 `dist/LottieConverter.app` 앱 번들이 생성되며, `/Applications` (응용 프로그램) 폴더로 옮겨 일반 Mac 앱처럼 사용할 수 있습니다.

### 3. GUI 데스크톱 프로그램 실행 (추천 🖥️)

```bash
python gui.py
```
* **영상 파일 선택**, **초당 프레임(FPS: 10, 15, 20, 30 선택)**, 배경 감도, 전경 색상 선택 가능.
* 변환 완료 시 `lottie-output/` 폴더에 자동으로 파일이 저장되며, **"다른 위치에 저장 (다운로드)"** 및 **"lottie-output 폴더 열기"** 기능 제공.

### 3. Web 브라우저 GUI 실행 (웹 UI 🌐)

```bash
python web_gui.py
```
* 웹 브라우저(`http://localhost:5000`)에서 영상 업로드 및 FPS 선택 후 즉시 Lottie 변환, 웹 실시간 애니메이션 미리보기 및 다운로드 제공.

### 4. CLI 명령줄 실행 (CLI 💻)

```bash
python main.py input/sample.mp4
```

실행 시 `lottie-output/sample.json` 파일이 생성됩니다.

### 3. 옵션 지정 실행

```bash
python main.py input/sample.mp4 --fps 15 --threshold 35 --fill-color "#3366FF" --debug
```

#### CLI 명령어 옵션 목록

| 옵션 | 기본값 | 설명 |
| :--- | :--- | :--- |
| `input` | *(필수)* | 입력 동영상 파일 경로 (`.mp4`, `.mov`) |
| `-o`, `--output` | `lottie-output/<파일명>` | 출력 파일 경로 |
| `--format` | `both` | 내보내기 형식 (`both`, `lottie`, `gif`) |
| `--width` | `None` | 아웃풋 너비 (px) 지정 (비율 자동 유지) |
| `--height` | `None` | 아웃풋 높이 (px) 지정 |
| `--mode` | `image` | 변환 모드 (`image`: 원본 이미지, `vector`: 실루엣) |
| `--fps` | `15` | 타겟 초당 프레임 (10, 15, 20, 30 등) |
| `--threshold` | `35` | 배경색 거리 마스킹 임계값 (CIELAB 거리) |
| `--epsilon` | `0.002` | 외곽선 단순화 비율 (`approxPolyDP` epsilon) |
| `--min-area` | `0.0005` | 노이즈 제거용 최소 외곽선 면적 비율 (0.05%) |
| `--fill-color` | `#FFFFFF` | 전경 객체 칠하기 색상 (Hex 코드, 예: `#FFFFFF`, `#FF0000`) |
| `--scale` | `1.0` | 벡터 출력 해상도 스케일 비율 |
| `--debug` | `False` | 마스크 및 외곽선 검증 PNG 이미지를 `debug/` 폴더에 저장 |
| `--no-optimize` | `False` | 키프레임 중복 생략 최적화 비활성화 |

---

## 🖥️ 실행 로그 예시

```text
$ python main.py input/sample.mp4

[1/6] Reading video: input/sample.mp4...
[2/6] Detecting background color...

--- Background Checkpoints ---
Frame   0% -> RGB(0, 255, 0)
Frame  25% -> RGB(0, 255, 0)
Frame  50% -> RGB(0, 255, 0)
Frame  75% -> RGB(0, 255, 0)
Frame 100% -> RGB(0, 255, 0)
Background detected successfully.

[3/6] Creating masks...
[4/6] Extracting contours...
[5/6] Creating Lottie paths...
[6/6] Writing JSON...
Lottie JSON saved: output/sample.json (42.15 KB)

Background:
RGB(0,255,0)

Frames:
150

Output:
output/sample.json

Completed.
```

---

## 🌐 결과 Lottie JSON 확인 방법 (test.html)

프로젝트에 포함된 `test.html`을 웹 브라우저(Chrome, Edge, Safari 등)에서 열어 생성된 Lottie 애니메이션을 실시간으로 미리보기 및 테스트할 수 있습니다.

1. 브라우저에서 `test.html` 파일을 엽니다.
2. 상단의 **파일 선택** 버튼으로 `output/*.json` 파일 선택 (기본적으로 `output/sample_test.json` 자동 로드 시도).
3. **재생/일시정지**, **다시 시작**, **배경 스타일 변경 (격자/어두움/밝음)** 기능을 통해 투명 처리 품질을 검증할 수 있습니다.

---

## 🧪 단계별 파이프라인 검증 테스트

개발 지침에 따른 단계별 테스트 스크립트 실행:

```bash
# Phase 1 & Phase 2 (배경 검출, 마스크 생성, 외곽선 단순화 및 debug/ PNG 저장)
python tests/test_phase1_2.py

# Phase 3 ~ Phase 5 (Lottie Path 변환, 키프레임 최적화 및 Lottie JSON 검증)
python tests/test_phase3_5.py
```
