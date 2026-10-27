"""
Evaluation service: persistence, orchestration and serialisation of reflexion runs.

The reflexion loop itself lives in services/reflexion.py (pure, no DB). This module
creates the evaluation row, runs the engine in a background task with its OWN
session (decision D11: the request session is closed before background tasks run),
commits after every round so the UI can poll progress, and writes the t0-relative
metric snapshots and summary fields at the end.

Async rule: ORM relationship attributes are never touched here; children are always
queried (and deleted) explicitly (decision D17).
"""

import importlib.metadata
import logging
import time
import uuid
from collections import Counter
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.logging_config import request_id_var
from app.models import (
    CodeVersion,
    Evaluation,
    MetricSnapshot,
    ReflectionAttempt,
    ScanResult,
    SecurityFinding,
)
from app.models.evaluation import (
    CodeValidationStatus,
    EvaluationStatus,
    ProgrammingLanguage,
    SecurityLabel,
)
from app.schemas.evaluation import (
    CodeVersionResponse,
    CreateEvaluationRequest,
    EvaluationDetailResponse,
    EvaluationListResponse,
    EvaluationSummaryResponse,
    FindingComparison,
    RoundMetricResponse,
    SecurityFindingResponse,
)
from app.schemas.scan import cwe_url
from app.services.metrics_service import compare_findings, repair_regression
from app.services.providers import AIProvider, ProviderError, get_provider
from app.services.reflexion import ReflexionEngine, RoundResult
from app.services.scanner import SEVERITY_ORDER, ScannerService, ScanReport
from app.services.scanner.bandit_runner import SKIPPED_TESTS

logger = logging.getLogger(__name__)

MAX_REFLEXION_ROUNDS = 10
ACTIVE_STATUSES = (EvaluationStatus.PENDING, EvaluationStatus.RUNNING)
# ai_config keys written by the service (user-provided keys with these names are overridden)
PRIVATE_CONFIG_KEYS = ("user_code",)
EMPTY_SEVERITY_COUNTS = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}


def _utcnow() -> datetime:
    return datetime.utcnow()


def _utc(value: Optional[datetime]) -> Optional[datetime]:
    """DB timestamps are naive UTC; mark them so the JSON carries an explicit 'Z'."""
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _enum_value(value) -> Optional[str]:
    return getattr(value, "value", value)


def _label_int(value) -> Optional[int]:
    return None if value is None else int(value)


def _version_round(version: str) -> int:
    try:
        return int(str(version).lstrip("t"))
    except ValueError:
        return 0


def _analyzer_version(analyzer: str) -> Optional[str]:
    if analyzer == "bandit":
        try:
            return importlib.metadata.version("bandit")
        except importlib.metadata.PackageNotFoundError:
            return None
    return "builtin-1"


class _TimedScanner(ScannerService):
    """ScannerService that remembers the wall-clock window of its last scan (for ScanResult rows)."""

    def __init__(self):
        super().__init__()
        self.last_window: Optional[Tuple[datetime, datetime, float]] = None

    def scan(self, code: str, language: str) -> ScanReport:
        started_at = _utcnow()
        started = time.perf_counter()
        report = super().scan(code, language)
        self.last_window = (started_at, _utcnow(), round(time.perf_counter() - started, 4))
        return report


def _finding_statuses(previous: Optional[RoundResult], current: RoundResult) -> List[str]:
    """Per-finding status vs the previous version, using the same (cwe_id, rule_id) multiset as compare_findings."""
    if previous is None:
        return ["open"] * len(current.report.findings)
    remaining = Counter((f.cwe_id, f.rule_id) for f in previous.report.findings)
    statuses = []
    for finding in current.report.findings:
        key = (finding.cwe_id, finding.rule_id)
        if remaining[key] > 0:
            remaining[key] -= 1
            statuses.append("unresolved")
        else:
            statuses.append("newly_introduced")
    return statuses


