
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, Optional
import structlog
import logging
from app.pipelines.integration_pipeline import integration_pipeline

router = APIRouter(prefix="/integration")
logger = structlog.get_logger(__name__)

from typing import Dict, Any, Optional, List

class IntegrationRequest(BaseModel):
    ticker: Optional[str] = None
    tickers: Optional[List[str]] = None

class IntegrationResult(BaseModel):
    status: str
    ticker: str
    company_id: Optional[str] = None
    final_score: Optional[float] = None
    v_r: Optional[float] = None
    h_r: Optional[float] = None
    synergy: Optional[float] = None
    confidence: Optional[float] = None
    ci_lower: Optional[float] = None
    ci_upper: Optional[float] = None
    dimension_scores: Optional[Dict[str, float]] = None
    signals_added: Optional[int] = None
    assessment_id: Optional[str] = None
    error: Optional[str] = None

class BatchIntegrationResponse(BaseModel):
    results: List[IntegrationResult]
    total: int
    successful: int
    failed: int

@router.post("/run", response_model=BatchIntegrationResponse)
async def run_integration(request: IntegrationRequest):
    """
    This fetches data from Snowflake and recalculates deep analytical scores for one or more tickers.
    """
    tickers = []
    if request.ticker:
        tickers.append(request.ticker)
    if request.tickers:
        tickers.extend([t for t in request.tickers if t not in tickers])
    
    if not tickers:
        raise HTTPException(status_code=400, detail="No tickers provided")

    logger.info(f"API Triggered Batch Integration Pipeline for {tickers}")
    
    responses = []
    successful = 0
    failed = 0
    
    for ticker in tickers:
        try:
            results = await integration_pipeline.run_integration(ticker)
            
            if "error" in results:
                responses.append(IntegrationResult(
                    status="failed",
                    ticker=ticker,
                    error=results["error"]
                ))
                failed += 1
                continue
            
            final = results["final_score"]
            responses.append(IntegrationResult(
                status="success",
                ticker=ticker,
                company_id=results["company_id"],
                final_score=float(final["org_air_score"]),
                v_r=float(final["v_r"]),
                h_r=float(final["h_r"]),
                synergy=float(final["synergy"]),
                confidence=float(final["confidence"]),
                ci_lower=float(final["ci_lower"]),
                ci_upper=float(final["ci_upper"]),
                dimension_scores={k: float(v) for k, v in results["scores"].items()},
                signals_added=results["signals_added"],
                assessment_id=results["assessment_id"]
            ))
            successful += 1
            
        except Exception as e:
            logger.error(f"Integration failed for {ticker}: {str(e)}", exc_info=True)
            responses.append(IntegrationResult(
                status="failed",
                ticker=ticker,
                error=str(e)
            ))
            failed += 1

    return BatchIntegrationResponse(
        results=responses,
        total=len(tickers),
        successful=successful,
        failed=failed
    )
