import re
import nltk

# Initialize spaCy if available
try:
    import spacy
    nlp = spacy.load("en_core_web_sm")
except Exception:
    nlp = None

# Cache NLTK resource status to avoid repeated disk checks
_nltk_checked = False

def download_nltk_resources():
    """
    Downloads NLTK resources silently, catching exceptions.
    Optimized to run once lazily.
    """
    global _nltk_checked
    if _nltk_checked:
        return
    resources = ['punkt', 'stopwords', 'wordnet', 'omw-1.4']
    for res in resources:
        try:
            if res == 'punkt':
                nltk.data.find('tokenizers/punkt')
            elif res == 'stopwords':
                nltk.data.find('corpora/stopwords')
            elif res == 'wordnet':
                nltk.data.find('corpora/wordnet')
            elif res == 'omw-1.4':
                nltk.data.find('corpora/omw-1.4')
        except LookupError:
            try:
                nltk.download(res, quiet=True)
            except Exception as e:
                print(f"Failed to download NLTK resource {res}: {e}")
    _nltk_checked = True

def clean_text(text):
    """
    Standardizes text by converting to lowercase, replacing line breaks, 
    and removing special characters while preserving programming tokens (like C++, C#, .NET, Node.js, React.js).
    """
    if not text:
        return ""
    text = text.lower()
    text = text.replace('\n', ' ').replace('\r', ' ')
    
    # Custom replacement to protect technical symbols
    tokens_to_shield = {
        'c++': 'cpp_token',
        'c#': 'csharp_token',
        '.net': 'dotnet_token',
        'node.js': 'nodejs_token',
        'react.js': 'reactjs_token',
        'vue.js': 'vuejs_token',
        'next.js': 'nextjs_token',
        'three.js': 'threejs_token',
        'socket.io': 'socketio_token'
    }
    
    for key, token in tokens_to_shield.items():
        text = text.replace(key, token)
        
    # Remove special characters but keep alphanumeric and spaces
    text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text)
    
    # Restore protected symbols
    for key, token in tokens_to_shield.items():
        text = text.replace(token, key)
        
    # Remove excessive spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def preprocess_and_tokenize(text):
    """
    Extracts meaningful lemmatized tokens from text, filtering stopwords.
    Uses spaCy if loaded; falls back to NLTK, and then to a simple string-splitting method.
    """
    download_nltk_resources()
    cleaned = clean_text(text)
    if not cleaned:
        return []
        
    # Strategy 1: spaCy
    if nlp:
        try:
            doc = nlp(cleaned)
            tokens = [token.lemma_ for token in doc if not token.is_stop and not token.is_space]
            return tokens
        except Exception as e:
            print(f"spaCy tokenization failed: {e}. Falling back to NLTK...")
            
    # Strategy 2: NLTK
    try:
        from nltk.tokenize import word_tokenize
        from nltk.corpus import stopwords
        from nltk.stem import WordNetLemmatizer
        
        tokens = word_tokenize(cleaned)
        try:
            stop_words = set(stopwords.words('english'))
        except Exception:
            stop_words = set()
            
        lemmatizer = WordNetLemmatizer()
        filtered = []
        for t in tokens:
            if t not in stop_words and len(t) > 1:
                try:
                    lemma = lemmatizer.lemmatize(t)
                except Exception:
                    lemma = t
                filtered.append(lemma)
        return filtered
    except Exception as e:
        print(f"NLTK tokenization failed: {e}. Falling back to basic tokenizer...")
        
    # Strategy 3: Basic python split
    common_stopwords = {'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', 'your', 'yours', 
                        'he', 'him', 'his', 'himself', 'she', 'her', 'hers', 'herself', 'it', 'its', 'itself', 
                        'they', 'them', 'their', 'theirs', 'themselves', 'what', 'which', 'who', 'whom', 
                        'this', 'that', 'these', 'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 
                        'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing', 'a', 'an', 'the', 'and', 
                        'but', 'if', 'or', 'because', 'as', 'until', 'while', 'of', 'at', 'by', 'for', 'with', 
                        'about', 'against', 'between', 'into', 'through', 'during', 'before', 'after', 'above', 
                        'below', 'to', 'from', 'up', 'down', 'in', 'out', 'on', 'off', 'over', 'under', 'again', 
                        'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'any', 
                        'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 
                        'own', 'same', 'so', 'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don', 'should', 'now'}
    words = cleaned.split()
    return [w for w in words if w not in common_stopwords and len(w) > 1]
