"""
Analytics endpoints - thin wrappers around services/analytics_service.py
"""

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.analytics import CWEPerformanceResponse, DashboardStatsResponse, LanguagePerformanceResponse
from app.services import analytics_service

router = APIRouter()


@router.get("/dashboard", response_model=DashboardStatsResponse)
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    """Dashboard KPIs, reflexion curve (Repair@t / Regression@t / NetGain@t vs t0) and breakdowns"""
    return await analytics_service.dashboard(db)


@router.get("/by-language", response_model=List[LanguagePerformanceResponse])
async def get_language_performance(db: AsyncSession = Depends(get_db)):
    """Secure rates (t0 vs final) per programming language over completed evaluations"""
    return await analytics_service.by_language(db)


@router.get("/by-cwe", response_model=List[CWEPerformanceResponse])
async def get_cwe_performance(db: AsyncSession = Depends(get_db)):
    """Found / fixed / remaining findings and fix rate per CWE (t0 vs final version)"""
    return await analytics_service.by_cwe(db)
