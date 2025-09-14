import re
import logging
from datetime import datetime
from Checklist.utils import (
    get_latest_10k, 
    get_cash_flow_data, 
    nlp_analyzer, 
    extract_percentage_sentences, 
    is_nlp_available,
    setup_logging
)
from Checklist.settings import (
    CUSTOMER_CONCENTRATION_THRESHOLD,
    CUSTOMER_CONCENTRATION_SIGNIFICANT,
    HIGH_RISK_COUNTRIES,
    MEDIUM_RISK_COUNTRIES,
    MARKET_UNDERPERFORM_SEVERE,
    MARKET_UNDERPERFORM_SIGNIFICANT,
    MARKET_UNDERPERFORM_MODERATE,
    MARKET_UNDERPERFORM_MINOR,
    MARKET_UNDERPERFORM_SLIGHT,
    SHARE_DILUTION_EXTREME,
    SHARE_DILUTION_SEVERE,
    SHARE_DILUTION_SIGNIFICANT,
    SHARE_DILUTION_MODERATE,
    CRITICAL_COMMODITIES,
    CRITICAL_INDUSTRIES,
    REGULATORY_KEYWORDS,
    ANTITRUST_PATTERNS,
    ANTITRUST_NEGATIVE_PATTERNS,
    ACQUISITION_KEYWORDS,
    ACQUISITION_SPENDING_EXTREME,
    ACQUISITION_SPENDING_SEVERE,
    ACQUISITION_SPENDING_SIGNIFICANT,
    ACQUISITION_SPENDING_MODERATE,
    SEGMENT_MAX_SCORES
)
import yfinance as yf
from Checklist.utilities.logging_config import get_logger, log_score, log_data_issue, log_segment_start, log_segment_complete, log_debug

logger = get_logger(__name__)

def check_customer_concentration(ticker):
    """
    Enhanced customer concentration check using smart business rules
    
    Analyzes SEC filings (10-K) for customer concentration disclosures.
    Companies are required to disclose customers that account for >10% of revenue.
    
    SIMPLIFIED SCORING - Only penalizes material concentration risks:
    -5: EXTREME RISK (single customer >50% OR top 2 customers >70%)
    -3: MODERATE RISK (single customer >25% OR top 3 customers >50%) 
     0: NO SIGNIFICANT CONCENTRATION (everything else)
    
    Returns:
        int: Penalty score (-5, -3, or 0), or None for manual review
    """
    log_debug(f"Checking customer concentration for {ticker}")
    
    try:
        filing = get_latest_10k(ticker)
        if not filing:
            log_data_issue(ticker, "Could not fetch latest 10-K", "Customer concentration check skipped")
            return None
            
        filing_text = filing['text']
        
        required_terms = {
            'customer': ['customer', 'customers', 'client', 'clients', 'account', 'accounts'],
            'revenue': ['revenue', 'revenues', 'sales', 'income', 'receipts', 'billing']
        }
        
        customer_type_classifiers = {
            'single': ['customer', 'client', 'a customer', 'one customer', 'single customer', 'largest customer'],
            'multiple': ['customers', 'clients', 'accounts', 'top customers', 'major customers']
        }
        
        if is_nlp_available():
            return _check_concentration_nlp_enhanced(ticker, filing_text, required_terms, customer_type_classifiers)
        else:
            return _check_concentration_enhanced_analysis(ticker, filing_text, required_terms, customer_type_classifiers)
            
    except Exception as e:
        logger.error(f"Error checking customer concentration for {ticker}: {e}")
        log_data_issue(ticker, f"Customer concentration check failed: {str(e)}", "Returning None")
        return None

def _check_concentration_nlp_enhanced(ticker: str, filing_text: str, required_terms: dict, customer_type_classifiers: dict):
    """NLP-enhanced customer concentration detection with semantic understanding"""
    try:
        log_debug(f"Using NLP-enhanced customer concentration analysis for {ticker}")
        
        sentences_with_percentages = nlp_analyzer.extract_sentences_with_numbers(filing_text)
        customer_concentration_findings = []
        
        for sentence, percentages in sentences_with_percentages:
            for percentage in percentages:
                finding = nlp_analyzer.analyze_sentence_context(
                    sentence, 
                    [percentage], 
                    required_terms, 
                    customer_type_classifiers
                )
                
                if finding and finding.is_actual:
                    customer_concentration_findings.append({
                        'value': finding.value,
                        'context': finding.context[:200],
                        'confidence': finding.confidence,
                        'finding_type': finding.finding_type,
                        'sentence': finding.sentence[:300]
                    })
        
        if not customer_concentration_findings:
            return _check_concentration_enhanced_patterns(ticker, filing_text)
        
        customer_concentration_findings.sort(key=lambda x: x['value'], reverse=True)
        top_finding = customer_concentration_findings[0]
        
        log_debug(f"NLP Analysis - Customer concentration found for {ticker}: {top_finding['value']}% (confidence: {top_finding['confidence']:.2f})")
        
        return _score_concentration_enhanced(top_finding, customer_concentration_findings)
        
    except Exception as e:
        logger.error(f"Error in NLP customer concentration analysis for {ticker}: {e}")
        return _check_concentration_enhanced_analysis(ticker, filing_text, required_terms, customer_type_classifiers)

def _check_concentration_enhanced_patterns(ticker: str, filing_text: str):
    """Enhanced pattern matching for complex disclosure formats like TSM"""
    try:
        text_lower = filing_text.lower()
        
        enhanced_patterns = [
            # "largest customer...accounted for 23%, 25% and 22% of our net revenue"
            r'(?:largest|biggest)\s+(?:customer|client)[^.]{0,300}accounted\s+for[^.]{0,100}(\d{1,2})\s*%[^.]{0,20}(\d{1,2})\s*%[^.]{0,30}(\d{1,2})\s*%[^.]{0,100}(?:net\s+)?revenue',
            
            # "customer accounted for 25% of revenue in 2024"  
            r'(?:customer|client)[^.]{0,100}accounted\s+for[^.]{0,50}(\d{1,2})\s*%[^.]{0,100}revenue[^.]{0,50}(?:in\s+)?(?:2024|2023)',
            
            # "Our largest customer represented 22% of total revenue"
            r'(?:largest|biggest)\s+(?:customer|client)[^.]{0,100}represented[^.]{0,50}(\d{1,2})\s*%[^.]{0,100}(?:total\s+)?revenue'
        ]
        
        findings = []
        
        for pattern in enhanced_patterns:
            matches = list(re.finditer(pattern, text_lower))
            for match in matches:
                percentages = [float(group) for group in match.groups() if group and group.isdigit()]
                if percentages:
                    latest_percentage = max(percentages)
                    start = max(0, match.start() - 200)
                    end = min(len(filing_text), match.end() + 200)
                    context = filing_text[start:end]
                    
                    findings.append({
                        'value': latest_percentage,
                        'context': context[:200],
                        'confidence': 0.95,
                        'finding_type': 'single',
                        'sentence': match.group()[:300]
                    })
        
        if not findings:
            log_debug(f"Enhanced Patterns - No customer concentration found for {ticker}")
            return 0
        
        findings.sort(key=lambda x: x['value'], reverse=True)
        top_finding = findings[0]
        
        log_debug(f"Enhanced Patterns - Customer concentration found for {ticker}: {top_finding['value']}%")
        
        return _score_concentration_enhanced(top_finding, findings)
        
    except Exception as e:
        logger.error(f"Error in enhanced pattern analysis for {ticker}: {e}")
        return 0

