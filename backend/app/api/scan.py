"""
Stand-alone scan and curated demo samples.
"""

from typing import List, Optional

from fastapi import APIRouter, Query

from app.schemas.evaluation import ProgrammingLanguageEnum
from app.schemas.scan import SampleResponse, ScanFindingResponse, ScanRequest, ScanResponse, cwe_url
from app.services.providers.demo_samples import SAMPLES
from app.services.scanner import ScannerService

router = APIRouter()


@router.post("/scan", response_model=ScanResponse)
async def scan_code(request: ScanRequest):
    """Scan code with the built-in rules (all languages) and Bandit (Python); nothing is stored"""
    report = await ScannerService().scan_async(request.code, request.language.value)
    data = report.to_dict()
    data["findings"] = [ScanFindingResponse(**f, cwe_url=cwe_url(f["cwe_id"])) for f in data["findings"]]
    return ScanResponse(**data)


@router.get("/samples", response_model=List[SampleResponse])
async def list_samples(language: Optional[ProgrammingLanguageEnum] = Query(None)):
    """Curated vulnerable examples (code = the vulnerable stage 0)"""
    return [
        SampleResponse(
            id=sample.id,
            language=sample.language,
            title=sample.title,
            cwes=list(sample.cwes),
            task=sample.task,
            code=sample.stages[0],
        )
        for sample in SAMPLES
        if language is None or sample.language == language.value
    ]
