from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.responses import RedirectResponse

from app.v1.repositories.upgrade import upgrade


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Upgrade database schema.
    upgrade()
    yield


router = APIRouter(
    lifespan=lifespan,
    prefix="/v1",
    tags=["v1"],
)

@router.get("/")
async def index():
    return RedirectResponse(url="/v5/budget")