def _check_concentration_enhanced_analysis(ticker: str, filing_text: str, required_terms: dict, customer_type_classifiers: dict):
    """Enhanced regex-based customer concentration check with smart business rules"""
    try:
        geographic_exclusions = [
            r'(?:outside|from|in).*(?:united states|us|u\.s\.|usa)',
            r'international.*(?:customers?|revenue|sales)',
            r'foreign.*(?:customers?|revenue|sales|operations)',
            r'overseas.*(?:customers?|revenue|sales)',
            r'geographic(?:al)?.*(?:revenue|sales|distribution)',
            r'(?:north america|europe|asia|americas?).*(?:revenue|sales)'
        ]
        
        procedural_exclusions = [
            r'audit.*procedures',
            r'accounting.*(?:policies|procedures)',
            r'revenue.*recognition',
            r'internal.*controls',
            r'(?:ifrs|gaap|accounting).*standards'
        ]
        
        distribution_exclusions = [
            r'(?:direct|indirect).*(?:distribution|sales|channels?)',
            r'distribution.*channels?',
            r'sales.*channels?',
            r'through.*(?:distributors?|resellers?|partners?)'
        ]
        
        equity_exclusions = [
            r'equity.*(?:awards?|compensation)',
            r'stock.*(?:options?|compensation|based)',
            r'employee.*(?:stock|equity)',
            r'share.*based.*compensation',
            r'stock-based.*compensation'
        ]
        
        strong_concentration_patterns = [
            # Direct customer concentration statements
            r'(?:largest|biggest|major|primary|principal)\s+(?:customer|client|tenant)\s+(?:accounted for|represented)\s+(?:approximately\s+)?(\d{1,2}(?:\.\d{1,2})?)\s*%',
            r'(?:one|single|a)\s+(?:customer|client|tenant)\s+(?:accounted for|represented)\s+(?:approximately\s+)?(\d{1,2}(?:\.\d{1,2})?)\s*%',
            r'(?:customer|client|tenant)\s+(?:that\s+)?(?:accounted for|represented)\s+(?:approximately\s+)?(\d{1,2}(?:\.\d{1,2})?)\s*%',
            
            # ENHANCED: Real-world "represented X% of" patterns
            r'(?:customer|client|tenant)[^.]{0,100}represented\s+(?:approximately\s+)?(\d{1,2}(?:\.\d{1,2})?)\s*%[^.]{0,50}(?:of\s+our\s+)?(?:revenue|sales|rent)',
            r'represented\s+(?:approximately\s+)?(\d{1,2}(?:\.\d{1,2})?)\s*%[^.]{0,100}(?:of\s+our\s+)?(?:total\s+)?(?:revenue|sales|rent)',
            
            # TSM-specific pattern: "largest customer...accounted for 23%, 25% and 22% of our net revenue"
            r'(?:largest|biggest)\s+(?:customer|client)[^.]{0,200}accounted\s+for[^.]{0,100}(\d{1,2})\s*%[^.]{0,50}(?:of\s+our\s+)?(?:net\s+)?(?:revenue|sales)',
            
            # ENHANCED: Multiple customer concentration (real TSM/PLTR patterns)
            r'(?:top|largest)\s+(?:three|four|five|ten|\d+)\s+(?:customers?|clients?|tenants?)[^.]{0,100}(?:accounted for|represented)\s+(?:approximately\s+)?(\d{1,2}(?:\.\d{1,2})?)\s*%',
            r'(?:ten|twenty|\d+)\s+largest\s+(?:customers?|clients?|tenants?)[^.]{0,100}(?:accounted for|represented)\s+(?:approximately\s+)?(\d{1,2}(?:\.\d{1,2})?)\s*%',
            
            # Government/agency concentration (common in defense, aerospace)
            r'(?:government|federal|military|defense|agency|agencies)\s+(?:contracts?|sales|revenue)\s+(?:accounted for|represented)\s+(?:approximately\s+)?(\d{1,2}(?:\.\d{1,2})?)\s*%',
            r'(?:u\.s\.|united states)\s+government\s+(?:accounted for|represented)\s+(?:approximately\s+)?(\d{1,2}(?:\.\d{1,2})?)\s*%',
            
            # Cloud/hyperscaler concentration (tech companies)
            r'(?:cloud|hyperscaler|data center)\s+(?:customers?|providers?)\s+(?:accounted for|represented)\s+(?:approximately\s+)?(\d{1,2}(?:\.\d{1,2})?)\s*%',
            r'(?:amazon|microsoft|google|meta|alibaba)\s+(?:accounted for|represented)\s+(?:approximately\s+)?(\d{1,2}(?:\.\d{1,2})?)\s*%',
            
            # Revenue percentage from customer perspective  
            r'(\d{1,2}(?:\.\d{1,2})?)\s*%\s+of\s+(?:our\s+)?(?:total\s+)?(?:revenue|sales|rent).*(?:from|was from|came from).*(?:one|single|largest|major|government)\s+(?:customer|client|tenant|contract)',
            
            # Concentration disclosure patterns
            r'no\s+(?:single\s+)?(?:customer|client|tenant)\s+(?:accounted for|represented)\s+more\s+than\s+(\d{1,2}(?:\.\d{1,2})?)\s*%',
            r'concentration\s+of\s+credit\s+risk.*(\d{1,2}(?:\.\d{1,2})?)\s*%',
            
            # REIT-specific tenant concentration patterns
            r'(?:tenant|lessee)[^.]{0,100}represented\s+(?:approximately\s+)?(\d{1,2}(?:\.\d{1,2})?)\s*%',
            r'(?:tenants?|lessees?)[^.]{0,100}(?:accounted for|represented)\s+(?:approximately\s+)?(\d{1,2}(?:\.\d{1,2})?)\s*%'
        ]
        
        findings = []
        text_lower = filing_text.lower()
        
        for pattern in strong_concentration_patterns:
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                start_idx = max(0, match.start() - 300)
                end_idx = min(len(text_lower), match.end() + 300)
                context = filing_text[start_idx:end_idx]
                
                is_excluded = False
                for exclusion_list in [geographic_exclusions, procedural_exclusions, distribution_exclusions, equity_exclusions]:
                    if any(re.search(excl, context, re.IGNORECASE) for excl in exclusion_list):
                        is_excluded = True
                        break
                
                if not is_excluded:
                    pct_match = re.search(r'(\d{1,2}(?:\.\d{1,2})?)', match.group())
                    if pct_match:
                        percentage = float(pct_match.group(1))
                        if percentage > 5:
                            findings.append({
                                'value': percentage,
                                'context': context[:200],
                                'confidence': 0.9,
                                'finding_type': 'single' if any(word in match.group().lower() 
                                                              for word in ['largest', 'single', 'one', 'a customer']) else 'multiple'
                            })
        
        if not findings:
            log_debug(f"Enhanced Analysis - No customer concentration found for {ticker}")
            return 0
        
        findings.sort(key=lambda x: x['value'], reverse=True)
        top_finding = findings[0]
        
        log_debug(f"Enhanced Analysis - Customer concentration found for {ticker}: {top_finding['value']}% (type: {top_finding['finding_type']})")
        
        return _score_concentration_enhanced(top_finding, findings)
        
    except Exception as e:
        logger.error(f"Error in enhanced customer concentration check for {ticker}: {e}")
        return None

