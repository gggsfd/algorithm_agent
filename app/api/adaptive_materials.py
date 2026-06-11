import os
import tempfile

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.domain_adapter.extractor_factory import UnsupportedDocumentError
from app.schemas.response import ResponseCode, SuccessResponse
from app.services.dynamic_knowledge_service import get_dynamic_knowledge_service


router = APIRouter()


@router.post("/adaptive/materials/upload")
async def upload_materials(
    files: list[UploadFile] = File(...),
    enable_supplement: bool = Form(True),
    supplement_limit: int = Form(30),
):
    if not files:
        raise HTTPException(status_code=ResponseCode.BAD_REQUEST, detail="请上传课程材料")

    service = get_dynamic_knowledge_service()
    temp_files: list[tuple[str, str]] = []
    try:
        for upload in files:
            if not upload.filename:
                continue
            suffix = os.path.splitext(upload.filename)[1]
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(await upload.read())
                temp_files.append((tmp.name, upload.filename))
        result = service.upload_materials(
            temp_files,
            enable_supplement=enable_supplement,
            supplement_limit=supplement_limit,
        )
    except UnsupportedDocumentError as exc:
        raise HTTPException(status_code=ResponseCode.BAD_REQUEST, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=ResponseCode.BAD_REQUEST, detail=str(exc))
    finally:
        for path, _ in temp_files:
            if os.path.exists(path):
                os.unlink(path)
    return SuccessResponse(data=result, message="课程材料已追加到动态知识库")


@router.get("/adaptive/materials/stats")
async def get_material_stats():
    service = get_dynamic_knowledge_service()
    return SuccessResponse(data=service.get_stats(), message="success")


@router.get("/adaptive/materials/candidates")
async def get_candidate_materials():
    service = get_dynamic_knowledge_service()
    return SuccessResponse(data=service.get_candidates(), message="success")


@router.post("/adaptive/materials/reset")
async def reset_materials():
    service = get_dynamic_knowledge_service()
    return SuccessResponse(data=service.reset(), message="动态知识库已清空")
