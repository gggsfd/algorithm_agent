from fastapi import APIRouter, HTTPException
from app.schemas.response import SuccessResponse, ResponseCode
from app.schemas.domain import is_supported_domain
from app.rag.domain_manager import get_domain_manager

router = APIRouter()


@router.get("/domains")
async def list_domains():
    manager = get_domain_manager()
    return SuccessResponse(
        data={"domains": manager.list_domains()},
        message="success"
    )


@router.get("/domains/{domain_id}/terms")
async def get_domain_terms_stats(domain_id: str):
    if not is_supported_domain(domain_id):
        raise HTTPException(
            status_code=ResponseCode.BAD_REQUEST,
            detail=f"Unsupported domain: {domain_id}"
        )
    manager = get_domain_manager()
    return SuccessResponse(
        data=manager.get_domain_stats(domain_id),
        message="success"
    )
