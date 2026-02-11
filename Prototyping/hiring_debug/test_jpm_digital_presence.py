import asyncio
import logging
import re
import pandas as pd
from typing import List, Dict, Any, Tuple, Set
from difflib import SequenceMatcher
from datetime import datetime
from jobspy import scrape_jobs
from playwright.async_api import async_playwright
from playwright_stealth import stealth

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("JPM-DigitalPresence-Debug")

# --- Keywords from app/pipelines/external_signals/tech_stack_collector.py ---

TECH_INDICATORS = {
    "cloud_ml": ["aws sagemaker", "azure ml", "google vertex", "databricks", "sagemaker", "vertex ai", "azure machine learning", "amazon sagemaker", "google ml engine"],
    "ml_framework": ["tensorflow", "pytorch", "scikit-learn", "keras", "cuda", "onnx", "jax", "flax", "xgboost", "lightgbm", "catboost", "detectron2", "opencv"],
    "data_platform": ["snowflake", "databricks", "spark", "hadoop", "bigquery", "redshift", "athena", "presto", "dremio", "teradata", "cloudera", "confluent"],
    "ai_api": ["openai", "anthropic", "huggingface", "cohere", "langchain", "mistral", "llama-index", "gradio", "streamlit", "pinecone", "weaviate", "milvus", "qdrant"]
}

# --- Similarity Logic (The fix we just applied to JobCollector) ---

def string_similarity(a: str, b: str) -> float:
    a = a.lower().strip()
    b = b.lower().strip()
    a_alpha = re.sub(r'[^a-z0-9]', '', a)
    b_alpha = re.sub(r'[^a-z0-9]', '', b)
    if a_alpha == b_alpha or a_alpha in b_alpha or b_alpha in a_alpha:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()

def _is_matching_company(listing_company: str, target_company: str, ticker: str = None) -> bool:
    if not listing_company: return False
    l_name = str(listing_company).lower().strip()
    t_name = str(target_company).lower().strip()
    if l_name in t_name or t_name in l_name: return True
    if ticker and ticker.lower() in l_name.split(): return True
    l_norm = re.sub(r'[^a-z0-9]', '', l_name)
    t_norm = re.sub(r'[^a-z0-9]', '', t_name)
    if l_norm == t_norm or l_norm in t_norm or t_norm in l_norm: return True
    return SequenceMatcher(None, l_name, t_name).ratio() > 0.75

# --- Digital Presence Simulation Logic ---

async def scan_web_presence(domain: str):
    """Simulates the web scan part of the pipeline."""
    found = []
    logger.info(f"Scanning web footprint for: {domain}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = await context.new_page()
        await stealth(page)
        
        try:
            # 1. BuiltWith Scan (Simplified)
            logger.info(f"Visiting BuiltWith for {domain}...")
            await page.goto(f"https://builtwith.com/{domain}", timeout=45000)
            await asyncio.sleep(2)
            content = (await page.inner_text("body")).lower()
            
            seen = set()
            for cat, techs in TECH_INDICATORS.items():
                for tech in techs:
                    if tech in content and tech not in seen:
                        found.append({"name": tech.upper(), "category": cat, "source": "builtwith"})
                        seen.add(tech)
            
            logger.info(f"BuiltWith found {len(found)} markers.")
            
        except Exception as e:
            logger.warning(f"Web scan failed: {e}")
        finally:
            await browser.close()
    return found

async def debug_jpm_digital_presence():
    target_company = "JPMorgan Chase"
    ticker = "JPM"
    domain = "jpmorganchase.com" # We know this is their domain
    
    logger.info("Step 1: Scraping Jobs for Textual Tech Signal...")
    try:
        df = scrape_jobs(
            site_name=["linkedin"],
            search_term=target_company,
            location="USA",
            results_wanted=20,
            hours_old=72, # Last 3 days
            linkedin_fetch_description=True
        )
    except Exception as e:
        logger.error(f"Job scrape failed: {e}")
        df = pd.DataFrame()

    job_markers = []
    if not df.empty:
        logger.info(f"Retrieved {len(df)} jobs. Filtering for {target_company}...")
        matching_jobs = df[df['company'].apply(lambda x: _is_matching_company(x, target_company, ticker))]
        logger.info(f"Found {len(matching_jobs)} matched jobs.")
        
        combined_text = " ".join(matching_jobs['description'].fillna("").astype(str)).lower()
        seen = set()
        for cat, techs in TECH_INDICATORS.items():
            for tech in techs:
                # Use word boundaries for tech markers to avoid false positives (e.g. "at" in "Atlassian")
                if re.search(r'\b' + re.escape(tech) + r'\b', combined_text):
                    job_markers.append({"name": tech.upper(), "category": cat, "source": "job_descriptions"})
                    seen.add(tech)
        logger.info(f"Job descriptions found {len(job_markers)} tech markers.")

    logger.info("\nStep 2: Scanning Web Infrastructure...")
    web_markers = await scan_web_presence(domain)
    
    # Merge all markers
    all_markers = {m['name']: m for m in (job_markers + web_markers)}
    final_markers = list(all_markers.values())
    unique_cats = set(m['category'] for m in final_markers)
    
    logger.info("\n--- FINAL RESULTS ---")
    logger.info(f"Total Unique Markers: {len(final_markers)}")
    logger.info(f"Category Diversity:   {len(unique_cats)}")
    
    if len(final_markers) == 0:
        logger.error("TOTAL 0 SCORE DETECTED. Root cause analysis:")
        if not job_markers: logger.info(" - Source 1 (Jobs): No markers found in descriptions.")
        if not web_markers: logger.info(" - Source 2 (Web): No markers found on BuiltWith/Live Site.")
        logger.info("Check keywords: " + str(TECH_INDICATORS))
    else:
        for m in final_markers:
            logger.info(f" [+] {m['name']} ({m['category']}) - via {m['source']}")
        
        # Current scoring formula
        score = min(len(final_markers) * 10, 50) + min(len(unique_cats) * 12.5, 50)
        logger.info(f"Calculated Score: {score}")

if __name__ == "__main__":
    asyncio.run(debug_jpm_digital_presence())
