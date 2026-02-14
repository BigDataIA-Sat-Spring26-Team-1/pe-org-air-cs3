import os
import sys
import pandas as pd
from dotenv import load_dotenv
from typing import List

# Setup path to import from current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from snowflake_client import SnowflakeClient
from talent_analyzer_v2 import TalentConcentrationCalculatorV2

def main():
    print("Starting Talent Analyzer POC for JPMorgan Chase (JPM)...")
    
    # 1. Load Environment Variables from Platform Dir
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'pe-org-air-platform', '.env'))
    if os.path.exists(env_path):
        print(f"Loading .env from {env_path}")
        load_dotenv(env_path)
    else:
        print("WARNING: .env file not found! Snowflake connection may fail.")

    # 2. Fetch Glassdoor Data (Components 1, 2, 4)
    csv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Glassdoor review analysis', 'target_company_reviews_strict.csv'))
    
    try:
        print(f"Loading '{csv_path}'...")
        if not os.path.exists(csv_path):
             raise FileNotFoundError(f"CSV not found at {csv_path}")
             
        df = pd.read_csv(csv_path)
        jpm_reviews = df[df['company_ticker'] == 'JPM'].copy()
        print(f"Found {len(jpm_reviews)} JPM reviews.")
        
    except Exception as e:
        print(f"ERROR: Could not load CSV data: {e}")
        return

    # 3. Fetch Snowflake Data (Component 3: Skill Concentration)
    job_descriptions = []
    
    print("Attempting to fetch job descriptions from Snowflake...")
    try:
        # Check credentials briefly
        user = os.getenv("SNOWFLAKE_USER")
        pwd = os.getenv("SNOWFLAKE_PASSWORD")
        if not user or not pwd:
            print("  Skipping Snowflake: Missing credentials in environment.")
            # Fallback to mock data for POC if connection fails
            job_descriptions = [
                "We are looking for a Python developer with SQL skills.",
                "Data Scientist needed having experience in TensorFlow, PyTorch and Keras.",
                "Senior Java Engineer for backend development.",
                "Machine Learning Engineer with AWS and Docker experience."
            ] * 5 # Mock some repetitions
            print("  (Using mock job data for demonstration)")
        else:
            client = SnowflakeClient()
            # Try to fetch
            job_descriptions = client.fetch_job_skills("JPMorgan") # Broad search
            if not job_descriptions:
                print("  No job descriptions found in Snowflake. Using fallback mock data.")
                job_descriptions = [
                    "We are looking for a Python developer with SQL skills.",
                    "Data Scientist needed having experience in TensorFlow, PyTorch and Keras.",
                    "Senior Java Engineer for backend development.",
                    "Machine Learning Engineer with AWS and Docker experience."
                ]
            else:
                 print(f"  Successfully fetched {len(job_descriptions)} job descriptions.")
                 
    except Exception as e:
        print(f"  Snowflake Error: {e}")
        print("  Using mock job data due to error.")
        job_descriptions = [
            "We are looking for a Python developer with SQL skills.",
            "Data Scientist needed having experience in TensorFlow, PyTorch and Keras.",
            "Senior Java Engineer for backend development.",
            "Machine Learning Engineer with AWS and Docker experience."
        ]

    # 4. Run Analysis
    print("-" * 50)
    print("Running Talent Analyzer V2...")
    analyzer = TalentConcentrationCalculatorV2()
    
    try:
        # Calculate individual components for visibility
        leadership_ratio = analyzer._calculate_leadership_ratio(jpm_reviews)
        team_size_factor = analyzer._calculate_team_size_factor(jpm_reviews)
        skill_concentration = analyzer._calculate_skill_concentration(job_descriptions)
        individual_metrics = analyzer._calculate_individual_mention_factor(jpm_reviews)
        
        final_tc = analyzer.calculate_tc(jpm_reviews, job_descriptions)
        
        print("\nResults for JPM:")
        print(f"  Total Reviews Analyzed:      {len(jpm_reviews):,}")
        print(f"  Job Descriptions Analyzed:   {len(job_descriptions):,}")
        print("-" * 30)
        print(f"  1. Leadership Ratio (40%):    {leadership_ratio:.4f}")
        print(f"  2. Team Size Factor (30%):    {team_size_factor:.4f}")
        print(f"  3. Skill Concentration (20%): {skill_concentration:.4f}")
        print(f"  4. Individual Mentions (10%): {individual_metrics:.4f}")
        print("-" * 30)
        print(f"  FINAL TALENT CONCENTRATION:   {final_tc:.4f}")
        
    except Exception as e:
        print(f"Analyzer Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
