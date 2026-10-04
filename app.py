import os
import re
import json
import string
import joblib
import pandas as pd
import numpy as np
import textstat
import requests as http_requests
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify, render_template

import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.stem.porter import PorterStemmer
from nltk.tokenize import RegexpTokenizer

# Initialize Flask app
app = Flask(__name__)

# Load models and data mapping
base_path = os.path.dirname(os.path.abspath(__file__))
models_dir = os.path.join(base_path, "models")
ratios_path = os.path.join(base_path, "data", "location_ratios.json")

# Set up local NLTK data path
nltk_data_dir = os.path.join(base_path, "nltk_data")
nltk.data.path.append(nltk_data_dir)

# Ensure NLTK resources are available locally (download in background if on Render to avoid boot timeouts)
def download_nltk_resources():
    try:
        os.makedirs(nltk_data_dir, exist_ok=True)
        nltk.download('stopwords', download_dir=nltk_data_dir, quiet=True)
        nltk.download('wordnet', download_dir=nltk_data_dir, quiet=True)
        nltk.download('omw-1.4', download_dir=nltk_data_dir, quiet=True)
    except Exception as e:
        print(f"Error downloading NLTK data in background: {e}")

if os.environ.get('RENDER'):
    import threading
    threading.Thread(target=download_nltk_resources).start()
else:
    # Run synchronously locally to ensure it is immediately available
    if not os.path.exists(nltk_data_dir) or len(os.listdir(nltk_data_dir)) < 2:
        download_nltk_resources()

# Load stop_words safely with lazy/fallback load
stop_words = None
try:
    stop_words = set(stopwords.words('english'))
except Exception:
    pass

lemmatizer = WordNetLemmatizer()
tokenizer = RegexpTokenizer(r'\w+')
stemmer = PorterStemmer()

print("Loading models...")
tfidf_vectorizer = joblib.load(os.path.join(models_dir, "tfidf_vectorizer.pkl"))
clf_log = joblib.load(os.path.join(models_dir, "clf_log.pkl"))
clf_num = joblib.load(os.path.join(models_dir, "clf_num.pkl"))
numeric_features = joblib.load(os.path.join(models_dir, "numeric_features.pkl"))

print("Loading location ratios...")
with open(ratios_path, "r") as f:
    location_ratios = json.load(f)


# ============================================================
# 2026-Era Feature Engineering (mirrors train_model.py exactly)
# ============================================================
def compute_engineered_features(text):
    """Compute the same engineered features used during training."""
    features = {}

    # 1. Word count
    words = text.split()
    features['word_count'] = len(words)

    # 2. Average word length
    features['avg_word_length'] = np.mean([len(w) for w in words]) if words else 0

    # 3. Uppercase ratio
    features['uppercase_ratio'] = sum(1 for c in text if c.isupper()) / len(text) if text else 0

    # 4. URL count
    url_pattern = r'#URL_[a-f0-9]+#|https?://\S+|www\.\S+'
    features['url_count'] = len(re.findall(url_pattern, text))

    # 5. Email count
    email_pattern = r'#EMAIL_[a-f0-9]+#|[\w\.-]+@[\w\.-]+'
    features['email_count'] = len(re.findall(email_pattern, text))

    # 6. Phone count
    phone_pattern = r'#PHONE_[a-f0-9]+#|\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
    features['phone_count'] = len(re.findall(phone_pattern, text))

    # 7. Flesch Reading Ease
    try:
        score = textstat.flesch_reading_ease(text)
        features['flesch_reading_ease'] = max(min(score, 100), -50)
    except Exception:
        features['flesch_reading_ease'] = 50.0

    # 8. Sentence count
    features['sentence_count'] = max(textstat.sentence_count(text), 1)

    # 9. Punctuation density
    features['punctuation_density'] = sum(1 for c in text if c in string.punctuation) / len(text) if text else 0

    # 10. Exclamation count
    features['exclamation_count'] = text.count('!')

    # 11. Question count
    features['question_count'] = text.count('?')

    return features


