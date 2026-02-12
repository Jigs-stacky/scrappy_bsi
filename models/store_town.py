from odoo import models, fields
import openai
import json
import logging
_logger = logging.getLogger(__name__)
from odoo import models, fields, api
import re
from pytrends.request import TrendReq
import time
from pytrends.exceptions import TooManyRequestsError
import requests
from collections import defaultdict
import http.client

class StoreDistrictPrompt(models.Model):
    _name = 'scraper.store.district.prompt'
    _description = 'District Search Interest Prompt'
    _order = 'id'

    name = fields.Char(
        string='Prompt Name',
        required=True,
        help='Name or description of the search prompt (e.g., "Self Storage", "Storage Near Me")'
    )
    district_id = fields.Many2one(
        'scraper.store.district',
        string='District',
        required=True,
        ondelete='cascade',
        index=True
    )
    count = fields.Float(string="Count")

class StoreDistrict(models.Model):
    _name = 'scraper.store.district'
    _description = 'Store District'
    _order = 'name'

    name = fields.Char(
        string='District Name',
        required=True,
        index=True
    )
   
    town_ids = fields.One2many(
        'scraper.store.town',
        'town_district_id',
        string='Towns/Cities',
        help='List of towns/cities in this district'
    )
   

    town_count = fields.Integer(compute="_compute_district_town")
    competition_store = fields.Integer(compute="_compute_district_compititors")

    average_income = fields.Float(string="Average Income",
        help="Average annual household income (€/year)"
        )
    average_commercial_rent_per_m2 = fields.Float(string="Average commercial rent per m2",
        help="Average monthly commercial rental cost (€/m²/month) for retail or business space in the town"
        )
    warehouse_rent_per_m2 = fields.Float(string="warehouse rent per m2",
        help="Average monthly warehouse or industrial space rent (€/m²/month)"
        )
    economic_output_reference = fields.Text(string="Output Reference",
        help="Economic Output References"
        )


    number_of_households =fields.Float(string="Number of households",
        help="Total number of households in the district, calculated as population ÷ average_household_size"
        )
    average_household_size = fields.Float(string="Average Household Size",
        help="Average number of persons per household in the district"
        )
    average_home_size_m2 = fields.Float(string="Average Home Size m2",
        help="Average residential unit size in square meters"
        )
    percentage_apartments =fields.Float(string="Percentage Living Apartments (%)",
        help="Percentage of residential units that are apartments."
        )
    percentage_rented_homes = fields.Float(string="Percentage Rented Home or Appartment (%)",
        help="Percentage of residential units that are rented rather than owner-occupied."
        )
    percentage_own_homes = fields.Float(string="Percentage own Homes or Appartment  (%)",
        help="Percentage of residential units that are Own Appartment for not rented."
        )
    housing_density_output_reference = fields.Text(string="Output Reference",
        help="Housing Density Output References"
        )



    annual_move_rate = fields.Float(string="Annual Move Rate (%)",
        help="Percent of residents who change homes each year."
        ) 
    student_population_percentage = fields.Float(string="Student Population Percentage  (%)",
        help="Percent of residents studying in college or university."
        ) 
    migrant_population_percentage = fields.Float(string="Migrant Population Percentage  (%)",
        help="Percentage of residents from other countries."
        ) 
    short_term_rentals_count = fields.Float(string="Short Term Rentals Count",
        help="Number of active short-term rentals in the town."
        ) 
    mobility_output_reference = fields.Text(string="Output Reference",
        help="Mobility Output References"
        )

    #not using this field
    # self_storage = fields.Float(string="Self Storage (0–100)",
    #     help="Search interest score (0–100) for ‘self storage’ in the area."
    #     )
    # storage_near_me = fields.Float(string="Storage Near Me (0–100)",
    #     help="Numeric interest score (0–100) reflecting local search demand for proximity-based storage queries such as 'storage near me',  from available Google Trends or comparable nearby urban areas."
    #     )
    # rent_storage_unit = fields.Float(string="Rent Storage Unit (0–100)",
    #     help="Numeric interest score (0–100) indicating search demand for transactional storage queries like 'rent storage unit', inferred from regional search behavior and scaled to the district context."
    #     )
    #  local_search_growth_12m_percentage = fields.Float(string="Local Search Growth 12m Percentage (%)",
    #     help=" percentage change in overall self-storage-related search interest over the last 12 months, derived from Google Trends growth patterns or proportional trends from similar cities."
    #     )

    
    prompt_ids = fields.One2many(
        'scraper.store.district.prompt',
        'district_id',
        string='Search Interest Prompts',
        help='Search interest scores for various storage-related queries in this district'
        )       
    demand_intent_level = fields.Char(string="Demand intent Level",
        help="Demand level: low / medium / high."
        )



    number_of_competitors = fields.Float(string="Number Of Competitors ",
        help="Active storage providers"
        )
    competitor_locations = fields.Text(string="Competitor Name",
        help="Locations of active self-storage providers (street or lat/lon)."
        )
    average_rating = fields.Float(string="Average Rating (%)",
        help="Average customer rating of competitors."
        )
    review_count = fields.Integer(string="Review Count",
        help="Total customer reviews for competitors."
        )
    price_range_min = fields.Float(string="Price Range Min",
        help="Minimum unit rental price."
        )
    price_range_max = fields.Float(string="Price Range Max",
        help="Maximum unit rental price."
        )
    price_currency = fields.Char(string="Price Currency",
        help="Currency code (e.g., EUR)"
        )
    compititor_output_reference = fields.Text(string="Output Reference",
        help="Competitor Output References"
        )


    all_compititor_store_ai_avg_price = fields.Float(string="All Store Ai Average Price Per M2",
        help="Competitor All store product Per m2 Price Average")

    avg_scrappy_store_location_price = fields.Float(string="Scrappy Store location Average Price",
        help="Location Related scrapped store data price Average calculated.",
        ) 

    avg_price_scrapp_ai = fields.Float(string="Average Price calculated On Both Ai and Scrapped aevrage price",
         help="Average Price calculated On Both Ai average Price  and Scrapped avrage price "
        )



    demand_score = fields.Float(string="Demand Score (0–100)",
        help="Local self-storage demand score (0–100)."
        )
    growth_score = fields.Float(string="Growth Score (0–100)",
        help="Growth potential score (0–100)"
        )
    affordability_score = fields.Float(string="Affordability Score (0–100)",
        help="Cost feasibility score (0–100)."
        )
    competition_score = fields.Float(string="Competition Score (0–100)",
        help="Competitive pressure score (0–100)."
        )
    mobility_score = fields.Float(string="Mobility Score (0–100)",
        help="Population mobility & storage propensity score (0–100)."
        )
    risk_score = fields.Float(string="Risk Score (0–100)",
        help="Numeric score (0–100) indicating lower operational and market risk, factoring in economic stability, affordability balance, demand consistency, and inferred vacancy pressure."
        )



    town_score = fields.Float(string="Town Score (0–100)",
        help="Score for opening a storage facility."
            )
    location_verdict = fields.Char(string="Location Verdict",
        help="Strategic recommendation: Avoid / Monitor / Launch / Expand."
        )
    confidence_level = fields.Char(string="Confidence Level",
        help="Likelihood of success for opening a store: High = strong support, Medium = some uncertainty, Low = risky"
        )

  
    economic_indicator_prompt=fields.Text(default="""                
              You are a location intelligence analyst.
                Objective: Collect, analyze, and score a town to determine suitability for opening a self-storage / rental box store.

                Rules (STRICT):

                Use Input location available data only.
                If town-level data is unavailable, infer from district or state-level averages based on logical reasoning.
                Return ONLY valid JSON.
                No explanations, no markdown, no extra text.
                Use null only if no reasonable estimate can be inferred.

                ────────────────────────
                INPUT LOCATION
                ────────────────────────
                District:{name}

                ────────────────────────
                Economic Indicators
                ────────────────────────
                Objective: Determine the average household income, commercial rent, and warehouse rent for a specified town.

                Rules (STRICT):

                Use only publicly available, official, or reliable sources (government stats, Eurostat, Statista).
                If commercial or warehouse rent is not published, estimate using average urban center rents in the same state or similar-sized towns.
                Always return numeric values.
                If truly unknown, return null.

                Return Fields:

                average_income → numeric, €/year per household
                average_commercial_rent_per_m2 → numeric, €/m²/month
                warehouse_rent_per_m2 → numeric, €/m²/month
                 economic_output_reference - give me reference with website of that data as list

                Output:
                {{
                "economic_indicators": {{
                "average_income": numeric_or_estimate,
                "average_commercial_rent_per_m2": numeric_or_estimate,
                "warehouse_rent_per_m2": numeric_or_estimate,
                 "economic_output_reference" :  array or null,
                }}
                }}
                        
                        """)

    housing_living_prompt=fields.Text(default="""   
               
            You are a location intelligence analyst.
                Objective:
                Collect, analyze, and score a town to determine suitability for opening a self-storage / rental box store.
                Rules (STRICT):
                - Use Input location  available data only.
                - Infer values if exact data is unavailable.
                - Return ONLY valid JSON.
                - No explanations, no markdown, no extra text.
                - Use null if a value cannot be reasonably inferred.
                ────────────────────────
                INPUT LOCATION
                ────────────────────────
                District:{name}

                ────────────────────────
                2. Housing & Living Density
                ────────────────────────
                -Objective: Determine housing and population characteristics of the town.

                Rules (STRICT):

                If exact town-level data is unavailable, infer from state averages, city population, and general German urban statistics.

                Calculations & Inferences:
                number_of_households = population ÷ average_household_size (use national/state average household size if unknown, ~2.0–2.1 people/household).
                average_household_size = use official average for town/state; if unknown, use ~2.0–2.1.
                average_home_size_m2 = typical German urban home size, 70–100 m² if unknown.
                percentage_apartments = estimate based on urban density (~60–70%).
                percentage_rented_homes = estimate based on state/national average (~50–55%).
                Always return numeric values; do not leave fields null unless absolutely unknown.
                No explanations or commentary.

                Return Fields:

                number_of_households → numeric
                average_household_size → numeric, persons/household
                average_home_size_m2 → numeric, m²
                percentage_apartments → numeric, %
                percentage_rented_homes → numeric, %
                 housing_density_output_reference - give me reference with website of that data as list
                Output : 
                {{
                    "housing_living_density": {{
                    "number_of_households": null,
                    "average_household_size": null,
                    "average_home_size_m2": null,
                    "percentage_apartments": null,
                    "percentage_rented_homes": null,
                     "housing_density_output_reference" : array or null,
                  }},

                }}        
        """)

    mobility_lifestyle_indicators_prompt = fields.Text(default="""
             
             You are a location intelligence analyst.

                Objective:
                Collect, analyze, and score a town to determine suitability for opening a self-storage / rental box store.

                ────────────────────────
                GLOBAL RULES (STRICT)
                ────────────────────────

                Use the provided District name as the geographic reference.
                Treat the district as part of its known town/city (e.g., Wuppertal) when applicable.
                If district-level data is unavailable, infer values using:

                Town-level data
                State-level (North Rhine-Westphalia) averages
                National (Germany) averages adjusted for city size and urban profile
                Logical inference is REQUIRED when direct data is missing.
                All returned values MUST be numeric.
                Use null ONLY if no reasonable inference can be made.
                Return ONLY valid JSON.

                No explanations, no markdown, no comments, no extra text.
                No trailing commas.

                ────────────────────────
                INPUT LOCATION
                ────────────────────────
                District: {name}

                ────────────────────────
                3. MOBILITY & LIFESTYLE INDICATORS
                ────────────────────────
                Objective:
                Determine the mobility and lifestyle characteristics of the town associated with the given district (Wuppertal).

                Permitted Data Sources:

                Official city or state statistics
                Destatis
                Eurostat
                University enrollment statistics
                Public short-term rental listings (e.g., Airbnb market estimates)
                Municipal or tourism registries

                Field Rules:

                annual_move_rate
                → Percentage of total population that changes residence per year.
                → Prefer Wuppertal data; if unavailable, infer from NRW average adjusted for city size.

                student_population_percentage
                → Percentage of residents enrolled in higher education.
                → Prefer Wuppertal University enrollment vs total population; otherwise infer from NRW urban average.

                migrant_population_percentage
                → Percentage of foreign-born residents.
                → Prefer town-level data; otherwise infer from NRW statistics adjusted for urban density.

                short_term_rentals_count
                → Estimated number of short-term rental units.
                → Infer using Wuppertal population size, tourism intensity, and NRW city averages if exact data is unavailable.
             
                 mobility_output_reference - give me reference with website of that data as list
                ────────────────────────
                OUTPUT FORMAT (STRICT)
                ────────────────────────
                {{
                "mobility_lifestyle_indicators": {{
                "annual_move_rate": number or null,
                "student_population_percentage": number or null,
                "migrant_population_percentage": number or null,
                "short_term_rentals_count": number or null,
                "mobility_output_reference" : arrays or null,
                }}
                }}                    
                          
        """)

    market_demand_prompt = fields.Text(default="""
                You are a location intelligence analyst.

                Objective:
                Collect, analyze, and score a town to determine suitability for opening a self-storage / rental box store.

                Rules (STRICT):

                Use ONLY the data provided in the input.
                Infer values logically if exact data is unavailable.
                Return ONLY valid JSON.
                No explanations, no markdown, no extra text.
                All numeric fields must contain numbers.
                Use null ONLY if a value cannot be reasonably inferred.

                ────────────────────────
                INPUT LOCATION
                ────────────────────────
                District: {name}
                prompt : {prompts}
                ────────────────────────
                MARKET DEMAND – KEYWORD ANALYSIS
                ────────────────────────

                You are given a list of keywords.
                Each keyword has:

                an id number
                a name (search phrase)

                Tasks:

                For each keyword:

                Count how many words appear in the keyword name.
                Return this count mapped to the corresponding id.

                Based on the overall relevance of the keywords to self-storage services:

                Infer demand_intent_level using:
                "high" → strong commercial storage intent
                "medium" → moderate storage intent
                "low" → weak or indirect storage intent

                ────────────────────────
                OUTPUT FORMAT (STRICT)
                ────────────────────────

                {{
                "prompt_ids": {{
                "id": count
                }},
                "demand_intent_level": "low"
                }}

        """)
    competition_data_prompt = fields.Text(default="""                  
        You are a Location Intelligence Analyst.

        Your task is to collect, infer, and structure competitive intelligence data to evaluate the suitability of opening a self-storage / rental box store.

        ────────────────────────
        GLOBAL RULES (STRICT)
        ────────────────────────
        - Use the provided District name as the primary geographic reference.
        - If the district belongs to a known town or city, treat it as part of that town.
        - Use ONLY publicly available and verifiable sources.
        - Logical estimation is REQUIRED when exact values are missing.
        - All quantitative fields MUST be numeric.
        - Use null ONLY when no reasonable estimation is possible.
        - Do NOT explain reasoning.
        - Do NOT include markdown.
        - Do NOT include comments.
        - Do NOT include extra text.
        - Do NOT include trailing commas.
        - Return ONLY valid JSON.

        ────────────────────────
        INPUT LOCATION
        ────────────────────────
        District: {name}

        ────────────────────────
        SECTION 5: COMPETITION DATA
        ────────────────────────
        Objective:
        Identify and quantify the competitive landscape for self-storage and rental storage providers operating in the specified district or its associated town.

        ────────────────────────
        PERMITTED DATA SOURCES
        ────────────────────────
        - Google Maps
        - Yelp
        - TripAdvisor
        - Local or national business directories
        - Official municipal or commercial registries
        - Competitor official websites

        ────────────────────────
        FIELD RULES (MANDATORY)
        ────────────────────────
        - Count ONLY active self-storage or rental storage providers.
        - Include both large chains and independent operators.
        - Exclude moving companies without storage units.
        - Exclude inactive or permanently closed locations.

        Field Definitions:
        - number_of_competitors  
          Total count of active competitors.

        - competitor_locations  
          List of street addresses OR latitude/longitude pairs for each competitor.

        - average_rating  
          Mean customer rating across all competitors.

        - review_count  
          Total number of customer reviews across all competitors.

        - price_range_min  
          Minimum monthly rental price per square meter (m²).

        - price_range_max  
          Maximum monthly rental price per square meter (m²).

        - price_currency  
          Must always be a valid ISO 4217 currency code (e.g., EUR).

        - compititor_output_reference  
          List of direct website URLs used to collect or infer competitor data.

        - all_compititor_store_avg_price  
          Calculation rules:
          1. Determine average monthly price per m² for EACH competitor.
          2. Sum all per-store average prices.
          3. Divide by the total number of competitors.
          4. Return the final overall average price per m².

        - If prices or ratings are unavailable for a competitor:
          - Infer using comparable providers in the same town or nearby districts.

        ────────────────────────
        OUTPUT FORMAT (STRICT)
        ────────────────────────
        {{
          "competition_data": {{
            "number_of_competitors": number or null,
            "competitor_locations": array or null,
            "average_rating": number or null,
            "review_count": number or null,
            "price_range_min": number or null,
            "price_range_max": number or null,
            "price_currency": string or null,
            "all_compititor_store_avg_price": number or null,
            "compititor_output_reference": array or null,
           
          }}
        }}

        """)


    scoring_prompt = fields.Text(default="""                   
                 You are a location intelligence analyst.

                Objective:
                Collect, analyze for previos chat, and score a town or district to determine suitability for opening a self-storage / rental box store.

                ────────────────────────
                GLOBAL RULES (STRICT)
                ────────────────────────

                Use the provided District name as the geographic anchor.
                Treat the district as part of its associated town or city when applicable.
                Use ONLY indicators already derived for this location in previous steps.
                If an indicator is missing, infer its impact using closely related available indicators.
                All scores MUST be numeric and scaled from 0 to 100.
                Higher scores always indicate more favorable conditions.
                Use null ONLY if a score cannot be computed with reasonable confidence.
                Return ONLY valid JSON.
                No explanations, no markdown, no comments, no extra text.
                No trailing commas.

                ────────────────────────
                INPUT LOCATION
                ────────────────────────
                  District: {name}
                 "economic_indicators": {{
                  "average_income": {average_income},
                  "average_commercial_rent_per_m2": {average_commercial_rent_per_m2},
                  "warehouse_rent_per_m2": {warehouse_rent_per_m2}
                }},
                "housing_living_density": {{
                  "number_of_households": {number_of_households},
                  "average_household_size": {average_household_size},
                  "average_home_size_m2": {average_home_size_m2},
                  "percentage_apartments": {percentage_apartments},
                  "percentage_rented_homes": {percentage_rented_homes}
                }},
                "mobility_lifestyle_indicators": {{
                  "annual_move_rate": {annual_move_rate},
                  "student_population_percentage": {student_population_percentage},
                  "migrant_population_percentage": {migrant_population_percentage},
                  "short_term_rentals_count": {short_term_rentals_count}
                }},
                "market_demand": {{                  
                  "demand_intent_level": {demand_intent_level}
                }},
                "competition_data": {{
                  "number_of_competitors": {number_of_competitors},
                  "competitor_locations": {competitor_locations},
                  "average_rating": {average_rating},
                  "review_count": {review_count},
                  "price_range_min": {price_range_min},
                  "price_range_max": {price_range_max},
                  "price_currency": {price_currency}
                }}

                ────────────────────────
                6. SCORING (NUMERIC 0–100)
                ────────────────────────
                Objective:
                Convert all analytical indicators into standardized numeric scores.
                 
                Scoring Rules:

                demand_score
                → Based on relative search interest, keyword presence, and intent signals for self-storage.

                growth_score
                → Based on population change, household formation, and growth-related demand signals.

                affordability_score
                → Based on household income relative to commercial rents, warehouse rents, and competitor pricing.

                competition_score
                → Higher score indicates lower competitive pressure, factoring in competitor count and average ratings.

                mobility_score
                → Based on annual move rate, student presence, and rental intensity.

                risk_score
                → Higher score indicates lower operational and market risk, factoring in economic stability and vacancy pressure.

                ────────────────────────
                OUTPUT FORMAT (STRICT)
                ────────────────────────
                {{
                "scoring": {{
                "demand_score": number or null,
                "growth_score": number or null,
                "affordability_score": number or null,
                "competition_score": number or null,
                "mobility_score": number or null,
                "risk_score": number or null
                }}
                }}        
        """)

    final_output_prompt = fields.Text(default="""                
                           
            You are a location intelligence analyst.

                Objective:
                Collect, analyze, and score a town or district to determine suitability for opening a self-storage / rental box store.

                ────────────────────────
                GLOBAL RULES (STRICT)
                ────────────────────────

                Use the provided District name as the geographic anchor.
                Treat the district as part of its associated town or city when applicable.
                Use ONLY data derived from previously computed indicators for this location.
                Logical inference is REQUIRED when exact values are missing.
                All numeric scores must be within a 0–100 scale.
                town_score must be a numeric value.
                location_verdict must be one of: Avoid, Monitor, Launch, Expand Aggressively.
                confidence_level must be one of: low, medium, high.
                Use null ONLY if a value cannot be computed with reasonable confidence.
                Return ONLY valid JSON.
                No explanations, no markdown, no comments, no extra text.
                No trailing commas.

                ────────────────────────
                INPUT LOCATION
                ────────────────────────
                District: {name}
               "scoring": {{
                    "demand_score": {demand},
                    "growth_score": {growth},
                    "affordability_score": {affordability},
                    "competition_score": {competition},
                    "mobility_score": {mobility},
                    "risk_score": {risk}
                  }}
                ────────────────────────
                7. FINAL OUTPUT
                ────────────────────────
                Objective:
                Compute an overall location suitability score for the specified district or its associated town.
                Computation Rules:

                town_score is the sum of the following component scores:
              Based On last chat
                demand_score
                growth_score
                affordability_score
                competition_score
                mobility_score
                risk_score

                If a component score is missing, infer it from available related indicators.
                
                If multiple component scores are missing and inference is not reliable, return null for town_score.
                Verdict Rules:
                Avoid → town_score < 40
                Monitor → 40 ≤ town_score < 60
                Launch → 60 ≤ town_score < 80
                Expand Aggressively → town_score ≥ 80

                Confidence Rules:
                high → most component scores are directly available or strongly inferred
                medium → mix of direct data and inferred data
                low → heavy reliance on inference or partial data
                town_score - 0 -100
                ────────────────────────
                OUTPUT FORMAT (STRICT)
                ────────────────────────
                {{
                "final_output": {{
                "town_score": number or null,
                "location_verdict": string or null,
                "confidence_level": string or null
                }}
                }}        
        """)

    def execute_all(self):
        for rec in self:
            try:
                rec.economic_indicator_analysis()
                rec.housing_living_density_analysis()
                rec.mobility_lifestyle_indicators_analysis()
                rec.market_demand_analysis()
                rec.competition_data_analysis()
                rec.scoring_analysis()
                rec.final_output_analysis()

            except Exception as e:
                print("\n\n\n Error :",e)
                continue


    def calculate_avg_scrappy_store_location_price(self):
        for rec in self:
            competition_store_ids = rec.env['scraped.store.data.line'].search([('district_id','=',rec.id)])
            prices = competition_store_ids.mapped('competitor_price') if  competition_store_ids else False
            rec.avg_scrappy_store_location_price = sum(prices) / len(prices) if prices else 0.0

    def final_output_analysis(self):
        for rec in self:
            try:
                if rec.final_output_prompt:
                    ai_api_key = self.env['ir.config_parameter'].sudo().get_param(
                        'scrapper.ai_key'
                    )
                    client = openai.OpenAI(api_key=ai_api_key)
                    prompt_template = rec.final_output_prompt or ""

                    values = {
                        "name": rec.name or "",
                        "demand": rec.demand_score or "",
                        "growth": rec.growth_score or "",
                        "affordability": rec.affordability_score or "",
                        "competition": rec.competition_score or "",
                        "mobility": rec.mobility_score or "",
                        "risk": rec.risk_score or ""
                    }
                     

                    final_prompt = prompt_template.format(**values)                
                    response = client.chat.completions.create(
                        model="gpt-5.2",
                        messages=[
                            {"role": "user", "content": final_prompt}
                        ],
                        response_format={"type": "json_object"},
                        timeout=15
                    )

                    raw_content = response.choices[0].message.content            
                    data = json.loads(raw_content)                     
                    print("\n\n\n data=",data)
                    if 'final_output' in data:
                        final_output = data.get('final_output')
                        if final_output:
                            rec.town_score = final_output.get('town_score')
                            rec.location_verdict = final_output.get('location_verdict')
                            rec.confidence_level = final_output.get('confidence_level')

            except json.JSONDecodeError as e:
                _logger.error(
                    "Invalid JSON in Economic Indicators returned by AI for record %s (ID %s). Raw output: %s",
                    rec.name, rec.id, raw_content
                )



    def scoring_analysis(self):
        for rec in self:
            try:
                if rec.scoring_prompt:
                    ai_api_key = self.env['ir.config_parameter'].sudo().get_param(
                        'scrapper.ai_key'
                    )
                    client = openai.OpenAI(api_key=ai_api_key)
                    prompt_template = rec.scoring_prompt or ""

                    values = {
                        "name": rec.name or "",
                        "average_income": rec.average_income or "",
                        "average_commercial_rent_per_m2": rec.average_commercial_rent_per_m2  or "",
                        "warehouse_rent_per_m2": rec.warehouse_rent_per_m2  or "",
                        "number_of_households": rec.number_of_households  or "",
                        "average_household_size": rec.average_household_size  or "",
                        "average_home_size_m2": rec.average_home_size_m2  or "",
                        "percentage_apartments": rec.percentage_apartments  or "",
                        "percentage_rented_homes": rec.percentage_rented_homes  or "",
                        "annual_move_rate": rec.annual_move_rate  or "",
                        "student_population_percentage": rec.student_population_percentage  or "",
                        "migrant_population_percentage": rec.migrant_population_percentage  or "",
                        "short_term_rentals_count": rec.short_term_rentals_count  or "",
                        "demand_intent_level": rec.demand_intent_level  or "",
                        "number_of_competitors": rec.number_of_competitors  or "",
                        "competitor_locations": rec.competitor_locations  or "",
                        "average_rating": rec.average_rating  or "",
                        "review_count": rec.review_count  or "",
                        "price_range_min": rec.price_range_min  or "",
                        "price_range_max": rec.price_range_max  or "",
                        "price_currency": rec.price_currency  or ""
                    }

                    final_prompt = prompt_template.format(**values)            
                    response = client.chat.completions.create(
                        model="gpt-5.2",
                        messages=[
                            {"role": "user", "content": final_prompt}
                        ],
                        response_format={"type": "json_object"},
                        timeout=15
                    )

                    raw_content = response.choices[0].message.content            
                    data = json.loads(raw_content)                     
                    print("\n\n\n data=",data)
                    if 'scoring' in data:
                        scoring = data.get('scoring')
                        if scoring:
                            rec.demand_score = scoring.get('demand_score')
                            rec.growth_score = scoring.get('growth_score')
                            rec.affordability_score = scoring.get('affordability_score')
                            rec.competition_score = scoring.get('competition_score')
                            rec.mobility_score = scoring.get('mobility_score')
                            rec.risk_score = scoring.get('risk_score')


            except json.JSONDecodeError as e:
                _logger.error(
                    "Invalid JSON in Economic Indicators returned by AI for record %s (ID %s). Raw output: %s",
                    rec.name, rec.id, raw_content
                )

    def competition_data_analysis(self):
        for rec in self:
            try:
                if rec.competition_data_prompt:
                    ai_api_key = self.env['ir.config_parameter'].sudo().get_param(
                        'scrapper.ai_key'
                    )
                    client = openai.OpenAI(api_key=ai_api_key)
                    prompt_template = rec.competition_data_prompt or ""

                    values = {
                        "name": rec.name or "",
                    }

                    final_prompt = prompt_template.format(**values)    
                    print("\n\n\n final_prompt=",final_prompt)       
                    response = client.chat.completions.create(
                        model="gpt-5.2",
                        messages=[
                            {"role": "user", "content": final_prompt}
                        ],
                        response_format={"type": "json_object"},
                        timeout=15
                    )

                    raw_content = response.choices[0].message.content            
                    data = json.loads(raw_content)                     
                    print("\n\n\n data=",data)
                    if 'competition_data' in data:
                        competition_data = data.get('competition_data')
                        if competition_data:
                            rec.number_of_competitors = competition_data.get('number_of_competitors')
                            locations_list = competition_data.get('competitor_locations')
                            if locations_list:
                                rec.competitor_locations = ",\n".join(locations_list)
                            else :
                                rec.competitor_locations = None
                            rec.average_rating =  competition_data.get('average_rating')
                            rec.review_count =  competition_data.get('review_count')
                            rec.price_range_min =  competition_data.get('price_range_min')
                            rec.price_range_max =  competition_data.get('price_range_max')
                            rec.price_currency =  competition_data.get('price_currency')
                            compititor_output_reference_list = competition_data.get('compititor_output_reference') 
                            if compititor_output_reference_list:
                                rec.compititor_output_reference = ",\n\n".join(compititor_output_reference_list)
                            else:
                                rec.compititor_output_reference = None
                            rec.all_compititor_store_ai_avg_price = competition_data.get('all_compititor_store_avg_price')
                            rec.calculate_avg_scrappy_store_location_price()
                            if rec.avg_scrappy_store_location_price and rec.all_compititor_store_ai_avg_price:
                                rec.avg_price_scrapp_ai = round( ((rec.avg_scrappy_store_location_price + rec.all_compititor_store_ai_avg_price) / 2),2)

            except json.JSONDecodeError as e:
                _logger.error(
                    "Invalid JSON in Economic Indicators returned by AI for record %s (ID %s). Raw output: %s",
                    rec.name, rec.id, raw_content
                )


  
    def market_demand_analysis(self):
        for rec in self:                           
            # if rec.market_demand_prompt:
            #     ai_api_key = self.env['ir.config_parameter'].sudo().get_param(
            #         'scrapper.ai_key'
            #     )
            #     client = openai.OpenAI(api_key=ai_api_key)
            #     prompt_template = rec.market_demand_prompt or ""    

            #     prompts = [
            #                 {d.id : d.name}
            #                     for d in rec.prompt_ids
            #                 ]
            #     values = {
            #         "name": rec.name or "",
            #         "prompts" : prompts or  "",
            #     }

            #     final_prompt = prompt_template.format(**values)  
                
            #     response = client.chat.completions.create(
            #         model="gpt-5.2",
            #         messages=[
            #             {"role": "user", "content": final_prompt}
            #         ],
            #         response_format={"type": "json_object"},
            #         timeout=15
            #     )

            #     raw_content = response.choices[0].message.content            
            #     data = json.loads(raw_content)                     
            #     print("\n\n\n data=",data)  
            # if data:
            #     prompt = data.get('prompt_ids')
            #     for pr in self.prompt_ids:
            #         pr.count = prompt.get(str(pr.id))                            
            #     rec.demand_intent_level =  data.get('demand_intent_level')

            try:                 
                                
                #------------------------This Is Has Data Searches -------------------------------   
                keywords = ",".join(rec.prompt_ids.mapped('name'))    
                # url = "https://api.hasdata.com/scrape/google-trends/search"
                url = self.env['ir.config_parameter'].sudo().get_param(
                    'scrapper.keywords_url'
                )
                keywords_api = self.env['ir.config_parameter'].sudo().get_param(
                    'scrapper.keywords_key'
                )
                if keywords:
                    headers = {
                        "Content-Type": "application/json",
                        "x-api-key": keywords_api,
                    }
                    params = {
                        "q": keywords,
                        "date" : "today 12-m"
                    }
                    
                    response = requests.get(url, headers=headers, params=params, timeout=300)
                    print("\n\n\n response=",response)

                    if response.status_code == 200 :
                        data = response.json()
                        keyword_totals = defaultdict(int)
                        timeline = data.get("interestOverTime", {}).get("timelineData", [])

                        for entry in timeline:
                            for value in entry.get("values", []):
                                keyword = value.get("query")
                                extracted_value = value.get("extractedValue", 0)
                                keyword_totals[keyword] += extracted_value

                        if keyword_totals:
                            prompt_map = {p.name: p for p in rec.prompt_ids}
                            for kw, value in keyword_totals.items():
                                if kw in prompt_map:
                                    prompt_map[kw].count = value

                        print("\n\n\n keyword_totals",keyword_totals)
                else:
                    _logger.warning("Not Any keyword arrived for counted keyword trends data")

                #-------------------------This IS DataForSEO Searches ---------------------------

                # API call
                # keywords = rec.prompt_ids.mapped('name')
                # if keywords:
                #     url = "https://api.dataforseo.com/v3/keywords_data/google_trends/explore/live"                
                #     payload = [
                #         {
                #             "date_from": "2025-01-01",
                #             "date_to": "2025-12-31",
                #             "keywords": keywords,
                #             "sort_by": "search_volume"
                #         }
                #     ]
                #     headers = {
                #         'Authorization': 'Basic amlnYXJfcC5wcmFqYXBhdGlAYm90c3BvdGluZm93YXJlLmNvbTpkZDJiMjJhNDJkZjMwODI0',
                #         'Content-Type': 'application/json'
                #     }
                #     print("\n\n\n dump=",json.dumps(payload))
                 
                #     response = requests.post(url, headers=headers, data=json.dumps(payload))
                #     print("\n\n\n response=",response)
                #     if response.status_code == 200 :
                #         data = response.json()
                #         print("\n\n\n data=",data)
                        
                #         keyword_totals = {}
                #         tasks = data.get("tasks", [])
                #         if tasks:
                #             results = tasks[0].get("result", [])
                #             for item in results:
                #                 keyword_totals[item.get("keyword")] = item.get("search_volume")

                #         print("\n\n\n keyword_totals=",keyword_totals)      
                #         if keyword_totals:
                #             prompt_map = {p.name: p for p in rec.prompt_ids}
                #             for kw, value in keyword_totals.items():
                #                 if kw in prompt_map:
                #                     prompt_map[kw].count = value                  
    
                #-------------------------This Is Pytrends  Searches ---------------------------
                
                # pytrends = TrendReq(
                #     hl='de-DE',
                #     tz=360,
                #     timeout=(20, 40),
                #     retries=3,
                #     backoff_factor=0.5
                # )

                # pytrends.build_payload(
                #     kw_list=keywords,
                #     timeframe='today 12-m',
                #     geo='DE',
                #     gprop=''   
                # )                       
                # data = pytrends.interest_over_time()                   
               
                # result = {}
                # if data is not None and not data.empty: 
                #     data = data.infer_objects(copy=False)                           
                #     df = data.drop(columns=['isPartial'], errors='ignore')
                #     result = {
                #             kw: int(df[kw].sum())
                #             for kw in keywords  
                #             if kw in df.columns
                #         }
            
                # if result:
                #     prompt_map = {p.name: p for p in rec.prompt_ids}
                #     print("\n\n\n prompt_map=",prompt_map)
                #     for kw, value in result.items():
                #         if kw in prompt_map:
                #             prompt_map[kw].count = value
                #             _logger.info("Trend count set: %s → %s", kw, value)
           
            except Exception as e:
                _logger.warning("\n\n\n\nPytrends failed: %s", e)
                    

           

    def mobility_lifestyle_indicators_analysis(self):
        for rec in self:
            try:
                if rec.mobility_lifestyle_indicators_prompt:
                    ai_api_key = self.env['ir.config_parameter'].sudo().get_param(
                        'scrapper.ai_key'
                    )
                    client = openai.OpenAI(api_key=ai_api_key)
                    prompt_template = rec.mobility_lifestyle_indicators_prompt or ""

                    values = {
                        "name": rec.name or "",
                    }

                    final_prompt =prompt_template.format(**values)                   
                    response = client.chat.completions.create(
                        model="gpt-5.2",
                        messages=[
                            {"role": "user", "content": final_prompt}
                        ],
                        response_format={"type": "json_object"},
                        timeout=15
                    )

                    raw_content = response.choices[0].message.content            
                    data = json.loads(raw_content)                     
                    print("\n\n\n data=",data)
                    if 'mobility_lifestyle_indicators' in data:
                        mobility_data = data.get('mobility_lifestyle_indicators')
                        if mobility_data:
                            rec.annual_move_rate = mobility_data.get('annual_move_rate')
                            rec.student_population_percentage = mobility_data.get('student_population_percentage')
                            rec.migrant_population_percentage = mobility_data.get('migrant_population_percentage')
                            rec.short_term_rentals_count = mobility_data.get('short_term_rentals_count')
                            mobility_output_reference_list = mobility_data.get('mobility_output_reference') 
                            if mobility_output_reference_list:
                                rec.mobility_output_reference = ",\n\n".join(mobility_output_reference_list)
                            else:
                                rec.mobility_output_reference = None

            except json.JSONDecodeError as e:
                _logger.error(
                    "Invalid JSON in Economic Indicators returned by AI for record %s (ID %s). Raw output: %s",
                    rec.name, rec.id, raw_content
                )

    def housing_living_density_analysis(self):
        for rec in self:
            try:
                if rec.housing_living_prompt:
                    ai_api_key = self.env['ir.config_parameter'].sudo().get_param(
                        'scrapper.ai_key'
                    )
                    client = openai.OpenAI(api_key=ai_api_key)
                    prompt_template = rec.housing_living_prompt or ""

                    values = {
                        "name": rec.name or "",
                    }

                    final_prompt = prompt_template.format(**values)                 

                    response = client.chat.completions.create(
                        model="gpt-5.2",
                        messages=[
                            {"role": "user", "content": final_prompt}
                        ],
                        response_format={"type": "json_object"},
                        timeout=15
                    )

                    raw_content = response.choices[0].message.content            
                    data = json.loads(raw_content)                     
                    print("\n\n\n data=",data)
                    if 'housing_living_density' in data:
                        housing_data = data.get('housing_living_density')
                        if housing_data:
                            rec.number_of_households = housing_data.get('number_of_households')
                            rec.average_household_size = housing_data.get('average_household_size')
                            rec.average_home_size_m2 = housing_data.get('average_home_size_m2')
                            rec.percentage_apartments = housing_data.get('percentage_apartments')
                            rec.percentage_rented_homes = housing_data.get('percentage_rented_homes')
                            rec.percentage_own_homes = housing_data.get('percentage_own_homes')
                            housing_density_output_reference_list = housing_data.get('housing_density_output_reference') 
                            if housing_density_output_reference_list:
                                rec.housing_density_output_reference = ",\n\n".join(housing_density_output_reference_list)
                            else:
                                rec.housing_density_output_reference = None

            except json.JSONDecodeError as e:
                _logger.error(
                    "Invalid JSON in Economic Indicators returned by AI for record %s (ID %s). Raw output: %s",
                    rec.name, rec.id, raw_content
                )



    def economic_indicator_analysis(self):
        for rec in self:
            try:
                if rec.economic_indicator_prompt:
                    ai_api_key = self.env['ir.config_parameter'].sudo().get_param(
                        'scrapper.ai_key'
                    )
                    client = openai.OpenAI(api_key=ai_api_key)


                    prompt_template = rec.economic_indicator_prompt or ""

                    values = {
                        "name": rec.name or "",
                    }

                    final_prompt = prompt_template.format(**values)
                    print("\n\n\n final_prompt",final_prompt)
                    response = client.chat.completions.create(
                        model="gpt-5.2",
                        messages=[
                            {"role": "user", "content": final_prompt}
                        ],
                        response_format={"type": "json_object"},
                        timeout=15
                    )

                    raw_content = response.choices[0].message.content            
                    data = json.loads(raw_content)                     
                    print("\n\n\n data=",data)
                    if 'economic_indicators' in data:
                        economic_data = data.get('economic_indicators')
                        if economic_data:
                            rec.average_income = economic_data.get('average_income')
                            rec.average_commercial_rent_per_m2 = economic_data.get('average_commercial_rent_per_m2')
                            rec.warehouse_rent_per_m2 = economic_data.get('warehouse_rent_per_m2')
                            economic_output_reference_list = economic_data.get('economic_output_reference')                            
                            if economic_output_reference_list:
                                rec.economic_output_reference = ",\n\n".join(economic_output_reference_list)
                            else :
                                rec.economic_output_reference = None

            except json.JSONDecodeError as e:
                _logger.error(
                    "Invalid JSON in Economic Indicators returned by AI for record %s (ID %s). Raw output: %s",
                    rec.name, rec.id, raw_content
                )

    def _compute_district_town(self):
        for rec in self:
            town_ids = rec.town_ids.mapped('town_id').ids
            rec.town_count = len(town_ids)
            

    def _compute_district_compititors(self):
        for rec in self:
            competition_store = rec.env['scraped.store.data.line'].search([('district_id','=',self.id)]).mapped('scraper_store_id')
            rec.competition_store = len(competition_store)

            
    def action_view_towns(self):
        self.ensure_one()
        town_ids = self.town_ids.mapped('town_id').ids
               
        return {
            'type': 'ir.actions.act_window',
            'name': 'Competitor Store Towns',
            'res_model': 'scraped.store.data.line',
            'view_mode': 'tree,form',
            'views': [
                (self.env.ref(
                    'bsi_competitor_scraper.view_scraped_store_data_line_tree'
                ).id, 'tree')
            ],
            'domain': [('town_id', 'in',town_ids),('district_id','=',self.id)],
            'context': {
                'default_district_id': self.id,
                'search_default_group_by_compititor_town':1,
                'search_default_group_by_store' : 1
            }
        }

    def action_view_competitor(self):
        self.ensure_one()
                      
        return {
            'type': 'ir.actions.act_window',
            'name': 'Competitor Store Towns',
            'res_model': 'scraped.store.data.line',
            'view_mode': 'tree,form',
            'views': [
                (self.env.ref(
                    'bsi_competitor_scraper.view_scraped_store_data_line_tree'
                ).id, 'tree')
            ],
            'domain': [('district_id','=',self.id)],
            'context': {
                'default_district_id': self.id,
                'search_default_group_by_store' : 1
            }
        }
    


