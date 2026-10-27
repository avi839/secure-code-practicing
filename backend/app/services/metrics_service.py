"""
Reflexion metrics (pure functions).

Cohort formulas relative to the baseline t0, with binary labels
(1 = insecure, 0 = secure):

    Repair@t     = #(y0=1 and yt=0) / #(y0=1) * 100
    Regression@t = #(y0=0 and yt=1) / #(y0=0) * 100
    NetGain@t    = Repair@t - Regression@t

A zero denominator yields 0.0 with the matching *_defined flag set to False.
"""

from collections import Counter
from dataclasses import asdict, dataclass
from typing import Dict, Iterable, List, Optional, Sequence

SEVERITY_KEYS = ("CRITICAL", "HIGH", "MEDIUM", "LOW")


@dataclass
class RoundMetrics:
    round: int
    repair_rate: float
    regression_rate: float
    net_gain: float
    repair_defined: bool
    regression_defined: bool
    n_insecure_t0: int
    n_secure_t0: int
    n_samples: int

    def to_dict(self) -> dict:
        return asdict(self)


def _validate_labels(labels: Sequence[int]) -> None:
    for label in labels:
        if label not in (0, 1):
            raise ValueError(f"labels must be 0 or 1, got {label!r}")


def repair_regression(labels_t0: Sequence[int], labels_t: Sequence[int], round_no: int) -> RoundMetrics:
    labels_t0 = list(labels_t0)
    labels_t = list(labels_t)
    if len(labels_t0) != len(labels_t):
        raise ValueError("labels_t0 and labels_t must have the same length")
    _validate_labels(labels_t0)
    _validate_labels(labels_t)

    n_insecure = sum(1 for y0 in labels_t0 if y0 == 1)
    n_secure = len(labels_t0) - n_insecure
    repaired = sum(1 for y0, yt in zip(labels_t0, labels_t) if y0 == 1 and yt == 0)
    regressed = sum(1 for y0, yt in zip(labels_t0, labels_t) if y0 == 0 and yt == 1)

    repair_defined = n_insecure > 0
    regression_defined = n_secure > 0
    repair = round(repaired / n_insecure * 100, 2) if repair_defined else 0.0
    regression = round(regressed / n_secure * 100, 2) if regression_defined else 0.0

    return RoundMetrics(
        round=round_no,
        repair_rate=repair,
        regression_rate=regression,
        net_gain=round(repair - regression, 2),
        repair_defined=repair_defined,
        regression_defined=regression_defined,
        n_insecure_t0=n_insecure,
        n_secure_t0=n_secure,
        n_samples=len(labels_t0),
    )


def reflexion_curve(label_rows: Sequence[Sequence[int]], max_round: Optional[int] = None) -> List[RoundMetrics]:
    """
    One row per sample: [y0, y1, ..., yk]. Rows shorter than the longest row
    carry their last label forward (an evaluation that stopped early stays at
    its final label). Returns metrics for rounds 1..max_round.
    """
    rows = [list(row) for row in label_rows if len(row) > 0]
    if not rows:
        return []
    if max_round is None:
        max_round = max(len(row) for row in rows) - 1
    if max_round < 1:
        return []

    labels_t0 = [row[0] for row in rows]
    curve = []
    for k in range(1, max_round + 1):
        labels_k = [row[k] if k < len(row) else row[-1] for row in rows]
        curve.append(repair_regression(labels_t0, labels_k, k))
    return curve


def secure_rate(labels: Iterable[int]) -> float:
    labels = list(labels)
    if not labels:
        return 0.0
    return round(sum(1 for y in labels if y == 0) / len(labels) * 100, 2)


def _get(item, name: str):
    return item.get(name) if isinstance(item, dict) else getattr(item, name, None)


def severity_counts(findings: Iterable) -> Dict[str, int]:
    counts = {key: 0 for key in SEVERITY_KEYS}
    for finding in findings:
        severity = str(_get(finding, "severity") or "").upper()
        if severity in counts:
            counts[severity] += 1
    return counts


def _summary(finding) -> dict:
    return {
        "rule_id": _get(finding, "rule_id"),
        "cwe_id": _get(finding, "cwe_id"),
        "title": _get(finding, "title"),
        "severity": _get(finding, "severity"),
    }


def compare_findings(prev: Iterable, curr: Iterable) -> Dict[str, List[dict]]:
    """
    Multiset comparison keyed on (cwe_id, rule_id), ignoring line numbers so
    that code moving up or down does not count as fixed + new.
    """
    prev = list(prev)
    curr = list(curr)
    remaining = Counter((_get(f, "cwe_id"), _get(f, "rule_id")) for f in curr)

    fixed: List[dict] = []
    unresolved: List[dict] = []
    for finding in prev:
        key = (_get(finding, "cwe_id"), _get(finding, "rule_id"))
        if remaining[key] > 0:
            remaining[key] -= 1
            unresolved.append(_summary(finding))
        else:
            fixed.append(_summary(finding))

    matched = Counter((_get(f, "cwe_id"), _get(f, "rule_id")) for f in prev)
    new: List[dict] = []
    for finding in curr:
        key = (_get(finding, "cwe_id"), _get(finding, "rule_id"))
        if matched[key] > 0:
            matched[key] -= 1
        else:
            new.append(_summary(finding))

    return {"fixed": fixed, "new": new, "unresolved": unresolved}
