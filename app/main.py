from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.endpoints import auth, matrix, users
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(matrix.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": f"{settings.APP_NAME} v{settings.APP_VERSION} is running"}
