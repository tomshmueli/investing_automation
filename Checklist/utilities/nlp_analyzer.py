"""
NLP Analyzer Module

This module provides NLP analysis framework with spaCy integration for text analysis.
Extracted from utils.py to provide better organization and separation of concerns.
"""

import re
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from .logging_config import get_logger, log_debug

logger = get_logger(__name__)

# NLP Setup - Load spaCy model for enhanced text analysis
try:
    import spacy
    nlp = spacy.load("en_core_web_sm")
    # Reasonable limit for individual sentences (no longer processing entire documents)
    nlp.max_length = 10000
    NLP_AVAILABLE = True
    log_debug("spaCy NLP model loaded successfully")
except (ImportError, OSError) as e:
    nlp = None
    NLP_AVAILABLE = False
    log_debug("spaCy not available. Install with: pip install spacy && python -m spacy download en_core_web_sm")
    log_debug("Some advanced analysis features will use fallback methods")


@dataclass
class TextFinding:
    """Generic structured data for text analysis findings"""
    value: float  # Numerical value (percentage, amount, etc.)
    context: str
    confidence: float
    finding_type: str  # 'single', 'multiple', 'general', etc.
    is_actual: bool  # True if actual fact, False if risk factor/hypothetical
    sentence: str
    metadata: Dict = None  # Additional context-specific data


@dataclass
class ContextFinding:
    """Enhanced finding structure for context analysis"""
    sentence: str
    value: float
    finding_type: str  # 'single', 'few', 'multiple'
    confidence: float
    is_actual: bool
    context: str = ""  # Add missing context attribute