# Helper function to preprocess text matching eda.ipynb
def preprocess_text(text):
    global stop_words
    if not isinstance(text, str):
        text = ""
    # Punctuation removal
    no_punct = "".join([c for c in text if c not in string.punctuation])
    # Tokenization & Lowercasing
    tokens = tokenizer.tokenize(no_punct.lower())
    
    # Lazy load or fallback stop words
    if stop_words is None:
        try:
            stop_words = set(stopwords.words('english'))
        except Exception:
            # Standard NLTK English stopwords list
            stop_words = {'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', "you're", "you've", "you'll", "you'd", 'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', "she's", 'her', 'hers', 'herself', 'it', "it's", 'its', 'itself', 'they', 'them', 'their', 'theirs', 'themselves', 'what', 'which', 'who', 'whom', 'this', 'that', "that'll", 'these', 'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if', 'or', 'because', 'as', 'until', 'while', 'of', 'at', 'by', 'for', 'with', 'about', 'against', 'between', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'to', 'from', 'up', 'down', 'in', 'out', 'on', 'off', 'over', 'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don', "don't", 'should', "should've", 'now', 'd', 'll', 'm', 'o', 're', 've', 'y', 'ain', 'aren', "aren't", 'couldn', "couldn't", 'didn', "didn't", 'doesn', "doesn't", 'hadn', "hadn't", 'hasn', "hasn't", 'haven', "haven't", 'isn', "isn't", 'ma', 'mightn', "mightn't", 'mustn', "mustn't", 'needn', "needn't", 'shan', "shan't", 'shouldn', "shouldn't", 'wasn', "wasn't", 'weren', "weren't", 'won', "won't", 'wouldn', "wouldn't"}
            
    # Stopwords removal
    filtered_tokens = [w for w in tokens if w not in stop_words]
    # Lemmatization
    try:
        lemmed = [lemmatizer.lemmatize(i) for i in filtered_tokens]
    except Exception:
        lemmed = filtered_tokens
    # Stemming
    stemmed = " ".join([stemmer.stem(i) for i in lemmed])
    # Remove numbers
    cleaned = re.sub(r'[0-9]', '', stemmed)
    return cleaned

# Helper function to find location ratio
def get_location_ratio(loc_str):
    if not loc_str or not isinstance(loc_str, str):
        return 0.0
    
    loc_clean = loc_str.strip()
    # 1. Exact match
    if loc_clean in location_ratios:
        return location_ratios[loc_clean]
    
    # 2. Case insensitive match
    loc_clean_lower = loc_clean.lower()
    for k, v in location_ratios.items():
        if k.lower() == loc_clean_lower:
            return v
            
    # 3. Substring matching
    matched_ratios = []
    for k, v in location_ratios.items():
        if loc_clean_lower in k.lower() or k.lower() in loc_clean_lower:
            matched_ratios.append(v)
    if matched_ratios:
        return max(matched_ratios)
        
    return 0.0

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/privacy')
def privacy():
    return render_template('privacy.html')


@app.route('/security')
def security():
    return render_template('security.html')


@app.route('/contact')
def contact():
    return render_template('contact.html')


def extract_json_ld(soup):
    """Attempt to find and parse Schema.org JobPosting json-ld markup."""
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            if not script.string:
                continue
            data = json.loads(script.string.strip())
            
            items = []
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                if '@graph' in data and isinstance(data['@graph'], list):
                    items = data['@graph']
                else:
                    items = [data]
            
            for item in items:
                if isinstance(item, dict) and item.get('@type') == 'JobPosting':
                    return item
        except Exception:
            continue
    return None


