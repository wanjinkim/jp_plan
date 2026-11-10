# JAPAN ATLAS · 일정별 사진 누락·깨짐 복구 v3

## 최종 상태: 패치 제작 완료, 실제 전체 사진 확보 여부는 배포 환경에서 검증 필요

- 대상: 12개 도시, 일정 281개. **ZIP에는 실사진 JPG가 아직 들어 있지 않습니다.** 이 환경에서 외부 이미지 원본 다운로드가 차단되었기 때문입니다.
- 기존 `download_photos.py`는 파일명에 영어 키워드가 없으면 사진을 떨어뜨리는 문제가 있었습니다. 새 수집기는 일정을 바탕으로 장소명을 먼저 찾고, Wikimedia Commons/일본어 Wikipedia/Openverse에서 사진을 재검색합니다.
- 실제 JPG를 내려받아 Pillow에서 디코딩한 다음에만 `assets/photos/schedules/{city}/d1-01.jpg`처럼 저장하고, 해당 일정의 `photo_file`과 사진 갤러리 JSON에 연결합니다. 실패한 일정은 정상 처리로 표시하지 않습니다.
- 장소 전용 사진이 없다면 **같은 도시 + 같은 활동 유형**의 이미지만 관련 참고사진으로 시도합니다. 랜덤 풍경을 해당 관광지 사진처럼 오인시키지 않습니다.
- Wikimedia API가 403/429 또는 네트워크 제한일 때 Openverse를 대체 공급자로 사용합니다. 두 공급자 모두 막히면 사진 281개 전부를 채운다고 보장할 수 없습니다.
- 배포 파일 외부 요청이 차단되더라도 **다운로드되어 GitHub에 저장된 사진은 외부 서버에 의존하지 않습니다**. 브라우저 자동 검색 기능은 아직 다운로드되지 않은 사진의 임시 복구 수단입니다.
- 비용, 예약 링크, 코스 내용, CSS, 기존 `app.js`는 수정하지 않습니다.

## GitHub에 적용하는 방법

1. ZIP을 컴퓨터에서 **압축 해제**하고, `photo-audit.html`, `assets/`, `scripts/`, `.github/workflows/`를 **GitHub 저장소 최상위의 같은 상대 경로에 업로드**하여 커밋합니다. ZIP 파일만 저장소에 업로드하면 동작하지 않습니다.
2. **기존 `index.html`은 덮어쓰지 않습니다.** Actions가 기존 HTML을 유지하며 사진 복구 스크립트 참조만 추가하도록 변경했습니다. 기존 경비·일정·디자인을 보호하기 위한 조치입니다.
3. GitHub → **Actions** → `FIX all itinerary images (licensed photos)` → **Run workflow**를 선택합니다. 기존 `Collect licensed travel photos` 및 `Collect 281 real Wikimedia travel photos`도 새 코드를 실행하도록 업데이트되어 있으나 혼동을 피하려면 `FIX all itinerary images`만 실행하세요. 이미 실행 중인 **옛 버전** 작업은 종료하고 새 작업을 실행하는 편이 안전합니다.
4. 작업이 완료되면 GitHub Pages가 반영된 뒤 `https://wanjinkim.github.io/jphUQgQXoSnXM6VP5rSECCcbQQ0u8YWhY8LpIsBjpi/photo-audit.html`에서 도시별 사진 상태를 확인합니다. **281/281이 실제 로딩되는지 반드시 점검**해야 합니다.

## 실패 시 확인할 항목

- Actions의 `Network diagnostics`에서 Commons와 Openverse가 각각 HTTP 200인지 봅니다. 두 서비스 모두 오류라면 어떤 키워드로도 사진 원본을 다운로드할 수 없습니다. 이때는 API 차단을 해결하거나 별도 인터넷 환경에서 다운로드해야 합니다.
- Actions `Job summary`: `Actual image files`와 `Unresolved` 개수가 나옵니다. **Unresolved가 0인 경우만 모든 일정에 파일이 연결된 상태**입니다.
- `PHOTO_REPAIR_STATUS.csv`: 누락된 일정의 정확한 키/장소를 확인합니다.
- `PHOTO_REPAIR_REPORT.json`: 검색 및 이미지 다운로드 실패 이유, 저장 여부를 확인합니다.
- `PHOTO_CREDITS.md`: 사진 출처·저작자·라이선스 정보. 재사용 라이선스 조건을 검토하세요.
- GitHub Pages가 아니라 GitHub Actions의 `Upload artifact`에 JPG가 들어 있는 경우, 저장소 커밋 단계가 실패한 것입니다. 이 경우 저장소 Settings → Actions → General의 `Workflow permissions`에서 **Read and write permissions**을 확인합니다.

## 유의사항

- 일부 온천·식당·체크인 활동은 실제 장소가 확정되지 않아, 실내 사진을 특정 업체 사진인 것처럼 표시하지 않습니다.
- 검색 결과와 사진 내용이 정확히 일치하는지 **281장 전부를 육안 확인한 것은 아닙니다**. 자동 매칭은 현장 사진 여부를 100% 보증하지 않습니다.
- 이 패치 자체는 **전부 확보한 281장 실사진 ZIP이 아니라, 현 배포 환경에서 이미지를 실제로 수집·저장하고 미확보를 진단하는 소스 패치**입니다. 성공했다고 허위 보고하지 않도록 검수 화면을 포함했습니다.
