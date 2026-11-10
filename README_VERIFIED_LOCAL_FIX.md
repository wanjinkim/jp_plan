# 이미지 경로 복구 - 실제 ZIP 기준

- 검토 대상: 281 일정
- ZIP에 파일이 존재하고 이미지 디코딩 검사를 통과한 것: 135
- 로컬 파일 자체가 없어 화면 표시를 보장할 수 없는 것: 146

## 고친 사항

1. `assets/app.js`: 다운로드된 `local` 경로를 `gPhoto()`에서 최우선 처리, JS 객체가 `src`에 들어가지 않도록 타입 검사.
2. `assets/app.js`: `city-day-step` 기준으로 `assets/local_schedule_photos.json`을 조회하므로 사진 갤러리의 제목/장소 매칭 누락과 무관하게 실제 로컬 JPG 표시.
3. `index.html`: 브라우저에서 Commons / Openverse API를 실시간 검색하는 `photo-resolver.js` 제거. CORS/504 발생 원인 차단.
4. `scripts/build_local_photo_index.py`: 사진 다운로드 후 실제 존재하는 파일만 인덱스 작성.
5. GitHub workflow: 다운로드 후 인덱스 재생성 및 커밋.

## 중요

이번 ZIP에는 135개의 실제 JPG가 있고, 146개는 사진이 없습니다. 따라서 '281개 모두 정상 표시' 결과가 아닙니다. 미확보 목록은 `PHOTO_MISSING_LOCAL_146.csv`입니다.

## 배포

저장소의 파일과 변경 내역을 검토한 뒤 이 ZIP의 파일을 동일 경로에 적용합니다. 최신 운영 저장소가 이 첨부 ZIP보다 최신이라면 전체를 덮어쓰지 말고 `assets/app.js`, `assets/local_schedule_photos.json`, `index.html`, 빌더 스크립트와 워크플로만 변경분을 병합하세요.

새로 다운로드된 사진은 `python scripts/build_local_photo_index.py` 실행 후 인덱스를 재커밋해야 반영됩니다.
