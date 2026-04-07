"""
단위 테스트: Pydantic 스키마 유효성 검증.
"""

import pytest
from uuid import uuid4
from pydantic import ValidationError

from schemas.chat import ChatRequest, ChatMessageResponse


class TestChatRequestSchema:
    def test_valid_request(self):
        req = ChatRequest(message="안녕하세요")
        assert req.message == "안녕하세요"
        assert req.conversation_id is None

    def test_with_conversation_id(self):
        cid = uuid4()
        req = ChatRequest(message="질문", conversation_id=cid)
        assert req.conversation_id == cid

    def test_empty_message_rejected(self):
        with pytest.raises(ValidationError):
            ChatRequest(message="")

    def test_missing_message_rejected(self):
        with pytest.raises(ValidationError):
            ChatRequest()
