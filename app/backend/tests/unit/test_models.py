"""
단위 테스트: SQLAlchemy 모델 구조 검증.
"""

import sqlalchemy
from models.chat import Conversation, Message


class TestConversationModel:
    def test_tablename(self):
        assert Conversation.__tablename__ == "conversations"

    def test_id_is_uuid(self):
        id_col = Conversation.__table__.c["id"]
        assert isinstance(id_col.type, sqlalchemy.Uuid)

    def test_has_messages_relationship(self):
        assert hasattr(Conversation, "messages")


class TestMessageModel:
    def test_tablename(self):
        assert Message.__tablename__ == "messages"

    def test_has_role_column(self):
        assert "role" in Message.__table__.c

    def test_has_conversation_fk(self):
        conv_id_col = Message.__table__.c["conversation_id"]
        fk = list(conv_id_col.foreign_keys)[0]
        assert fk.target_fullname == "conversations.id"
