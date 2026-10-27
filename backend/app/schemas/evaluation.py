"""
Pydantic schemas for evaluation endpoints
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.config import settings


class ProgrammingLanguageEnum(str, Enum):
    """Supported programming languages"""
    C = "c"
    CPP = "cpp"
    CSHARP = "csharp"
    JAVA = "java"
    JAVASCRIPT = "javascript"
    PYTHON = "python"
    PHP = "php"
    RUST = "rust"


class AIProviderEnum(str, Enum):
    """AI providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    DEMO = "demo"


class EvaluationStatusEnum(str, Enum):
    """Evaluation status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


MAX_AI_CONFIG_KEYS = 20


# Request schemas
class CreateEvaluationRequest(BaseModel):
    """Request to create a new evaluation"""

    task: str = Field(
        ...,
        min_length=3,
        max_length=settings.MAX_TASK_CHARS,
        description="Programming task description",
    )
    language: ProgrammingLanguageEnum = Field(..., description="Target programming language")
    ai_provider: AIProviderEnum = Field(default=AIProviderEnum.DEMO, description="AI provider to use")
    ai_model: Optional[str] = Field(
        default=None,
        max_length=100,
        pattern=r"^[\w.\-:/]+$",
        description="Model identifier (defaults to the provider's configured model)",
    )
    reflexion_rounds: int = Field(
        default=settings.DEFAULT_REFLEXION_ROUNDS,
        ge=1,
        le=10,
        description="Number of reflexion rounds (1-10)",
    )
    code: Optional[str] = Field(
        default=None,
        max_length=settings.MAX_CODE_CHARS,
        description="Optional user-supplied code used as t0 instead of AI generation",
    )
    ai_config: Dict[str, Any] = Field(default_factory=dict, description="Additional model configuration")

    @field_validator("task", mode="before")
    @classmethod
    def _strip_task(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("code", mode="after")
    @classmethod
    def _blank_code_is_none(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not value.strip():
            return None
        return value

    @field_validator("ai_config", mode="after")
    @classmethod
    def _validate_ai_config(cls, value: Dict[str, Any]) -> Dict[str, Any]:
        if len(value) > MAX_AI_CONFIG_KEYS:
            raise ValueError(f"ai_config may contain at most {MAX_AI_CONFIG_KEYS} keys")
        for key, item in value.items():
            if not isinstance(key, str) or len(key) > 64:
                raise ValueError("ai_config keys must be strings of at most 64 characters")
            if item is not None and not isinstance(item, (str, int, float, bool)):
                raise ValueError("ai_config values must be scalars (string, number, boolean or null)")
            if isinstance(item, str) and len(item) > 500:
                raise ValueError("ai_config string values must be at most 500 characters")
        return value


class CancelEvaluationRequest(BaseModel):
    """Request to cancel an evaluation"""
    reason: Optional[str] = Field(None, max_length=500, description="Cancellation reason")


# Response schemas
class SecurityFindingResponse(BaseModel):
    """Persisted security finding of one code version"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    analyzer: str
    rule_id: str
    cwe_id: Optional[str]
    cwe_name: Optional[str]
    cwe_url: Optional[str]
    severity: str
    confidence: Optional[str]
    title: str
    description: str  # why it is vulnerable
    remediation: Optional[str]  # how to fix it
    start_line: Optional[int]
    end_line: Optional[int]
    code_snippet: Optional[str]
    status: str  # open (t0) | unresolved | newly_introduced
    corroborated_by: List[str] = []


class FindingSummary(BaseModel):
    """Compact finding reference used in version comparisons"""
    rule_id: Optional[str]
    cwe_id: Optional[str]
    title: Optional[str]
    severity: Optional[str]


class FindingComparison(BaseModel):
    """Findings fixed / introduced / still present compared with the previous version"""
    fixed: List[FindingSummary] = []
    new: List[FindingSummary] = []
    unresolved: List[FindingSummary] = []


class CodeVersionResponse(BaseModel):
    """Code version details"""
    id: str
    version: str  # t0, t1, t2, ...
    round_number: int
    code: str
    security_label: Optional[int]  # 0=secure, 1=insecure
    is_secure: Optional[bool]
    findings_count: int = 0
    severity_counts: Dict[str, int]
    findings: List[SecurityFindingResponse] = []
    diff: Optional[str]
    explanation: Optional[str]
    comparison: FindingComparison
    scan_error: Optional[str] = None
    generation_time_seconds: Optional[float]
    tokens_used: Optional[int]
    created_at: datetime


class RoundMetricResponse(BaseModel):
    """Repair@t / Regression@t / NetGain@t of version t relative to t0"""
    round: int
    version: str
    repair_rate: float
    regression_rate: float
    net_gain: float
    repair_defined: bool
    regression_defined: bool
    from_label: int  # label of t0
    to_label: int  # label of version t


class EvaluationSummaryResponse(BaseModel):
    """Summary response for evaluation list"""
    id: str
    task: str
    language: str
    ai_provider: str
    ai_model: str
    is_demo: bool
    status: str
    requested_rounds: int
    completed_rounds: int
    baseline_secure: Optional[bool]
    final_secure: Optional[bool]
    total_findings_t0: int
    total_findings_final: int
    findings_fixed: int
    findings_new: int
    created_at: datetime
    completed_at: Optional[datetime]
    total_duration_seconds: Optional[float]


class EvaluationDetailResponse(BaseModel):
    """Detailed evaluation response"""
    id: str
    task: str
    language: str
    ai_provider: str  # effective provider (demo when a fallback happened)
    ai_model: str
    ai_config: Dict[str, Any]  # never contains user_code
    is_demo: bool
    status: str
    error_message: Optional[str]
    requested_rounds: int
    completed_rounds: int
    stopped_early: bool
    baseline_secure: Optional[bool]
    final_secure: Optional[bool]
    total_findings_t0: int
    total_findings_final: int
    findings_fixed: int
    findings_new: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    total_duration_seconds: Optional[float]
    total_tokens_used: int
    created_at: datetime
    updated_at: datetime
    code_versions: List[CodeVersionResponse] = []
    metrics: List[RoundMetricResponse] = []


class EvaluationListResponse(BaseModel):
    """Paginated list of evaluations"""
    total: int
    page: int
    page_size: int
    items: List[EvaluationSummaryResponse]


class EvaluationActionResponse(BaseModel):
    """Result of cancel / delete"""
    message: str
    evaluation_id: str
    status: Optional[str] = None
