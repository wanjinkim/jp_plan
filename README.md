# JAPAN ATLAS — GitHub Pages 정적 배포 버전

이 버전은 Firebase / Cloud Run 의존성을 모두 제거한 GitHub Pages 전용 정적 사이트입니다.
로그인·비밀번호·서버 세션·데이터베이스 코드가 없습니다.

## 배포 방법 (GitHub Free · 공개 저장소)

1. GitHub에서 **New repository**를 선택합니다.
2. 저장소 이름을 본인이 정합니다. 난수형 이름도 가능합니다(예: `jp-atlas-fae38d12` — 예시일 뿐 실제 생성된 저장소가 아닙니다).
3. **Public**으로 만들고 생성합니다.
4. 이 폴더의 `index.html`, `assets/`, `.nojekyll`, `robots.txt` 등을 **저장소 최상위(root)** 에 업로드하고 commit합니다. **ZIP 파일 자체를 업로드하는 것이 아닙니다.**
5. 저장소 **Settings → Pages → Build and deployment → Source: Deploy from a branch → Branch: main / (root) → Save**.
6. 사이트는 GitHub 계정과 저장소 이름을 사용한 URL에서 열립니다.
   `https://<GitHub-사용자명>.github.io/<저장소명>/`
7. 이후 동일 파일을 수정해서 commit하면 사이트가 다시 배포됩니다.

## 구조와 링크

- 홈: `?` 없이 루트
- 항공·숙소: `?page=booking`
- 도시: `?page=city&id=hiroshima` (도시별 ID가 달라짐)
- 사진: `?page=photos&city=hiroshima`

이렇게 쿼리 기반으로 만든 이유는 GitHub Pages에서 서버 rewrite 없이도 새로고침·직접 링크가 동작하도록 하기 위해서입니다.
지도·항공·호텔 링크는 외부 공식 도메인으로 열리며 링크 이동 확인창이 나타납니다.

## 공개 범위와 사진 유의사항

- GitHub Free의 Pages는 **공개 저장소**를 사용합니다. 누구나 사이트와 원본 파일을 볼 수 있습니다.
- 긴 저장소 이름, `noindex`, `robots.txt`는 **보안·접근 제한 수단이 아닙니다**.
- 사진은 현재 Wikimedia Commons 외부 링크로 제공되는 경우가 있습니다. 파일 자체를 모두 저장한 것은 아닙니다. 촬영 대상·저작자·라이선스를 원본에서 확인해야 합니다.
- 여행 일정 및 교통 소요 시간은 실시간 확정 정보가 아닙니다. 방문 전에 운영시간·예약·교통편을 재검증하세요.
- 이 사이트는 무료 정적 호스팅만 사용하며 프론트엔드 내에 API 비밀키를 포함해서는 안 됩니다.
- GitHub Pages 사용 제한: 게시 사이트 최대 1 GB, 월 100 GB soft bandwidth, 시간당 10개 빌드 soft limit(일반 브랜치 배포).

공식 문서: https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site
