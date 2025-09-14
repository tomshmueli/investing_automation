# Alpha vintage api key
import os

# Logging Configuration
LOG_LEVEL = "INFO"  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "results", "Runtime_Logs.log")  # Set to None to disable file logging
LOG_TO_CONSOLE = True  # Set to False to disable console logging

# Scoring Thresholds
CASH_TO_DEBT_THRESHOLD = 1          # Cash > Debt
DEBT_TO_EQUITY_THRESHOLD = 1        # Debt > Equity
ASSETS_TO_DEBT_RATIO = 2            # Total Assets / Total Debt
CONSECUTIVE_GROWTH_QUARTERS = 3     # Growth trend quarters
ROE_LOW = 0.08                      # 8% threshold for ROE
ROE_HIGH = 0.15                     # 15% threshold for ROE
GROSS_MARGIN_LOW = 0.3              # 30% threshold for Gross Margin
GROSS_MARGIN_MED = 0.5              # 50% threshold for Gross Margin
GROSS_MARGIN_HIGH = 0.8             # 80% threshold for Gross Margin


# Thresholds for Operating Leverage
CAPEX_THRESHOLD_HIGH = 1.5
CAPEX_THRESHOLD_LOW = 1.0
S_AND_M_THRESHOLD_HIGH = 0.5
S_AND_M_THRESHOLD_LOW = 0.3
R_AND_D_THRESHOLD_HIGH = 0.25
R_AND_D_THRESHOLD_LOW = 0.15

# Example file path for the Google Sheet
EXCEL_NAME = "my_Portfolio_Dashboard"
PORTFOLIO_SHEET_NAME = "Portfolio"  # The sheet responsible for storing the tickers
FEROLDI_SHEET_NAME = "Scores" # The sheet responsible for storing the Feroldi Scores / checklist
START_COL = 4  # Column index where tickers start in the sheet
FINANCIAL_ROWS = {
    "Resilience Score": 5,     # Row for Resilience Score
    "Gross Margin Score": 6,  # Row for Gross Margin Score
    "ROE Score": 7,           # Row for ROE Score
    "FCF Score": 8,           # Row for Free Cash Flow Score
    "EPS Score": 9,           # Row for EPS Score
}


# calculate operating leverage
POTENTIAL_ROWS = {
    "Optionality Score": 18,  # Row for Optionality score , manually calculated
    "Organic Growth Score": 19,    # row for Organic Growth
    "Top Dog Score": 20,    # Row for Top Dog and first mover , manually calculated
    "Operating Leverage Score": 21,  # Row for Operating Leverage
}
MIN_REVENUE_CHANGE = 0.02  # Ignore changes smaller than 2%

# Constants for Customers Scoring
CUSTOMERS_ROWS = {
    "Acquisitions Score": 23,
    "Dependence Score": 24,
}

# Constants for Specific Factors Scoring
SPECIFIC_FACTORS_ROWS = {
    "Recurring Revenue Score": 26,  # Row for Recurring Revenue Score (0-5)
    "Pricing Power Score": 27,      # Row for Pricing Power Score (0-5)
}

# Pricing Power (Gross Margin analysis)
# --------------------------------------------------------------------------
PRICING_POWER_HIGH_MARGIN = 70.0  # Exceptional margin threshold (e.g., >70%)
PRICING_POWER_MODERATE_MARGIN = 50.0  # High margin threshold (e.g., >50%)
PRICING_POWER_AVG_MARGIN = 30.0 # Average margin threshold (e.g., >30%)
PRICING_POWER_LOW_MARGIN = 20.0  # Low margin threshold (e.g., <20%)

PRICING_POWER_LOW_VOLATILITY = 3.0  # Std dev of margins < 3 is low
PRICING_POWER_HIGH_VOLATILITY = 5.0  # High volatility threshold (stdev > 5)
PRICING_POWER_TREND_THRESHOLD = 1.0  # Trend significance threshold (>1% change)

MANAGEMENT_ROWS = {
    "Soul in the Game Score": 29,
    "Inside Ownership Score": 30,
    "Glassdoor Ratings Score": 31,
    "Mission Statement Score": 32,
}
RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "results")
MISSION_STATEMENTS_FILE = os.path.join(RESULTS_DIR, "mission_statements.txt")

# stock section constants
SP500_TICKER = "^GSPC"
PERFORMANCE_MARGIN_INLINE = 0 # 10% margin to consider inline
PERFORMANCE_THRESHOLD_50 = 0.5
PERFORMANCE_THRESHOLD_100 = 1.0

STOCK_ROWS = {
    "5-Year Performance Score": 34,
    "Shareholder Friendly Actions Score": 35,
    "Consistently Beats Expectations Score": 36,
}