class EvaluationService:
    """Service for managing code generation evaluations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------ create
    async def create_evaluation(
        self,
        user_id: str,
        req: CreateEvaluationRequest,
        provider_info: Tuple[AIProvider, Optional[str]],
    ) -> Evaluation:
        """Store the evaluation with the EFFECTIVE provider and the fallback reason (decision D14)."""
        provider, fallback_reason = provider_info
        ai_config = {
            **req.ai_config,
            "requested_provider": req.ai_provider.value,
            "fallback_reason": fallback_reason,
            "source": "user_code" if req.code else "generated",
            "user_code": req.code,
        }
        evaluation = Evaluation(
            id=str(uuid.uuid4()),
            user_id=user_id,
            task=req.task,
            language=ProgrammingLanguage(req.language.value),
            ai_provider=provider.name,
            ai_model=provider.model,
            ai_config=ai_config,
            max_rounds=MAX_REFLEXION_ROUNDS,
            requested_rounds=req.reflexion_rounds,
            completed_rounds=0,
            status=EvaluationStatus.PENDING,
        )
        self.db.add(evaluation)
        await self.db.commit()
        return evaluation

    # --------------------------------------------------------------------- run
    @staticmethod
    async def run_evaluation(evaluation_id: str, request_id: Optional[str] = None) -> None:
        """
        Background task. Opens its own session, persists every round as it completes
        and never raises (failures are recorded on the evaluation).
        """
        token = request_id_var.set(request_id or "-")
        try:
            async with AsyncSessionLocal() as db:
                await EvaluationService._run(db, evaluation_id, request_id)
        finally:
            request_id_var.reset(token)

    @staticmethod
    async def _current_status(db: AsyncSession, evaluation_id: str) -> Optional[EvaluationStatus]:
        result = await db.execute(select(Evaluation.status).where(Evaluation.id == evaluation_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def _run(db: AsyncSession, evaluation_id: str, request_id: Optional[str]) -> None:
        evaluation = await db.get(Evaluation, evaluation_id)
        if evaluation is None or evaluation.status != EvaluationStatus.PENDING:
            return

        started_at = _utcnow()
        evaluation.status = EvaluationStatus.RUNNING
        evaluation.started_at = started_at
        await db.commit()

        task = evaluation.task
        language = _enum_value(evaluation.language)
        config = dict(evaluation.ai_config or {})
        rounds = int(evaluation.requested_rounds or 1)

        try:
            provider, fallback_reason = get_provider(evaluation.ai_provider, evaluation.ai_model)
            if fallback_reason and evaluation.ai_provider != "demo":
                # The provider chosen at creation time is no longer usable; never fall back silently mid-run.
                raise ProviderError(f"Provider '{evaluation.ai_provider}' is no longer available: {fallback_reason}")

            scanner = _TimedScanner()
            engine = ReflexionEngine(provider, scanner)
            persisted: List[RoundResult] = []
            state: Dict[str, object] = {"previous": None, "tokens": 0, "cancelled": False}

            async def persist(result: RoundResult) -> bool:
                status = await EvaluationService._current_status(db, evaluation_id)
                if status != EvaluationStatus.RUNNING:
                    state["cancelled"] = True
                    return False

                previous: Optional[RoundResult] = state["previous"]  # type: ignore[assignment]
                EvaluationService._add_version_rows(db, evaluation_id, result, previous, scanner)
                state["tokens"] = int(state["tokens"]) + int(result.tokens_used or 0)
                evaluation.completed_rounds = result.round_number
                evaluation.total_tokens_used = state["tokens"]
                await db.commit()
                state["previous"] = result
                persisted.append(result)

                # Re-read the status before the next (possibly slow, paid) provider call.
                if await EvaluationService._current_status(db, evaluation_id) != EvaluationStatus.RUNNING:
                    state["cancelled"] = True
                    return False
                return True

            await engine.run(task, language, config.get("user_code"), rounds, on_round=persist)

            final_status = await EvaluationService._current_status(db, evaluation_id)
            if final_status is None:  # deleted while running
                return
            if not persisted:
                return

            EvaluationService._add_metric_rows(db, evaluation_id, persisted)
            t0, final = persisted[0], persisted[-1]
            versus_t0 = compare_findings(t0.report.findings, final.report.findings)
            completed_at = _utcnow()
            evaluation.baseline_secure = t0.report.label == 0
            evaluation.final_secure = final.report.label == 0
            evaluation.total_findings_t0 = len(t0.report.findings)
            evaluation.total_findings_final = len(final.report.findings)
            evaluation.findings_fixed = len(versus_t0["fixed"])
            evaluation.findings_new = len(versus_t0["new"])
            evaluation.total_tokens_used = int(state["tokens"])
            evaluation.ai_config = {**config, "stopped_early": engine.stopped_early}
            evaluation.completed_at = completed_at
            evaluation.total_duration_seconds = round((completed_at - started_at).total_seconds(), 3)
            if final_status == EvaluationStatus.RUNNING:
                evaluation.status = EvaluationStatus.COMPLETED
            await db.commit()
            logger.info(
                "evaluation=%s completed rounds=%s findings_t0=%s findings_final=%s",
                evaluation_id, final.round_number, evaluation.total_findings_t0, evaluation.total_findings_final,
            )
        except ProviderError as exc:
            logger.warning("evaluation=%s failed: provider error", evaluation_id)
            await EvaluationService._mark_failed(db, evaluation_id, str(exc), started_at)
        except Exception:
            logger.exception("evaluation=%s failed with an internal error", evaluation_id)
            message = f"Evaluation failed due to an internal error (request id {request_id or 'n/a'})"
            await EvaluationService._mark_failed(db, evaluation_id, message, started_at)

    @staticmethod
    async def _mark_failed(db: AsyncSession, evaluation_id: str, message: str, started_at: datetime) -> None:
        completed_at = _utcnow()
        try:
            await db.rollback()
            await db.execute(
                update(Evaluation)
                .where(Evaluation.id == evaluation_id, Evaluation.status.in_(ACTIVE_STATUSES))
                .values(
                    status=EvaluationStatus.FAILED,
                    error_message=message,
                    completed_at=completed_at,
                    total_duration_seconds=round((completed_at - started_at).total_seconds(), 3),
                    updated_at=completed_at,
                )
                .execution_options(synchronize_session=False)
            )
            await db.commit()
        except Exception:
            logger.exception("evaluation=%s could not be marked as failed", evaluation_id)

    @staticmethod
    def _add_version_rows(db: AsyncSession, evaluation_id: str, result: RoundResult,
                          previous: Optional[RoundResult], scanner: _TimedScanner) -> None:
        report = result.report
        version_id = str(uuid.uuid4())
        db.add(
            CodeVersion(
                id=version_id,
                evaluation_id=evaluation_id,
                version=result.version,
                round_number=result.round_number,
                code=result.code,
                raw_response=result.raw_response or "",
                prompt_used=result.prompt or "",
                validation_status=(
                    CodeValidationStatus.COMPLETE_CODE if result.code.strip() else CodeValidationStatus.NOT_VALIDATED
                ),
                is_valid_code=bool(result.code.strip()),
                security_label=SecurityLabel(report.label),
                scan_completed=True,
                scan_error="; ".join(report.errors) or None,
                generation_time_seconds=result.generation_time_seconds,
                tokens_used=result.tokens_used,
                diff=result.diff or None,
                explanation=result.explanation,
                severity_counts=dict(report.severity_counts),
                comparison=result.comparison,
            )
        )

        for finding, status in zip(report.findings, _finding_statuses(previous, result)):
            db.add(
                SecurityFinding(
                    id=str(uuid.uuid4()),
                    code_version_id=version_id,
                    analyzer=finding.analyzer,
                    rule_id=finding.rule_id,
                    cwe_id=finding.cwe_id,
                    cwe_name=finding.cwe_name,
                    severity=finding.severity,
                    confidence=finding.confidence,
                    title=finding.title,
                    description=finding.description,
                    remediation=finding.remediation,
                    start_line=finding.start_line,
                    end_line=finding.end_line,
                    code_snippet=finding.code_snippet,
                    status=status,
                    raw_finding={"corroborated_by": list(finding.corroborated_by)},
                )
            )

        now = _utcnow()
        started_at, completed_at, duration = scanner.last_window or (now, now, 0.0)
        for analyzer in report.analyzers_run:
            errors = [e for e in report.errors if e.lower().startswith(analyzer)]
            matched = [
                f for f in report.findings
                if f.analyzer == analyzer or any(tag.startswith(f"{analyzer}:") for tag in f.corroborated_by)
            ]
            db.add(
                ScanResult(
                    id=str(uuid.uuid4()),
                    code_version_id=version_id,
                    analyzer=analyzer,
                    analyzer_version=_analyzer_version(analyzer),
                    scan_started_at=started_at,
                    scan_completed_at=completed_at,
                    scan_duration_seconds=duration,  # combined scan window (analyzers run back to back)
                    success=not errors,
                    error_message="; ".join(errors) or None,
                    findings_count=len(matched),
                    raw_output={"rule_ids": [f.rule_id for f in matched]},
                    config_used={"skipped_tests": SKIPPED_TESTS} if analyzer == "bandit" else None,
                )
            )

        if result.round_number >= 1 and previous is not None:
            db.add(
                ReflectionAttempt(
                    id=str(uuid.uuid4()),
                    evaluation_id=evaluation_id,
                    round_number=result.round_number,
                    previous_version=previous.version,
                    new_version=result.version,
                    reflection_prompt=result.prompt or "",
                    reflection_buffer=[
                        {"version": previous.version, "findings_count": previous.findings_count},
                        {"version": result.version, "findings_count": result.findings_count},
                    ],
                    previous_findings=[f.to_dict() for f in previous.report.findings],
                    cwe_hints=sorted({f.cwe_id for f in previous.report.findings if f.cwe_id}),
                    model_response=result.raw_response or "",
                    revised_code=result.code,
                    generation_time_seconds=result.generation_time_seconds,
                    tokens_used=result.tokens_used,
                    success=True,
                )
            )

    @staticmethod
    def _add_metric_rows(db: AsyncSession, evaluation_id: str, results: List[RoundResult]) -> None:
        t0 = results[0]
        y0 = t0.report.label
        for current in results[1:]:
            k = current.round_number
            yk = current.report.label
            metrics = repair_regression([y0], [yk], k)
            versus_t0 = compare_findings(t0.report.findings, current.report.findings)
            db.add(
                MetricSnapshot(
                    id=str(uuid.uuid4()),
                    evaluation_id=evaluation_id,
                    from_version="t0",
                    to_version=f"t{k}",
                    transition_name=f"t0_to_t{k}",
                    from_label=y0,
                    to_label=yk,
                    repair_rate=metrics.repair_rate,
                    regression_rate=metrics.regression_rate,
                    net_gain=metrics.net_gain,
                    is_repair=y0 == 1 and yk == 0,
                    is_regression=y0 == 0 and yk == 1,
                    is_unchanged_secure=y0 == 0 and yk == 0,
                    is_unchanged_insecure=y0 == 1 and yk == 1,
                    findings_fixed_count=len(versus_t0["fixed"]),
                    findings_new_count=len(versus_t0["new"]),
                    findings_unresolved_count=len(versus_t0["unresolved"]),
                    total_findings_from=len(t0.report.findings),
                    total_findings_to=len(current.report.findings),
                    fixed_findings=versus_t0["fixed"],
                    new_findings=versus_t0["new"],
                    unresolved_findings=versus_t0["unresolved"],
                )
            )

    # -------------------------------------------------------------------- read
    async def _get(self, evaluation_id: str, user_id: Optional[str] = None) -> Optional[Evaluation]:
        query = select(Evaluation).where(Evaluation.id == evaluation_id)
        if user_id is not None:
            query = query.where(Evaluation.user_id == user_id)
        return (await self.db.execute(query)).scalar_one_or_none()

    async def _findings_by_version(self, version_ids: List[str]) -> Dict[str, List[SecurityFinding]]:
        grouped: Dict[str, List[SecurityFinding]] = {vid: [] for vid in version_ids}
        if not version_ids:
            return grouped
        rows = (
            await self.db.execute(select(SecurityFinding).where(SecurityFinding.code_version_id.in_(version_ids)))
        ).scalars().all()
        for row in rows:
            grouped.setdefault(row.code_version_id, []).append(row)
        for items in grouped.values():
            items.sort(key=lambda f: (f.start_line or 0, -SEVERITY_ORDER.get(f.severity, 0), f.rule_id))
        return grouped

    @staticmethod
    def _finding_response(row: SecurityFinding) -> SecurityFindingResponse:
        raw = row.raw_finding or {}
        return SecurityFindingResponse(
            id=row.id,
            analyzer=row.analyzer,
            rule_id=row.rule_id,
            cwe_id=row.cwe_id,
            cwe_name=row.cwe_name,
            cwe_url=cwe_url(row.cwe_id),
            severity=row.severity,
            confidence=row.confidence,
            title=row.title,
            description=row.description,
            remediation=row.remediation,
            start_line=row.start_line,
            end_line=row.end_line,
            code_snippet=row.code_snippet,
            status=row.status or "open",
            corroborated_by=list(raw.get("corroborated_by") or []),
        )

    @staticmethod
    def _version_response(version: CodeVersion, findings: List[SecurityFinding]) -> CodeVersionResponse:
        label = _label_int(version.security_label)
        return CodeVersionResponse(
            id=version.id,
            version=version.version,
            round_number=version.round_number,
            code=version.code,
            security_label=label,
            is_secure=None if label is None else label == 0,
            findings_count=len(findings),
            severity_counts={**EMPTY_SEVERITY_COUNTS, **(version.severity_counts or {})},
            findings=[EvaluationService._finding_response(f) for f in findings],
            diff=version.diff,
            explanation=version.explanation,
            comparison=FindingComparison(**(version.comparison or {})),
            scan_error=version.scan_error,
            generation_time_seconds=version.generation_time_seconds,
            tokens_used=version.tokens_used,
            created_at=_utc(version.created_at),
        )

    @staticmethod
    def _public_config(config: Optional[dict]) -> dict:
        return {k: v for k, v in (config or {}).items() if k not in PRIVATE_CONFIG_KEYS}

    async def get_evaluation_detail(self, evaluation_id: str,
                                    user_id: Optional[str] = None) -> Optional[EvaluationDetailResponse]:
        evaluation = await self._get(evaluation_id, user_id)
        if evaluation is None:
            return None

        versions = (
            await self.db.execute(
                select(CodeVersion)
                .where(CodeVersion.evaluation_id == evaluation_id)
                .order_by(CodeVersion.round_number)
            )
        ).scalars().all()
        findings = await self._findings_by_version([v.id for v in versions])
        snapshots = (
            await self.db.execute(select(MetricSnapshot).where(MetricSnapshot.evaluation_id == evaluation_id))
        ).scalars().all()
        snapshots = sorted(snapshots, key=lambda s: _version_round(s.to_version))

        config = evaluation.ai_config or {}
        return EvaluationDetailResponse(
            id=evaluation.id,
            task=evaluation.task,
            language=_enum_value(evaluation.language),
            ai_provider=evaluation.ai_provider,
            ai_model=evaluation.ai_model,
            ai_config=self._public_config(config),
            is_demo=evaluation.ai_provider == "demo",
            status=_enum_value(evaluation.status),
            error_message=evaluation.error_message,
            requested_rounds=evaluation.requested_rounds or 0,
            completed_rounds=evaluation.completed_rounds or 0,
            stopped_early=bool(config.get("stopped_early", False)),
            baseline_secure=evaluation.baseline_secure,
            final_secure=evaluation.final_secure,
            total_findings_t0=evaluation.total_findings_t0 or 0,
            total_findings_final=evaluation.total_findings_final or 0,
            findings_fixed=evaluation.findings_fixed or 0,
            findings_new=evaluation.findings_new or 0,
            started_at=_utc(evaluation.started_at),
            completed_at=_utc(evaluation.completed_at),
            total_duration_seconds=evaluation.total_duration_seconds,
            total_tokens_used=evaluation.total_tokens_used or 0,
            created_at=_utc(evaluation.created_at),
            updated_at=_utc(evaluation.updated_at or evaluation.created_at),
            code_versions=[self._version_response(v, findings.get(v.id, [])) for v in versions],
            metrics=[
                RoundMetricResponse(
                    round=_version_round(s.to_version),
                    version=s.to_version,
                    repair_rate=s.repair_rate or 0.0,
                    regression_rate=s.regression_rate or 0.0,
                    net_gain=s.net_gain or 0.0,
                    # N = 1 per evaluation: only one of the two denominators is non-zero.
                    repair_defined=s.from_label == 1,
                    regression_defined=s.from_label == 0,
                    from_label=s.from_label,
                    to_label=s.to_label,
                )
                for s in snapshots
            ],
        )

    async def get_code_version(self, evaluation_id: str, version: str,
                               user_id: Optional[str] = None) -> Optional[CodeVersionResponse]:
        if await self._get(evaluation_id, user_id) is None:
            return None
        row = (
            await self.db.execute(
                select(CodeVersion).where(CodeVersion.evaluation_id == evaluation_id, CodeVersion.version == version)
            )
        ).scalar_one_or_none()
        if row is None:
            return None
        findings = await self._findings_by_version([row.id])
        return self._version_response(row, findings[row.id])

    @staticmethod
    def summary_response(evaluation: Evaluation) -> EvaluationSummaryResponse:
        return EvaluationSummaryResponse(
            id=evaluation.id,
            task=evaluation.task,
            language=_enum_value(evaluation.language),
            ai_provider=evaluation.ai_provider,
            ai_model=evaluation.ai_model,
            is_demo=evaluation.ai_provider == "demo",
            status=_enum_value(evaluation.status),
            requested_rounds=evaluation.requested_rounds or 0,
            completed_rounds=evaluation.completed_rounds or 0,
            baseline_secure=evaluation.baseline_secure,
            final_secure=evaluation.final_secure,
            total_findings_t0=evaluation.total_findings_t0 or 0,
            total_findings_final=evaluation.total_findings_final or 0,
            findings_fixed=evaluation.findings_fixed or 0,
            findings_new=evaluation.findings_new or 0,
            created_at=_utc(evaluation.created_at),
            completed_at=_utc(evaluation.completed_at),
            total_duration_seconds=evaluation.total_duration_seconds,
        )

    async def list_evaluations(self, user_id: str, page: int, page_size: int,
                               status: Optional[str] = None, language: Optional[str] = None) -> EvaluationListResponse:
        filters = [Evaluation.user_id == user_id]
        if status:
            filters.append(Evaluation.status == EvaluationStatus(status))
        if language:
            filters.append(Evaluation.language == ProgrammingLanguage(language))

        total = (await self.db.execute(select(func.count(Evaluation.id)).where(*filters))).scalar() or 0
        rows = (
            await self.db.execute(
                select(Evaluation)
                .where(*filters)
                .order_by(Evaluation.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).scalars().all()
        return EvaluationListResponse(
            total=total, page=page, page_size=page_size, items=[self.summary_response(e) for e in rows]
        )

    # ----------------------------------------------------------- cancel/delete
    async def cancel_evaluation(self, evaluation_id: str, user_id: Optional[str] = None,
                                reason: Optional[str] = None) -> Optional[bool]:
        """None = not found, False = not cancellable (already finished), True = cancelled."""
        evaluation = await self._get(evaluation_id, user_id)
        if evaluation is None:
            return None
        now = _utcnow()
        result = await self.db.execute(
            update(Evaluation)
            .where(Evaluation.id == evaluation_id, Evaluation.status.in_(ACTIVE_STATUSES))
            .values(
                status=EvaluationStatus.CANCELLED,
                error_message=reason or "Cancelled by user",
                completed_at=now,
                updated_at=now,
            )
            .execution_options(synchronize_session=False)
        )
        await self.db.commit()
        return result.rowcount > 0

    async def delete_evaluation(self, evaluation_id: str, user_id: Optional[str] = None) -> bool:
        """Delete children with explicit statements (no ORM cascade in async code, decision D17)."""
        if await self._get(evaluation_id, user_id) is None:
            return False
        version_ids = select(CodeVersion.id).where(CodeVersion.evaluation_id == evaluation_id)
        statements = [
            delete(SecurityFinding).where(SecurityFinding.code_version_id.in_(version_ids)),
            delete(ScanResult).where(ScanResult.code_version_id.in_(version_ids)),
            delete(CodeVersion).where(CodeVersion.evaluation_id == evaluation_id),
            delete(ReflectionAttempt).where(ReflectionAttempt.evaluation_id == evaluation_id),
            delete(MetricSnapshot).where(MetricSnapshot.evaluation_id == evaluation_id),
            delete(Evaluation).where(Evaluation.id == evaluation_id),
        ]
        for statement in statements:
            await self.db.execute(statement.execution_options(synchronize_session=False))
        await self.db.commit()
        return True
