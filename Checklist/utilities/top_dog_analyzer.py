"""
Top Dog Analyzer Module

This module provides top dog and first mover analysis functionality.
Extracted from utils.py to provide better organization and separation of concerns.
"""

import re
from .logging_config import get_logger, log_debug, log_data_issue

logger = get_logger(__name__)

# Emerging Industry Terms
EMERGING_INDUSTRY_TERMS = {
    'artificial_intelligence': [
        'machine learning', 'deep learning', 'neural networks', 'ai/ml', 'artificial intelligence',
        'predictive analytics', 'computer vision', 'natural language processing', 'nlp',
        'generative ai', 'large language models', 'llms', 'ai-powered', 'intelligent automation',
        'foundation models', 'transformer models', 'reinforcement learning', 'federated learning'
    ],
    'electric_vehicles': [
        'electric vehicles', 'evs', 'battery electric', 'plug-in hybrid', 'charging infrastructure',
        'lithium-ion batteries', 'autonomous driving', 'self-driving', 'electric mobility',
        'sustainable transportation', 'zero-emission vehicles', 'battery technology'
    ],
    'renewable_energy': [
        'solar energy', 'photovoltaic', 'wind power', 'renewable energy', 'clean energy',
        'energy storage', 'battery storage', 'grid modernization', 'smart grid',
        'carbon capture', 'hydrogen fuel', 'green hydrogen', 'microgrids'
    ],
    'fintech': [
        'digital payments', 'mobile payments', 'blockchain', 'cryptocurrency', 'digital banking',
        'neobanks', 'insurtech', 'regtech', 'wealthtech', 'buy now pay later', 'bnpl',
        'open banking', 'api banking', 'digital wallets', 'defi', 'decentralized finance'
    ],
    'ecommerce_emerging': [
        'social commerce', 'live streaming commerce', 'cross-border ecommerce', 'b2b ecommerce',
        'marketplace platforms', 'direct-to-consumer', 'dtc', 'omnichannel retail',
        'last-mile delivery', 'logistics technology', 'quick commerce', 'q-commerce'
    ],
    'digital_health': [
        'telemedicine', 'digital health', 'healthtech', 'precision medicine', 'genomics',
        'crispr', 'gene editing', 'remote patient monitoring', 'digital therapeutics', 
        'healthcare analytics', 'wearable health devices', 'personalized medicine'
    ],
    'cloud_computing': [
        'cloud infrastructure', 'saas', 'paas', 'iaas', 'edge computing', 'serverless',
        'containerization', 'microservices', 'cloud-native', 'multi-cloud', 'hybrid cloud',
        'api-first', 'low-code', 'no-code', 'devops', 'mlops'
    ],
    'cybersecurity': [
        'zero trust', 'threat detection', 'endpoint security', 'cloud security', 'identity management',
        'data protection', 'privacy technology', 'quantum cryptography', 'ai security',
        'security orchestration', 'soar', 'siem', 'devsecops'
    ],
    'space_tech': [
        'satellite technology', 'space exploration', 'commercial space', 'space tourism',
        'satellite internet', 'space mining', 'orbital debris removal', 'space manufacturing',
        'small satellites', 'cubesats', 'reusable rockets', 'space logistics'
    ],
    'quantum_computing': [
        'quantum computing', 'quantum algorithms', 'quantum cryptography', 'quantum sensors',
        'quantum networking', 'quantum advantage', 'qubits', 'quantum supremacy',
        'quantum error correction', 'quantum machine learning'
    ],
    'advanced_manufacturing': [
        '3d printing', 'additive manufacturing', 'industrial iot', 'digital twins',
        'smart manufacturing', 'robotics automation', 'cobots', 'collaborative robots'
    ],
    'ar_vr': [
        'augmented reality', 'virtual reality', 'mixed reality', 'extended reality', 'xr',
        'spatial computing', 'metaverse', 'digital twins', 'ar glasses', 'vr headsets'
    ]
}

