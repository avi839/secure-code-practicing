import pytest

from app.services.metrics_service import (
    compare_findings,
    reflexion_curve,
    repair_regression,
    secure_rate,
    severity_counts,
)


def test_mixed_cohort():
    m = repair_regression([1, 1, 0, 0], [0, 1, 0, 1], 1)
    assert (m.repair_rate, m.regression_rate, m.net_gain) == (50.0, 50.0, 0.0)
    assert m.repair_defined and m.regression_defined
    assert (m.n_insecure_t0, m.n_secure_t0, m.n_samples) == (2, 2, 4)


def test_all_insecure_repaired_regression_undefined():
    m = repair_regression([1, 1], [0, 0], 2)
    assert m.repair_rate == 100.0 and m.regression_rate == 0.0 and m.net_gain == 100.0
    assert m.repair_defined and not m.regression_defined


def test_regression_only():
    m = repair_regression([0], [1], 1)
    assert m.regression_rate == 100.0 and m.net_gain == -100.0
    assert not m.repair_defined and m.regression_defined


def test_empty_gives_zeros_and_undefined_flags():
    m = repair_regression([], [], 1)
    assert (m.repair_rate, m.regression_rate, m.net_gain) == (0.0, 0.0, 0.0)
    assert not m.repair_defined and not m.regression_defined


def test_single_evaluation_repaired():
    assert repair_regression([1], [0], 1).repair_rate == 100.0


def test_rounding_two_decimals():
    assert repair_regression([1, 1, 1], [0, 1, 1], 1).repair_rate == 33.33


@pytest.mark.parametrize("t0,t", [([1, 0], [1]), ([1], [2]), ([3], [0])])
def test_value_errors(t0, t):
    with pytest.raises(ValueError):
        repair_regression(t0, t, 1)


def test_curve_carries_shorter_rows_forward():
    curve = reflexion_curve([[1, 0], [1, 1, 1, 0], [0, 0, 1]])
    assert [p.round for p in curve] == [1, 2, 3]
    # round 3: row0 carries 0 (repaired), row1 -> 0 (repaired), row2 carries 1 (regressed)
    assert curve[0].repair_rate == 50.0 and curve[0].regression_rate == 0.0
    assert curve[1].regression_rate == 100.0
    assert curve[2].repair_rate == 100.0 and curve[2].regression_rate == 100.0 and curve[2].net_gain == 0.0


def test_curve_empty_and_max_round():
    assert reflexion_curve([]) == []
    assert reflexion_curve([[1]]) == []
    assert len(reflexion_curve([[1, 0]], max_round=3)) == 3


def test_secure_rate():
    assert secure_rate([0, 1, 0, 0]) == 75.0
    assert secure_rate([]) == 0.0


def test_severity_counts_keys_always_present():
    counts = severity_counts([{"severity": "HIGH"}, {"severity": "high"}, {"severity": "INFO"}])
    assert counts == {"CRITICAL": 0, "HIGH": 2, "MEDIUM": 0, "LOW": 0}
    assert severity_counts([]) == {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}


def _f(rule, cwe, line):
    return {"rule_id": rule, "cwe_id": cwe, "title": rule, "severity": "HIGH", "start_line": line}


def test_compare_findings_ignores_line_shifts():
    prev = [_f("PY-SQLI-001", "CWE-89", 10), _f("PY-SECRET-001", "CWE-798", 3), _f("PY-SECRET-001", "CWE-798", 4)]
    curr = [_f("PY-SECRET-001", "CWE-798", 8), _f("PY-EVAL-001", "CWE-95", 12)]
    result = compare_findings(prev, curr)
    assert [i["rule_id"] for i in result["fixed"]] == ["PY-SQLI-001", "PY-SECRET-001"]
    assert [i["rule_id"] for i in result["unresolved"]] == ["PY-SECRET-001"]
    assert [i["rule_id"] for i in result["new"]] == ["PY-EVAL-001"]
    assert set(result["new"][0]) == {"rule_id", "cwe_id", "title", "severity"}
