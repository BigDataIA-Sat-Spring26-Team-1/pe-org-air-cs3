
import asyncio
import structlog
import logging
import uuid
import hashlib
import json
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Any, Optional

from app.services.snowflake import db
from app.services.redis_cache import cache
from app.scoring.rubric_scorer import RubricScorer
from app.pipelines.board_analyzer import BoardCompositionAnalyzer
from app.scoring.talent_analyzer import TalentConcentrationCalculator
from app.pipelines.glassdoor.glassdoor_collector import GlassdoorCultureCollector
from app.scoring.calculators import OrgAIRCalculator
from app.models.signals import SignalCategory
from app.models.scoring import SignalSource
from app.services.sector_config import sector_config


logger = structlog.get_logger(__name__)

class IntegrationPipeline:
    """
    Case Study 3 Integration Pipeline.
    Calculates main scores by fetching raw data bits from Snowflake and SEC-API.
    """

    def __init__(self):
        self.rubric_scorer = RubricScorer()
        self.board_analyzer = BoardCompositionAnalyzer()
        self.talent_calculator = TalentConcentrationCalculator()
        self.culture_collector = GlassdoorCultureCollector()
        self.org_air_calc = OrgAIRCalculator()

    async def run_integration(self, ticker: str) -> Dict[str, Any]:
        """
        Executes the full analytical integration for a company.
        """
        logger.info(f"Starting Integration Pipeline for {ticker}")
        
        # 1. Resolve Company
        company = await db.fetch_company_by_ticker(ticker)
        if not company:
            logger.error(f"Company {ticker} not found in database.")
            return {"error": "Company not found"}
        
        company_id = company['id']
        sector = company.get('sector', 'default')
        position_factor = Decimal(str(company.get('position_factor', 0.5)))

        # 2. Fetch Existing External Signals for dimension bootstrapping
        summary = await db.fetch_company_signal_summary(company_id)
        logger.info(f"Retrieved signal summary for {ticker}", summary=summary)
        
        # Base dimensions from signals
        results = {
            "ticker": ticker,
            "company_id": company_id,
            "scores": {
                "data_infrastructure": Decimal(str(summary.get('digital_presence_score', 50.0) if (summary and summary.get('digital_presence_score') is not None) else 50.0)),
                "technology_stack": Decimal(str(summary.get('technology_hiring_score', 50.0) if (summary and summary.get('technology_hiring_score') is not None) else 50.0)),
                "talent": Decimal(str(summary.get('technology_hiring_score', 50.0) if (summary and summary.get('technology_hiring_score') is not None) else 50.0)), # Talent maturity = volume/skills
                "leadership": Decimal(str(summary.get('leadership_signals_score', 50.0) if (summary and summary.get('leadership_signals_score') is not None) else 50.0)),
                "culture": Decimal(str(summary.get('innovation_activity_score', 50.0) if (summary and summary.get('innovation_activity_score') is not None) else 50.0))
            },
            "signals_added": 0
        }
        logger.info(f"Initialized base scores for {ticker}", scores={k: float(v) for k, v in results["scores"].items()})

        # 3. SEC Rubric Scoring
        chunks = await db.fetch_sec_chunks_by_company(company_id, limit=2000)
        full_text = ""
        if chunks:
            full_text = "\n".join([c['chunk_text'] for c in chunks if c.get('chunk_text')])
            
            tasks = [
                ("use_case_portfolio", SignalSource.SEC_ITEM_1),
                ("ai_governance", SignalSource.SEC_ITEM_1A),
                ("leadership", SignalSource.SEC_ITEM_7)
            ]
            
            for dim, source in tasks:
                res = self.rubric_scorer.score_dimension(dim, full_text, {})
                if float(res.score) > 10:
                    await self._save_signal(company_id, source.value, "SEC Analytical Rubric", res.score, res.confidence, res.rationale, {
                        "matched_keywords": res.matched_keywords,
                        "level": res.level.name
                    })
                    # Blend with existing signals for dimension (Prototype logic)
                    if dim in results["scores"]:
                        results["scores"][dim] = (results["scores"][dim] * Decimal("0.3") + res.score * Decimal("0.7"))
                    else:
                        results["scores"][dim] = res.score
                    results["signals_added"] += 1

        # 4. Board Analysis
        try:
            members, committees = self.board_analyzer.fetch_board_data(ticker)
            if members:
                strategy_text = ""
                if "Item 1. Business" in full_text:
                    strategy_text = full_text.split("Item 1. Business")[1][:5000]
                
                gov_signal = self.board_analyzer.analyze_board(company_id, ticker, members, committees, strategy_text)
                await self._save_signal(company_id, SignalCategory.BOARD_COMPOSITION, "Board Audit", gov_signal.governance_score, gov_signal.confidence, "Board composition analysis for tech oversight.", {
                    "ai_experts": gov_signal.ai_experts,
                    "committees": gov_signal.relevant_committees,
                    "independent_ratio": float(gov_signal.independent_ratio)
                })
                # Governance score blend
                if "ai_governance" in results["scores"]:
                    results["scores"]["ai_governance"] = (results["scores"]["ai_governance"] * Decimal("0.6") + Decimal(str(gov_signal.governance_score)) * Decimal("0.4"))
                else:
                    results["scores"]["ai_governance"] = Decimal(str(gov_signal.governance_score))
                
                results["signals_added"] += 1
        except Exception as e:
            logger.error(f"Board analysis failed for {ticker}: {e}")

        # 5. Talent Concentration Analysis (TC Modifies HR, lacks parity with Talent Maturity score)
        hr_modifier = Decimal("1.0")
        try:
            talent_risk = await self.talent_calculator.get_company_talent_risk(company_id, db)
            tc_score = Decimal(str(talent_risk["talent_concentration_score"]))
            
            # Persist TC signal but don't overwrite Talent Maturity dimension
            await self._save_signal(
                company_id, SignalCategory.TALENT_CONCENTRATION, "Talent Scorer", 
                tc_score * 100, Decimal("0.85"), 
                "Talent concentration risk assessment.", talent_risk["breakdown"]
            )
            
            # Calculate HR Modifier from Prototype: 1 - 0.15 * max(0, TC - 0.25)
            hr_modifier = Decimal(str(talent_risk["talent_risk_adjustment"]))
            results["signals_added"] += 1
        except Exception as e:
            logger.error(f"Talent analysis failed for {ticker}: {e}")

        # 6. Glassdoor Culture Blend
        try:
            raw_reviews_data = await db.fetch_glassdoor_reviews_for_talent(company_id)
            if raw_reviews_data:
                from app.models.glassdoor_models import GlassdoorReview
                parsed_reviews = []
                for r in raw_reviews_data:
                    meta = r.get('metadata')
                    if isinstance(meta, str) and meta: meta = json.loads(meta)
                    parsed_reviews.append(GlassdoorReview(
                        id=str(uuid.uuid4()), company_id=company_id, ticker=ticker,
                        review_date=datetime.now(), rating=0.0,
                        title=r['title'], pros=r['review_text'], cons="",
                        is_current_employee=True, raw_json={}
                    ))
                
                culture_signal = self.culture_collector.analyze_reviews(company_id, ticker, parsed_reviews)
                if culture_signal:
                    await self._save_signal(
                        company_id, SignalCategory.GLASSDOOR_REVIEWS, "Glassdoor Cultural Audit",
                        culture_signal.overall_sentiment, culture_signal.confidence,
                        "Cultural alignment and AI awareness among employees.",
                        {"innovation": float(culture_signal.innovation_score), "ai_awareness": float(culture_signal.ai_awareness_score)}
                    )
                    # Blend culture
                    results["scores"]["culture"] = (results["scores"]["culture"] * Decimal("0.5") + culture_signal.overall_sentiment * Decimal("0.5"))
                    results["signals_added"] += 1
        except Exception as e:
            logger.error(f"Culture analysis failed for {ticker}: {e}")

        # 7. Final Org-AI-R Aggregation
        final_dimensions = ["data_infrastructure", "ai_governance", "technology_stack", "talent", "leadership", "use_case_portfolio", "culture"]
        dimension_inputs = {}
        for d in final_dimensions:
            dimension_inputs[d] = results["scores"].get(d, Decimal("50.0"))
        
        dimension_confidences = [Decimal("0.8")] * len(dimension_inputs)
        
        # Calculate HR Base with Talent Risk Adjustment
        # hr_score = clamp(Decimal("70.0") * hr_modifier * (Decimal("1") + Decimal("0.15") * pf))
        hr_base_adjusted = Decimal("70.0") * hr_modifier
        
        # Use parity alpha/beta to match prototype (0.6, 0.28, 0.12 weights)
        final_org_air = self.org_air_calc.calculate_org_air(
            dimension_scores=dimension_inputs,
            dimension_confidences=dimension_confidences,
            position_factor=position_factor,
            hr_base=hr_base_adjusted,
            sector=sector,
            company_id=company_id,
            alpha=Decimal("0.60"), # V^R vs H^R within 88%
            beta=Decimal("0.12")   # Synergy weight
        )
        
        # 8. Persistence
        assessment_id = str(uuid.uuid4())
        await db.create_assessment({
            "id": assessment_id, "company_id": company_id, 
            "assessment_type": "INTEGRATED_CS3", "assessment_date": date.today().isoformat(),
            "primary_assessor": "IntegrationPipeline", "status": "completed"
        })
        
        for dim, score in dimension_inputs.items():
            await db.create_dimension_score({
                "id": str(uuid.uuid4()), "assessment_id": assessment_id, "dimension": dim,
                "score": float(score), "weight": float(sector_config.get_weights(sector).get(dim, 0.14)),
                "confidence": 0.8, "evidence_count": 1
            })
            
        update_query = """
            UPDATE assessments 
            SET org_air_score = %s, 
                v_r_score = %s, 
                h_r_score = %s, 
                synergy_score = %s, 
                confidence_score = %s,
                confidence_lower = %s, 
                confidence_upper = %s 
            WHERE id = %s
        """
        await db.execute(update_query, (
            final_org_air["org_air_score"], 
            final_org_air["v_r"],
            final_org_air["h_r"],
            final_org_air["synergy"],
            final_org_air["confidence"],
            final_org_air["ci_lower"], 
            final_org_air["ci_upper"], 
            assessment_id
        ))

        results["final_score"] = final_org_air
        results["assessment_id"] = assessment_id
        
        logger.info(f"Integration complete for {ticker}. Assessment ID: {assessment_id}")
        return results

    async def _save_signal(self, company_id: str, category: str, source: str, score: Decimal, confidence: Decimal, rationale: str, metadata: dict):
        hash_input = f"{company_id}{category}{score}"
        signal_hash = hashlib.sha256(hash_input.encode()).hexdigest()
        
        signal = {
            "id": str(uuid.uuid4()),
            "company_id": company_id,
            "signal_hash": signal_hash,
            "category": category,
            "source": source,
            "signal_date": date.today().isoformat(),
            "raw_value": rationale[:500],
            "normalized_score": float(score),
            "confidence": float(confidence),
            "metadata": metadata
        }
        await db.create_external_signal(signal)

integration_pipeline = IntegrationPipeline()