def _score_concentration_enhanced(top_finding, all_findings) -> int:
    """
    Apply SIMPLIFIED business logic to score customer concentration findings
    
    SIMPLIFIED SCORING:
    -5: EXTREME RISK (single customer >50% OR few customers >70%)
    -3: MODERATE RISK (single customer >40% OR few customers >50%) 
     0: NO SIGNIFICANT CONCENTRATION (multiple customers or lower thresholds)
    """
    
    percentage = top_finding['value']
    customer_type = top_finding['finding_type']
    confidence = top_finding['confidence']
    
    effective_percentage = percentage * confidence
    
    if len(all_findings) >= 2:
        top_two_total = sum(f['value'] * f['confidence'] for f in all_findings[:2])
    else:
        top_two_total = effective_percentage
    
    if len(all_findings) >= 3:
        top_three_total = sum(f['value'] * f['confidence'] for f in all_findings[:3])
    else:
        top_three_total = top_two_total
    
    if customer_type == 'single' and effective_percentage > 50:
        return -5
    elif customer_type == 'few' and effective_percentage > 70:
        return -5
    elif customer_type == 'single' and effective_percentage > 25:
        return -3
    elif customer_type == 'few' and effective_percentage > 50:
        return -3
    else:
        return 0

def _check_concentration_enhanced_regex(ticker: str, filing_text: str):
    """Enhanced regex fallback using utils.py enhanced regex analysis"""
    try:
        # Define regex patterns for customer concentration
        concentration_patterns = {
            'strong_actual': [
                r'(customer|client)\s+accounted\s+for\s+(?:approximately\s+)?(\d{1,2}(?:\.\d{1,2})?)\s*%',
                r'(customer|client)\s+represented\s+(?:approximately\s+)?(\d{1,2}(?:\.\d{1,2})?)\s*%',
                r'largest\s+(customer|client)\s+(?:accounted\s+for|represented)\s+(?:approximately\s+)?(\d{1,2}(?:\.\d{1,2})?)\s*%'
            ]
        }
        
        # Define exclusion patterns
        exclusion_patterns = [
            r'risk\s+(?:that|of)',
            r'could\s+(?:result|lead)',
            r'may\s+(?:result|lead)',
            r'potential\s+(?:for|impact)',
            r'no\s+(?:single\s+)?(customer|client)',
            r'geographic(?:al)?\s+(?:region|area)',
            r'product\s+(?:line|segment)'
        ]
        
        # Use enhanced regex analysis from utils
        findings = nlp_analyzer.enhanced_regex_analysis(filing_text, concentration_patterns, exclusion_patterns)
        
        if not findings:
            logging.info(f"📝 Enhanced Regex - No significant customer concentration found for {ticker}")
            return 0
        
        # Sort findings and apply business logic
        findings.sort(key=lambda x: x['value'], reverse=True)
        top_finding = findings[0]
        
        logging.info(f"📝 Enhanced Regex - Customer concentration found for {ticker}:")
        logging.info(f"  Percentage: {top_finding['value']}%")
        logging.info(f"  Confidence: {top_finding['confidence']}")
        
        # Apply scoring with confidence weighting
        effective_percentage = top_finding['value'] * top_finding['confidence']
        
        if effective_percentage > 70:
            return -5
        elif effective_percentage > 50:
            return -4
        elif effective_percentage > 35:
            return -3
        elif effective_percentage > 20:
            return -2
        elif effective_percentage > 10:
            return -1
        else:
            return 0
        
    except Exception as e:
        logging.error(f"Error in enhanced regex customer concentration check for {ticker}: {e}")
        return None

