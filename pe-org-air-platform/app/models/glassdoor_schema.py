-- Glassdoor Reviews Table
CREATE TABLE IF NOT EXISTS glassdoor_reviews (
    id VARCHAR(255) PRIMARY KEY,
    company_id VARCHAR(255) NOT NULL,
    ticker VARCHAR(50),
    review_date TIMESTAMP_NTZ,
    rating FLOAT,
    title VARCHAR(500),
    pros VARCHAR(4000),
    cons VARCHAR(4000),
    advice_to_management VARCHAR(4000),
    is_current_employee BOOLEAN,
    job_title VARCHAR(255),
    location VARCHAR(255), 
    culture_rating FLOAT,
    diversity_rating FLOAT,
    work_life_rating FLOAT,
    senior_management_rating FLOAT,
    comp_benefits_rating FLOAT,
    career_opp_rating FLOAT,
    recommend_to_friend VARCHAR(50),
    ceo_rating VARCHAR(50),
    business_outlook VARCHAR(50),
    raw_json VARIANT, -- Store the full JSON here for backup/re-parsing
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Culture Scores Table (Derived from reviews)
CREATE TABLE IF NOT EXISTS culture_scores (
    id VARCHAR(255) PRIMARY KEY, -- company_id || '_' || batch_date
    company_id VARCHAR(255) NOT NULL,
    ticker VARCHAR(50),
    batch_date DATE,
    innovation_score FLOAT, -- Derived from keywords in reviews
    data_driven_score FLOAT,
    ai_awareness_score FLOAT,
    change_readiness_score FLOAT,
    overall_sentiment FLOAT,
    review_count INT,
    confidence_score FLOAT,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
