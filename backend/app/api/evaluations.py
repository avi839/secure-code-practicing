"""
Evaluation endpoints - create a reflexion run, poll its progress, cancel or delete it.

Runs execute in a BackgroundTask that opens its own DB session (decision D11);
the client polls GET /api/evaluations/{id} while rounds are committed one by one.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Path, Query, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.schemas.evaluation import (
    CancelEvaluationRequest,
    CodeVersionResponse,
    CreateEvaluationRequest,
    EvaluationActionResponse,
    EvaluationDetailResponse,
    EvaluationListResponse,
    EvaluationStatusEnum,
    ProgrammingLanguageEnum,
)
from app.services.evaluation_service import EvaluationService
from app.services.providers import get_provider

router = APIRouter()

NOT_FOUND = "Evaluation not found"
VERSION_PATTERN = r"^t\d{1,2}$"


DEMO_USERNAME = "demo"


async def _select_demo_user(db: AsyncSession) -> Optional[User]:
    result = await db.execute(select(User).where(User.username == DEMO_USERNAME))
    return result.scalar_one_or_none()


async def ensure_demo_user(db: AsyncSession) -> User:
    """
    Return the demo user, creating it if missing. Concurrency-safe: if another
    request inserts it first, the UNIQUE violation is rolled back and the row re-read.
    Called once at startup (main.lifespan) and as a fallback from get_current_user.
    """
    user = await _select_demo_user(db)
    if user is not None:
        return user

    db.add(
        User(
            id=str(uuid.uuid4()),
            username=DEMO_USERNAME,
            email="demo@securereflex.ai",
            hashed_password="!",  # not a usable password hash; login is not implemented
        )
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
    user = await _select_demo_user(db)
    if user is None:  # pragma: no cover - the insert either succeeded or lost the race to an identical row
        raise RuntimeError("Demo user could not be created")
    return user


# There is no authentication yet (see README): every request acts as one demo user.
async def get_current_user(db: AsyncSession = Depends(get_db)) -> User:
    """The demo user (seeded at startup; re-created safely if it was removed)."""
    return await ensure_demo_user(db)


@router.post("", response_model=EvaluationDetailResponse, status_code=201)
async def create_evaluation(
    request: CreateEvaluationRequest,
    http_request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create an evaluation and start the reflexion workflow (t0 -> t1 -> ... -> tN) in the background.
    The effective provider is resolved now; a demo fallback is recorded in ai_config.fallback_reason.
    """
    service = EvaluationService(db)
    provider_info = get_provider(request.ai_provider, request.ai_model)
    evaluation = await service.create_evaluation(current_user.id, request, provider_info)

    # Only the id is passed: the request session is closed before background tasks run.
    background_tasks.add_task(
        EvaluationService.run_evaluation,
        evaluation.id,
        getattr(http_request.state, "request_id", None),
    )
    return await service.get_evaluation_detail(evaluation.id)


@router.get("", response_model=EvaluationListResponse)
async def list_evaluations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[EvaluationStatusEnum] = None,
    language: Optional[ProgrammingLanguageEnum] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List evaluations (newest first) with pagination and filters"""
    return await EvaluationService(db).list_evaluations(
        current_user.id,
        page,
        page_size,
        status=status.value if status else None,
        language=language.value if language else None,
    )


@router.get("/{evaluation_id}", response_model=EvaluationDetailResponse)
async def get_evaluation(
    evaluation_id: str = Path(..., max_length=64),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Detailed evaluation: every code version with findings, diff, explanation and metrics"""
    detail = await EvaluationService(db).get_evaluation_detail(evaluation_id, current_user.id)
    if detail is None:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    return detail


@router.get("/{evaluation_id}/code/{version}", response_model=CodeVersionResponse)
async def get_code_version(
    evaluation_id: str = Path(..., max_length=64),
    version: str = Path(..., pattern=VERSION_PATTERN),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """A single code version (t0, t1, ...)"""
    code_version = await EvaluationService(db).get_code_version(evaluation_id, version, current_user.id)
    if code_version is None:
        raise HTTPException(status_code=404, detail="Code version not found")
    return code_version


@router.post("/{evaluation_id}/cancel", response_model=EvaluationActionResponse)
async def cancel_evaluation(
    evaluation_id: str = Path(..., max_length=64),
    request: Optional[CancelEvaluationRequest] = Body(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel a pending or running evaluation (the run stops before its next round)"""
    cancelled = await EvaluationService(db).cancel_evaluation(
        evaluation_id, current_user.id, request.reason if request else None
    )
    if cancelled is None:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    if not cancelled:
        raise HTTPException(status_code=409, detail="Evaluation has already finished and cannot be cancelled")
    return EvaluationActionResponse(
        message="Evaluation cancelled", evaluation_id=evaluation_id, status=EvaluationStatusEnum.CANCELLED.value
    )


@router.delete("/{evaluation_id}", response_model=EvaluationActionResponse)
async def delete_evaluation(
    evaluation_id: str = Path(..., max_length=64),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an evaluation and all associated data"""
    if not await EvaluationService(db).delete_evaluation(evaluation_id, current_user.id):
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    return EvaluationActionResponse(message="Evaluation deleted", evaluation_id=evaluation_id)