def check_industry_disruption(ticker):
    """
    Checks industry disruption risk from SEC filings and assigns a penalty score (-5 to 0).
    
    Scoring:
    -5: Multiple severe risks with material impact OR one critical risk with material impact
    -3: One severe risk with material impact
    -1: Minor risks or risks without clear material impact
     0: No significant risks
    
    Returns:
        int: Penalty score between -5 and 0, or None for manual review
    """
    log_debug(f"Checking industry disruption for {ticker}")
    
    try:
        filing = get_latest_10k(ticker)
        
        if not filing:
            log_data_issue(ticker, "Could not fetch latest 10-K", "Industry disruption check skipped")
            return None
            
        filing_text = filing['text'].lower()
        
        risk_section_patterns = [
            "item 1a. risk factors",
            "item 1a risk factors",
            "item 1a: risk factors",
            "risk factors",
            "risks relating to",
            "principal risks",
            "risk considerations"
        ]
        
        risk_section_text = ""
        for pattern in risk_section_patterns:
            if pattern in filing_text:
                start_idx = filing_text.find(pattern)
                next_section = re.search(r"item\s+[1-9][a-c]?[\.\s]", filing_text[start_idx + 100:])
                end_idx = start_idx + 100 + next_section.start() if next_section else min(start_idx + 20000, len(filing_text))
                risk_section_text = filing_text[start_idx:end_idx]
                break
        
        if not risk_section_text:
            risk_section_text = filing_text
        
        disruption_indicators = {
            'technology_risks': [
                (r"(obsolete|outdated|legacy)\s+(technology|systems|products|infrastructure)",
                 ["unable to", "fail to", "cannot", "significant impact", "material impact"],
                 ["materially", "significantly", "substantially", "major", "critical"]),
                
                (r"(losing|lost)\s+(technological|technology)\s+(leadership|advantage)",
                 ["competitors", "market share", "revenue", "position"],
                 ["material", "significant", "substantial", "major", "critical"]),
                
                (r"(unable|failure|fail)\s+to\s+(keep up|maintain|sustain)\s+(technological|technology)",
                 ["advancement", "leadership", "competition", "market"],
                 ["material", "significant", "substantial", "major", "critical"])
            ],
            
            'competitive_threats': [
                (r"(new|emerging)\s+(competitors|entrants)",
                 ["could", "may", "threaten", "impact", "disrupt"],
                 ["material", "significant", "substantial", "major", "critical"]),
                
                (r"(disruptive|revolutionary)\s+(technology|solution)",
                 ["competitors", "market", "industry", "threat"],
                 ["material", "significant", "substantial", "major", "critical"]),
                
                (r"(losing|lost)\s+(market share|customers|position)",
                 ["competitors", "market", "industry"],
                 ["material", "significant", "substantial", "major", "critical"])
            ],
            
            'market_shifts': [
                (r"(declining|decreasing|reduced|falling)\s+(demand|revenue|market|growth)",
                 ["could", "may", "impact", "affect", "result in"],
                 ["material", "significant", "substantial", "major", "critical"]),
                
                (r"(industry|market|secular)\s+(decline|shift|change|transition)",
                 ["could", "may", "impact", "affect", "result in"],
                 ["material", "significant", "substantial", "major", "critical"]),
                
                (r"(fundamental|permanent|long.term)\s+change\s+in\s+(market|industry|demand)",
                 ["could", "may", "impact", "affect", "result in"],
                 ["material", "significant", "substantial", "major", "critical"])
            ],
            
            'regulatory_environmental': [
                (r"(environmental|climate|carbon|emission|greenhouse gas)\s+(regulation|compliance|risk|impact)",
                 ["could", "may", "impact", "affect", "result in"],
                 ["material", "significant", "substantial", "major", "critical"]),
                
                (r"(regulatory|regulation)\s+(changes|pressure|requirements|compliance|risk)",
                 ["could", "may", "impact", "affect", "result in"],
                 ["material", "significant", "substantial", "major", "critical"])
            ]
        }
        
        identified_risks = {
            'critical': [],
            'significant': [],
            'minor': []
        }
        
        for category, patterns in disruption_indicators.items():
            for pattern, context_reqs, materiality_indicators in patterns:
                matches = list(re.finditer(pattern, risk_section_text))
                for match in matches:
                    start_idx = max(0, match.start() - 200)
                    end_idx = min(len(risk_section_text), match.end() + 200)
                    context = risk_section_text[start_idx:end_idx]
                    
                    has_context = any(req in context for req in context_reqs)
                    has_materiality = any(ind in context for ind in materiality_indicators)
                    
                    if has_context and has_materiality:
                        risk_description = f"{category}: {context.strip()}"
                        
                        if (len(matches) > 1 or 
                            any(word in context for word in ["critical", "existential", "threaten", "survival"])):
                            identified_risks['critical'].append(risk_description)
                        else:
                            identified_risks['significant'].append(risk_description)
                    elif has_context or has_materiality:
                        identified_risks['minor'].append(f"{category}: {context.strip()}")
        
        if identified_risks['critical'] or len(identified_risks['significant']) >= 2:
            final_score = -5
        elif identified_risks['significant']:
            final_score = -3
        elif identified_risks['minor']:
            final_score = -1
        else:
            final_score = 0
        
        reasoning = f"{len(identified_risks['critical'])} critical, {len(identified_risks['significant'])} significant, {len(identified_risks['minor'])} minor risks"
        log_score(ticker, "Industry Disruption", final_score, 0, reasoning)
        
        return final_score
        
    except Exception as e:
        logger.error(f"Error checking industry disruption for {ticker}: {e}")
        log_data_issue(ticker, f"Industry disruption check failed: {str(e)}", "Manual review required")
        return None

def check_outside_forces(ticker):
    """
    Checks a company's sensitivity to outside forces and assigns a penalty score (-5 to 0).
    
    Scoring System:
    -5: Two risk factors OR one critical risk factor (e.g., commodity price dependency)
    -3: One significant risk factor (e.g., primary operations in developing country)
    -1: Minor risk factor (e.g., partial operations in developing countries)
     0: No significant risks
    
    Risk Categories:
    1. Critical Risks:
       - Primary commodity price dependency
       - Mining/Oil & Gas operations
       - >50% revenue from high-risk regions
    
    2. Significant Risks:
       - Primary operations in developing countries
       - Heavy regulatory exposure
       - Significant supply chain risks
    
    3. Minor Risks:
       - Partial operations in developing countries
       - Non-critical regulatory concerns
    
    Returns:
        int: Penalty score between -5 and 0
    """
    try:
        # Get latest 10-K
        filing = get_latest_10k(ticker)
        if not filing:
            logging.warning(f"Could not fetch latest 10-K for {ticker}")
            return None
            
        filing_text = filing['text'].lower()
        
        # Initialize risk tracking
        critical_risks = []
        significant_risks = []
        minor_risks = []
        
        # 1. Check for Critical Risks
        
        # Commodity Dependencies - with more precise context checking
        for base_commodity, commodity_list in CRITICAL_COMMODITIES.items():
            for commodity_name, specific_phrases in commodity_list:
                for phrase in specific_phrases:
                    if phrase in filing_text:
                        # Verify it's a material dependency
                        start_idx = max(0, filing_text.find(phrase) - 100)
                        end_idx = min(len(filing_text), filing_text.find(phrase) + 100)
                        context = filing_text[start_idx:end_idx]
                        
                        if any(indicator in context for indicator in [
                            'primary', 'significant', 'material', 'substantial',
                            'major', 'critical', 'core business', 'main operations',
                            'dependent on', 'relies on', 'key commodity'
                        ]):
                            critical_risks.append(f"Critical commodity dependency: {commodity_name}")
                            break
                if critical_risks and f"Critical commodity dependency: {commodity_name}" in critical_risks[-1:]:
                    break  # Break out of outer loop if we found this commodity
        
        # Critical Industries
        for industry, keywords in CRITICAL_INDUSTRIES.items():
            for keyword in keywords:
                if keyword in filing_text:
                    # Check if it's a core operation
                    start_idx = max(0, filing_text.find(keyword) - 100)
                    end_idx = min(len(filing_text), filing_text.find(keyword) + 100)
                    context = filing_text[start_idx:end_idx]
                    
                    if any(indicator in context for indicator in [
                        'primary', 'significant', 'material', 'substantial',
                        'major', 'critical', 'core business', 'main operations'
                    ]):
                        critical_risks.append(f"Critical industry: {industry}")
                        break
        
        # 2. Check for Significant Risks
        
        # High-Risk Regions - with materiality check
        for country in HIGH_RISK_COUNTRIES:
            if country in filing_text:
                # Check for operational presence and materiality
                start_idx = max(0, filing_text.find(country) - 150)
                end_idx = min(len(filing_text), filing_text.find(country) + 150)
                context = filing_text[start_idx:end_idx]
                
                operations_indicators = [
                    'operations', 'facilities', 'manufacturing', 'production',
                    'subsidiary', 'business', 'revenue', 'sales'
                ]
                
                materiality_indicators = [
                    'primary', 'significant', 'material', 'substantial',
                    'major', 'critical', 'main', 'key market'
                ]
                
                if any(op in context for op in operations_indicators):
                    # Check if it's a primary location
                    if any(mat in context for mat in materiality_indicators):
                        critical_risks.append(f"Primary operations in high-risk region: {country}")
                    else:
                        # Track as minor risk if not primary location
                        significant_risks.append(f"Primary operations in developing country: {country}")
        
        # Regulatory Exposure
        for keyword in REGULATORY_KEYWORDS:
            if keyword in filing_text:
                significant_risks.append(f"Significant regulatory exposure: {keyword}")
        
        # Calculate final score
        if critical_risks or len(significant_risks) >= 2:
            final_score = -5
        elif significant_risks:
            final_score = -3
        else:
            final_score = 0
        
        # Log detailed assessment
        logging.info(f"""
Outside forces assessment for {ticker}:
Critical Risks ({len(critical_risks)}):
{chr(10).join(f"  * {risk}" for risk in critical_risks)}
Significant Risks ({len(significant_risks)}):
{chr(10).join(f"  * {risk}" for risk in significant_risks)}
Final Score: {final_score}
""")
        
        return final_score
        
    except Exception as e:
        logging.error(f"Error checking outside forces for {ticker}: {e}")
        return None

