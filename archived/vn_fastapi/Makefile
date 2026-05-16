# ═══════════════════════════════════════════════════════════
#  Nietzsche AI — Backend Makefile
#  사용 위치: apps/backend/
#  전제 조건: Poetry 설치, Docker PostgreSQL/Qdrant 실행 중
# ═══════════════════════════════════════════════════════════

.PHONY: help run dev test test-unit test-int test-cov test-file test-k \
        db-init db-reset db-reset-test lint format check install

# ───────────────────────────────────────────────
# 기본 타겟: help
# ───────────────────────────────────────────────
help:
	@echo ""
	@echo "  Nietzsche AI — Backend 명령어 목록"
	@echo "  ─────────────────────────────────────────────────"
	@echo "  [실행]"
	@echo "    make run            서버 실행 (reload 없음, 프로덕션용)"
	@echo "    make dev            서버 실행 (--reload, 개발용)"
	@echo ""
	@echo "  [테스트]"
	@echo "    make test           전체 테스트 실행"
	@echo "    make test-unit      단위 테스트만 실행"
	@echo "    make test-int       통합 테스트만 실행"
	@echo "    make test-cov       커버리지 리포트 포함 전체 테스트"
	@echo "    make test-file      특정 파일 테스트 (예: make test-file TARGET=tests/integration/test_chat_api.py)"
	@echo "    make test-k         키워드 매칭 테스트 (예: make test-k K=chat)"
	@echo ""
	@echo "  [DB]"
	@echo "    make db-init        개발 DB 테이블 생성 (데이터 유지)"
	@echo "    make db-reset       개발 DB 완전 초기화 (데이터 삭제)"
	@echo "    make db-reset-test  테스트 DB 완전 초기화"
	@echo ""
	@echo "  [코드 품질]"
	@echo "    make format         black + isort 자동 포맷"
	@echo "    make lint           black + isort 검사 (수정 없음)"
	@echo "    make check          lint + test 한 번에"
	@echo ""
	@echo "  [설치]"
	@echo "    make install        프로덕션 의존성 설치"
	@echo "    make install-dev    dev 의존성 포함 전체 설치"
	@echo ""

# ───────────────────────────────────────────────
# 실행
# ───────────────────────────────────────────────
VENV_PYTHON = .venv/bin/python
PYPATH = PYTHONPATH=.

run:
	$(PYPATH) $(VENV_PYTHON) -m uvicorn main:app --host 0.0.0.0 --port 8000

dev:
	$(PYPATH) $(VENV_PYTHON) -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# ───────────────────────────────────────────────
# 테스트
# ───────────────────────────────────────────────
test:
	$(PYPATH) $(VENV_PYTHON) -m pytest -v

test-unit:
	$(PYPATH) $(VENV_PYTHON) -m pytest tests/unit/ -v

test-int:
	$(PYPATH) $(VENV_PYTHON) -m pytest tests/integration/ -v

test-cov:
	$(PYPATH) $(VENV_PYTHON) -m pytest --cov=. --cov-report=term-missing --cov-report=html:htmlcov -v
	@echo "📊 커버리지 리포트: htmlcov/index.html"

test-file:
	$(PYPATH) $(VENV_PYTHON) -m pytest $(TARGET) -v

test-k:
	$(PYPATH) $(VENV_PYTHON) -m pytest -k "$(K)" -v

# ───────────────────────────────────────────────
# DB 초기화
# ───────────────────────────────────────────────
db-init:
	@echo "▶ 개발 DB 테이블 생성 (없는 경우에만)..."
	poetry run python db/reset_db.py --init

db-reset:
	@echo "⚠️  개발 DB를 초기화합니다."
	poetry run python db/reset_db.py

db-reset-test:
	@echo "▶ 테스트 DB 초기화..."
	poetry run python -c "\
import asyncio, os; \
from dotenv import load_dotenv; \
load_dotenv('.env.test', override=True); \
from db.reset_db import reset_db; \
asyncio.run(reset_db(os.environ['DATABASE_URL']))"
	@echo "✅ 테스트 DB 초기화 완료"

# ───────────────────────────────────────────────
# 코드 품질
# ───────────────────────────────────────────────
format:
	poetry run black .
	poetry run isort .

lint:
	poetry run black --check .
	poetry run isort --check-only .

check: lint test

# ───────────────────────────────────────────────
# 의존성 설치
# ───────────────────────────────────────────────
install:
	poetry install --only main

install-dev:
	poetry install
