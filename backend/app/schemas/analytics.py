"""
Pydantic schemas for analytics endpoints
"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel


class CWECount(BaseModel):
    """Occurrence count of a CWE across all findings (legacy dashboard field)"""
    cwe_id: str
    cwe_name: str
    count: int


class MetricsFlags(BaseModel):
    """False when the matching denominator is zero (the rate is then reported as 0.0)"""
    repair_defined: bool
    regression_defined: bool


class ReflexionCurvePoint(BaseModel):
    """Cohort metrics at round k relative to t0 (round 0 = the baseline itself)"""
    round: int
    version: str
    repair_rate: float
    regression_rate: float
    net_gain: float
    secure_rate: float
    repair_defined: bool
    regression_defined: bool


class SeverityDistributionItem(BaseModel):
    severity: str
    t0: int
    final: int


class SeverityByRoundItem(BaseModel):
    round: int
    version: str
    CRITICAL: int
    HIGH: int
    MEDIUM: int
    LOW: int


class CWEBreakdownItem(BaseModel):
    """found = fixed + remaining (found includes issues introduced after t0 that remain)"""
    cwe_id: str
    cwe_name: str
    found: int
    fixed: int
    remaining: int


class RecentEvaluation(BaseModel):
    id: str
    task: str
    language: str
    ai_provider: str
    status: str
    created_at: datetime
    total_findings_t0: int
    total_findings_final: int
    final_secure: Optional[bool]


class DashboardStatsResponse(BaseModel):
    """Overall dashboard statistics (aggregated over completed evaluations)"""
    total_evaluations: int
    completed_evaluations: int
    total_code_versions: int
    total_security_findings: int
    baseline_secure_rate: float  # Percentage
    final_secure_rate: float  # Percentage
    average_repair_rate: float  # Percentage (last reflexion_curve point)
    average_regression_rate: float  # Percentage
    average_net_gain: float  # Percentage points
    metrics_flags: MetricsFlags
    reflexion_curve: List[ReflexionCurvePoint]
    severity_distribution: List[SeverityDistributionItem]
    severity_by_round: List[SeverityByRoundItem]
    cwe_breakdown: List[CWEBreakdownItem]
    most_common_cwes: List[CWECount]
    evaluations_by_language: Dict[str, int]  # {language: count}
    evaluations_by_status: Dict[str, int]  # {status: count}
    recent_evaluations: List[RecentEvaluation]


class LanguagePerformanceResponse(BaseModel):
    """Security performance by programming language"""
    language: str
    total_evaluations: int
    baseline_secure_rate: float
    final_secure_rate: float
    average_improvement: float
    total_findings_baseline: int
    total_findings_final: int


class CWEPerformanceResponse(BaseModel):
    """Repair performance by CWE category (t0 vs final version of completed evaluations)"""
    cwe_id: str
    cwe_name: str
    evaluations: int  # completed evaluations in which the CWE appeared
    found: int
    fixed: int
    remaining: int
    fix_rate: float  # fixed / found * 100


class ModelComparisonResponse(BaseModel):
    """Comparison across AI models"""
    ai_model: str
    ai_provider: str
    total_evaluations: int
    baseline_secure_rate: float
    t1_secure_rate: float
    t2_secure_rate: float
    t3_secure_rate: float
    average_improvement: float
    average_tokens_used: int
    average_cost_usd: float


class ReflectionRoundMetrics(BaseModel):
    """Metrics for a specific reflexion round"""
    round_number: int
    version: str  # t1, t2, t3
    secure_rate: float
    repair_rate: float
    regression_rate: float
    net_gain: float
    total_samples: int


class TimeSeriesDataPoint(BaseModel):
    """Single data point for time series"""
    date: str
    value: float
    label: str


class AnalyticsFilterRequest(BaseModel):
    """Filters for analytics queries"""
    language: Optional[str] = None
    cwe_id: Optional[str] = None
    ai_provider: Optional[str] = None
    ai_model: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    min_rounds: Optional[int] = None