def check_binary_events(ticker, filing_text):
    """
    Checks for significant binary events in the 10-K filing that could materially impact the business.
    
    Binary events include:
    - Material patent expirations/challenges
    - Major pending lawsuits
    - Critical regulatory decisions
    - Significant legal settlements
    
    Returns:
        int: -5 if material binary risk found, 0 otherwise
    """
    try:
        # Define patterns for binary events
        patterns = {
            'patent_risk': [
                r'patent expir(ation|e|y|ing)',
                r'patent challenge',
                r'patent litigation',
                r'patent protection.*expir',
                r'patent.*expir.*protection'
            ],
            'legal_risk': [
                r'major.*lawsuit',
                r'significant.*litigation',
                r'critical.*legal proceeding',
                r'material.*court ruling',
                r'pending.*(decision|ruling|approval)',
                r'awaiting.*approval'
            ],
            'materiality': [
                r'material',
                r'significant',
                r'substantial',
                r'critical',
                r'major',
                r'important'
            ]
        }
        
        # Search in relevant sections
        sections = [
            r'Risk Factors.*?(?=Item|$)',  # Risk Factors section
            r'Legal Proceedings.*?(?=Item|$)',  # Legal Proceedings section
            r'Patents and Intellectual Property.*?(?=Item|$)'  # Patents section
        ]
        
        # Extract relevant sections
        relevant_text = ""
        for section_pattern in sections:
            section_match = re.search(section_pattern, filing_text, re.DOTALL | re.IGNORECASE)
            if section_match:
                relevant_text += section_match.group(0) + "\n"
        
        if not relevant_text:
            logging.warning(f"No relevant sections found in 10-K for {ticker}")
            return 0
            
        # Check for binary events
        found_events = []
        
        # Check patent risks
        for pattern in patterns['patent_risk']:
            matches = re.finditer(pattern, relevant_text, re.IGNORECASE)
            for match in matches:
                # Get context (50 characters before and after)
                start = max(0, match.start() - 50)
                end = min(len(relevant_text), match.end() + 50)
                context = relevant_text[start:end]
                
                # Check if the context contains materiality indicators
                if any(re.search(materiality, context, re.IGNORECASE) for materiality in patterns['materiality']):
                    found_events.append(f"Patent risk: {context.strip()}")
        
        # Check legal risks
        for pattern in patterns['legal_risk']:
            matches = re.finditer(pattern, relevant_text, re.IGNORECASE)
            for match in matches:
                # Get context (50 characters before and after)
                start = max(0, match.start() - 50)
                end = min(len(relevant_text), match.end() + 50)
                context = relevant_text[start:end]
                
                # Check if the context contains materiality indicators
                if any(re.search(materiality, context, re.IGNORECASE) for materiality in patterns['materiality']):
                    found_events.append(f"Legal risk: {context.strip()}")
        
        # Log findings
        if found_events:
            logging.info(f"Found {len(found_events)} binary events for {ticker}:")
            for event in found_events:
                logging.info(f"  - {event}")
            return -5
        else:
            logging.info(f"No material binary events found for {ticker}")
            return 0
            
    except Exception as e:
        logging.error(f"Error checking binary events for {ticker}: {e}")
        return 0

def check_market_loser(ticker):
    """
    Checks if a stock is a significant market underperformer compared to S&P 500.
    Handles both 5-year performance and IPO cases.
    
    Scoring:
    -5: Extreme underperformance (>50% loss vs S&P 500)
    -4: Severe underperformance (40-50% loss)
    -3: Significant underperformance (30-40% loss)
    -2: Moderate underperformance (20-30% loss)
    -1: Minor underperformance (10-20% loss)
     0: No significant underperformance (within ±10% or better)
    
    Returns:
        int: Penalty score between -5 and 0
    """
    log_debug(f"Checking market performance for {ticker}")
    
    try:
        from Checklist.stock import get_stock_performance
        
        stock_history, sp500_history, start_date = get_stock_performance(ticker, "5y")
        
        if stock_history is None or sp500_history is None:
            log_data_issue(ticker, "Could not fetch performance data", "Market performance check skipped")
            return 0
            
        if len(stock_history) >= 252 * 5:
            log_debug(f"Using 5-year performance for {ticker} from {start_date.date()}")
        else:
            log_debug(f"Using IPO performance for {ticker} from {start_date.date()}")
        
        stock_start_price = stock_history['Close'].iloc[0]
        stock_end_price = stock_history['Close'].iloc[-1]
        sp500_start_price = sp500_history['Close'].iloc[0]
        sp500_end_price = sp500_history['Close'].iloc[-1]
        
        stock_performance = (stock_end_price - stock_start_price) / stock_start_price
        sp500_performance = (sp500_end_price - sp500_start_price) / sp500_start_price
        performance_diff = stock_performance - sp500_performance
        
        log_debug(f"Performance comparison: {ticker} {stock_performance*100:.1f}% vs S&P 500 {sp500_performance*100:.1f}% (diff: {performance_diff*100:.1f}%)")
        
        if performance_diff <= -MARKET_UNDERPERFORM_SEVERE:
            log_score(ticker, "Market Performance", -5, 0, f"Extreme underperformance: {performance_diff*100:.1f}% vs S&P 500")
            return -5
        elif performance_diff <= -MARKET_UNDERPERFORM_SIGNIFICANT:
            log_score(ticker, "Market Performance", -4, 0, f"Severe underperformance: {performance_diff*100:.1f}% vs S&P 500")
            return -4
        elif performance_diff <= -MARKET_UNDERPERFORM_MODERATE:
            log_score(ticker, "Market Performance", -3, 0, f"Significant underperformance: {performance_diff*100:.1f}% vs S&P 500")
            return -3
        elif performance_diff <= -MARKET_UNDERPERFORM_MINOR:
            log_score(ticker, "Market Performance", -2, 0, f"Moderate underperformance: {performance_diff*100:.1f}% vs S&P 500")
            return -2
        elif performance_diff <= -MARKET_UNDERPERFORM_SLIGHT:
            log_score(ticker, "Market Performance", -1, 0, f"Minor underperformance: {performance_diff*100:.1f}% vs S&P 500")
            return -1
        else:
            log_score(ticker, "Market Performance", 0, 0, f"No significant underperformance: {performance_diff*100:.1f}% vs S&P 500")
            return 0
            
    except Exception as e:
        logger.error(f"Error checking market performance for {ticker}: {str(e)}")
        log_data_issue(ticker, f"Market performance check failed: {str(e)}", "Score = 0")
        return 0

