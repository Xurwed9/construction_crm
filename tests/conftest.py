import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.user import User, UserRole

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

_fixture_counter = 0


def _next_id() -> int:
    global _fixture_counter
    _fixture_counter += 1
    return _fixture_counter


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(engine) -> AsyncGenerator[AsyncClient, None]:
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_token(engine) -> str:
    uid = _next_id()
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        user = User(
            first_name="Admin",
            last_name=f"User{uid}",
            email=f"admin{uid}@test.com",
            phone=f"+9989012345{uid:02d}",
            password_hash=hash_password("StrongPass1"),
            role=UserRole.ADMIN,
        )
        session.add(user)
        await session.commit()
        return create_access_token(str(user.id), user.role.value)


@pytest_asyncio.fixture
async def manager_token(engine) -> str:
    uid = _next_id()
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        user = User(
            first_name="Manager",
            last_name=f"User{uid}",
            email=f"manager{uid}@test.com",
            phone=f"+9989012346{uid:02d}",
            password_hash=hash_password("StrongPass1"),
            role=UserRole.MANAGER,
        )
        session.add(user)
        await session.commit()
        return create_access_token(str(user.id), user.role.value)


@pytest_asyncio.fixture
async def client_token(engine) -> str:
    uid = _next_id()
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        user = User(
            first_name="Client",
            last_name=f"User{uid}",
            email=f"client{uid}@test.com",
            phone=f"+9989012347{uid:02d}",
            password_hash=hash_password("StrongPass1"),
            role=UserRole.CLIENT,
        )
        session.add(user)
        await session.commit()
        return create_access_token(str(user.id), user.role.value)