# Constants for Penalties Section
PENALTIES_ROWS = {
    "Accounting Irregularities": 39,  # (-10)
    "Customer Concentration": 40,     # (-5, -3, 0)
    "Industry Disruption": 41,       # (-5, -3, 0)
    "Outside Forces": 42,            # (-5, -3, 0)
    "Big Market Loser": 43,          # (-5, -3, 0)
    "Binary Events": 44,             # (-5, 0)
    "Extreme Dilution": 45,          # (-4, -2, 0)
    "Growth By Acquisition": 46,      # (-4, -2, 0)
    "Complicated Financials": 47,     # (-3, 0)
    "Antitrust Concerns": 48,        # (-3, 0)
    "Headquarters Risk": 49,         # (-3, -2, 0)
}

# Penalty Score Thresholds
ACCOUNTING_IRREGULARITIES_PENALTY = -10  # Fixed penalty for accounting issues

# Customer Concentration Penalties
CUSTOMER_CONCENTRATION_SEVERE = -5    # >20% revenue from single customer
CUSTOMER_CONCENTRATION_MODERATE = -3  # >10% revenue from single customer
CUSTOMER_CONCENTRATION_NONE = 0       # No significant concentration

# Industry Disruption Penalties
INDUSTRY_DISRUPTION_ACTIVE = -5      # Active disruption
INDUSTRY_DISRUPTION_POSSIBLE = -3    # Possible disruption
INDUSTRY_DISRUPTION_NONE = 0         # No disruption

# Outside Forces Penalties
OUTSIDE_FORCES_SEVERE = -5           # Severe exposure
OUTSIDE_FORCES_MODERATE = -3         # Moderate exposure
OUTSIDE_FORCES_NONE = 0              # Limited exposure

# Binary Events Penalties
BINARY_EVENTS_SEVERE = -5            # Critical binary event
BINARY_EVENTS_NONE = 0               # No binary events

# Share Dilution Penalties
SHARE_DILUTION_EXTREME_PENALTY = -4  # >5% annual growth
SHARE_DILUTION_MODERATE_PENALTY = -2 # 3% to 5% growth
SHARE_DILUTION_NONE = 0              # <3% growth

# Growth by Acquisition Penalties
ACQUISITION_GROWTH_EXCLUSIVE = -4    # Growth exclusively through acquisitions
ACQUISITION_GROWTH_PARTIAL = -2      # Partial growth through acquisitions
ACQUISITION_GROWTH_NONE = 0          # Organic growth

# Complicated Financials Penalties
FINANCIALS_COMPLEX = -3              # Complex financials
FINANCIALS_NORMAL = 0                # Normal financials

# Antitrust Penalties
ANTITRUST_CONCERNS_SEVERE = -3       # Significant concerns
ANTITRUST_CONCERNS_NONE = 0          # No concerns

# Headquarters Risk Penalties
HEADQUARTERS_HIGH_RISK = -3          # High risk country
HEADQUARTERS_MEDIUM_RISK = -2        # Medium risk country
HEADQUARTERS_LOW_RISK = 0            # Low risk country

# Thresholds for Share Dilution
SHARE_DILUTION_HIGH = 0.05  # 5%+ Annual Share Count Growth
SHARE_DILUTION_MEDIUM = 0.03  # 3% to 5% Growth

# Thresholds for Customer Concentration
CUSTOMER_CONCENTRATION_THRESHOLD = 0.20  # 20% of Revenue or AR from One/Few
CUSTOMER_CONCENTRATION_SIGNIFICANT = 0.10  # >10% considered significant

# Market Performance Thresholds
MARKET_UNDERPERFORM_SEVERE = 0.50  # 50% Loss to S&P500
MARKET_UNDERPERFORM_SIGNIFICANT = 0.30  # 30% Loss to S&P500
MARKET_COMPARISON_YEARS = 5  # Number of years to compare

# Currency Risk Thresholds
CURRENCY_RISK_HIGH = 0.75  # >75% Foreign
CURRENCY_RISK_MEDIUM = 0.50  # >50% Foreign

# Country Risk Categories
HIGH_RISK_COUNTRIES = [
    'venezuela', 'iran', 'iraq', 'libya', 'nigeria',"North Korea",
    'democratic republic of congo', 'zimbabwe', 'syria',
    'yemen', 'afghanistan', 'myanmar', 'north korea',
    'cuba', 'sudan', 'south sudan', 'somalia'
]

MEDIUM_RISK_COUNTRIES = [
    'brazil', 'russia', 'india', 'china', 'mexico',
    'indonesia', 'turkey', 'south africa', 'argentina',
    'colombia', 'thailand', 'vietnam', 'philippines',
    'malaysia', 'egypt', 'pakistan', 'bangladesh',
    'ukraine', 'belarus', 'kazakhstan'
]

# Outside Forces Risk Weights
OUTSIDE_FORCES_WEIGHTS = {
    "commodity_prices": 0.3,
    "interest_rates": 0.3,
    "stock_market": 0.2,
    "economy": 0.2
}

# Cache settings
CACHE_EXPIRY_DAYS = 15  # Cache expires after 1 day

