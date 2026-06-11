import os
import tempfile

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.schemas.response import ResponseCode, SuccessResponse
from app.services.adaptive_srt_service import AdaptiveSRTService


router = APIRouter()
adaptive_service = AdaptiveSRTService()


@router.post("/correct/adaptive")
async def correct_adaptive(
    file: UploadFile = File(...),
):
    if not file.filename or not file.filename.endswith(".srt"):
        raise HTTPException(status_code=ResponseCode.BAD_REQUEST, detail="仅支持 .srt 格式")

    try:
        srt_content = (await file.read()).decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=ResponseCode.BAD_REQUEST, detail="文件编码错误，请使用 UTF-8 编码")

    try:
        result = await adaptive_service.correct_current(srt_content)
    except ValueError as exc:
        raise HTTPException(status_code=ResponseCode.BAD_REQUEST, detail=str(exc))

    return SuccessResponse(data=result, message="动态领域纠错完成")


@router.post("/correct/adaptive/with-material")
async def correct_adaptive_with_material(
    file: UploadFile = File(...),
    material: UploadFile = File(...),
    append_to_current: bool = Form(default=False),
):
    if not file.filename or not file.filename.endswith(".srt"):
        raise HTTPException(status_code=ResponseCode.BAD_REQUEST, detail="仅支持 .srt 格式")
    if not material.filename:
        raise HTTPException(status_code=ResponseCode.BAD_REQUEST, detail="请上传课程材料")

    try:
        srt_content = (await file.read()).decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=ResponseCode.BAD_REQUEST, detail="文件编码错误，请使用 UTF-8 编码")

    suffix = os.path.splitext(material.filename)[1]
    material_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(await material.read())
            material_path = tmp.name
        result = await adaptive_service.correct_with_material(
            srt_content=srt_content,
            material_path=material_path,
            filename=material.filename,
            append_to_current=append_to_current,
        )
    except ValueError as exc:
        raise HTTPException(status_code=ResponseCode.BAD_REQUEST, detail=str(exc))
    finally:
        if material_path and os.path.exists(material_path):
            os.unlink(material_path)

    return SuccessResponse(data=result, message="动态材料纠错完成")


@router.post("/feedback")
async def submit_feedback(
    source: str = Form(...),
    raw_score: float = Form(...),
    calibrated_score: float = Form(...),
    accepted: bool = Form(...),
):
    adaptive_service.submit_feedback(source, raw_score, calibrated_score, accepted)
    return SuccessResponse(message="反馈已记录")
