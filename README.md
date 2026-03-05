# linuxmaster-dday-planner

Flask + MySQL 8 기반 D-day 학습계획/AI 퀴즈/오답복습 웹앱입니다.
이 문서는 **EKS/Kubernetes가 아닌 Docker 런처(docker compose / docker run)** 기준 실행 방법을 설명합니다.

## 구조도
<img width="1000" height="1228" alt="image" src="https://github.com/user-attachments/assets/1d7cb0a3-d4a1-4fa1-956c-1593260f81d6" />

## Why (왜 만들었나)

리눅스마스터 및 다른 과목들을 공부하면서 제일 불편했던 건 두 가지였습니다.

1) D-day 기준으로 “오늘 뭘 해야 하는지”가 매일 흔들리는 문제  
2) 기출/연습 문제를 풀어도 틀린 문제들이 흩어져서, 결국 다시 안 보게 되는 문제

처음엔 노트/엑셀/메모앱으로 일정과 오답을 관리했는데, 시간이 지나면 관리가 깨지고 복습 루틴이 흐트러졌습니다.
그래서 아예 **시험일을 입력하면 학습 계획을 자동으로 만들고**, 공부 자료(텍스트/PDF)로부터 **퀴즈를 생성해서 반복 학습**하며, **오답을 누적해서 복습 페이지에서 다시 풀 수 있는** 형태로 직접 구현하기로 했습니다.

## 구조
```
linuxmaster-dday-planner/
  app/
  migrations/
  scripts/
  uploads/
  k8s/
  deploy/
    docker/
      Dockerfile
      docker-compose.yml
      docker-compose.override.yml
      nginx.conf
      .env.example
      .dockerignore
  config.py
  requirements.txt
  run.py
  README.md
```
## 1) 구성
- `web`: Flask app (`/app`, port `5000`)
- `db`: MySQL 8 (`3306`)
- 기본 실행: `docker compose` (web + db)
- 스케일링 옵션:
  - Option A: `docker compose --scale web=2` (단순 동시 실행)
  - Option B: `web 2개 + nginx reverse proxy` (권장 LB 방식)

## 2) 사전 준비
```bash
cp .env.example .env
```

`.env`를 열어 다음 값을 실제 환경에 맞게 채우세요.
- 비민감 Config:
  - `FLASK_APP`, `FLASK_ENV`, `OPENAI_MODEL`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `MAX_CONTENT_LENGTH`
- 민감 Secret:
  - `SECRET_KEY`, `OPENAI_API_KEY`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_ROOT_PASSWORD`

권장 방식: `.env`에 완성형 `DB_URL` 사용
```env
DB_URL=mysql+pymysql://appuser:apppassword@db:3306/linuxmaster?charset=utf8mb4
```

참고: `DB_URL`이 없으면 `entrypoint.sh`가 `MYSQL_* + DB_*` 값으로 자동 조합합니다.

## 3) 기본 실행 (Option A)

```bash
docker compose up --build
```

접속:
- App: [http://localhost:5001](http://localhost:5001)
- MySQL: `localhost:3307`

마이그레이션 적용:
```bash
docker compose exec web flask db upgrade
```

초기 데이터까지 필요하면:
```bash
docker compose exec web sh -c "./scripts/bootstrap.sh"
```

### Option A에서 web 2개 실행
```bash
docker compose up --build --scale web=2
```

주의: `web` 서비스가 `5001:5000` 포트를 고정 바인딩하면 scale 시 포트 충돌이 납니다.
실제 로드밸런싱이 필요하면 아래 Option B를 사용하세요.

## 4) nginx 리버스프록시 실행 (Option B, 권장)

`docker-compose.override.yml` + `nginx.conf`가 포함되어 있습니다.

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml up --build --scale web=2
```

접속:
- Nginx(LB): [http://localhost:5001](http://localhost:5001)

동작 방식:
- `web` 컨테이너는 내부 포트만 사용 (`expose 5000`)
- `nginx`만 외부 `5001` 노출

## 5) docker run 기반 예시 (Option B 대안)

```bash
# 네트워크 생성
docker network create dday-net

# DB
docker run -d --name db --network dday-net \
  -e MYSQL_DATABASE=linuxmaster \
  -e MYSQL_USER=appuser \
  -e MYSQL_PASSWORD=apppassword \
  -e MYSQL_ROOT_PASSWORD=replace-root-password \
  -v dday_mysql_data:/var/lib/mysql \
  mysql:8 \
  mysqld --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci

# WEB 1/2
docker run -d --name web1 --network dday-net --env-file .env linuxmaster-dday-planner-web
docker run -d --name web2 --network dday-net --env-file .env linuxmaster-dday-planner-web

# Nginx
# nginx.conf의 upstream을 web1/web2로 지정한 별도 설정 사용 가능
```

## 6) 현재 반영된 이슈 대응
- `documents.text_extracted`: `MEDIUMTEXT`로 확장 반영됨
  - 모델: `app/models.py`
  - 마이그레이션: `migrations/versions/2f87bc9361b1_expand_documents_text_extracted.py`
- PDF 업로드 제한: 기본 `20MB`
  - `MAX_CONTENT_LENGTH=20971520`
- `review_tasks` 테이블 반영됨
  - 마이그레이션: `migrations/versions/9c1f4f0f4a01_add_review_tasks.py`
- MySQL 인증/암호화 이슈 대비
  - `cryptography` 의존성과 런타임 SSL 라이브러리 포함

## 7) 트러블슈팅

### 1) `cryptography` 관련 MySQL 인증 오류
- 증상: MySQL 접속 시 인증 플러그인/암호화 관련 오류
- 해결:
  - 이미지 재빌드: `docker compose build --no-cache web`
  - `requirements.txt`에 `cryptography` 포함 여부 확인

### 2) `review_tasks` 테이블 없음
- 증상: `Table '...review_tasks' doesn't exist`
- 해결:
```bash
docker compose exec web flask db upgrade
```

### 3) PDF 텍스트 저장 길이 초과
- 증상: `Data too long for column text_extracted`
- 해결:
```bash
docker compose exec web flask db upgrade
```
(`MEDIUMTEXT` 마이그레이션이 적용되어야 함)

### 4) DB 상태가 꼬였을 때 초기화
```bash
docker compose down -v
docker compose up --build
```

## 8) 보안
- `.env`, `.env.*`는 `.gitignore`/`.dockerignore`로 제외되어 Git에 올라가지 않습니다.
- 실제 키/비밀번호를 코드/README에 넣지 마세요.
