


````md
# linuxmaster-dday-planner

Flask + MySQL 8 기반 D-day 학습계획/AI 퀴즈/오답복습 웹앱입니다.

---

<img width="1323" height="1034" alt="image" src="https://github.com/user-attachments/assets/137ee497-2ad0-4659-a1d7-62caf83c4908" />



## Why (왜 만들었나)
리눅스마스터를 준비하면서 가장 힘들었던 건 “오늘 뭘 해야 하는지”와 “틀린 문제를 어떻게 누적해서 복습할지"였습니다.
단순히 일정표를 적는 수준이 아니라, 시험일(D-day)에 맞춘 계획을 자동으로 생성하고, 공부 자료(텍스트/PDF)로부터 퀴즈를 만들어 반복 학습하며, 오답을 자동 누적해서 복습 루틴을 만들 수 있는 웹앱을 직접 만들어보자는 목표로 시작했습니다.

---

## 1) 구성
- Backend: Flask (Blueprint), SQLAlchemy, Flask-Migrate
- Auth: Flask-Login
- DB: MySQL 8
- AI: OpenAI API (`OPENAI_API_KEY` 없으면 더미 모드)
- Docs: PDF 업로드 후 PyMuPDF 텍스트 추출
- Infra: Docker Compose (`web` + `db`)

---

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
````

---

## 3) 실행 방법 (Docker)

### 1) 환경파일 생성

```bash
cp .env.example .env
# .env 파일을 열고 OPENAI_API_KEY를 실제 값으로 채우세요.
```

### 2) 컨테이너 실행

```bash
docker compose up --build
```

### 3) 마이그레이션 + 시드

권장(부트스트랩 스크립트):

```bash
docker compose exec web sh -c "./scripts/bootstrap.sh"
```

수동 실행:

```bash
docker compose exec web flask db init
docker compose exec web flask db migrate -m "init"
docker compose exec web flask db upgrade
docker compose exec web flask seed
```

### 4) 접속

* App: [http://localhost:5001](http://localhost:5001)
* MySQL: localhost:3307 (user/pass: `appuser/apppassword`, DB: `linuxmaster`)

---

## 4) 주요 라우트

* `/` 대시보드
* `/auth/register`, `/auth/login`, `/auth/logout`
* `/exam/new` 시험 입력 + 계획 생성
* `/plan` 학습 계획 조회
* `/quiz/new` 텍스트/PDF/URL(옵션) 퀴즈 생성
* `/quiz/<id>` 퀴즈 풀이
* `/review` 오답 리스트
* `/review/session` 오답 복습 세션

---

## 5) 구현 포인트

* PDF 업로드 보안

  * `secure_filename`, 확장자 제한(pdf), 10MB 제한
* 키워드 기반 출제 파이프라인

  * `ALL`: 전체 문맥
  * `SYLLABUS`/`CUSTOM`: `extract_relevant_passages`로 키워드 주변 문맥 추출
  * 키워드 매칭 부족 시 fallback(키워드 중심 문제 생성 지시)
* AI JSON 파싱 실패 대비

  * 스키마 검증 + 최대 3회 재시도
  * API 키 미설정 시 더미 질문 JSON 반환
* 오답노트 누적

  * 오답 시 `wrong_count += 1`, `last_wrong_at` 갱신, `mastered=False`
  * 복습 세션 정답 시 `mastered=True`

---

## 6) 주의

* 외부 기출 무단 크롤링 기능은 포함하지 않았습니다.
* URL 입력은 사용자가 제공한 공개 문서 1건만 최소 fetch하도록 구현되어 있습니다.
* `.env`는 GitHub에 올리지 않습니다. (`.gitignore`로 제외)

````

---

## ✅ 머지 충돌 해결 후 커밋/푸시 명령어

README 저장한 다음:

```bash
git add README.md
git commit -m "docs: resolve README merge conflict"
git push
````
