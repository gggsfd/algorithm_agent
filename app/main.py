from contextlib import asynccontextmanager
from dotenv import load_dotenv
from pathlib import Path
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv(Path(__file__).parent.parent / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[APP] 应用启动中...")
    yield
    print("[APP] 应用关闭中...")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Algorithm Agent - 字幕纠错系统",
        description="高并发强约束多 Agent 字幕纠错系统",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from app.api import srt, device, domain, adaptive, adaptive_materials
    app.include_router(srt.router, prefix="/api/v1", tags=["字幕处理"])
    app.include_router(device.router, prefix="/api/v1", tags=["设备管理"])
    app.include_router(domain.router, prefix="/api/v1", tags=["领域管理"])
    app.include_router(adaptive.router, prefix="/api/v1", tags=["动态领域自适应"])
    app.include_router(adaptive_materials.router, prefix="/api/v1", tags=["课程材料动态知识库"])

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