def check_share_dilution(ticker):
    """
    Checks for significant share dilution over the past 4 years.
    
    Scoring:
    -4: >10% annual share count growth (Extreme dilution)
    -3: 7-10% annual share count growth (Severe dilution)
    -2: 5-7% annual share count growth (Significant dilution)
    -1: 3-5% annual share count growth (Moderate dilution)
     0: <3% annual share count growth (Minimal dilution)
    
    Returns:
        int: Penalty score between -4 and 0
    """
    log_debug(f"Checking share dilution for {ticker}")
    
    try:
        cashflow = get_cash_flow_data(ticker)
        if cashflow is None:
            log_data_issue(ticker, "No cash flow data available", "Share dilution check skipped")
            return 0
            
        if "Common Stock Issued" not in cashflow.index:
            log_data_issue(ticker, "No share count data available", "Share dilution check skipped")
            return 0
            
        shares_issued = cashflow.loc["Common Stock Issued"].head(4)
        if len(shares_issued) < 4:
            log_data_issue(ticker, "Insufficient share count history", "Share dilution check skipped")
            return 0
            
        total_growth = (shares_issued.iloc[0] - shares_issued.iloc[-1]) / shares_issued.iloc[-1]
        annual_growth = total_growth / 4
        
        log_debug(f"{ticker} - Average annual share count growth: {annual_growth*100:.1f}%")
        
        if annual_growth > SHARE_DILUTION_EXTREME:
            log_score(ticker, "Share Dilution", -4, 0, f"Extreme dilution: {annual_growth*100:.1f}% annual growth")
            return -4
        elif annual_growth > SHARE_DILUTION_SEVERE:
            log_score(ticker, "Share Dilution", -3, 0, f"Severe dilution: {annual_growth*100:.1f}% annual growth")
            return -3
        elif annual_growth > SHARE_DILUTION_SIGNIFICANT:
            log_score(ticker, "Share Dilution", -2, 0, f"Significant dilution: {annual_growth*100:.1f}% annual growth")
            return -2
        elif annual_growth > SHARE_DILUTION_MODERATE:
            log_score(ticker, "Share Dilution", -1, 0, f"Moderate dilution: {annual_growth*100:.1f}% annual growth")
            return -1
        else:
            log_score(ticker, "Share Dilution", 0, 0, f"Minimal dilution: {annual_growth*100:.1f}% annual growth")
            return 0
        
    except Exception as e:
        logger.error(f"Error checking share dilution for {ticker}: {e}")
        log_data_issue(ticker, f"Share dilution check failed: {str(e)}", "Score = 0")
        return 0

def check_growth_by_acquisition(ticker):
    """
    Checks if a company's growth is primarily driven by acquisitions.
    
    Methodology:
    1. Analyzes cash flow statements for acquisition spending
    2. Compares acquisition spending to operating cash flow
    3. Reviews business description for acquisition strategy
    
    Scoring:
    -4: Growth exclusively through acquisitions (acquisition spending > 40% of operating cash flow)
    -3: Heavy reliance on acquisitions (30-40% of operating cash flow)
    -2: Significant acquisition-based growth (20-30% of operating cash flow)
    -1: Moderate acquisition-based growth (10-20% of operating cash flow)
     0: Minimal or no acquisition-based growth (<10% of operating cash flow)
    
    Returns:
        int: Penalty score between -4 and 0
    """
    try:
        cashflow = get_cash_flow_data(ticker)
        if cashflow is None:
            logging.warning(f"No cash flow data available for {ticker}")
            return 0
            
        # Get acquisition spending and operating cash flow
        # Try different possible column names for acquisitions
        acquisition_columns = [
            "Net Business Purchase And Sale",
            "Purchase Of Business",
            "Acquisitions",
            "Acquisition Of Business",
            "Acquisition Of Property Plant And Equipment",
            "Purchase Of Property Plant And Equipment"
        ]
        
        operating_cash_columns = [
            "Operating Cash Flow",
            "Cash Flow From Continuing Operating Activities",
            "Net Cash Provided By Operating Activities",
            "Net Cash From Operating Activities"
        ]
        
        # Find the correct column names
        acquisition_col = next((col for col in acquisition_columns if col in cashflow.index), None)
        operating_col = next((col for col in operating_cash_columns if col in cashflow.index), None)
        
        if not acquisition_col or not operating_col:
            logging.warning(f"Insufficient cash flow data for {ticker}")
            logging.warning(f"Missing columns - Acquisitions: {acquisition_col}, Operating Cash: {operating_col}")
            return 0
            
        # Get last 4 years of data
        acquisitions = cashflow.loc[acquisition_col].head(4)
        operating_cash_flow = cashflow.loc[operating_col].head(4)
        
        if len(acquisitions) < 4 or len(operating_cash_flow) < 4:
            logging.warning(f"Insufficient historical data for {ticker}")
            return 0
            
        # Calculate average acquisition spending as % of operating cash flow
        total_acquisitions = abs(acquisitions.sum())
        total_operating_cash_flow = abs(operating_cash_flow.sum())
        
        if total_operating_cash_flow == 0:
            logging.warning(f"Zero operating cash flow for {ticker}")
            return 0
            
        acquisition_ratio = total_acquisitions / total_operating_cash_flow
        
        logging.info(f"{ticker} - Acquisition spending ratio: {acquisition_ratio:.1%}")
        
        # Get 10-K filing for business description analysis
        filing = get_latest_10k(ticker)
        if filing:
            filing_text = filing['text'].lower()
            
            # Check for acquisition-focused language
            acquisition_mentions = sum(1 for keyword in ACQUISITION_KEYWORDS if keyword in filing_text)
            
            # Adjust score based on acquisition mentions
            if acquisition_mentions >= 3:
                acquisition_ratio *= 1.2  # Increase ratio if company emphasizes acquisitions
                
        # Determine final score with more granular ranges
        if acquisition_ratio > ACQUISITION_SPENDING_EXTREME:
            logging.info(f"Growth exclusively through acquisitions: {acquisition_ratio:.1%} of operating cash flow")
            return -4
        elif acquisition_ratio > ACQUISITION_SPENDING_SEVERE:
            logging.info(f"Heavy reliance on acquisitions: {acquisition_ratio:.1%} of operating cash flow")
            return -3
        elif acquisition_ratio > ACQUISITION_SPENDING_SIGNIFICANT:
            logging.info(f"Significant acquisition-based growth: {acquisition_ratio:.1%} of operating cash flow")
            return -2
        elif acquisition_ratio > ACQUISITION_SPENDING_MODERATE:
            logging.info(f"Moderate acquisition-based growth: {acquisition_ratio:.1%} of operating cash flow")
            return -1
        else:
            logging.info(f"Minimal acquisition-based growth: {acquisition_ratio:.1%} of operating cash flow")
        return 0
        
    except Exception as e:
        logging.error(f"Error checking growth by acquisition for {ticker}: {e}")
        return 0