class StoreTown(models.Model):
    _name = 'scraper.store.town'
    _description = 'Town/District List'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    scraper_store_ids = fields.Many2many(
            'scraper.store',
            string='Competitor Store',
            help=(
            "Stores the competitor store record that was fetched via the Scrapy "
            "data extraction process. This field links the scraped data to the "
            "corresponding competitor store."
        ),
        tracking=True
    )

    name = fields.Char(
        string='Input Address',
        required=True, help="Stores the name of the town associated with the competitor store."
    )

    town_id = fields.Many2one('compititor.store.towns',string="Town")

    product_count = fields.Integer(compute="_compute_product_data_count",
    help=(
        "Shows the total number of products available for the selected "
        "competitor store in this town."
    ))

    town_district_id = fields.Many2one(
        'scraper.store.district',
        string='District',
        required=False,
        help='The district to which this town belongs',
        tracking=True
    )
    town_name = fields.Char(string='Town',tracking=True)
    address = fields.Char(string='Address',tracking=True)
    zip_code = fields.Char(string='Zip Code',tracking=True)
    state_id = fields.Many2one("res.country.state",string="State",tracking=True)
    country_id = fields.Many2one("res.country",string="Country",tracking=True)

    company_id = fields.Many2one('res.company',string="Company",tracking=True)
    status = fields.Selection([('draft','Draft'),('verified','Verified')], 
            default='draft',
            help="Current status of the store address in ai executed or not",string="Status",tracking=True)

    address_prompt = fields.Text(String="Address Filtering",default="""
        
        Forced-State Extraction Prompt

        You are an address parser and company matcher.

        Input:
        "{name}"

        Tasks:
       Peter-Grieß-Straße 12-18, 51061 Köln, Deutschland 

        Extract and return the following structured location components:

        Full street address

        House/building number

        Street name

        actual not neighbouring District 

        Town / City

        State / Region

        Postal code / ZIP

        Country

        Format the output as JSON with field names exactly as above. Include null for any field that cannot be determined.

              Company Matching:

        Compare this address with company locations:
        {company_ids}

        If no deterministic match → company_id = false

        Output JSON (all fields must be filled):

        {{
          "company_id": false,
          "address": "{name}",
          "zip": "FILL_HERE",
          "town_name": "FILL_HERE",
          "district": "FILL_HERE",
          "state_name": "FILL_HERE",
          "country_name": "FILL_HERE"
        }}


        Important Notes:

        Never leave any field null.

        Mandatory inference order for state_name and country_name:

        Look in the input text for state/country.

        If missing, look up the town/city name.

        If still missing, use the postal/ZIP code.

        Always use exact text from input for address and other fields if available.

        company_id = false if no exact match, but all other fields must be filled.

        """)

    def _compute_product_data_count(self):
        for rec in self:
            count = rec.env['scraped.store.data.line'].search_count([
                ('store_location_id', '=', rec.id)])
            rec.product_count = count

    def action_view_products(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Scraped Competitor Data',
            'res_model': 'scraped.store.data.line',
            'view_mode': 'tree,form',
            'views': [
                (self.env.ref(
                    'bsi_competitor_scraper.view_scraped_store_data_line_tree'
                ).id, 'tree')
            ],
            'domain': [('store_location_id', '=', self.id)],
            'context': {
                'default_store_location_id': self.id,
                'search_default_group_by_store' : 1
            }
        }

    def towns_create(self):
        st_id = self.env['scraper.store.town'].search([])
        tn_id = self.env['compititor.store.towns']
        if st_id:
            for rec in st_id:
                if rec.town_name:
                    town_id = tn_id.search([('name','=',rec.town_name)])
                    if town_id:
                        rec.town_id = town_id.id
                    else:
                        rec.town_id = tn_id.create({'name' : rec.town_name})

    def status_assign(self):
        for rec in self:
            rec.write({
                 'status': 'verified'
                })

    def adress_filtering(self):
        ai_api_key = self.env['ir.config_parameter'].sudo().get_param('scrapper.ai_key')
        if not ai_api_key:
            _logger.error(
                    "AI API key is missing! %s (ID %s): %s",rec.id )

        client = openai.OpenAI(api_key=ai_api_key)

        District = self.env['scraper.store.district'].sudo()
        district_cache = {
            d.name.lower(): d.id for d in District.search([])
        }
        company_domain = self.env['res.company'].sudo()
        company_ids = {
                       c.id : [c.name.lower(),c.location_name.lower()] for c in company_domain.search([])  if c.location_name
                    }
        
        for rec in self: 
            if not rec.name:
                continue

            if all([
                rec.town_name,
                rec.address,
                rec.zip_code,
                rec.company_id,
                rec.town_district_id,
                rec.country_id,
                rec.state_id,
            ]):
                print("\n\n\n ===========continue===============")
                continue
            
            try:       
                final_prompt = rec.address_prompt    
                values = {
                    'name' : rec.name,
                    'company_ids' : company_ids
                }
                print("\n\n\n final =",final_prompt.format(**values) )
                response = client.chat.completions.create(
                    model="gpt-5.2",
                    messages=[
                        {"role": "user", "content": final_prompt.format(**values)}
                    ],
                    response_format={"type": "json_object"},
                    timeout=10
                )
                data = json.loads(response.choices[0].message.content)
               
                print("\ndata=",data)
                rec.write({
                    "zip_code": data.get("zip"),
                    "address": data.get("address"),
                })

                town = data.get("town_name")
                if town:
                    town_id = rec.env['compititor.store.towns'].search([('name','=',town)])
                    if town_id:
                        rec.town_id = town_id.id
                    else:
                        rec.town_id = rec.env['compititor.store.towns'].create({'name':town})
                
                district = data.get("district")               
                if district:
                    key = district.strip().lower()
                    district_id = district_cache.get(key)
                   
                    if not district_id:
                        district_id = District.create({"name": district})
                        rec.town_district_id = district_id.id                        
                    else:
                        rec.town_district_id = district_id
                else:
                    rec.town_district_id = False

                company_json_id = data.get("company_id")
                mapping = rec.env['scraper.company.town.mapping']
               
                old_company = rec.company_id.id if rec.company_id else False
                
                if old_company and old_company != company_json_id:
                    old_mapping = mapping.search(
                        [('company_id', '=', old_company)],
                        limit=1
                    )
                    if old_mapping:
                        old_mapping.town_ids = [(3, rec.id)]
               
                if not rec.company_id or rec.company_id.id != company_json_id:
                    rec.company_id = company_json_id
               
                new_mapping = mapping.search(
                    [('company_id', '=', company_json_id)],
                    limit=1
                )
                if new_mapping:
                    new_mapping.town_ids = [(4, rec.id)]
                
                country_json_name = data.get("country_name")  
                if country_json_name:
                    country_id = self.env['res.country'].sudo().search([('name','=',country_json_name)],limit=1)
                    if country_id:
                        rec.country_id = country_id.id
                else:
                    rec.country_id = False
 
                state_name = data.get("state_name")               
                if state_name:
                    state_id = self.env['res.country.state'].sudo().search([('name','=',state_name)],limit=1)
                    if state_id:                       
                        rec.state_id = state_id.id if state_id else False
                    else:                  
                        if rec.country_id :
                            rec.state_id = self.env['res.country.state'].sudo().create({
                                        'name' :state_name,
                                        'code' : rec.country_id.code + "".join(state_name.strip().split()[:2]),
                                        'country_id' : rec.country_id.id 
                            })
                else :
                    rec.state_id = False

            except Exception as e:
                _logger.error(
                    "AI address parsing failed for record %s (ID %s): %s",
                    rec.name, rec.id, str(e)
                )
                continue

