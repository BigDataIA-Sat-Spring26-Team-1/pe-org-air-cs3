import logging
import re
from datetime import datetime
import os
import asyncio
import random
import pandas as pd
from typing import List, Dict, Any, Tuple
from difflib import SequenceMatcher
from jobspy import scrape_jobs
from .utils import WebUtils
from app.models.signals import CollectorResult, SignalCategory, SignalEvidenceItem


logger = logging.getLogger(__name__)

class JobCollector:
    """Scans job boards to find AI-related hiring trends and technical skill demands."""

    # Core keywords and skills used to identify AI-centric roles
    AI_KEYWORDS = [
        "machine learning", "ml engineer", "data scientist",
        "artificial intelligence", "deep learning", "nlp",
        "natural language processing", "computer vision", "mlops",
        "ai engineer", "pytorch", "tensorflow", "llm",
        "large language model", "generative ai", "genai",
        "transformer", "bert", "gpt", "rag", "vector database",
        "reinforcement learning", "neural network", "predictive modeling",
        "statistical learning", "autoencoder", "gan", "diffusion model",
        "applied ai", "ai solutions", "ml researcher"
    ]

    AI_SKILLS_LIST = [
        "python", "pytorch", "tensorflow", "scikit-learn",
        "spark", "hadoop", "kubernetes", "docker",
        "aws sagemaker", "azure ml", "gcp vertex",
        "huggingface", "langchain", "openai", "anthropic",
        "cohere", "llama", "mistral", "pandas", "numpy",
        "jax", "keras", "xgboost", "lightgbm", "pinecone",
        "milvus", "weaviate", "chroma", "mongodb", "snowflake",
        "databricks", "mlflow", "kubeflow", "airflow", "dvc"
    ]

    # Identifies roles with engineering, data, or analytical focus
    TECH_TITLE_KEYWORDS = [
        "engineer", "developer", "programmer", "software",
        "data", "analyst", "scientist", "technical",
        "quantitative", "researcher", "architect", "computing", "technology"
    ]

    def __init__(self, output_file: str = "processed_jobs.csv"):
        self.output_file = output_file

    def _is_tech_role(self, title: str) -> bool:
        """Determines if a role is technical based on common keywords."""
        return any(kw in title.lower() for kw in self.TECH_TITLE_KEYWORDS)

    def _analyze_description(self, text: str) -> Tuple[bool, List[str], List[str]]:
        """Scans job text for AI categories and specific tools."""
        text = text.lower()
        
        is_ai = False
        for kw in self.AI_KEYWORDS:
            if re.search(r'\b' + re.escape(kw) + r'\b', text):
                is_ai = True
                break
                
        skills = [skill for skill in self.AI_SKILLS_LIST if re.search(r'\b' + re.escape(skill) + r'\b', text)]
        
        categories = []
        if any(re.search(r'\b' + re.escape(k) + r'\b', text) for k in ["neural", "deep learning", "transformer", "gan", "applied ai"]): 
            categories.append("deep_learning")
        if any(re.search(r'\b' + re.escape(k) + r'\b', text) for k in ["vision", "image", "object detection"]): 
            categories.append("computer_vision")
        if any(re.search(r'\b' + re.escape(k) + r'\b', text) for k in ["predictive", "forecasting", "statistical"]): 
            categories.append("predictive_analytics")
        if any(re.search(r'\b' + re.escape(k) + r'\b', text) for k in ["natural language", "nlp", "semantic"]): 
            categories.append("nlp")
        if any(re.search(r'\b' + re.escape(k) + r'\b', text) for k in ["generative", "gpt", "llm", "chatbot", "claude"]): 
            categories.append("generative_ai")
                    
        return is_ai, categories, skills

    def _is_matching_company(self, listing_company: str, target_company: str, ticker: str = None) -> bool:
        """Robust check to ensure the job listing belongs to the target company using similarity."""
        if not listing_company:
            return False
            
        l_name = str(listing_company).lower().strip()
        t_name = str(target_company).lower().strip()
        
        # 1. Exact or partial name match
        if l_name in t_name or t_name in l_name:
            return True
            
        # 2. Ticker match
        if ticker and ticker.lower() in l_name.split():
            return True
            
        # 3. Alphanumeric normalization match (CRITICAL for JPMorganChase)
        l_norm = re.sub(r'[^a-z0-9]', '', l_name)
        t_norm = re.sub(r'[^a-z0-9]', '', t_name)
        if l_norm == t_norm or l_norm in t_norm or t_norm in l_norm:
            return True

        # 4. Sequence similarity ratio (Fuzzy match)
        similarity = SequenceMatcher(None, l_name, t_name).ratio()
        if similarity > 0.75:
            return True

        # 5. Significant word overlap
        ignore_words = {"inc", "corp", "corporation", "limited", "ltd", "company", "group", "holdings", "llc", "the", "and", "&"}
        l_words = {w for w in l_name.replace(',', ' ').replace('.', ' ').split() if w not in ignore_words and len(w) > 2}
        t_words = {w for w in t_name.replace(',', ' ').replace('.', ' ').split() if w not in ignore_words and len(w) > 2}
        
        if l_words & t_words:
            return True
            
        return False

    async def collect(self, company_name: str, days: int = 30, ticker: str = None) -> CollectorResult:
        """Scrapes LinkedIn for jobs and analyzes them for AI signals."""
        logger.info(f"Checking job postings for {company_name} (Ticker: {ticker})")
        search_query = WebUtils.clean_company_name(company_name)
        
        try:
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(None, lambda: scrape_jobs(
                site_name=["linkedin"],
                search_term=search_query,
                location="USA",
                results_wanted=50,
                hours_old=days * 24,
                linkedin_fetch_description=True
            ))
        except Exception as e:
            logger.error(f"Hiring data collection failed: {str(e)}")
            return self._empty_result(f"Scraper error: {str(e)}")

        if df.empty:
            return self._empty_result("No jobs found")

        processed_jobs = []
        evidence_items = []
        tech_count = 0
        ai_count = 0
        total_skills = set()
        
        for _, row in df.iterrows():
            listing_company = row.get('company', '')
            # Filter out random/unrelated companies
            if not self._is_matching_company(listing_company, company_name, ticker):
                continue

            title = str(row.get('title', '')).strip()
            desc = str(row.get('description', '')).strip()
            url = str(row.get('job_url', ''))
            
            # Enrich short descriptions with a second-pass scrape
            if len(desc) < 500 and url:
                try:
                    full_text = await WebUtils.fetch_page_text(url)
                    if len(full_text) > len(desc):
                        desc = full_text
                        # Respectful delay after full page fetch
                        await asyncio.sleep(random.uniform(1, 2))
                except Exception:
                    pass

            is_ai, cats, skills = self._analyze_description(desc)
            
            # Check title for AI keywords if description is ambiguous
            title_is_ai = any(re.search(r'\b' + re.escape(kw.lower()) + r'\b', title.lower()) for kw in ["ai", "ml", "intelligence"])
            final_is_ai = is_ai or title_is_ai
            
            is_tech = self._is_tech_role(title) or final_is_ai
            
            if is_tech:
                tech_count += 1
                if final_is_ai:
                    ai_count += 1
                    total_skills.update(skills)
                
                # Sanitize date - handle pandas NaN or empty strings
                raw_date = row.get('date_posted')
                if pd.isna(raw_date) or not str(raw_date).strip() or str(raw_date).lower() == 'nan':
                    evidence_date = datetime.now().date().isoformat()
                else:
                    evidence_date = str(raw_date)

                processed_jobs.append({
                    "company": company_name,
                    "title": title,
                    "description": desc,
                    "url": url,
                    "is_ai": is_ai,
                    "categories": cats,
                    "skills": skills,
                    "posted_at": evidence_date
                })
                evidence_items.append(SignalEvidenceItem(
                    title=title,
                    description=desc[:2000] if desc else None,
                    url=url,
                    tags=cats + (["AI"] if is_ai else []) + (["Tech"] if is_tech else []),
                    date=evidence_date,
                    metadata={
                        "skills": skills,
                        "is_ai": is_ai
                    }
                ))

        # 5. Persistent Cache for debugging/audit
        if self.output_file and processed_jobs:
            new_df = pd.DataFrame(processed_jobs)
            
            # Align schema if appending to existing history
            if os.path.exists(self.output_file):
                try:
                    old_df = pd.read_csv(self.output_file)
                    
                    # Normalize URL column for consistency
                    if 'job_url' in old_df.columns and 'url' in new_df.columns:
                        new_df = new_df.rename(columns={'url': 'job_url'})
                    
                    combined_df = pd.concat([old_df, new_df], ignore_index=True)
                    
                    # Deduplicate ensuring we keep the latest or just unique URLs
                    dedup_key = 'job_url' if 'job_url' in combined_df.columns else 'url'
                    if dedup_key in combined_df.columns:
                        combined_df = combined_df.drop_duplicates(subset=[dedup_key], keep='last')
                    
                    combined_df.to_csv(self.output_file, index=False)
                except Exception as e:
                    logger.warning(f"Could not merge with existing jobs file: {e}")
                    new_df.to_csv(self.output_file, index=False)
            else:
                new_df.to_csv(self.output_file, index=False)

        # Scoring: Proportion (60) + Skill Breadth (20) + Absolute Volume (20)
        ai_ratio = ai_count / tech_count if tech_count > 0 else 0
        score = (
            min(ai_ratio * 60, 60) +
            min(len(total_skills) / 10, 1) * 20 +
            min(ai_count / 5, 1) * 20
        )
        
        return CollectorResult(
            category=SignalCategory.TECHNOLOGY_HIRING,
            normalized_score=round(float(score), 2),
            confidence=min(0.5 + tech_count / 100, 0.95),
            raw_value=f"{ai_count} AI roles found within {tech_count} tech openings",
            source="LinkedIn",
            evidence=evidence_items,
            metadata={
                "tech_count": tech_count,
                "ai_count": ai_count,
                "skills": list(total_skills),
                "count": len(processed_jobs)
            }
        )

    def _empty_result(self, msg: str) -> CollectorResult:
        return CollectorResult(
            category=SignalCategory.TECHNOLOGY_HIRING,
            normalized_score=0,
            confidence=0.5,
            raw_value=msg,
            source="LinkedIn"
        )
