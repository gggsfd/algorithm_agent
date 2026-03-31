from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional
from app.schemas.response import SuccessResponse, ErrorResponse, ResponseCode
from app.services.srt_service import SRTService
from app.core.exceptions import SRTParseError

router = APIRouter()
srt_service = SRTService()


@router.post("/parse")
async def parse_srt(file: UploadFile = File(...)):
    if not file.filename.endswith('.srt'):
        raise HTTPException(
            status_code=ResponseCode.BAD_REQUEST,
            detail="仅支持 .srt 格式文件"
        )

    content = await file.read()
    try:
        srt_content = content.decode('utf-8')
        parse_result = srt_service.parse_srt(srt_content)
        timeline = srt_service.get_timeline(srt_content)

        return SuccessResponse(
            data={
                "total": len(parse_result),
                "subtitles": timeline
            },
            message="SRT 文件解析成功"
        )
    except SRTParseError as e:
        raise HTTPException(
            status_code=ResponseCode.BAD_REQUEST,
            detail=str(e)
        )
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=ResponseCode.BAD_REQUEST,
            detail="文件编码错误，请使用 UTF-8 编码"
        )


@router.post("/correct")
async def correct_srt(file: UploadFile = File(...)):
    if not file.filename.endswith('.srt'):
        raise HTTPException(
            status_code=ResponseCode.BAD_REQUEST,
            detail="仅支持 .srt 格式文件"
        )

    content = await file.read()
    try:
        srt_content = content.decode('utf-8')
        corrected_srt, success = srt_service.process_srt(srt_content)

        return SuccessResponse(
            data={
                "success": success,
                "corrected_srt": corrected_srt
            },
            message="字幕纠错完成" if success else "字幕纠错失败，已保留原字幕"
        )
    except SRTParseError as e:
        raise HTTPException(
            status_code=ResponseCode.BAD_REQUEST,
            detail=str(e)
        )
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=ResponseCode.BAD_REQUEST,
            detail="文件编码错误，请使用 UTF-8 编码"
        )


@router.post("/batch")
async def batch_correct_srt(
    files: UploadFile = File(...),
    chunk_size: int = Form(default=20, ge=5, le=100),
    overlap: int = Form(default=5, ge=0, le=20)
):
    if not files.filename.endswith('.srt'):
        raise HTTPException(
            status_code=ResponseCode.BAD_REQUEST,
            detail="仅支持 .srt 格式文件"
        )

    content = await files.read()
    try:
        srt_content = content.decode('utf-8')
        corrected_srt, success = await srt_service.process_srt_batch(
            srt_content,
            chunk_size=chunk_size,
            overlap=overlap
        )

        return SuccessResponse(
            data={
                "success": success,
                "corrected_srt": corrected_srt,
                "chunk_size": chunk_size,
                "overlap": overlap
            },
            message=f"批量处理完成（每块 {chunk_size} 句，重叠 {overlap} 句）"
        )
    except SRTParseError as e:
        raise HTTPException(
            status_code=ResponseCode.BAD_REQUEST,
            detail=str(e)
        )
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=ResponseCode.BAD_REQUEST,
            detail="文件编码错误，请使用 UTF-8 编码"
        )


@router.post("/batch/robust")
async def batch_correct_srt_robust(
    files: UploadFile = File(...),
    chunk_size: int = Form(default=20, ge=5, le=100),
    overlap: int = Form(default=5, ge=0, le=20),
    max_retries: int = Form(default=3, ge=0, le=5)
):
    if not files.filename.endswith('.srt'):
        raise HTTPException(
            status_code=ResponseCode.BAD_REQUEST,
            detail="仅支持 .srt 格式文件"
        )

    content = await files.read()
    try:
        srt_content = content.decode('utf-8')

        corrected_srt, success, stats = await srt_service.process_srt_robust(
            srt_content,
            chunk_size=chunk_size,
            overlap=overlap,
            max_retries=max_retries
        )

        return SuccessResponse(
            data={
                "success": success,
                "corrected_srt": corrected_srt,
                "stats": stats,
                "config": {
                    "chunk_size": chunk_size,
                    "overlap": overlap,
                    "max_retries": max_retries
                }
            },
            message=f"处理完成: {stats['success']}/{stats['total']} 块成功"
        )
    except SRTParseError as e:
        raise HTTPException(
            status_code=ResponseCode.BAD_REQUEST,
            detail=str(e)
        )
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=ResponseCode.BAD_REQUEST,
            detail="文件编码错误，请使用 UTF-8 编码"
        )