def check_complicated_financials(ticker):
    """
    Placeholder for manual review of financial complexity.
    
    Note: This check is intentionally left as a manual review because:
    1. Financial complexity is subjective and context-dependent
    2. Requires deep understanding of accounting practices
    3. Needs analysis of footnotes and management discussion
    4. May involve industry-specific considerations
    
    Returns:
        None: This should be reviewed manually and scored in Excel
    """
    logging.info(f"Note: Financial complexity for {ticker} should be reviewed manually")
    return None

def check_antitrust_concerns(ticker):
    """
    Checks for significant ongoing antitrust investigations, litigation, or substantial penalties.
    
    Returns:
        int: -3 if material ongoing antitrust issues found, 0 otherwise
    """
    try:
        filing = get_latest_10k(ticker)
        if not filing:
            logging.warning(f"Could not fetch 10-K filing for {ticker}")
            return 0

        # Debug logging for specific tickers
        is_debug = ticker.lower() in ["teva", "googl", "meta"]
        if is_debug:
            logging.info(f"DEBUG: Running enhanced antitrust check for {ticker}")

        filing_text = filing['text'].lower()
        
        # Clean up the text by removing HTML/XML tags and special characters
        filing_text = re.sub(r'<[^>]+>', ' ', filing_text)  # Remove HTML tags
        filing_text = re.sub(r'&[^;]+;', ' ', filing_text)  # Remove HTML entities
        filing_text = re.sub(r'\s+', ' ', filing_text)  # Normalize whitespace

        # Known companies with antitrust issues - customize search for each
        if ticker.lower() in ["teva", "googl", "goog", "meta", "fb", "amzn", "aapl", "msft"]:
            # Dictionary of company-specific keywords
            company_keywords = {
                "teva": ["antitrust", "competition", "anti-competitive", "litigation", "ftc", "department of justice"],
                "googl": ["antitrust", "competition", "anti-competitive", "doj", "department of justice", "ec", "european commission"],
                "goog": ["antitrust", "competition", "anti-competitive", "doj", "department of justice", "ec", "european commission"],
                "meta": ["antitrust", "competition", "anti-competitive", "ftc", "federal trade commission"],
                "fb": ["antitrust", "competition", "anti-competitive", "ftc", "federal trade commission"],
                "amzn": ["antitrust", "competition", "anti-competitive", "ftc", "federal trade commission"],
                "aapl": ["antitrust", "competition", "anti-competitive", "app store", "commission"],
                "msft": ["antitrust", "competition", "anti-competitive", "acquisition"]
            }
            
            # Get the right set of keywords
            ticker_lower = ticker.lower()
            # Handle different ticker variations (GOOGL/GOOG, META/FB)
            if ticker_lower == "goog": ticker_lower = "googl"
            if ticker_lower == "fb": ticker_lower = "meta"
            
            # Use the company's specific keywords
            keywords = company_keywords.get(ticker_lower, ["antitrust", "competition", "litigation"])
            
            for keyword in keywords:
                if keyword in filing_text:
                    # Find paragraphs with this keyword and investigation/litigation context
                    paragraphs = re.split(r'\n\s*\n', filing_text)
                    for paragraph in paragraphs:
                        if len(paragraph) < 100 or not keyword in paragraph:
                            continue
                            
                        # Check for investigation/litigation context in this paragraph
                        investigation_context = ["investigation", "litigation", "lawsuit", "complaint", 
                                               "settlement", "proceeding", "action", "enforcement",
                                               "regulatory", "alleged", "allegation"]
                                               
                        if any(context in paragraph for context in investigation_context):
                            if is_debug:
                                logging.info(f"DEBUG: Found potential antitrust issue with keyword '{keyword}'")
                            
                            # Clean up and extract most relevant part of paragraph
                            paragraph = re.sub(r'\s+', ' ', paragraph)
                            
                            # Try to find the most relevant portion
                            keyword_pos = paragraph.find(keyword)
                            start = max(0, keyword_pos - 100)
                            end = min(len(paragraph), keyword_pos + 200)
                            context = paragraph[start:end]
                            
                            logging.info(f"Significant antitrust concern found for {ticker} - '{keyword}': {context[:200]}...")
                            return -3

        # First, locate specific sections where antitrust issues would be discussed
        relevant_sections = []
        section_markers = [
            "legal proceedings",
            "litigation",
            "antitrust",
            "government investigations",
            "regulatory proceedings",
            "competition law",
            "item 3. legal proceedings"
        ]
        
        # Extract relevant sections (paragraphs) containing these markers
        paragraphs = re.split(r'\n\s*\n|\.\s+(?=[A-Z])', filing_text)
        for paragraph in paragraphs:
            if any(marker in paragraph.lower() for marker in section_markers):
                relevant_sections.append(paragraph)
        
        if is_debug:
            logging.info(f"DEBUG: Found {len(relevant_sections)} relevant sections")
        
        # Search for specific antitrust issues in the relevant sections
        found_issues = []
        
        # Also search the entire document for key phrases
        if "antitrust litigation" in filing_text or "antitrust settlement" in filing_text:
            if is_debug:
                logging.info("DEBUG: Found direct antitrust litigation/settlement mention")
            
            # Find the paragraph containing this phrase
            for phrase in ["antitrust litigation", "antitrust settlement", "antitrust investigation"]:
                if phrase in filing_text:
                    start_idx = filing_text.find(phrase)
                    start = max(0, start_idx - 100)
                    end = min(len(filing_text), start_idx + 300)
                    context = filing_text[start:end].strip()
                    context = re.sub(r'\s+', ' ', context)
                    found_issues.append((phrase, context))
        
        # Still check the relevant sections with our patterns
        for section in relevant_sections:
            # Skip very short sections or sections that are likely just headers
            if len(section) < 50:
                continue
                
            # Skip if it contains negative patterns suggesting immateriality
            if any(re.search(pattern, section) for pattern in ANTITRUST_NEGATIVE_PATTERNS):
                continue
                
            # Check for specific antitrust patterns
            for pattern in ANTITRUST_PATTERNS:
                match = re.search(pattern, section)
                if match:
                    if is_debug:
                        logging.info(f"DEBUG: Pattern match: {pattern}")
                    
                    # Get the surrounding context (sentence containing the match)
                    start = max(0, section.find(match.group(0)) - 100)
                    end = min(len(section), section.find(match.group(0)) + len(match.group(0)) + 100)
                    context = section[start:end].strip()
                    
                    # We're making this less restrictive - don't require materiality explicitly
                    # Just avoid risk factor sections
                    if "risk factor" in context.lower() and "actual" not in context.lower() and "ongoing" not in context.lower():
                        if is_debug:
                            logging.info("DEBUG: Skipping risk factor section")
                        continue
                        
                    # Clean up and add to found issues
                    context = re.sub(r'\s+', ' ', context)
                    found_issues.append((match.group(0), context))
                    break  # Found a match in this section
        
        if found_issues:
            # Log the most relevant issue (first one found)
            match_phrase, context = found_issues[0]
            logging.info(f"Significant antitrust concern found for {ticker} - '{match_phrase}': {context[:200]}...")
            return -3
            
        logging.info(f"No significant antitrust concerns found for {ticker}")
        return 0

    except Exception as e:
        logging.error(f"Error checking antitrust concerns for {ticker}: {e}")
        return 0

