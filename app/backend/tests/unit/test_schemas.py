"""
단위 테스트: Pydantic 스키마 유효성 검증.
DB 연결 없이 순수 Python 로직만 검증.
"""

import pytest
from uuid import uuid4
from datetime import datetime
from pydantic import ValidationError

from schemas.user import UserCreate, UserResponse
from models.user import UserRole


class TestUserCreateSchema:
    def test_valid_user_create(self):
        """정상적인 UserCreate 생성."""
        user = UserCreate(name="니체")
        assert user.name == "니체"

    def test_name_required(self):
        """name 필드 누락 시 ValidationError 발생."""
        with pytest.raises(ValidationError):
            UserCreate()

    def test_empty_name_rejected(self):
        """빈 문자열 name은 거부되어야 함."""
        with pytest.raises(ValidationError):
            UserCreate(name="")


class TestUserResponseSchema:
    def test_valid_user_response(self):
        """정상적인 UserResponse 직렬화."""
        user_id = uuid4()
        now = datetime.now()
        resp = UserResponse(
            id=user_id,
            name="니체",
            role=UserRole.USER,
            created_at=now,
        )
        assert resp.id == user_id
        assert resp.name == "니체"
        assert resp.role == UserRole.USER

    def test_admin_role(self):
        """ADMIN role이 올바르게 처리됨."""
        resp = UserResponse(
            id=uuid4(),
            name="admin",
            role=UserRole.ADMIN,
            created_at=datetime.now(),
        )
        assert resp.role == UserRole.ADMIN

    def test_from_orm_compatible(self):
        """from_attributes=True 설정 확인 (ORM 객체 직렬화용)."""
        config = UserResponse.model_config
        assert config.get("from_attributes") is True
