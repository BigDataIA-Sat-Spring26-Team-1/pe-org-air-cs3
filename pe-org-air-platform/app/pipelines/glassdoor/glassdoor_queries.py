MERGE_GLASSDOOR_REVIEWS = """
MERGE INTO glassdoor_reviews AS target
USING (SELECT 
    %s AS id, %s AS company_id, %s AS ticker, %s AS review_date, %s AS rating, 
    %s AS title, %s AS pros, %s AS cons, %s AS advice_to_management, 
    %s AS is_current_employee, %s AS job_title, %s AS location, 
    %s AS culture_rating, %s AS diversity_rating, %s AS work_life_rating, 
    %s AS senior_management_rating, %s AS comp_benefits_rating, 
    %s AS career_opp_rating, %s AS recommend_to_friend, %s AS ceo_rating, 
    %s AS business_outlook, PARSE_JSON(%s) AS raw_json
) AS source
ON target.id = source.id
WHEN MATCHED THEN UPDATE SET
    company_id = source.company_id, ticker = source.ticker, review_date = source.review_date, rating = source.rating,
    title = source.title, pros = source.pros, cons = source.cons, advice_to_management = source.advice_to_management,
    is_current_employee = source.is_current_employee, job_title = source.job_title, location = source.location,
    culture_rating = source.culture_rating, diversity_rating = source.diversity_rating, work_life_rating = source.work_life_rating,
    senior_management_rating = source.senior_management_rating, comp_benefits_rating = source.comp_benefits_rating,
    career_opp_rating = source.career_opp_rating, recommend_to_friend = source.recommend_to_friend,
    ceo_rating = source.ceo_rating, business_outlook = source.business_outlook, raw_json = source.raw_json
WHEN NOT MATCHED THEN INSERT (
    id, company_id, ticker, review_date, rating, title, pros, cons, advice_to_management,
    is_current_employee, job_title, location, culture_rating, diversity_rating, work_life_rating,
    senior_management_rating, comp_benefits_rating, career_opp_rating, recommend_to_friend,
    ceo_rating, business_outlook, raw_json
) VALUES (
    source.id, source.company_id, source.ticker, source.review_date, source.rating, source.title, source.pros, source.cons, source.advice_to_management,
    source.is_current_employee, source.job_title, source.location, source.culture_rating, source.diversity_rating, source.work_life_rating,
    source.senior_management_rating, source.comp_benefits_rating, source.career_opp_rating, source.recommend_to_friend,
    source.ceo_rating, source.business_outlook, source.raw_json
)
"""
  