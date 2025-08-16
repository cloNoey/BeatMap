from fastapi import FastAPI
# from app.core.logging import logger
# from app.db.base import Base
# from app.db.session import engine
from app.api.routes.tracks import router as tracks_router
from app.api.routes.analysis import router as analysis_router
from app.api.routes.stems import router as stems_router

app = FastAPI(title="Music Analyzer API for dancer")

# @app.on_event("startup")
# async def startup():
#     Base.metadata.create_all(bind=engine)
#     logger.info("DB tables ensured.")

app.include_router(tracks_router, prefix="/tracks", tags=["tracks"])
app.include_router(analysis_router, prefix="/analysis", tags=["analysis"])
app.include_router(stems_router, prefix="/stems", tags=["stems"])


@app.get("/test")
def test_api():
    return "SUCCESS"