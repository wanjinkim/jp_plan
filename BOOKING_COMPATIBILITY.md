# 네이버 검색 연동 정확성

| 기능 | 구현된 사항 | 미확인 / 제한 |
|---|---|---|
| 항공권 | 왕복 공항·날짜·성인·직항 `flight.naver.com/flights/international/` 검색 URL 생성 | 네이버 UI의 동작은 서비스 변경, 운항편 미존재 등으로 달라질 수 있음 |
| 숙소(해외호텔/공유숙박/모텔) | 숙소 종류와 도시/권역을 키워드로 묶어 `search.naver.com/search.naver` 통합검색을 실행 | 호텔 전용 검색 결과에 체크인·체크아웃·인원·객실 필터가 자동 적용되는 공개 링크를 검증하지 못함 |
| 숙소 공식 웹 | `hotels.naver.com/` 접속 | 호텔 페이지에서 날짜/인원/객실 재선택 필요 |
| 일정 사진 | 일정별 매칭된 Commons 실사진, 사진 클릭 시 `google.com/search?tbm=isch&q=...` | 검색 결과에 같은 사진이 반드시 처음 나타나는 것은 아님 |

공식 참고: https://help.naver.com/service/30031/contents/4100?lang=ko&osType=COMMONOS
네이버 공유숙박 공식 제휴: https://news.airbnb.com/ko/navermetasearch
왕복 항공권 URL 형식은 실제 공개 링크 예시와 동일합니다.

서비스 제공자의 화면에서 설치/권한 요청을 요구하는 경우에는 진행하지 말고 공식 주소를 확인하세요.
