# 신규 6개 도시 사진 수집 — 실행 방법 및 한계

## 실제 수행 상태

- 사진이 빠진 신규 6개 도시 **141개 일정**의 장소명·상세 일정명을 기반으로 검색어를 생성했습니다 (`PHOTO_SEARCH_141.csv`, `assets/photo_tasks.json`).
- Wikimedia Commons에서 실제로 존재하는 장소 사진 후보 일부는 수동 웹 조사로 확보했습니다. 목록에 있는 `commons_candidates`는 다운로드 확정이 아니라 **후보 파일명**이며, 다운로더가 Commons API로 존재 여부와 라이선스를 검증합니다.
- **이 ZIP 안에는 외부에서 다운로드한 JPG가 없습니다.** 생성 실행 환경의 외부 사진 파일 접근이 차단되어 실제 이미지 픽셀 데이터까지 받을 수 없었습니다.
- 대신 **사진을 실제로 다운로드하여 `assets/photos/{city}`에 포함시키는 실행 스크립트**와 이를 GitHub에서 실행할 수 있는 수동 workflow를 포함했습니다. 스크립트는 재사용 가능한 라이선스(CC BY, CC BY-SA, CC0, 퍼블릭 도메인)를 확인하고 썸네일을 JPG로 압축하며, 작가/저작권 정보를 `PHOTO_LICENSES.json`에 저장합니다.
- 파일이 실제로 내려받힌 일정만 `new_routes.json`의 `photo_file` 값을 로컬 파일로 바꾸도록 했습니다. 다운로드 실패 건을 성공처럼 처리하지 않습니다. 추가 검색으로 찾은 이미지가 실제 시설 사진으로 확인되지 않은 경우 `지역참고`라고 표시합니다.

## GitHub에서 실행 (네트워크 연결 가능한 환경)

1. 이 ZIP 내용을 저장소 루트에 업로드하거나 합칩니다. `.github/workflows/collect-commons-photos.yml`이 포함되어야 합니다.
2. GitHub 저장소 **Actions → Collect licensed travel photos → Run workflow**를 누릅니다. 저장소 설정에서 Actions가 `contents: write` 권한으로 커밋할 수 있도록 허용되어야 합니다.
3. 워크플로가 성공하면 실제 사진 JPG, `new_routes.json`, 사진별 출처/라이선스 및 실패 보고서가 자동 커밋됩니다. 실패 목록을 확인해 남은 장소 사진은 수동 검토해야 합니다.

로컬에서는 `python -m pip install Pillow` 뒤 `python scripts/download_photos.py`를 실행합니다.

## 주의사항

- 141개 모두 다운로드 성공한다고 보증하지 않습니다. Wikimedia Commons에 없는 관광지·온천·식당은 출처 확인 후 수작업으로 허가된 사진을 추가해야 합니다.
- 구글 이미지 검색 결과를 임의로 캡처하여 GitHub Pages에서 공개하는 방식은 저작권 문제가 발생할 수 있으므로 자동화하지 않았습니다. 구글 이미지는 후보 확인용 링크로만 제공합니다.
- 사진들이 정확한 업체의 실제 내부를 보여주는지, 복수의 반복 방문 일정에 어울리는지 최종 육안 검수해야 합니다.
- 이 패키지의 항공권·숙박·예산 데이터는 변경하지 않았습니다.
