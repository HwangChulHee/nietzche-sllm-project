다음 명령으로 FastAPI 엔드포인트를 테스트하라:

1. 백엔드 서버가 실행 중인지 확인. 실행 중이 아니라면:
   `cd apps/backend && poetry run uvicorn main:app --reload &`
   (서버 준비까지 2초 대기)

2. 다음 명령으로 요청을 보내라:
   `curl -N http://localhost:8000$ARGUMENTS`
   SSE 엔드포인트라면 `-N` 플래그로 스트리밍 출력 확인.

3. 응답 결과(상태 코드, 바디)를 요약해서 알려줘.

4. 테스트 완료 후 백그라운드 서버 종료:
   `kill %1 2>/dev/null || true`
