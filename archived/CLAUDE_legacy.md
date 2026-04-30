# 니체 sLLM 프로젝트 — Claude Code 컨텍스트

## 프로젝트 개요

니체 페르소나를 학습한 sLLM 기반 철학 상담 서비스. 졸업 캡스톤 프로젝트.

프리드리히 니체의 철학적 저서를 학습한 Gemma 4 모델로 사용자에게 니체 특유의 문체와 철학적 통찰이 담긴 상담을 제공한다.

## 현재 진행 상태

**중간발표일: 2026-04-13 (월)**

두 갈래로 병렬 진행 중:

### Track 1: 데이터 파이프라인 + 파인튜닝
- 위치: `ml/data_pipeline/`
- 담당: 사용자가 다른 Claude 세션에서 직접 작업
- 산출물: 파인튜닝된 Gemma 4 26B-A4B 모델 + vLLM 추론 서버
- **이 트랙은 건드리지 말 것. ml/ 디렉토리는 .claudeignore로 차단되어 있음.**

### Track 2: 프론트엔드 + 백엔드 (Claude Code 작업 영역)
- 위치: `app/`
- 목표: Track 1에서 나올 모델과 연동되는 채팅 UI + API 서버
- 작업 지시: `app/CLAUDE.md` 참조

## 전체 디렉토리 구조

```
nietzche-sllm-project/
├── ml/                  # Track 1 (차단됨, 건드리지 말 것)
│   ├── data_pipeline/
│   ├── data/
│   └── models/
├── app/                 # Track 2 (Claude Code 작업 영역)
│   ├── frontend/        # Next.js
│   └── backend/         # FastAPI
└── docker-compose.yml
```

## 두 트랙 사이의 인터페이스

Track 1이 Track 2에 제공하는 것:
- 파인튜닝된 모델 (Hugging Face 형식)
- vLLM 추론 서버 (OpenAI 호환 `/v1/chat/completions` API)
- 시스템 프롬프트 텍스트 파일

Track 2가 Track 1에 의존하는 방식:
- HTTP로 vLLM 서버에 요청 (OpenAI Chat Completions API)
- 환경변수로 모델 엔드포인트/이름 주입
- **모델이 아직 준비 안 돼 있어도 mock 모드로 개발 가능해야 함**

## Track 2의 단일 미션

> 파인튜닝된 Gemma 4가 vLLM으로 서빙되었을 때, 환경변수 한두 개만 바꾸면
> 즉시 동작하는 채팅 웹 앱을 만든다.

평가 시나리오, 시연 방식, 시스템 프롬프트 강도 같은 결정은 후순위.
**연동 가능한 코드가 작성되어 있는 것이 최우선.**

## 작업 원칙

1. **갈아끼울 수 있는 구조**: LLM 클라이언트, 시스템 프롬프트, 모델 정보는 모두 환경변수/외부파일로 분리
2. **mock 우선 개발**: 실제 모델이 없어도 개발/테스트 가능
3. **MVP 우선**: 동작하는 것 > 완벽한 것
4. **변경 최소**: 기존 코드 구조를 최대한 존중
5. **안전한 변경**: 파괴적 변경(대량 삭제, 구조 변경)은 사용자 확인 필수

## 작업 시 주의사항

- ml/ 디렉토리는 절대 건드리지 말 것 (.claudeignore로 차단됨)
- docker-compose.yml의 ml 관련 부분은 수정 금지
- Track 1에서 사용자가 작업 중이므로, 루트 README.md 수정은 사용자 확인 필요
- 작업 끝날 때마다 한 줄 요약 + 다음 할 일을 명시