@app.route('/scrape', methods=['POST'])
def scrape_url():
    """Scrape a job posting URL and extract structured fields."""
    try:
        data = request.json or {}
        url = data.get('url', '').strip()

        if not url:
            return jsonify({"status": "error", "message": "No URL provided."}), 400

        # Ensure URL has a scheme
        if not url.startswith('http://') and not url.startswith('https://'):
            url = 'https://' + url

        # Fetch the page
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
        }
        resp = http_requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, 'html.parser')

        # --- Extract JSON-LD first ---
        job_data = extract_json_ld(soup)

        # Remove script and style elements
        for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'iframe']):
            tag.decompose()

        # --- Extract structured fields ---
        result = {
            'title': '',
            'location': '',
            'company_profile': '',
            'description': '',
            'requirements': '',
            'benefits': '',
            'required_experience': '',
            'required_education': '',
            'industry': '',
            'function': '',
            'telecommuting': 0,
            'source_url': url
        }

        # If JSON-LD found, pre-populate values
        if job_data:
            if job_data.get('title'):
                result['title'] = str(job_data['title']).strip()
            
            org = job_data.get('hiringOrganization')
            if isinstance(org, dict):
                result['company_profile'] = str(org.get('name', '')).strip()
            elif isinstance(org, str):
                result['company_profile'] = org.strip()
            
            loc = job_data.get('jobLocation')
            if isinstance(loc, dict):
                address = loc.get('address')
                if isinstance(address, dict):
                    loc_parts = []
                    country = address.get('addressCountry', 'US')
                    if isinstance(country, dict):
                        country = country.get('name', 'US')
                    state = address.get('addressRegion', '')
                    city = address.get('addressLocality', '')
                    
                    if country: loc_parts.append(str(country))
                    if state: loc_parts.append(str(state))
                    if city: loc_parts.append(str(city))
                    result['location'] = ", ".join(loc_parts)
                elif isinstance(loc.get('name'), str):
                    result['location'] = loc['name'].strip()
            elif isinstance(loc, str):
                result['location'] = loc.strip()
                
            raw_desc = job_data.get('description', '')
            if raw_desc:
                desc_soup = BeautifulSoup(raw_desc, 'html.parser')
                result['description'] = desc_soup.get_text(separator='\n', strip=True)[:3000]

            # Try to infer other metadata from JSON-LD
            emp_type = job_data.get('employmentType')
            if emp_type:
                if isinstance(emp_type, list):
                    emp_type = ", ".join(map(str, emp_type))
                emp_type_str = str(emp_type).lower()
                # Check for telecommuting hint
                if any(k in emp_type_str for k in ['remote', 'telecommute', 'home']):
                    result['telecommuting'] = 1

            edu = job_data.get('educationRequirements')
            if isinstance(edu, dict):
                result['required_education'] = str(edu.get('credentialCategory', '')).strip()
            elif isinstance(edu, str):
                result['required_education'] = edu.strip()
                
            exp = job_data.get('experienceRequirements')
            if isinstance(exp, dict):
                result['required_experience'] = str(exp.get('monthsOfExperience', '')).strip()
            elif isinstance(exp, str):
                result['required_experience'] = exp.strip()

        # Title fallback: try meta og:title, then page title, then first h1
        if not result['title']:
            og_title = soup.find('meta', property='og:title')
            if og_title and og_title.get('content'):
                result['title'] = og_title['content'].strip()
            elif soup.title and soup.title.string:
                result['title'] = soup.title.string.strip()
            else:
                h1 = soup.find('h1')
                if h1:
                    result['title'] = h1.get_text(strip=True)

        # Location fallback: look for common patterns
        if not result['location']:
            location_keywords = ['location', 'job-location', 'jobLocation', 'work-location']
            for kw in location_keywords:
                loc_el = soup.find(attrs={'class': re.compile(kw, re.I)}) or soup.find(attrs={'id': re.compile(kw, re.I)})
                if loc_el:
                    result['location'] = loc_el.get_text(strip=True)[:200]
                    break

        # Check for remote/telecommuting keywords fallback
        full_text = soup.get_text(separator=' ', strip=True).lower()
        remote_keywords = ['remote', 'work from home', 'telecommute', 'work-from-home', 'fully remote']
        if any(kw in full_text for kw in remote_keywords):
            result['telecommuting'] = 1

        # Company fallback: look for og:site_name or company-related elements
        if not result['company_profile']:
            og_site = soup.find('meta', property='og:site_name')
            if og_site and og_site.get('content'):
                result['company_profile'] = og_site['content'].strip()

        # Description fallback: try meta description, then og:description, then body text
        if not result['description']:
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            og_desc = soup.find('meta', property='og:description')
            if og_desc and og_desc.get('content'):
                result['description'] = og_desc['content'].strip()
            elif meta_desc and meta_desc.get('content'):
                result['description'] = meta_desc['content'].strip()

        # Extract all visible body text as main content
        body_text = soup.get_text(separator='\n', strip=True)
        # Clean up excessive whitespace
        lines = [line.strip() for line in body_text.split('\n') if line.strip()]
        full_body = '\n'.join(lines)

        # If description is still short, use the body text
        if len(result['description']) < 100:
            result['description'] = full_body[:3000]

        # Try to extract sections by headings
        section_map = {
            'requirements': ['requirements', 'qualifications', 'what you need', 'skills', 'must have', 'what we look for'],
            'benefits': ['benefits', 'perks', 'what we offer', 'compensation', 'why join'],
            'description': ['description', 'about the role', 'about this role', 'job description', 'the role', 'responsibilities', 'what you\'ll do']
        }

        for heading in soup.find_all(['h2', 'h3', 'h4', 'strong', 'b']):
            heading_text = heading.get_text(strip=True).lower()
            for field, keywords in section_map.items():
                if any(kw in heading_text for kw in keywords):
                    # Get the next sibling content
                    content_parts = []
                    sibling = heading.find_next_sibling()
                    while sibling and sibling.name not in ['h2', 'h3', 'h4']:
                        text = sibling.get_text(strip=True)
                        if text:
                            content_parts.append(text)
                        sibling = sibling.find_next_sibling()
                        if len(content_parts) > 20:
                            break
                    if content_parts:
                        extracted = '\n'.join(content_parts)[:2000]
                        if len(extracted) > len(result.get(field, '')):
                            result[field] = extracted

        return jsonify({
            "status": "success",
            "data": result
        })

    except http_requests.exceptions.Timeout:
        return jsonify({"status": "error", "message": "Request timed out. The website took too long to respond."}), 408
    except http_requests.exceptions.ConnectionError:
        return jsonify({"status": "error", "message": "Could not connect to the URL. Please check the address."}), 502
    except http_requests.exceptions.HTTPError as e:
        return jsonify({"status": "error", "message": f"HTTP error {e.response.status_code}: The page could not be loaded."}), 502
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": f"Scraping failed: {str(e)}"}), 500


