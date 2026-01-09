# Browser Link Tracker

개인용 링크 트래커 - 여러 브라우저의 방문 기록을 자동으로 수집하고 관리하는 도구

## 주요 기능

### 핵심 기능
- **다중 브라우저 지원**: Chrome, Edge, Brave, Opera, Vivaldi 등 Chromium 기반 브라우저 지원
- **자동 수집**: 주기적으로 브라우저 히스토리를 스캔하여 방문 링크 수집
- **URL 필터링**: 특정 도메인이나 패턴을 수집에서 제외 (예: sts.secosso.net)
- **휴지통 기능**: 소프트 삭제로 실수 방지, 필요시 복원 가능

### 데이터 관리
- **카테고리/태그 분류**: 링크를 카테고리와 태그로 체계적으로 정리
- **Import/Export**: JSON 형식으로 데이터 내보내기/가져오기 (중복 자동 처리)
- **강력한 검색**: URL, 제목, 태그, 메모 등으로 빠른 검색
- **방문 기록 추적**: 마지막 접속 시각, 총 방문 횟수 기록

### 사용자 경험
- **GUI 인터페이스**: 사용하기 쉬운 데스크톱 애플리케이션
- **배치 작업**: 여러 링크 동시 선택 및 삭제/복원
- **성능 최적화**: 병렬 처리 및 배치 작업으로 빠른 속도

## 설치 및 실행

### 개발 환경에서 실행

1. Python 3.8+ 설치 필요