# Market Performance Thresholds
MARKET_UNDERPERFORM_MODERATE = 0.30  # 30% underperformance
MARKET_UNDERPERFORM_MINOR = 0.20  # 20% underperformance
MARKET_UNDERPERFORM_SLIGHT = 0.10  # 10% underperformance

# Share Dilution Thresholds
SHARE_DILUTION_EXTREME = 0.10  # >10% annual growth
SHARE_DILUTION_SEVERE = 0.07  # 7-10% annual growth
SHARE_DILUTION_SIGNIFICANT = 0.05  # 5-7% annual growth
SHARE_DILUTION_MODERATE = 0.03  # 3-5% annual growth

# Commodity Dependencies
CRITICAL_COMMODITIES = {
    'metals': [
        ('copper', ['copper price', 'copper production', 'copper mining']),
        ('gold', ['gold price', 'gold production', 'gold mining']),
        ('silver', ['silver price', 'silver production', 'silver mining']),
        ('iron ore', ['iron ore']),
        ('aluminum', ['aluminum price', 'aluminum production']),
        ('nickel', ['nickel price', 'nickel production']),
        ('zinc', ['zinc price', 'zinc production']),
        ('platinum', ['platinum price', 'platinum production']),
        ('palladium', ['palladium price', 'palladium production']),
        ('lithium', ['lithium price', 'lithium production']),
        ('uranium', ['uranium price', 'uranium production'])
    ],
    'energy': [
        ('crude oil', ['oil price', 'oil production', 'oil exploration']),
        ('natural gas', ['gas price', 'gas production', 'gas exploration']),
        ('coal', ['coal price', 'coal production', 'coal mining']),
        ('petroleum', ['petroleum price', 'petroleum production']),
        ('oil and gas', ['oil and gas production', 'oil and gas exploration'])
    ]
}

# Critical Industries
CRITICAL_INDUSTRIES = {
    'mining': [
        'mining operations', 'mineral reserves', 'ore deposits',
        'mining production', 'mineral exploration'
    ],
    'oil_gas': [
        'oil production', 'gas production', 'oil and gas operations',
        'drilling operations', 'exploration and production'
    ]
}

# Regulatory Keywords
REGULATORY_KEYWORDS = [
    'regulatory approval', 'regulatory compliance', 'government regulation',
    'regulatory requirements', 'regulatory framework', 'regulatory oversight'
]

# Antitrust Patterns
ANTITRUST_PATTERNS = [
    # Direct mentions of antitrust investigations/litigation
    r'antitrust.{0,50}(investigation|proceeding|litigation|lawsuit|complaint|allegation)',
    r'anti.?competitive.{0,50}(investigation|proceeding|litigation|lawsuit|complaint|allegation)',
    r'competition law.{0,50}(investigation|proceeding|litigation|lawsuit|complaint|allegation)',
    r'monopol.{0,50}(investigation|proceeding|litigation|lawsuit|complaint|allegation)',
    
    # Specific regulatory authorities + investigation
    r'(doj|department of justice).{0,100}antitrust',
    r'(ftc|federal trade commission).{0,100}antitrust',
    r'(ec|european commission).{0,100}competition',
    
    # Material penalties or settlements
    r'antitrust.{0,100}(fine|penalty|settlement).{0,50}(million|billion)',
    r'competition.{0,100}(fine|penalty|settlement).{0,50}(million|billion)',
    
    # Simpler patterns (less restrictive)
    r'antitrust\s+litigation',
    r'antitrust\s+settlement',
    r'antitrust\s+(matters|cases|issues|concerns)',
    r'competition\s+law\s+proceedings'
]

# Negative patterns for antitrust checks
ANTITRUST_NEGATIVE_PATTERNS = [
    r'not\s+material',
    r'no\s+material',
    r'no\s+pending.*antitrust',
    r'boilerplate',
    r'forward.looking\s+statement',
    r'not\s+party\s+to.*antitrust'
]

# Acquisition Keywords
ACQUISITION_KEYWORDS = [
    "growth through acquisition",
    "acquisition strategy",
    "acquisition program",
    "acquisition pipeline",
    "acquisition targets",
    "acquisition opportunities",
    "acquisition growth",
    "acquisition-driven",
    "acquisition-based"
]

# Acquisition Spending Thresholds
ACQUISITION_SPENDING_EXTREME = 0.40  # >40% of operating cash flow
ACQUISITION_SPENDING_SEVERE = 0.30  # 30-40% of operating cash flow
ACQUISITION_SPENDING_SIGNIFICANT = 0.20  # 20-30% of operating cash flow
ACQUISITION_SPENDING_MODERATE = 0.10  # 10-20% of operating cash flow


# Maximum possible scores for each business segment (for logging and reporting)
SEGMENT_MAX_SCORES = {
    'Financials': 14,
    'Moat': 20,
    'Potential': 18,
    'Customers': 10,
    'Company-specific factors': 10,
    'Management & Culture': 14,
    'Stock': 11,
    'Penalties': 0  # Penalties are negative, so max is 0
}