class NLPAnalyzer:
    """Reusable NLP analyzer for SEC filings and financial documents"""
    
    def __init__(self):
        self.nlp = nlp
        self.nlp_available = NLP_AVAILABLE
        
    def extract_sentences_with_numbers(self, text: str, number_pattern: str = r'(\d{1,2}(?:\.\d{1,2})?)\s*%') -> List[Tuple[str, List[float]]]:
        """
        Extract sentences containing specific number patterns using SMART preprocessing
        - Fast regex preprocessing to find candidate sentences
        - Only use NLP on relevant sentences (much faster!)
        """
        return self._extract_sentences_smart(text, number_pattern)
    
    def _extract_sentences_smart(self, text: str, number_pattern: str) -> List[Tuple[str, List[float]]]:
        """
        Smart preprocessing: Fast regex + targeted NLP
        
        Performance: ~100x faster than processing entire document
        """
        # Step 1: Fast regex preprocessing to find candidate sentences
        candidate_sentences = self._find_candidate_sentences(text, number_pattern)
        
        if not candidate_sentences:
            return []
        
        # Step 2: Only use NLP on candidate sentences (much smaller dataset)
        if self.nlp_available and len(candidate_sentences) < 100:  # Safety limit
            return self._refine_with_nlp(candidate_sentences, number_pattern)
        else:
            # Use enhanced regex for large datasets or when NLP unavailable
            return self._process_candidates_regex(candidate_sentences, number_pattern)
    
    def _find_candidate_sentences(self, text: str, number_pattern: str) -> List[str]:
        """
        Fast regex-based preprocessing to find sentences containing numbers
        """
        # Split into sentences using multiple delimiters
        sentences = re.split(r'[.!?]+', text)
        candidates = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20:  # Skip very short fragments
                continue
                
            # Check if sentence contains numbers matching our pattern
            if re.search(number_pattern, sentence):
                candidates.append(sentence)
        
        return candidates
    
    def _refine_with_nlp(self, candidate_sentences: List[str], number_pattern: str) -> List[Tuple[str, List[float]]]:
        """
        Use NLP only on pre-filtered candidate sentences (much faster!)
        """
        sentences_with_numbers = []
        
        for sentence in candidate_sentences:
            # Only process individual sentences through NLP (very fast)
            try:
                doc = self.nlp(sentence)
                sent_text = sentence.strip()
                
                # Find numbers matching the pattern
                numbers = re.findall(number_pattern, sent_text)
                if numbers:
                    num_values = [float(n) for n in numbers if self._is_meaningful_number(float(n))]
                    if num_values:
                        sentences_with_numbers.append((sent_text, num_values))
            except Exception as e:
                # Fallback to regex for problematic sentences
                numbers = re.findall(number_pattern, sentence)
                if numbers:
                    num_values = [float(n) for n in numbers if self._is_meaningful_number(float(n))]
                    if num_values:
                        sentences_with_numbers.append((sentence, num_values))
        
        return sentences_with_numbers
    
    def _process_candidates_regex(self, candidate_sentences: List[str], number_pattern: str) -> List[Tuple[str, List[float]]]:
        """
        Process candidate sentences using enhanced regex (fallback method)
        """
        sentences_with_numbers = []
        
        for sentence in candidate_sentences:
            numbers = re.findall(number_pattern, sentence)
            if numbers:
                num_values = [float(n) for n in numbers if self._is_meaningful_number(float(n))]
                if num_values:
                    sentences_with_numbers.append((sentence, num_values))
        
        return sentences_with_numbers
    
    def _extract_sentences_regex(self, text: str, number_pattern: str) -> List[Tuple[str, List[float]]]:
        """Fallback method using regex sentence splitting"""
        # Simple sentence splitting
        sentences = re.split(r'[.!?]+', text)
        sentences_with_numbers = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:  # Skip very short fragments
                continue
                
            numbers = re.findall(number_pattern, sentence)
            if numbers:
                num_values = [float(n) for n in numbers if self._is_meaningful_number(float(n))]
                if num_values:
                    sentences_with_numbers.append((sentence, num_values))
        
        return sentences_with_numbers
    
    def _is_meaningful_number(self, number: float) -> bool:
        """Determine if a number is meaningful for analysis (override in subclasses)"""
        return number > 5  # Default: percentages > 5%
    
    def analyze_sentence_context(self, sentence: str, numbers: List[float], 
                               required_terms: dict, context_classifiers: dict = None) -> ContextFinding:
        """Enhanced context analysis with business logic"""
        # Check if all required terms are present
        terms_found = {}
        for category, terms in required_terms.items():
            found = any(term in sentence.lower() for term in terms)
            terms_found[category] = found
        
        # Must have both customer and revenue terms
        if not all(terms_found.values()):
            return None
        
        # Use new classification method
        customer_type = self.classify_customer_type(sentence, max(numbers))
        
        # If classification returns None (should be excluded), return None
        if customer_type is None:
            return None
        
        # Get the highest percentage
        max_percentage = max(numbers)
        
        # Determine if this is actual vs risk/forward-looking
        is_actual = self._is_actual_statement(sentence)
        
        return ContextFinding(
            sentence=sentence,
            value=max_percentage,
            finding_type=customer_type,
            confidence=0.9 if is_actual else 0.7,
            is_actual=is_actual,
            context=sentence[:200]  # Truncate for readability
        )
    
    def classify_customer_type(self, sentence: str, percentage: float) -> str:
        """
        Classify customer concentration type based on sentence content and percentage.
        
        Returns:
            str: 'single', 'few', 'multiple', or None if should be excluded
        """
        sentence_lower = sentence.lower()
        
        # Exclusion patterns - these should not be counted
        exclusion_patterns = [
            'geographic', 'geographical', 'region', 'international', 'domestic',
            'industry', 'sector', 'market segment', 'product line', 'business unit',
            'channel', 'distribution', 'sales channel', 'revenue stream',
            'service line', 'division', 'subsidiary', 'segment'
        ]
        
        # Check if sentence should be excluded
        if any(pattern in sentence_lower for pattern in exclusion_patterns):
            return None
        
        # Single customer patterns
        single_patterns = [
            'customer', 'client', 'account', 'largest customer', 'major customer',
            'significant customer', 'key customer', 'primary customer'
        ]
        
        # Multiple customer patterns  
        multiple_patterns = [
            'customers', 'clients', 'accounts', 'top customers', 'major customers',
            'largest customers', 'key customers', 'significant customers'
        ]
        
        # Count pattern matches
        single_matches = sum(1 for pattern in single_patterns if pattern in sentence_lower)
        multiple_matches = sum(1 for pattern in multiple_patterns if pattern in sentence_lower)
        
        # Classification logic
        if single_matches > multiple_matches:
            return 'single'
        elif multiple_matches > 0:
            # Further classify based on percentage and context
            if percentage >= 50:
                return 'single'  # Very high concentration likely means single customer
            elif percentage >= 20:
                return 'few'     # Moderate concentration likely means few customers
            else:
                return 'multiple'  # Lower concentration likely means multiple customers
        else:
            # No clear customer indicators, use percentage-based classification
            if percentage >= 50:
                return 'single'
            elif percentage >= 25:
                return 'few'
            else:
                return 'multiple'
    
    def _is_actual_statement(self, sentence: str) -> bool:
        """
        Determine if a sentence describes actual facts vs risks/forward-looking statements.
        
        Returns:
            bool: True if actual fact, False if risk/forward-looking
        """
        sentence_lower = sentence.lower()
        
        # Risk/forward-looking indicators
        risk_patterns = [
            'risk', 'could', 'may', 'might', 'potential', 'possible', 'if', 'would',
            'forward-looking', 'projection', 'estimate', 'expect', 'anticipate',
            'believe', 'plan', 'intend', 'future', 'outlook', 'guidance'
        ]
        
        return not any(pattern in sentence_lower for pattern in risk_patterns)
    
    def enhanced_regex_analysis(self, text: str, patterns: Dict[str, List[str]], 
                               exclusion_patterns: List[str]) -> List[Dict]:
        """
        Enhanced regex analysis with exclusion patterns and context extraction.
        
        Args:
            text: Text to analyze
            patterns: Dict of pattern categories and their regex patterns
            exclusion_patterns: List of patterns to exclude from results
            
        Returns:
            List of findings with context and classification
        """
        findings = []
        
        for category, pattern_list in patterns.items():
            for pattern in pattern_list:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                
                for match in matches:
                    # Extract context around match
                    start = max(0, match.start() - 100)
                    end = min(len(text), match.end() + 100)
                    context = text[start:end].strip()
                    
                    # Check exclusion patterns
                    if any(excl_pattern in context.lower() for excl_pattern in exclusion_patterns):
                        continue
                    
                    findings.append({
                        'category': category,
                        'match': match.group(),
                        'context': context,
                        'position': match.start()
                    })
        
        return findings


def extract_percentage_sentences(text: str) -> List[Tuple[str, List[float]]]:
    """Extract sentences containing percentage values."""
    analyzer = NLPAnalyzer()
    return analyzer.extract_sentences_with_numbers(text, r'(\d{1,2}(?:\.\d{1,2})?)\s*%')


def extract_dollar_sentences(text: str) -> List[Tuple[str, List[float]]]:
    """Extract sentences containing dollar amounts."""
    analyzer = NLPAnalyzer()
    return analyzer.extract_sentences_with_numbers(text, r'\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)')


def is_nlp_available() -> bool:
    """Check if NLP capabilities are available."""
    return NLP_AVAILABLE


nlp_analyzer = NLPAnalyzer() 