2. 가상환경 생성 및 활성화:
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac
```

3. 의존성 설치:
```bash
pip install -r requirements.txt
```

4. 애플리케이션 실행:
```bash
python src/main.py
```

### Windows 실행 파일 빌드

```bash
# build.bat 실행 또는:
pyinstaller build.spec
```

빌드 완료 후 `dist/LinkTracker.exe` 파일이 생성됩니다.

## 사용 방법

### 초기 설정

1. 애플리케이션을 처음 실행하면 자동으로 브라우저 프로필을 검색합니다
2. 검색된 브라우저가 상태바에 표시됩니다

### 링크 수집

- **자동 스캔**: 기본적으로 5분마다 자동 스캔 (설정에서 변경 가능)
- **수동 스캔**: 상단 툴바의 "📡 Scan" 버튼 클릭 또는 F5 키

### 단축키

- **F5**: 브라우저 히스토리 스캔
- **Ctrl+R**: 링크 목록 새로고침
- **Delete**: 선택한 링크 휴지통으로 이동
- **Ctrl+A**: 모든 링크 선택
- **Ctrl+클릭**: 개별 항목 선택/해제
- **Shift+클릭**: 범위 선택

### 링크 관리

#### 검색 및 필터링
- 상단 검색창에서 키워드 입력
- 카테고리 드롭다운으로 카테고리별 필터링
- 시간 필터: All / Today / 7 Days / 30 Days

#### 카테고리 관리
- 메뉴 → Edit → Categories 에서 카테고리 생성/수정/삭제
- 각 카테고리에 색상 지정 가능

#### URL 필터 관리
- 메뉴 → Edit → URL Filters 에서 수집 제외 패턴 관리
- 필터 타입: domain(도메인), prefix(시작 문자), contains(포함), regex(정규식)
- 필터 활성화/비활성화 및 테스트 기능

#### 휴지통 관리
- 메뉴 → Edit → Recycle Bin 에서 삭제된 링크 확인
- 선택적 복원 또는 영구 삭제
- Ctrl/Shift 클릭으로 다중 선택

#### 링크 편집
1. 링크 목록에서 항목 선택
2. 우측 상세 패널에서 정보 편집:
   - 제목 수정
   - 카테고리 할당
   - 태그 추가 (쉼표로 구분)
   - 메모 작성
   - 즐겨찾기 설정

### 데이터 Import/Export
- **내보내기**: 메뉴 → File → Export (JSON 형식)
  - 삭제된 링크 제외
  - 카테고리와 태그 정보 포함
- **가져오기**: 메뉴 → File → Import
  - 중복 URL 자동 병합
  - access_count 누적
  - 삭제된 링크는 복구하지 않음

## 기술 스택

- **언어**: Python 3.8+
- **GUI**: Tkinter (Python 내장)
- **데이터베이스**: SQLite (로컬 저장)
- **브라우저 추적**: Chromium History DB 직접 읽기

## 데이터 저장 위치

- **개발 모드**: `data/links.db`
- **배포 모드**: `%APPDATA%/LinkTracker/links.db`
- **로그 파일**: `%APPDATA%/LinkTracker/logs/linktracker.log`

## 프로젝트 구조

```
browserTracker/
├── src/
│   ├── main.py                      # 진입점
│   ├── database/                     # 데이터베이스 레이어
│   │   ├── models.py                 # 데이터 모델 (Link, Category, Tag, URLFilter)
│   │   └── db_manager.py             # DB 작업 관리
│   ├── tracker/                      # 브라우저 추적 모듈
│   │   ├── browser_history.py        # 기본 히스토리 스캐너
│   │   ├── browser_history_optimized.py  # 최적화된 병렬 스캐너
│   │   └── browser_paths.py          # 브라우저 경로 유틸리티
│   ├── gui/                          # GUI 컴포넌트
│   │   ├── main_window.py            # 메인 윈도우
│   │   ├── link_list.py              # 링크 리스트 뷰
│   │   ├── detail_panel.py           # 상세 정보 패널
│   │   ├── category_dialog.py        # 카테고리 관리 대화상자
│   │   ├── trash_dialog.py           # 휴지통 대화상자
│   │   └── filter_dialog.py          # URL 필터 관리 대화상자
│   └── utils/                        # 유틸리티
│       ├── url_utils.py              # URL 정규화
│       └── config.py                 # 앱 설정
├── requirements.txt                  # Python 의존성
├── build.spec                       # PyInstaller 설정
└── build.bat                        # Windows 빌드 스크립트
```

## 개발 로드맵

### v0.1 (완료)
- ✅ Chrome/Edge History 주기 스캔
- ✅ 링크 저장 및 관리
- ✅ 카테고리/태그 기능
- ✅ GUI 검색/정렬/필터
- ✅ Windows 실행 파일 빌드

### v0.2 (현재)
- ✅ 소프트 삭제 및 휴지통 기능
- ✅ Import/Export 기능 (JSON)
- ✅ URL 필터링 (도메인 제외)
- ✅ 배치 작업 성능 최적화
- ✅ 병렬 브라우저 스캔
- ✅ 다중 선택 및 배치 삭제

### v0.3 (계획)
- [ ] 프로필별 분리 표시
- [ ] 설정 대화상자
- [ ] 백업 자동화
- [ ] 통계 대시보드

### v0.4 (미래)
- [ ] 브라우저 확장 프로그램 연동 (실시간 추적)
- [ ] 링크 프리뷰
- [ ] 고급 통계 및 시각화
- [ ] 클라우드 동기화 옵션

## 주의사항

- 이 프로그램은 로컬 브라우저 히스토리를 읽기 때문에 개인정보 보호에 유의하세요
- 모든 데이터는 로컬에만 저장되며 외부로 전송되지 않습니다
- 브라우저가 실행 중일 때 히스토리 DB가 잠길 수 있으나, 프로그램은 복사본을 만들어 읽기 때문에 문제없습니다

## 라이센스

Personal Use Only - 개인 사용 목적으로만 사용 가능

## 문제 해결

### 브라우저가 감지되지 않는 경우
- 브라우저가 기본 경로에 설치되어 있는지 확인
- 관리자 권한으로 실행 시도

### 스캔이 작동하지 않는 경우
- 브라우저 History 파일 접근 권한 확인
- 로그 파일에서 오류 메시지 확인

### 한글이 깨지는 경우
- UTF-8 인코딩 설정 확인
- Windows 지역 설정에서 UTF-8 사용 활성화