# Top Dog Analysis - spaCy Entity Patterns
TOP_DOG_PATTERNS = {
    'MARKET_LEADER': [
        [{"LOWER": {"IN": ["leading", "dominant", "largest", "top"]}},
         {"LOWER": {"IN": ["provider", "company", "player", "supplier"]}}],
        [{"LOWER": "market"}, {"LOWER": {"IN": ["leader", "leading", "leadership"]}}],
        [{"LOWER": {"IN": ["#1", "number", "no."]}}, {"IS_DIGIT": True, "OP": "?"}, 
         {"LOWER": {"IN": ["in", "provider", "company"]}}],
        [{"LOWER": {"IN": ["pioneer", "pioneering"]}}, {"LOWER": {"IN": ["in", "of", "the"]}, "OP": "?"}, 
         {"LOWER": {"IN": ["industry", "market", "field", "space"]}}],
        [{"LOWER": {"IN": ["first", "original"]}}, {"LOWER": {"IN": ["to", "company"]}}],
        [{"LOWER": {"IN": ["established", "recognized"]}}, 
         {"LOWER": {"IN": ["leader", "leadership", "position"]}}]
    ],
    'FIRST_MOVER': [
        [{"LOWER": {"IN": ["first", "earliest", "initial"]}}, 
         {"LOWER": {"IN": ["to", "company", "mover"]}}],
        [{"LOWER": {"IN": ["pioneer", "pioneered", "pioneering"]}}, 
         {"LOWER": {"IN": ["in", "the", "of"]}, "OP": "?"}],
        [{"LOWER": {"IN": ["invented", "created", "developed"]}}, 
         {"LOWER": {"IN": ["the", "first", "original"]}, "OP": "?"}],
        [{"LOWER": {"IN": ["breakthrough", "innovative", "groundbreaking"]}}, 
         {"LOWER": {"IN": ["technology", "solution", "approach"]}}],
        [{"LOWER": {"IN": ["originated", "introduced"]}}, 
         {"LOWER": {"IN": ["the", "concept", "technology"]}, "OP": "?"}]
    ],
    'EMERGING_INDUSTRY': [
        [{"LOWER": {"IN": ["emerging", "growing", "expanding"]}}, 
         {"LOWER": {"IN": ["market", "industry", "sector", "space"]}}],
        [{"LOWER": {"IN": ["high-growth", "fast-growing", "rapidly"]}}, 
         {"LOWER": {"IN": ["growing", "expanding"]}, "OP": "?"}, 
         {"LOWER": {"IN": ["market", "industry", "sector"]}}],
        [{"LOWER": {"IN": ["new", "nascent", "developing"]}}, 
         {"LOWER": {"IN": ["market", "industry", "technology", "category"]}}],
        [{"LOWER": {"IN": ["next-generation", "cutting-edge", "advanced"]}}, 
         {"LOWER": {"IN": ["technology", "solutions", "platform"]}}],
        [{"LOWER": {"IN": ["digital", "cloud", "ai", "artificial"]}}, 
         {"LOWER": {"IN": ["intelligence", "transformation", "revolution"]}, "OP": "?"}]
    ],
    'DISRUPTOR': [
        [{"LOWER": {"IN": ["disrupt", "disrupting", "disruption"]}}, 
         {"LOWER": {"IN": ["the", "traditional", "industry"]}, "OP": "?"}],
        [{"LOWER": {"IN": ["transforming", "revolutionizing", "changing"]}}, 
         {"LOWER": {"IN": ["the", "how", "industry", "way"]}}],
        [{"LOWER": {"IN": ["paradigm", "fundamental"]}}, 
         {"LOWER": {"IN": ["shift", "change", "transformation"]}}],
        [{"LOWER": {"IN": ["innovative", "breakthrough", "game-changing"]}}, 
         {"LOWER": {"IN": ["technology", "approach", "solution"]}}],
        [{"LOWER": {"IN": ["replacing", "obsoleting", "eliminating"]}}, 
         {"LOWER": {"IN": ["traditional", "legacy", "existing"]}}]
    ]
}

# Fallback keyword groups for when spaCy is not available
TOP_DOG_KEYWORDS = {
    'market_leader': [
        'market leader', 'leading provider', 'dominant position', 'largest company',
        'top provider', '#1 in', 'number one', 'market leadership', 'industry leader'
    ],
    'first_mover': [
        'first to', 'pioneer', 'pioneered', 'first company', 'originated',
        'breakthrough', 'innovative', 'groundbreaking', 'invented', 'created'
    ],
    'emerging_industry': [
        'emerging market', 'growing market', 'high-growth', 'fast-growing',
        'new market', 'nascent industry', 'next-generation', 'cutting-edge'
    ],
    'disruptor': [
        'disrupt', 'disrupting', 'disruption', 'transforming', 'revolutionizing',
        'paradigm shift', 'game-changing', 'replacing traditional'
    ]
}


