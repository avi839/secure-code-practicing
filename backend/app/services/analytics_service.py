"""
Dashboard analytics over completed evaluations.

All aggregates are computed from a fixed number of queries (no per-evaluation
queries). Reflexion metrics use metrics_service.reflexion_curve: every completed
evaluation is one sample, and an evaluation that stopped early carries its last
label (and severity counts) forward to later rounds.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CodeVersion, Evaluation, SecurityFinding
from app.models.evaluation import EvaluationStatus
from app.schemas.analytics import (
    CWEBreakdownItem,
    CWECount,
    CWEPerformanceResponse,
    DashboardStatsResponse,
    LanguagePerformanceResponse,
    MetricsFlags,
    RecentEvaluation,
    ReflexionCurvePoint,
    SeverityByRoundItem,
    SeverityDistributionItem,
)
from app.services.evaluation_service import _utc
from app.services.metrics_service import (
    SEVERITY_KEYS,
    compare_findings,
    reflexion_curve,
    repair_regression,
    secure_rate,
)

RECENT_LIMIT = 10
MOST_COMMON_LIMIT = 10


def _value(item) -> str:
    return str(getattr(item, "value", item))


@dataclass
class _Sample:
    """One completed evaluation with its versions ordered by round."""
    evaluation: Evaluation
    labels: List[int] = field(default_factory=list)
    severity: List[Dict[str, int]] = field(default_factory=list)
    t0_version_id: Optional[str] = None
    final_version_id: Optional[str] = None


async def _load_samples(db: AsyncSession) -> List[_Sample]:
    """Completed evaluations + their version labels/severity counts (2 queries)."""
    evaluations = (
        await db.execute(
            select(Evaluation)
            .where(Evaluation.status == EvaluationStatus.COMPLETED)
            .order_by(Evaluation.created_at)
        )
    ).scalars().all()
    if not evaluations:
        return []

    samples = {e.id: _Sample(evaluation=e) for e in evaluations}
    rows = (
        await db.execute(
            select(
                CodeVersion.id,
                CodeVersion.evaluation_id,
                CodeVersion.round_number,
                CodeVersion.security_label,
                CodeVersion.severity_counts,
            )
            .where(CodeVersion.evaluation_id.in_(list(samples)))
            .order_by(CodeVersion.evaluation_id, CodeVersion.round_number)
        )
    ).all()
    for row in rows:
        sample = samples[row.evaluation_id]
        if row.security_label is None:
            continue
        sample.labels.append(int(row.security_label))
        sample.severity.append({k: int((row.severity_counts or {}).get(k, 0)) for k in SEVERITY_KEYS})
        if sample.t0_version_id is None:
            sample.t0_version_id = row.id
        sample.final_version_id = row.id
    return [s for s in samples.values() if s.labels]


async def _endpoint_findings(db: AsyncSession, samples: List[_Sample]) -> Dict[str, List[SecurityFinding]]:
    """Findings of every t0 and final version (1 query)."""
    version_ids = {s.t0_version_id for s in samples} | {s.final_version_id for s in samples}
    version_ids.discard(None)
    grouped: Dict[str, List[SecurityFinding]] = defaultdict(list)
    if not version_ids:
        return grouped
    rows = (
        await db.execute(select(SecurityFinding).where(SecurityFinding.code_version_id.in_(list(version_ids))))
    ).scalars().all()
    for row in rows:
        grouped[row.code_version_id].append(row)
    return grouped


def _cwe_stats(samples: List[_Sample], findings: Dict[str, List[SecurityFinding]]) -> List[dict]:
    """
    Per CWE across completed evaluations, t0 vs final version:
    fixed = t0 findings no longer present, remaining = findings in the final version,
    found = fixed + remaining.
    """
    stats: Dict[str, dict] = {}

    def entry(cwe_id: str, cwe_name: Optional[str]) -> dict:
        item = stats.setdefault(
            cwe_id, {"cwe_id": cwe_id, "cwe_name": cwe_name or "Unknown", "fixed": 0, "remaining": 0, "evals": set()}
        )
        if item["cwe_name"] == "Unknown" and cwe_name:
            item["cwe_name"] = cwe_name
        return item

    for sample in samples:
        t0 = findings.get(sample.t0_version_id, [])
        final = findings.get(sample.final_version_id, []) if sample.final_version_id != sample.t0_version_id else t0
        names = {f.cwe_id: f.cwe_name for f in t0 + final if f.cwe_id}
        comparison = compare_findings(t0, final)
        for item in comparison["fixed"]:
            if item["cwe_id"]:
                stat = entry(item["cwe_id"], names.get(item["cwe_id"]))
                stat["fixed"] += 1
                stat["evals"].add(sample.evaluation.id)
        for finding in final:
            if finding.cwe_id:
                stat = entry(finding.cwe_id, finding.cwe_name)
                stat["remaining"] += 1
                stat["evals"].add(sample.evaluation.id)

    result = []
    for item in stats.values():
        found = item["fixed"] + item["remaining"]
        result.append(
            {
                "cwe_id": item["cwe_id"],
                "cwe_name": item["cwe_name"],
                "evaluations": len(item["evals"]),
                "found": found,
                "fixed": item["fixed"],
                "remaining": item["remaining"],
                "fix_rate": round(item["fixed"] / found * 100, 2) if found else 0.0,
            }
        )
    return sorted(result, key=lambda r: (-r["found"], r["cwe_id"]))


def _carried(values: list, k: int):
    return values[k] if k < len(values) else values[-1]


def _curve(samples: List[_Sample]) -> List[ReflexionCurvePoint]:
    rows = [s.labels for s in samples]
    if not rows:
        return []
    labels_t0 = [row[0] for row in rows]
    baseline = repair_regression(labels_t0, labels_t0, 0)
    points = [
        ReflexionCurvePoint(
            round=0,
            version="t0",
            repair_rate=0.0,
            regression_rate=0.0,
            net_gain=0.0,
            secure_rate=secure_rate(labels_t0),
            repair_defined=baseline.repair_defined,
            regression_defined=baseline.regression_defined,
        )
    ]
    for metrics in reflexion_curve(rows):
        k = metrics.round
        points.append(
            ReflexionCurvePoint(
                round=k,
                version=f"t{k}",
                repair_rate=metrics.repair_rate,
                regression_rate=metrics.regression_rate,
                net_gain=metrics.net_gain,
                secure_rate=secure_rate(_carried(row, k) for row in rows),
                repair_defined=metrics.repair_defined,
                regression_defined=metrics.regression_defined,
            )
        )
    return points


def _severity_by_round(samples: List[_Sample]) -> List[SeverityByRoundItem]:
    if not samples:
        return []
    max_round = max(len(s.severity) for s in samples) - 1
    items = []
    for k in range(max_round + 1):
        totals = Counter()
        for sample in samples:
            totals.update(_carried(sample.severity, k))
        items.append(SeverityByRoundItem(round=k, version=f"t{k}", **{key: totals[key] for key in SEVERITY_KEYS}))
    return items


async def _count(db: AsyncSession, column) -> int:
    return int((await db.execute(select(func.count(column)))).scalar() or 0)


async def dashboard(db: AsyncSession) -> DashboardStatsResponse:
    total_evaluations = await _count(db, Evaluation.id)
    total_code_versions = await _count(db, CodeVersion.id)
    total_security_findings = await _count(db, SecurityFinding.id)

    samples = await _load_samples(db)
    findings = await _endpoint_findings(db, samples)

    curve = _curve(samples)
    last = curve[-1] if curve else None

    severity_t0 = Counter()
    severity_final = Counter()
    for sample in samples:
        severity_t0.update(sample.severity[0])
        severity_final.update(sample.severity[-1])

    cwe_rows = (
        await db.execute(
            select(SecurityFinding.cwe_id, func.max(SecurityFinding.cwe_name), func.count(SecurityFinding.id))
            .where(SecurityFinding.cwe_id.isnot(None))
            .group_by(SecurityFinding.cwe_id)
            .order_by(func.count(SecurityFinding.id).desc(), SecurityFinding.cwe_id)
            .limit(MOST_COMMON_LIMIT)
        )
    ).all()
    by_language = (
        await db.execute(select(Evaluation.language, func.count(Evaluation.id)).group_by(Evaluation.language))
    ).all()
    by_status = (
        await db.execute(select(Evaluation.status, func.count(Evaluation.id)).group_by(Evaluation.status))
    ).all()
    recent = (
        await db.execute(select(Evaluation).order_by(Evaluation.created_at.desc()).limit(RECENT_LIMIT))
    ).scalars().all()

    return DashboardStatsResponse(
        total_evaluations=total_evaluations,
        completed_evaluations=len(samples),
        total_code_versions=total_code_versions,
        total_security_findings=total_security_findings,
        baseline_secure_rate=secure_rate(s.labels[0] for s in samples),
        final_secure_rate=secure_rate(s.labels[-1] for s in samples),
        average_repair_rate=last.repair_rate if last else 0.0,
        average_regression_rate=last.regression_rate if last else 0.0,
        average_net_gain=last.net_gain if last else 0.0,
        metrics_flags=MetricsFlags(
            repair_defined=last.repair_defined if last else False,
            regression_defined=last.regression_defined if last else False,
        ),
        reflexion_curve=curve,
        severity_distribution=[
            SeverityDistributionItem(severity=key, t0=severity_t0[key], final=severity_final[key])
            for key in SEVERITY_KEYS
        ],
        severity_by_round=_severity_by_round(samples),
        cwe_breakdown=[
            CWEBreakdownItem(
                cwe_id=row["cwe_id"], cwe_name=row["cwe_name"],
                found=row["found"], fixed=row["fixed"], remaining=row["remaining"],
            )
            for row in _cwe_stats(samples, findings)
        ],
        most_common_cwes=[
            CWECount(cwe_id=cwe_id, cwe_name=cwe_name or "Unknown", count=count) for cwe_id, cwe_name, count in cwe_rows
        ],
        evaluations_by_language={_value(language): count for language, count in by_language},
        evaluations_by_status={_value(status): count for status, count in by_status},
        recent_evaluations=[
            RecentEvaluation(
                id=e.id,
                task=e.task,
                language=_value(e.language),
                ai_provider=e.ai_provider,
                status=_value(e.status),
                created_at=_utc(e.created_at),
                total_findings_t0=e.total_findings_t0 or 0,
                total_findings_final=e.total_findings_final or 0,
                final_secure=e.final_secure,
            )
            for e in recent
        ],
    )


async def by_language(db: AsyncSession) -> List[LanguagePerformanceResponse]:
    samples = await _load_samples(db)
    grouped: Dict[str, List[_Sample]] = defaultdict(list)
    for sample in samples:
        grouped[_value(sample.evaluation.language)].append(sample)

    result = []
    for language, items in grouped.items():
        baseline = secure_rate(s.labels[0] for s in items)
        final = secure_rate(s.labels[-1] for s in items)
        result.append(
            LanguagePerformanceResponse(
                language=language,
                total_evaluations=len(items),
                baseline_secure_rate=baseline,
                final_secure_rate=final,
                average_improvement=round(final - baseline, 2),
                total_findings_baseline=sum(s.evaluation.total_findings_t0 or 0 for s in items),
                total_findings_final=sum(s.evaluation.total_findings_final or 0 for s in items),
            )
        )
    return sorted(result, key=lambda r: (-r.total_evaluations, r.language))


async def by_cwe(db: AsyncSession) -> List[CWEPerformanceResponse]:
    samples = await _load_samples(db)
    findings = await _endpoint_findings(db, samples)
    return [CWEPerformanceResponse(**row) for row in _cwe_stats(samples, findings)]
