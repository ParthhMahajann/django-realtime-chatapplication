# chat/emotion_analyzer.py
import re
import nltk
from textblob import TextBlob
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from datetime import datetime
import logging

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('vader_lexicon')
except LookupError:
    nltk.download('vader_lexicon')

logger = logging.getLogger(__name__)


class EmotionAnalyzer:
    """Advanced emotion analysis using multiple approaches"""
    
    def __init__(self):
        """Initialize analyzer with VADER and emotion patterns"""
        self.vader_analyzer = SentimentIntensityAnalyzer()
        
        # Emotion keyword patterns
        self.emotion_patterns = {
            'happy': [
                r'\b(happy|joy|excited|great|awesome|amazing|love|wonderful|fantastic|excellent|brilliant|perfect|good|nice|pleased|delighted|thrilled|ecstatic)\b',
                r'[😊😄😃😀🥳🎉😍🤩]',
                r'\b(yay|woohoo|hurray|yes!|yess|woo)\b'
            ],
            'sad': [
                r'\b(sad|depressed|down|low|upset|hurt|disappointed|miserable|unhappy|gloomy|blue|heartbroken|devastated)\b',
                r'[😢😭😞😔☹️💔😪😟]',
                r'\b(cry|crying|tears|weep|sob)\b'
            ],
            'angry': [
                r'\b(angry|mad|furious|pissed|annoyed|frustrated|irritated|rage|hate|disgusted|fed up|sick of)\b',
                r'[😠😡🤬😤💢]',
                r'\b(damn|shit|fuck|hell|stupid|idiot|hate)\b'
            ],
            'surprised': [
                r'\b(surprised|shocked|amazed|wow|whoa|omg|incredible|unbelievable|astonishing)\b',
                r'[😲😱🤯😧😮]',
                r'\b(wow!|omg!|no way!|really\?|seriously\?)\b'
            ],
            'fearful': [
                r'\b(scared|afraid|frightened|terrified|worried|anxious|nervous|panic|fear)\b',
                r'[😨😰😱🙈]',
                r'\b(help|scared|terrifying|nightmare)\b'
            ],
            'disgusted': [
                r'\b(disgusted|sick|gross|yuck|eww|nasty|revolting|repulsive)\b',
                r'[🤢🤮😷🤧]',
                r'\b(yuck|eww|gross|ugh)\b'
            ]
        }
        
        # Intensifiers and diminishers
        self.intensifiers = ['very', 'extremely', 'incredibly', 'super', 'really', 'so', 'absolutely']
        self.diminishers = ['slightly', 'somewhat', 'kind of', 'sort of', 'a bit', 'little']
    
    def preprocess_text(self, text):
        """Clean and preprocess text for analysis"""
        if not text or not isinstance(text, str):
            return ""
        
        # Convert to lowercase for analysis
        text = text.lower().strip()
        
        # Remove excessive punctuation but keep some for emphasis
        text = re.sub(r'[!]{2,}', '!', text)
        text = re.sub(r'[?]{2,}', '?', text)
        
        # Handle repeated letters (e.g., "sooooo" -> "so")
        text = re.sub(r'(.)\1{2,}', r'\1\1', text)
        
        return text
    
    def analyze_with_vader(self, text):
        """Use VADER sentiment analyzer"""
        try:
            scores = self.vader_analyzer.polarity_scores(text)
            return {
                'compound': scores['compound'],
                'positive': scores['pos'],
                'negative': scores['neg'],
                'neutral': scores['neu']
            }
        except Exception as e:
            logger.error(f"VADER analysis error: {e}")
            return {'compound': 0.0, 'positive': 0.0, 'negative': 0.0, 'neutral': 1.0}
    
    def analyze_with_textblob(self, text):
        """Use TextBlob for sentiment analysis"""
        try:
            blob = TextBlob(text)
            return {
                'polarity': blob.sentiment.polarity,
                'subjectivity': blob.sentiment.subjectivity
            }
        except Exception as e:
            logger.error(f"TextBlob analysis error: {e}")
            return {'polarity': 0.0, 'subjectivity': 0.0}
    
    def analyze_emotion_patterns(self, text):
        """Analyze text using regex patterns for specific emotions"""
        emotion_scores = {emotion: 0 for emotion in self.emotion_patterns.keys()}
        
        # Check each emotion pattern
        for emotion, patterns in self.emotion_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    # Base score for matches
                    base_score = len(matches) * 0.3
                    
                    # Check for intensifiers
                    for intensifier in self.intensifiers:
                        if intensifier in text:
                            base_score *= 1.5
                            break
                    
                    # Check for diminishers
                    for diminisher in self.diminishers:
                        if diminisher in text:
                            base_score *= 0.7
                            break
                    
                    emotion_scores[emotion] += base_score
        
        return emotion_scores
    
    def classify_emotion(self, vader_scores, textblob_scores, pattern_scores):
        """Combine all analysis methods to classify emotion"""
        compound = vader_scores['compound']
        polarity = textblob_scores['polarity']
        
        # Find the highest pattern score
        max_pattern_emotion = max(pattern_scores.items(), key=lambda x: x[1])
        max_pattern_score = max_pattern_emotion[1]
        
        # If we have a strong pattern match, use it
        if max_pattern_score > 0.5:
            emotion = max_pattern_emotion[0]
            confidence = min(max_pattern_score, 1.0)
        else:
            # Use sentiment scores for classification
            if compound >= 0.5 or polarity >= 0.3:
                emotion = 'happy' if compound >= 0.7 or polarity >= 0.5 else 'positive'
                confidence = abs(compound) if compound != 0 else abs(polarity)
            elif compound <= -0.5 or polarity <= -0.3:
                emotion = 'angry' if compound <= -0.7 or polarity <= -0.5 else 'sad'
                confidence = abs(compound) if compound != 0 else abs(polarity)
            else:
                emotion = 'neutral'
                confidence = 1.0 - abs(compound)
        
        # Ensure confidence is between 0 and 1
        confidence = max(0.0, min(1.0, confidence))
        
        return emotion, confidence
    
    def analyze(self, text):
        """Main analysis method that combines all approaches"""
        if not text or not isinstance(text, str) or len(text.strip()) == 0:
            return {
                'emotion': 'neutral',
                'confidence': 0.5,
                'polarity': 0.0,
                'subjectivity': 0.0,
                'vader_scores': {'compound': 0.0, 'positive': 0.0, 'negative': 0.0, 'neutral': 1.0},
                'pattern_scores': {emotion: 0 for emotion in self.emotion_patterns.keys()}
            }
        
        # Preprocess text
        processed_text = self.preprocess_text(text)
        
        # Run all analysis methods
        vader_scores = self.analyze_with_vader(processed_text)
        textblob_scores = self.analyze_with_textblob(processed_text)
        pattern_scores = self.analyze_emotion_patterns(processed_text)
        
        # Classify final emotion
        emotion, confidence = self.classify_emotion(vader_scores, textblob_scores, pattern_scores)
        
        return {
            'emotion': emotion,
            'confidence': confidence,
            'polarity': textblob_scores['polarity'],
            'subjectivity': textblob_scores['subjectivity'],
            'vader_scores': vader_scores,
            'pattern_scores': pattern_scores
        }
    
    def get_emotion_emoji(self, emotion):
        """Get emoji representation of emotion"""
        emoji_map = {
            'happy': '😊',
            'sad': '😢',
            'angry': '😠',
            'surprised': '😲',
            'fearful': '😨',
            'disgusted': '🤢',
            'neutral': '😐',
            'positive': '🙂',
            'negative': '😞'
        }
        return emoji_map.get(emotion, '😐')


# Example usage and testing
if __name__ == "__main__":
    analyzer = EmotionAnalyzer()
    
    test_messages = [
        "I'm so happy today! This is amazing!",
        "I feel really sad and down right now 😢",
        "This is making me so angry! I hate this!",
        "Wow! That's incredible! I'm so surprised!",
        "I'm scared and worried about this...",
        "This is disgusting and gross 🤮",
        "Just a normal day, nothing special.",
        "It's okay, I guess. Not bad.",
    ]
    
    print("Testing Emotion Analyzer:")
    print("=" * 50)
    
    for message in test_messages:
        result = analyzer.analyze(message)
        print(f"Message: {message}")
        print(f"Emotion: {result['emotion']} {analyzer.get_emotion_emoji(result['emotion'])}")
        print(f"Confidence: {result['confidence']:.2f}")
        print(f"Polarity: {result['polarity']:.2f}")
        print("-" * 30)