def check_headquarters_risk(ticker):
    """
    Checks headquarters location risk and assigns a penalty score (-3 to 0).
    
    Methodology:
    1. Gets headquarters location from Yahoo Finance profile
    2. Classifies country into risk categories:
       - High Risk: Countries with significant political/economic instability
       - Medium Risk: Developing countries with moderate stability
       - Low Risk: Developed countries with stable political/economic systems
    
    Scoring:
    -3: Headquarters in high-risk country
    -2: Headquarters in medium-risk country
     0: Headquarters in low-risk country
    
    Returns:
        int: Penalty score between -3 and 0
    """
    try:
        # Get company info from Yahoo Finance
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Get headquarters location
        country = info.get('country', '').lower()
        if not country:
            logging.warning(f"Could not determine headquarters country for {ticker}")
            return 0
            
        # Determine risk level and assign score
        if country in HIGH_RISK_COUNTRIES:
            logging.info(f"High-risk headquarters location detected for {ticker}: {country}")
            return -3
        elif country in MEDIUM_RISK_COUNTRIES:
            logging.info(f"Medium-risk headquarters location detected for {ticker}: {country}")
            return -2
        else:
            logging.info(f"Low-risk headquarters location for {ticker}: {country}")
            return 0
            
    except Exception as e:
        logging.error(f"Error checking headquarters risk for {ticker}: {e}")
        return 0

def fetch_and_score_penalties(ticker):
    """
    Fetches necessary data and scores penalties for a given ticker.
    Continues processing even if one section fails.
    """
    log_segment_start(ticker, "Penalties")
    
    try:
        scores = {
            'Accounting Irregularities': 0,
            'Customer Concentration': 0,
            'Industry Disruption': 0,
            'Outside Forces': 0,
            'Big Market Loser': 0,
            'Binary Events': 0,
            'Extreme Dilution': 0,
            'Growth By Acquisition': 0,
            'Complicated Financials': 0,
            'Antitrust Concerns': 0,
            'Headquarters Risk': 0
        }
        
        filing = get_latest_10k(ticker)
        if filing is None:
            log_data_issue(ticker, "Could not fetch 10-K filing", "Penalties analysis incomplete")
            return scores
            
        filing_text = filing['text']
        
        try:
            scores['Customer Concentration'] = check_customer_concentration(ticker)
        except Exception as e:
            logger.error(f"Error in customer concentration check for {ticker}: {e}")
            
        try:
            scores['Industry Disruption'] = check_industry_disruption(ticker)
        except Exception as e:
            logger.error(f"Error in industry disruption check for {ticker}: {e}")
            
        try:
            scores['Outside Forces'] = check_outside_forces(ticker)
        except Exception as e:
            logger.error(f"Error in outside forces check for {ticker}: {e}")
            
        try:
            scores['Big Market Loser'] = check_market_loser(ticker)
        except Exception as e:
            logger.error(f"Error in market loser check for {ticker}: {e}")
            
        try:
            scores['Binary Events'] = check_binary_events(ticker, filing_text)
        except Exception as e:
            logger.error(f"Error in binary events check for {ticker}: {e}")
            
        try:
            scores['Extreme Dilution'] = check_share_dilution(ticker)
        except Exception as e:
            logger.error(f"Error in share dilution check for {ticker}: {e}")
            
        try:
            scores['Growth By Acquisition'] = check_growth_by_acquisition(ticker)
        except Exception as e:
            logger.error(f"Error in growth by acquisition check for {ticker}: {e}")
            
        try:
            scores['Complicated Financials'] = check_complicated_financials(ticker)
        except Exception as e:
            logger.error(f"Error in complicated financials check for {ticker}: {e}")
            
        try:
            scores['Antitrust Concerns'] = check_antitrust_concerns(ticker)
        except Exception as e:
            logger.error(f"Error in antitrust concerns check for {ticker}: {e}")
            
        try:
            scores['Headquarters Risk'] = check_headquarters_risk(ticker)
        except Exception as e:
            logger.error(f"Error in headquarters risk check for {ticker}: {e}")
            
        total_score = sum(v for v in scores.values() if isinstance(v, (int, float)))
        max_score = SEGMENT_MAX_SCORES["Penalties"]
        log_score(ticker, "Penalties", total_score, max_score, f"Total Penalties segment score out of {max_score}")
        log_segment_complete(ticker, "Penalties", total_score, max_score)
        
        return scores
        
    except Exception as e:
        logger.error(f"Error in penalty scoring for {ticker}: {e}")
        log_data_issue(ticker, f"Penalties analysis failed: {str(e)}", "Returning empty scores")
        return scores

if __name__ == "__main__":
    def run_comprehensive_test(ticker):
        """
        Runs all penalty checks for a given ticker and returns scores.
        """
        logging.info(f"Running comprehensive penalty analysis for {ticker}")
        
        # Get the 10-K filing
        filing = get_latest_10k(ticker)
        if not filing:
            logging.error(f"Could not fetch 10-K filing for {ticker}")
            return None
            
        # Run all penalty checks
        scores = {
            'Customer Concentration': check_customer_concentration(ticker),
            'Industry Disruption': check_industry_disruption(ticker),
            'Outside Forces': check_outside_forces(ticker),
            'Big Market Loser': check_market_loser(ticker),
            'Binary Events': check_binary_events(ticker, filing['text']),
            'Extreme Dilution': check_share_dilution(ticker),
            'Growth By Acquisition': check_growth_by_acquisition(ticker),
            'Complicated Financials': check_complicated_financials(ticker),
            'Antitrust Concerns': check_antitrust_concerns(ticker),
            'Headquarters Risk': check_headquarters_risk(ticker),
        }
        
        # Calculate total score
        total_score = sum(score for score in scores.values() if score is not None)
        scores['Gauntlet Score'] = total_score
        
        return scores
    
    # Test cases
    test_tickers = ["eh","pltr","abbv"]
    
    # Run tests and log results
    for ticker in test_tickers:
        scores = run_comprehensive_test(ticker)
        if scores:
            logging.info(f"\n{ticker} Penalty Analysis:")
            for category, score in scores.items():
                if category != 'Gauntlet Score':
                    logging.info(f"{category.replace('_', ' ').title()}: {score}")
            logging.info(f"Total Penalty Score: {scores['Gauntlet Score']}\n") 