def analyze_top_dog_with_spacy(text, ticker):
    """
    Analyze text using spaCy NER patterns for Top Dog indicators with a focus on
    emerging markets and industry disruptors. Uses context analysis to distinguish
    between positive mentions (company as innovator) and negative mentions (risks).
    
    Args:
        text (str): Combined business and risk factors text
        ticker (str): Stock ticker for logging
        
    Returns:
        dict: Match counts for each category and detected emerging industries
    """
    try:
        import spacy
        from spacy.matcher import Matcher
        
        # Load spaCy model
        nlp = spacy.load("en_core_web_sm")
        nlp.max_length = 2000000  # Increase limit for large documents
        
        # Create matcher for entity patterns
        matcher = Matcher(nlp.vocab)
        
        # Add patterns to matcher
        for category, patterns in TOP_DOG_PATTERNS.items():
            matcher.add(category, patterns)
        
        # Process text in smaller chunks for efficiency
        chunk_size = 50000  # 50KB chunks
        all_matches = {"MARKET_LEADER": 0, "FIRST_MOVER": 0, "EMERGING_INDUSTRY": 0, "DISRUPTOR": 0}
        
        # Track emerging industry mentions
        emerging_industry_matches = {industry: 0 for industry in EMERGING_INDUSTRY_TERMS}
        
        # Simple negative context patterns (much smaller window)
        negative_words = {"risk", "threat", "competition", "competitive", "face", "disrupt", 
                         "adversely", "negatively", "challenge", "could", "may", "might"}
        
        for i in range(0, len(text), chunk_size):
            chunk = text[i:i + chunk_size]
            doc = nlp(chunk)
            
            # Process Top Dog pattern matches with efficient context checking
            matches = matcher(doc)
            for match_id, start, end in matches:
                label = nlp.vocab.strings[match_id]
                
                # Check small context window (3 tokens before/after) for negative words
                context_start = max(0, start - 3)
                context_end = min(len(doc), end + 3)
                context_text = doc[context_start:context_end].text.lower()
                
                # Simple negative context check
                is_negative = any(neg_word in context_text for neg_word in negative_words)
                
                if not is_negative:
                    all_matches[label] += 1
                    
                    # Log first few matches for debugging
                    if all_matches[label] <= 2:
                        span = doc[start:end]
                        log_debug(f"Found {label} for {ticker}: '{span.text}' in context: '{context_text[:50]}...'")
            
            # Process emerging industry terms with context analysis
            for industry, terms in EMERGING_INDUSTRY_TERMS.items():
                for sent in doc.sents:
                    # Skip very short sentences
                    if len(sent) < 5:
                        continue
                    
                    # Check for industry terms in the sentence
                    sent_text = sent.text.lower()
                    matched_terms = [term for term in terms if term in sent_text]
                    
                    if matched_terms:
                        # Simple negative context check
                        is_negative = any(neg_word in sent_text for neg_word in negative_words)
                        
                        if not is_negative:
                            emerging_industry_matches[industry] += len(matched_terms)
                            
                            # Only log first match per industry
                            if emerging_industry_matches[industry] == len(matched_terms):
                                log_debug(f"Found emerging industry term '{matched_terms[0]}' ({industry}) for {ticker}")
        
        # Add emerging industry data to results
        all_matches['EMERGING_INDUSTRIES'] = {
            industry: count for industry, count in emerging_industry_matches.items() if count > 0
        }
        
        # Log summary of emerging industries found
        industries_found = [industry for industry, count in emerging_industry_matches.items() if count > 0]
        if industries_found:
            log_debug(f"Emerging industries detected for {ticker}: {', '.join(industries_found)}")
        
        return all_matches
        
    except ImportError:
        log_debug(f"spaCy not available for {ticker}")
        return None
    except Exception as e:
        logger.error(f"Error in spaCy analysis for {ticker}: {e}")
        return None 