from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.routers.shopping import router as shopping_router
from app.core.middleware import add_cors, register_exception_handlers
from app.graph.graph import build_graph


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.graph = build_graph()
    yield


app = FastAPI(title="AI Shopping Assistant API", lifespan=lifespan)

add_cors(app)
register_exception_handlers(app)
app.include_router(shopping_router, prefix="/api/v1/shopping", tags=["shopping"])
