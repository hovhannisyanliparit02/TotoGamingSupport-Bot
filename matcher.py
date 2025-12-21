import re
import logging
from rules_data import RULES

# Setup logger for this module
logger = logging.getLogger(__name__)

def normalize(text: str) -> str:
    """Normalize text for matching - better Armenian support."""
    if not text:
        return ""
    
    # Convert to lowercase and strip whitespace
    text = text.lower().strip()
    
    # Remove punctuation but keep Armenian characters
    # Armenian Unicode ranges: \u0530-\u058F (uppercase), \u0561-\u0587 (lowercase)
    # Also keep Latin letters and numbers
    text = re.sub(r'[^\w\s\u0530-\u058F\u0561-\u0587]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    
    return text

def detect_language(text: str) -> str:
    """Detect if text is in Armenian or Latin script."""
    if not text:
        return "hy"
    
    # Count Armenian vs Latin characters
    armenian_count = 0
    latin_count = 0
    
    for ch in text:
        if '\u0530' <= ch <= '\u058F' or '\u0561' <= ch <= '\u0587':
            armenian_count += 1
        elif ch.isalpha():
            latin_count += 1
    
    return "hy" if armenian_count >= latin_count else "latin"

def find_answer(message: str):
    """Find matching answer for the message with improved matching."""
    if not message or not message.strip():
        return None
    
    original_text = message
    normalized_text = normalize(message)
    
    if not normalized_text:
        return None
    
    lang = detect_language(message)
    logger.info(f"Processing: '{original_text}' -> '{normalized_text}' -> Lang: {lang}")
    
    # Get all words from the normalized text
    words = normalized_text.split()
    logger.info(f"Words extracted: {words}")
    
    best_match = None
    highest_score = 0
    best_rule = None
    
    # First pass: exact word matching
    for rule_name, rule in RULES.items():
        matched_keywords = []
        score = 0
        
        for keyword in rule["keywords"]:
            normalized_keyword = normalize(keyword)
            
            # Exact word match
            if normalized_keyword in words:
                matched_keywords.append(keyword)
                score += 3  # High score for exact match
                logger.debug(f"Exact match: '{keyword}' -> '{normalized_keyword}'")
            
            # Also check if any word contains the keyword or keyword contains the word
            else:
                for word in words:
                    if len(word) > 2 and len(normalized_keyword) > 2:
                        if word in normalized_keyword or normalized_keyword in word:
                            matched_keywords.append(keyword)
                            score += 2  # Medium score for partial match
                            logger.debug(f"Partial match: '{word}' in '{normalized_keyword}' or vice versa")
                            break
        
        if matched_keywords:
            logger.info(f"Rule '{rule_name}' matched with keywords: {matched_keywords}, score: {score}")
            
            if score > highest_score:
                highest_score = score
                best_rule = rule_name
                
                # Get answer in correct language
                if lang in rule["answer"]:
                    best_match = rule["answer"][lang]
                else:
                    best_match = rule["answer"].get("hy", rule["answer"].get("latin", ""))
    
    # If no matches found with exact/partial matching, try fuzzy matching
    if not best_match:
        logger.info("No exact matches found, trying fuzzy matching...")
        
        for rule_name, rule in RULES.items():
            for keyword in rule["keywords"]:
                normalized_keyword = normalize(keyword)
                
                # Check if any word from the query appears in the keyword or vice versa
                for word in words:
                    if len(word) > 3 and word in normalized_keyword:
                        logger.info(f"Fuzzy match: '{word}' in keyword '{keyword}'")
                        
                        if lang in rule["answer"]:
                            best_match = rule["answer"][lang]
                        else:
                            best_match = rule["answer"].get("hy", rule["answer"].get("latin", ""))
                        break
                
                if best_match:
                    break
            
            if best_match:
                break
    
    if best_match:
        logger.info(f"Best match: rule '{best_rule}' with score {highest_score}")
        return best_match
    
    logger.info("No matching rule found")
    return None

def test_matcher():
    """Test the matcher with sample queries."""
    # Enable debug logging
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    test_cases = [
        "Ինչպես դեպոզիտ անել",
        "Քարտ",
        "Ընկերության մասին",
        "Տարիքային սահմանափակում",
        "Կանոններ",
        "Դուրսբերում",
        "Կապի տվյալներ",
        "վճարում",
        "բանկ",
        "գումար"
    ]
    
    print("Testing matcher with Armenian queries...\n")
    print("=" * 60)
    
    for query in test_cases:
        print(f"\nQuery: '{query}'")
        result = find_answer(query)
        if result:
            print(f"✓ Found match!")
            print(f"Answer preview: {result[:150]}...")
        else:
            print("✗ No match found")
        
        print("-" * 40)

if __name__ == "__main__":
    test_matcher()