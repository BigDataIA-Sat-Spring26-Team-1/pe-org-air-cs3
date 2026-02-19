
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, Optional
import structlog
import logging
from app.pipelines.integration_pipeline import integration_pipeline

router = APIRouter(prefix="/integration")
logger = structlog.get_logger(__name__)

class IntegrationRequest(BaseModel):
    ticker: str

class IntegrationResponse(BaseModel):
    status: str
    ticker: str
    company_id: str
    final_score: float
    v_r: float
    h_r: float
    synergy: float
    confidence: float
    ci_lower: float
    ci_upper: float
    dimension_scores: Dict[str, float]
    signals_added: int
    assessment_id: str

@router.post("/run", response_model=IntegrationResponse)
async def run_integration(request: IntegrationRequest):
    """
    This fetches data from Snowflake and recalculates all deep analytical scores.
    """
    logger.info(f"API Triggered Integration Pipeline for {request.ticker}")
    
    try:
        results = await integration_pipeline.run_integration(request.ticker)
        
        if "error" in results:
            raise HTTPException(status_code=404, detail=results["error"])
        
        final = results["final_score"]
        
        # Format response
        return IntegrationResponse(
            status="success",
            ticker=request.ticker,
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
        )
        
    except Exception as e:
        logger.error(f"Integration Pipeline failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {str(e)}")
