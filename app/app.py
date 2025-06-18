import traceback

import logfire
from fastapi import FastAPI, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config.settings import settings
from app.v1.controllers.middleware.bs4_middleware import BS4Middleware
from app.v1.controllers.v1_router import router as v1_router

app = FastAPI(title=settings.app_name, debug=settings.debug)
app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=5)
app.add_middleware(BS4Middleware)

logfire.configure(environment=settings.logfire_environment, token=settings.logfire_token)
logfire.instrument_fastapi(app, capture_headers=True)
logfire.instrument_sqlite3()


@app.exception_handler(Exception)
async def debug_exception_handler(_: Request, exc: Exception):
    if settings.debug:
        return JSONResponse(
            status_code=500,
            content={"error": str(exc), "traceback": traceback.format_exc()},
        )
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error"},
    )


app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(v1_router)


@app.get("/")
async def index():
    return RedirectResponse(url="/v1")