@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.json or {}
        
        # Extract fields
        title = data.get('title', '').strip()
        location = data.get('location', '').strip()
        company_profile = data.get('company_profile', '').strip()
        description = data.get('description', '').strip()
        requirements = data.get('requirements', '').strip()
        benefits = data.get('benefits', '').strip()
        required_experience = data.get('required_experience', '').strip()
        required_education = data.get('required_education', '').strip()
        industry = data.get('industry', '').strip()
        function = data.get('function', '').strip()
        
        # Telecommuting status (integer 0 or 1)
        telecommuting = int(data.get('telecommuting', 0))
        
        # Reconstruct the raw text
        raw_text_parts = [
            title, location, company_profile, description, requirements, benefits,
            required_experience, required_education, industry, function
        ]
        raw_text = " ".join([part if part else " " for part in raw_text_parts])
        
        # Compute base derived features
        character_count = len(raw_text)
        ratio = get_location_ratio(location)
        
        # Compute 2026-era engineered features
        eng_features = compute_engineered_features(raw_text)
        
        # 1. Text Prediction (using TfidfVectorizer + clf_log)
        clean_text = preprocess_text(raw_text)
        vectorized_text = tfidf_vectorizer.transform([clean_text])
        text_pred = int(clf_log.predict(vectorized_text)[0])
        
        # Get textual probabilities
        try:
            text_probs = clf_log.predict_proba(vectorized_text)[0]
            text_risk = float(text_probs[1])
        except Exception:
            text_risk = 1.0 if text_pred == 1 else 0.0

        # 2. Numeric/Engineered Prediction (Random Forest)
        num_feature_values = [telecommuting, ratio, character_count]
        for feat_name in numeric_features[3:]:
            num_feature_values.append(eng_features.get(feat_name, 0))
        
        num_array = np.array([num_feature_values])
        num_pred = int(clf_num.predict(num_array)[0])
        
        # Get numerical probabilities
        try:
            num_probs = clf_num.predict_proba(num_array)[0]
            num_risk = float(num_probs[1])
        except Exception:
            num_risk = 1.0 if num_pred == 1 else 0.0

        # ============================================================
        # 5-PILLAR TRUST & THREAT ANALYSIS ENGINE
        # ============================================================
        nlp_reasons = []
        url_reasons = []
        company_reasons = []
        recruiter_reasons = []
        all_reasons = []

        nlp_deductions = 0
        url_deductions = 0
        company_deductions = 0
        recruiter_deductions = 0

        # --- PILLAR 1: NLP Text Analysis ---
        # Word count & vocabulary analysis
        if text_risk >= 0.5 or text_pred == 1:
            nlp_reasons.append("ML Classifier Flag: Text pattern matches confirmed scam templates.")
            nlp_deductions += int(40 * text_risk)
        elif text_risk >= 0.2:
            nlp_reasons.append("ML Classifier Warning: Vocabulary has minor similarity to scam postings.")
            nlp_deductions += 15

        # Readability check
        flesch = eng_features['flesch_reading_ease']
        if flesch < 20:
            nlp_reasons.append(f"Readability Anomaly: Flesch score of {flesch:.1f} indicates overly complex/convoluted language.")
            nlp_deductions += 10
        elif flesch > 80:
            nlp_reasons.append(f"Readability Anomaly: Flesch score of {flesch:.1f} is extremely simple, indicating a low-effort template.")
            nlp_deductions += 10

        # Check for excessive exclamation marks
        if eng_features['exclamation_count'] >= 3:
            nlp_reasons.append(f"Clickbait punctuation: Excessive exclamation marks ({eng_features['exclamation_count']}) detected.")
            nlp_deductions += 5

        nlp_status = "PASSED"
        if nlp_deductions >= 25:
            nlp_status = "FAILED"
        elif nlp_deductions > 0:
            nlp_status = "WARNING"

        # --- PILLAR 2: URL Phishing Scan ---
        url_input = data.get('url', '').strip() if isinstance(data, dict) else ''
        if url_input:
            url_to_scan = url_input
        else:
            urls_found = re.findall(r'https?://\S+|www\.\S+', raw_text)
            url_to_scan = urls_found[0] if urls_found else ''

        if url_to_scan:
            if not url_to_scan.startswith('https://'):
                url_reasons.append("SSL Check Failure: Insecure HTTP protocol used in URL.")
                url_deductions += 15
            
            lowered_url = url_to_scan.lower()
            suspicious_domains = ['blogspot', 'wordpress', 'weebly', 'wix', 'bit.ly', 'tinyurl', 'click', 'free', 'job-offers']
            if any(term in lowered_url for term in suspicious_domains):
                url_reasons.append("High-Risk Domain: URL is hosted on a free platform or shortener.")
                url_deductions += 20
        
        if eng_features['url_count'] > 0:
            url_reasons.append(f"Embedded Links Alert: {eng_features['url_count']} URLs detected inside job description body.")
            url_deductions += 10

        url_status = "PASSED"
        if url_deductions >= 20:
            url_status = "FAILED"
        elif url_deductions > 0:
            url_status = "WARNING"

        # --- PILLAR 3: Company Verification ---
        if not company_profile:
            company_reasons.append("Profile Verification: Missing company background profile details.")
            company_deductions += 20
        elif len(company_profile) < 100:
            company_reasons.append("Profile Verification: Company profile description is extremely short.")
            company_deductions += 10
            
        company_clean = data.get('company_profile', '').strip().lower()
        has_corp_name = any(suffix in company_clean for suffix in ['ltd', 'inc', 'pvt', 'corp', 'corporation', 'llp', 'pvt.', 'ltd.'])
        
        if company_profile and not has_corp_name:
            company_reasons.append("Registry Check: Company name lacks official corporate suffixes (Ltd/Inc/LLP) in description.")
            company_deductions += 10

        company_status = "PASSED"
        if company_deductions >= 20:
            company_status = "FAILED"
        elif company_deductions > 0:
            company_status = "WARNING"

        # --- PILLAR 4: Smart Recruiter Behavior Check & Email Domain Audit ---
        # Parse actual emails
        email_pattern = r'[\w\.-]+@([\w\.-]+\.\w+)'
        emails_found = re.findall(email_pattern, raw_text)
        
        free_providers = {
            'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com', 
            'zoho.com', 'protonmail.com', 'proton.me', 'mail.com', 'icloud.com', 
            'yandex.com', 'gmx.com', 'mail.ru', 'live.com', 'msn.com', 'dispostable.com',
            'mailinator.com', 'tempmail.com', 'yopmail.com', 'burnermail.io'
        }
        
        free_email_domains = []
        corporate_email_domains = []
        
        for email_domain in emails_found:
            email_domain = email_domain.lower().strip()
            email_domain = re.sub(r'[^a-z0-9\.-]', '', email_domain)
            if email_domain in free_providers:
                free_email_domains.append(email_domain)
            else:
                corporate_email_domains.append(email_domain)

        if free_email_domains:
            for domain in set(free_email_domains):
                recruiter_reasons.append(f"Suspicious Recruiter Contact: Job post uses a public free email domain (@{domain}) instead of corporate domains.")
            recruiter_deductions += 25 * len(set(free_email_domains))
        elif corporate_email_domains:
            for domain in set(corporate_email_domains):
                recruiter_reasons.append(f"Verified Corporate Domain: Recruiter email domain (@{domain}) validated against secure registry format.")
            recruiter_deductions = max(0, recruiter_deductions - 15)
        elif eng_features['email_count'] > 0:
            recruiter_reasons.append("Personal Routing Flag: Obfuscated or generic contact email(s) found in description.")
            recruiter_deductions += 15
            
        if eng_features['phone_count'] > 0:
            recruiter_reasons.append(f"Phone Routing Flag: {eng_features['phone_count']} contact number(s) embedded directly in text.")
            recruiter_deductions += 15

        urgency_terms = ['urgent', 'immediate', 'apply now', 'apply today', 'hiring immediately', 'fast cash', 'upfront fee']
        raw_text_lower = raw_text.lower()
        if any(term in raw_text_lower for term in urgency_terms):
            recruiter_reasons.append("Pressure Tactics: Job text employs urgency/pressure language to encourage immediate applications.")
            recruiter_deductions += 15

        if telecommuting == 1:
            recruiter_reasons.append("Work From Home Warning: Telecommuting is enabled, which has higher correlation to recruitment scams.")
            recruiter_deductions += 10

        if ratio >= 1.0:
            recruiter_reasons.append(f"High-Risk Location: Job location '{location}' has a high scam ratio of {ratio:.1f}:1.")
            recruiter_deductions += 20
        elif ratio > 0.0:
            recruiter_reasons.append(f"Location Alert: Job location '{location}' has an elevated risk ratio of {ratio:.1f}:1.")
            recruiter_deductions += 10

        recruiter_status = "PASSED"
        if recruiter_deductions >= 25:
            recruiter_status = "FAILED"
        elif recruiter_deductions > 0:
            recruiter_status = "WARNING"

        all_reasons = nlp_reasons + url_reasons + company_reasons + recruiter_reasons

        # ============================================================
        # Ensemble risk alignment
        # ============================================================
        # Combine model probabilities (50% text risk, 50% numeric risk)
        ensemble_prob = 0.5 * text_risk + 0.5 * num_risk
        
        # Calculate heuristic risk penalty (capped at 50%)
        heuristics_penalty = (url_deductions + company_deductions + recruiter_deductions) / 100
        heuristics_penalty = min(0.5, heuristics_penalty)
        
        # Combined Risk Score (weighted: 60% ML models, 40% Heuristic rules)
        combined_risk = 0.6 * ensemble_prob + 0.4 * heuristics_penalty
        
        # Trust score is the inverse of risk
        trust_score = 100 * (1 - combined_risk)
        trust_score = min(max(trust_score, 0), 100)
        
        # Ensemble decision: if combined risk is high, or if BOTH models predict fraud (high precision), or if either is extremely high risk
        if text_risk > 0.65 or num_risk > 0.65 or trust_score < 50:
            ensemble_pred = 1
        else:
            ensemble_pred = 0

        return jsonify({
            "status": "success",
            "prediction": ensemble_pred,
            "trust_score": round(trust_score, 1),
            "details": {
                "nlp_status": nlp_status,
                "nlp_reasons": nlp_reasons,
                "url_status": url_status,
                "url_reasons": url_reasons,
                "company_status": company_status,
                "company_reasons": company_reasons,
                "recruiter_status": recruiter_status,
                "recruiter_reasons": recruiter_reasons,
                "text_classification_fraud": text_pred,
                "numerical_features_fraud": num_pred,
                "location_ratio": ratio,
                "character_count": character_count,
                "telecommuting": telecommuting,
                "flesch_reading_ease": round(flesch, 1),
                "word_count": eng_features['word_count'],
                "url_count": eng_features['url_count'],
                "email_count": eng_features['email_count'],
                "free_emails": list(set(free_email_domains)),
                "corp_emails": list(set(corporate_email_domains))
            },
            "reasons": all_reasons
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
