"""
Pydantic schemas for the stand-alone scan and demo-sample endpoints
"""

import re
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from app.config import settings
from app.schemas.evaluation import ProgrammingLanguageEnum

_CWE_NUMBER = re.compile(r"^CWE-(\d+)$")


def cwe_url(cwe_id: Optional[str]) -> Optional[str]:
    """MITRE definition page for a CWE id such as "CWE-89" (None if the id is not numeric)."""
    match = _CWE_NUMBER.match(cwe_id or "")
    return f"https://cwe.mitre.org/data/definitions/{match.group(1)}.html" if match else None


class ScanRequest(BaseModel):
    """Scan a code snippet without running the reflexion loop"""
    code: str = Field(..., min_length=1, max_length=settings.MAX_CODE_CHARS)
    language: ProgrammingLanguageEnum


class ScanFindingResponse(BaseModel):
    """A finding produced by the scanner (not persisted)"""
    rule_id: str
    analyzer: str
    cwe_id: str
    cwe_name: str
    cwe_url: Optional[str]
    severity: str
    confidence: str
    title: str
    description: str
    remediation: str
    start_line: int
    end_line: int
    code_snippet: str
    corroborated_by: List[str] = []


class ScanResponse(BaseModel):
    label: int  # 1 = insecure (any MEDIUM+ finding), 0 = secure
    is_secure: bool
    findings: List[ScanFindingResponse]
    severity_counts: Dict[str, int]
    analyzers_run: List[str]
    errors: List[str]


class SampleResponse(BaseModel):
    """Curated vulnerable example (code = stage 0)"""
    id: str
    language: str
    title: str
    cwes: List[str]
    task: str
    code: str
