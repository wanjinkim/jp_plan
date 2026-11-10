# JAPAN ATLAS · 281개 일정 사진 수집/검증 패키지

## 현재 상태와 주의사항

**현재 ZIP은 `281장 실사진 확보 완료본`이 아닙니다.** 생성 환경에서 외부 이미지 다운로드가 차단되어 실제 JPG 파일을 확보하지 못했습니다. `assets/photo_manifest_281.json`은 준비된 검수 대상 281개 목록이며, 모든 항목의 `status`는 초기 상태 `not_downloaded`입니다. 사진을 실제로 받은 것처럼 처리하지 않습니다.

- 기존 추천 6개 도시 **140개 일정**, 신규 6개 도시 **141개 일정** 총 281개 검수.
- 기존 JSON 안에 존재했지만 실제 JPG가 없는 `local` 필드를 제거하여 잘못된 로컬 경로를 우선하지 않도록 수정했습니다.
- 일정의 장소·이름 기반 Commons 파일 후보, 일본어 위키피디아 문서 대표 이미지, Commons 파일 검색 순서로 시도합니다.
- 저작자/라이선스 메타데이터가 확인되고 실제 디코딩에 성공한 이미지만 저장합니다.
- 다운로드 이미지도 장소 사진으로 정확히 일치하는지 육안 검토가 필요합니다. 특히 식사·휴식·교통 사진은 `참고사진`일 수 있습니다.
- **실제 파일 281개가 모두 존재할 때만** `JAPAN_ATLAS_281_REAL_PHOTOS_FINAL.zip`이 생성됩니다.
- 기존 항공권·예산 수치는 변경하지 않았습니다.

## 로컬 Windows에서 실행

저장소 루트에 파일을 풀고 `RUN_COLLECT_WINDOWS.bat`을 실행합니다. Python 3가 필요합니다. 파일 다운로드에는 인터넷이 연결되어 있어야 합니다. 누락 항목은 `PHOTO_VERIFICATION_REPORT.md` 및 `PHOTO_DOWNLOAD_REPORT.json`에 기록됩니다.

## GitHub Actions에서 실행

이 ZIP 내용을 저장소의 최상위에 반영하면 `.github/workflows/collect-281-real-photos.yml`에서 **Actions → Collect 281 real Wikimedia travel photos → Run workflow**를 실행할 수 있습니다. 결과는 Actions의 Artifacts에서 내려받을 수 있습니다. 모든 281개의 실사진 검증이 끝났을 때만 GitHub에 파일이 자동 커밋됩니다. 그렇지 않으면 누락 목록과 받은 사진만 Artifacts로 제공되며 **미완성본이 최종으로 배포되지 않습니다**.

저작권이 있는 구글 이미지 검색 화면을 캡처해서 공개 사이트에 재배포하지 않습니다. Wikimedia Commons 라이선스 원문을 기준으로 사용 조건을 확인해야 합니다.

### 제공되는 진단 자료

`PHOTO_STATUS_281.csv`: 일정별 사진 누락 상태 및 후보
`PHOTO_SEARCH_141.csv`: 신규 6개 도시별 장소 기반 검색어
`assets/photo_tasks.json`: 신규 6개 도시의 파일명 후보
`assets/photo_manifest_281.json`: 전체 281개 일정 검증표

### 원본 출처 예

- Fukuoka Airport International Terminal: https://commons.wikimedia.org/wiki/File:Fukuoka_Airport_international_terminal.jpg
- Commons의 사진 사용 조건은 파일별로 다르므로 각 라이선스와 저작자를 보존해야 합니다.
