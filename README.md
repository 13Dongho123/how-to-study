<<<<<<< HEAD
# how-to-study
=======
# linuxmaster-dday-planner

Flask + MySQL 8 기반 D-day 학습계획/AI 퀴즈/오답복습 웹앱입니다.

## 1) 구성
- Backend: Flask (Blueprint), SQLAlchemy, Flask-Migrate
- Auth: Flask-Login
- DB: MySQL 8
- AI: OpenAI API (`OPENAI_API_KEY` 없으면 더미 모드)
- Docs: PDF 업로드 후 PyMuPDF 텍스트 추출
- Infra: Docker Compose (`web` + `db`)

## 2) 디렉터리
```text
linuxmaster-dday-planner/
  app/
    __init__.py
    extensions.py
    models.py
    seed.py
    blueprints/
      auth.py
      main.py
      exam.py
      quiz.py
      review.py
    services/
      ai.py
      content.py
      planning.py
    templates/
      base.html
      ...
  scripts/
    entrypoint.sh
    bootstrap.sh
  uploads/
  run.py
  config.py
  Dockerfile
  docker-compose.yml
  requirements.txt
  .env.example
```

## 3) 실행 방법
1. 환경파일 생성
```bash
cp .env.example .env
```

2. 컨테이너 실행
```bash
docker compose up --build
```

3. 마이그레이션 + 시드
```bash
docker compose exec web sh -c "./scripts/bootstrap.sh"
```

수동으로 하려면:
```bash
docker compose exec web flask db init
docker compose exec web flask db migrate -m "init"
docker compose exec web flask db upgrade
docker compose exec web flask seed
```

4. 접속
- App: http://localhost:5001
- MySQL: localhost:3307 (`appuser/apppassword`, DB: `linuxmaster`)

## 4) 주요 라우트
- `/` 대시보드
- `/auth/register`, `/auth/login`, `/auth/logout`
- `/exam/new` 시험 입력 + 계획 생성
- `/plan` 학습 계획 조회
- `/quiz/new` 텍스트/PDF/URL(옵션) 퀴즈 생성
- `/quiz/<id>` 퀴즈 풀이
- `/review` 오답 리스트
- `/review/session` 오답 복습 세션

## 5) 구현 포인트
- PDF 업로드 보안: `secure_filename`, 확장자 제한(pdf), 10MB 제한
- 키워드 기반 출제 파이프라인:
  - `ALL`: 전체 문맥
  - `SYLLABUS`/`CUSTOM`: `extract_relevant_passages`로 키워드 주변 문맥 추출
  - 키워드 매칭 부족 시 fallback(키워드 중심 문제 생성 지시)
- AI JSON 파싱 실패 대비:
  - 스키마 검증 + 최대 3회 재시도
  - API 키 미설정 시 더미 질문 JSON 반환
- 오답노트 누적:
  - 오답 시 `wrong_count += 1`, `last_wrong_at` 갱신, `mastered=False`
  - 복습 세션 정답 시 `mastered=True`

## 6) 주의
- 외부 기출 무단 크롤링 기능은 포함하지 않았습니다.
- URL 입력은 사용자가 제공한 공개 문서 1건만 최소 fetch하도록 구현되어 있습니다.
>>>>>>> 7e85027 (Initial commit)
