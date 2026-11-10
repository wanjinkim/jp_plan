# GitHub Actions 사진 다운로드 후 사이트 반영 안 되는 문제 수정

이 패치는 **이전에 전달한 `JAPAN_ATLAS_photo_recovery_workflow.zip`의 파일 구조**를 기준으로 합니다. 현재 GitHub 저장소 파일을 직접 열어 일치 여부를 검증한 것은 아닙니다. 다른 수정사항이 있다면 덮어쓰기 전에 비교하세요.

## 원인

기존 워크플로는 `steps.verify.outcome == 'success'` 즉 **281/281 파일이 모두 확보된 경우에만 git commit/push**하도록 작성됐습니다. 일부 파일만 성공한 실행은 Artifact에만 남고, GitHub Pages에는 반영되지 않습니다. 또한 120분 실행 제한에 걸리면 파일 저장 단계까지 도달하지 못할 수 있습니다.

## 고친 부분

- 전체 완료 전이라도, 이미지 원본이 실제 다운로드된 항목은 `git commit`·`git push`로 저장소에 반영
- 이미 받은 JPG는 재검증한 다음 다음 실행에서 건너뛰기
- 45분 이내에 다운로드 루프를 종료하여 커밋 단계까지 진행하도록 안전장치 추가
- 최종 281개 완료 여부를 분리해 검증; 미완료면 Actions 상태는 실패지만 이미 받은 사진은 반영 가능
- Actions Artifacts에 로그, 사진, 누락 목록 업로드

## 사용

기존 저장소에서 `scripts/collect_281_photos.py`와 `.github/workflows/collect-281-real-photos.yml` 두 파일을 동일 경로에 교체하여 커밋하고, `Actions → Collect 281 real Wikimedia travel photos → Run workflow` 실행.

**주의**: GitHub Actions에서 `git push` 성공 여부 및 실제 사진 수는 로그를 봐야 알 수 있습니다. 로컬 이미지 파일을 확보했다는 사실과 정확한 방문지 사진이라는 사실은 별개의 문제입니다. 사진 후보는 육안 검수하세요. 저장소에 쓰기 권한이 제한되어 있으면 워크플로 `permissions: contents: write`를 설정해도 push가 실패할 수 있습니다.

배포 반영 여부는 GitHub Actions의 `Commit and deploy photos already downloaded` 단계 및 저장소 `assets/photos/schedules/` 파일 생성을 확인하세요. 페이지가 실패하면 사진 파일 URL을 직접 열어 200 응답 여부를 검사해야 합니다.
