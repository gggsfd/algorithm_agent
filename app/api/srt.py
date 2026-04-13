from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from app.schemas.response import SuccessResponse, ResponseCode
from app.services.srt_service import SRTService
from app.services.srt_file_saver import SRTFileSaver
from app.core.srt_file_saver_config import SRTFileSaverConfig
from app.core.exceptions import SRTParseError
from app.schemas.domain import Domain
from app.schemas.correction_mode import CorrectionMode

router = APIRouter()
srt_service = SRTService()
srt_file_saver_config = SRTFileSaverConfig()
srt_file_saver = SRTFileSaver(config=srt_file_saver_config)


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
async def correct_srt(
    file: UploadFile = File(...),
    domain: str = Form(default=Domain.ALGORITHM.value),
    correction_mode: str = Form(default=CorrectionMode.RULE.value)
):
    if not file.filename.endswith('.srt'):
        raise HTTPException(
            status_code=ResponseCode.BAD_REQUEST,
            detail="仅支持 .srt 格式文件"
        )

    content = await file.read()
    try:
        srt_content = content.decode('utf-8')
        corrected_srt, success, mode_meta = await srt_service.process_srt_async(
            srt_content,
            domain=domain,
            correction_mode=correction_mode
        )

        return SuccessResponse(
            data={
                "success": success,
                "corrected_srt": corrected_srt,
                "domain": domain,
                "correction_mode": mode_meta["correction_mode"],
                "effective_mode": mode_meta["effective_mode"],
                "degraded": mode_meta["degraded"],
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
    except ValueError as e:
        raise HTTPException(
            status_code=ResponseCode.BAD_REQUEST,
            detail=str(e)
        )


@router.post("/correct/save")
async def correct_and_save_srt(
    file: UploadFile = File(...),
    domain: str = Form(default=Domain.ALGORITHM.value),
    correction_mode: str = Form(default=CorrectionMode.HYBRID_AUTO.value),
    save_file: bool = Query(default=True, description="是否保存文件"),
    generate_report: bool = Query(default=True, description="是否生成报告")
):
    if not file.filename.endswith('.srt'):
        raise HTTPException(
            status_code=ResponseCode.BAD_REQUEST,
            detail="仅支持 .srt 格式文件"
        )

    content = await file.read()
    try:
        srt_content = content.decode('utf-8')
        original_items = srt_service.parser.parse(srt_content).items

        corrected_srt, success, mode_meta = await srt_service.process_srt_async(
            srt_content,
            domain=domain,
            correction_mode=correction_mode
        )

        corrected_items = srt_service.parser.parse(corrected_srt).items

        file_info = None
        correction_report = None
        warning = None

        if save_file:
            srt_file_saver.config.auto_save = True
            srt_file_saver.config.generate_report = generate_report
            save_result = srt_file_saver.save(
                corrected_srt=corrected_srt,
                original_filename=file.filename,
                original_items=original_items,
                corrected_items=corrected_items
            )

            file_info = save_result.file_info.model_dump() if save_result.file_info else None
            correction_report = save_result.correction_report.model_dump() if save_result.correction_report else None
            warning = save_result.warning

        return SuccessResponse(
            data={
                "success": success,
                "corrected_srt": corrected_srt,
                "domain": domain,
                "correction_mode": mode_meta["correction_mode"],
                "effective_mode": mode_meta["effective_mode"],
                "degraded": mode_meta["degraded"],
                "file_info": file_info,
                "correction_report": correction_report,
                "warning": warning
            },
            message="字幕纠错完成" + ("并已保存文件" if save_file else "")
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
    except ValueError as e:
        raise HTTPException(
            status_code=ResponseCode.BAD_REQUEST,
            detail=str(e)
        )


@router.post("/batch")
async def batch_correct_srt(
    files: UploadFile = File(...),
    chunk_size: int = Form(default=20, ge=5, le=100),
    overlap: int = Form(default=5, ge=0, le=20),
    domain: str = Form(default=Domain.ALGORITHM.value),
    correction_mode: str = Form(default=CorrectionMode.RULE.value)
):
    if not files.filename.endswith('.srt'):
        raise HTTPException(
            status_code=ResponseCode.BAD_REQUEST,
            detail="仅支持 .srt 格式文件"
        )

    content = await files.read()
    try:
        srt_content = content.decode('utf-8')
        corrected_srt, success, mode_meta = await srt_service.process_srt_batch(
            srt_content,
            chunk_size=chunk_size,
            overlap=overlap,
            domain=domain,
            correction_mode=correction_mode
        )

        return SuccessResponse(
            data={
                "success": success,
                "corrected_srt": corrected_srt,
                "chunk_size": chunk_size,
                "overlap": overlap,
                "domain": domain,
                "correction_mode": mode_meta["correction_mode"],
                "effective_mode": mode_meta["effective_mode"],
                "degraded": mode_meta["degraded"],
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
    except ValueError as e:
        raise HTTPException(
            status_code=ResponseCode.BAD_REQUEST,
            detail=str(e)
        )


@router.post("/batch/robust")
async def batch_correct_srt_robust(
    files: UploadFile = File(...),
    chunk_size: int = Form(default=20, ge=5, le=100),
    overlap: int = Form(default=5, ge=0, le=20),
    max_retries: int = Form(default=3, ge=0, le=5),
    domain: str = Form(default=Domain.ALGORITHM.value),
    correction_mode: str = Form(default=CorrectionMode.RULE.value)
):
    if not files.filename.endswith('.srt'):
        raise HTTPException(
            status_code=ResponseCode.BAD_REQUEST,
            detail="仅支持 .srt 格式文件"
        )

    content = await files.read()
    try:
        srt_content = content.decode('utf-8')

        corrected_srt, success, stats, mode_meta = await srt_service.process_srt_robust(
            srt_content,
            chunk_size=chunk_size,
            overlap=overlap,
            max_retries=max_retries,
            domain=domain,
            correction_mode=correction_mode
        )

        return SuccessResponse(
            data={
                "success": success,
                "corrected_srt": corrected_srt,
                "stats": stats,
                "correction_mode": mode_meta["correction_mode"],
                "effective_mode": mode_meta["effective_mode"],
                "degraded": mode_meta["degraded"],
                "config": {
                    "domain": domain,
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
    except ValueError as e:
        raise HTTPException(
            status_code=ResponseCode.BAD_REQUEST,
            detail=str(e)
        )
