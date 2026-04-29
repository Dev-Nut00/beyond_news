# Beyond News Backend (MVP)

중앙일보 RSS에서 최신 뉴스 1건을 가져와 간단한 지식그래프(JSON)로 변환합니다.

## 실행 방법

```bash
python backend/news_kg.py
```

출력 파일 기본값:

- `backend/output/news1_kg.json`

다른 경로로 저장하려면:

```bash
python backend/news_kg.py --output backend/output/custom_kg.json
```

최신 기사 3개 중 선택해서 생성:

```bash
python backend/news_kg.py --article-count 3 --article-index 1
```

- `--article-index`: 0, 1, 2 중 선택

## 웹에서 임시 확인하기 (프론트 없이)

아래 서버를 실행하면 브라우저에서 지식그래프를 바로 볼 수 있습니다.

```bash
python backend/web_preview.py
```

접속:

- `http://localhost:8000`

기능:

- 시작 시 `backend/output/news1_kg.json`이 없으면 자동 생성
- 최신 기사 3개 목록을 불러와 선택 가능
- 선택한 기사로 RSS 재수집 + 그래프 갱신
- 관계 라벨은 `related_to` 대신 문장 기반 관계명(예: `발표했다`, `요청했다`) 사용

