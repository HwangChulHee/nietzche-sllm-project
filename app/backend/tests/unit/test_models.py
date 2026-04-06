"""
단위 테스트: SQLAlchemy 모델 구조 검증.
실제 DB 연결 없이 모델 정의의 컬럼, 관계, 기본값을 검증.
"""

import uuid
import pytest
from models.user import User, UserRole
from models.chat import ChatRoom, ChatMessage


class TestUserModel:
    def test_user_tablename(self):
        assert User.__tablename__ == "user"

    def test_user_default_role(self):
        """role 기본값이 USER인지 확인."""
        user = User(name="test_user")
        # column default는 Python 레벨에서 바로 접근 가능
        role_col = User.__table__.c["role"]
        assert role_col.default.arg == UserRole.USER

    def test_user_id_is_uuid(self):
        """id 컬럼이 UUID 타입인지 확인."""
        id_col = User.__table__.c["id"]
        import sqlalchemy
        assert isinstance(id_col.type, sqlalchemy.Uuid)

    def test_user_name_unique(self):
        """name 컬럼에 unique 제약 조건이 있는지 확인."""
        name_col = User.__table__.c["name"]
        assert name_col.unique is True

    def test_user_has_chat_rooms_relationship(self):
        """User → ChatRoom 관계가 정의되어 있는지 확인."""
        assert hasattr(User, "chat_rooms")


class TestChatRoomModel:
    def test_chatroom_tablename(self):
        assert ChatRoom.__tablename__ == "chat_room"

    def test_chatroom_has_user_fk(self):
        """chat_room.user_id가 user.id를 참조하는지 확인."""
        user_id_col = ChatRoom.__table__.c["user_id"]
        fk = list(user_id_col.foreign_keys)[0]
        assert fk.target_fullname == "user.id"

    def test_chatroom_has_messages_relationship(self):
        assert hasattr(ChatRoom, "messages")


class TestChatMessageModel:
    def test_message_tablename(self):
        assert ChatMessage.__tablename__ == "chat_message"

    def test_message_role_column(self):
        """role 컬럼이 존재하는지 확인."""
        assert "role" in ChatMessage.__table__.c

    def test_message_has_references_column(self):
        """RAG 참조 저장용 references(JSON) 컬럼 존재 확인."""
        assert "references" in ChatMessage.__table__.c

    def test_message_has_room_fk(self):
        """chat_message.room_id가 chat_room.id를 참조하는지 확인."""
        room_id_col = ChatMessage.__table__.c["room_id"]
        fk = list(room_id_col.foreign_keys)[0]
        assert fk.target_fullname == "chat_room.id"
