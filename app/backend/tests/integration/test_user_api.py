"""
통합 테스트: /api/v1/user 및 /api/v1/auth 엔드포인트.
"""

import pytest
from httpx import AsyncClient


class TestSignup:
    async def test_signup_success(self, client: AsyncClient):
        """정상 회원가입 → 201 Created, 사용자 정보 + 토큰 반환."""
        response = await client.post(
            "/api/v1/user/signup",
            json={"name": "프리드리히", "password": "password123"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "프리드리히"
        assert data["role"] == "user"
        assert "id" in data
        assert "created_at" in data
        assert "token" in data
        assert data["token"] is not None

    async def test_signup_duplicate_name(self, client: AsyncClient):
        """동일한 name으로 두 번 가입 시 400 반환."""
        await client.post("/api/v1/user/signup", json={"name": "차라투스트라", "password": "password123"})
        response = await client.post(
            "/api/v1/user/signup",
            json={"name": "차라투스트라", "password": "password123"},
        )
        assert response.status_code == 400
        assert "이미 존재하는 이름" in response.json()["detail"]

    async def test_signup_missing_name(self, client: AsyncClient):
        """name 필드 누락 시 422 Unprocessable Entity."""
        response = await client.post("/api/v1/user/signup", json={"password": "password123"})
        assert response.status_code == 422

    async def test_signup_empty_name(self, client: AsyncClient):
        """빈 문자열 name은 422로 거부됨."""
        response = await client.post(
            "/api/v1/user/signup",
            json={"name": "", "password": "password123"},
        )
        assert response.status_code == 422

    async def test_signup_short_password(self, client: AsyncClient):
        """6자 미만 password는 422로 거부됨."""
        response = await client.post(
            "/api/v1/user/signup",
            json={"name": "테스터", "password": "abc"},
        )
        assert response.status_code == 422


class TestLogin:
    async def test_login_success(self, client: AsyncClient):
        """올바른 자격증명으로 로그인 → 200 + 토큰."""
        await client.post("/api/v1/user/signup", json={"name": "로그인유저", "password": "password123"})
        response = await client.post(
            "/api/v1/auth/login",
            json={"name": "로그인유저", "password": "password123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["token"] is not None

    async def test_login_wrong_password(self, client: AsyncClient):
        """잘못된 패스워드 → 401."""
        await client.post("/api/v1/user/signup", json={"name": "보안유저", "password": "correct123"})
        response = await client.post(
            "/api/v1/auth/login",
            json={"name": "보안유저", "password": "wrong123"},
        )
        assert response.status_code == 401

    async def test_login_unknown_user(self, client: AsyncClient):
        """존재하지 않는 사용자 → 401."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"name": "없는사람", "password": "password123"},
        )
        assert response.status_code == 401


class TestHealthCheck:
    async def test_health_endpoint(self, client: AsyncClient):
        """/health 엔드포인트가 200을 반환하는지 확인."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
