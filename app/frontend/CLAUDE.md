@AGENTS.md

# Frontend — Next.js 16 가이드

## 상태 관리
- Redux Toolkit (RTK): 전역 상태
- RTK Query: REST API 호출
- createAsyncThunk + Fetch API: SSE 스트리밍

## 폴더 구조 (예정)
- `app/` : Next.js App Router 페이지
- `components/ui/` : shadcn/ui 기본 컴포넌트
- `components/chat/` : 채팅 도메인 컴포넌트
- `lib/store/` : Redux store, slices
- `lib/hooks/` : 커스텀 훅

## API 연동
- 백엔드 base URL: http://localhost:8000
- SSE 스트리밍: EventSource 또는 fetch + ReadableStream
