import os
import re
import joblib
import pandas as pd
import numpy as np
import textstat
import nltk
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.linear_model import SGDClassifier
from sklearn import metrics
from imblearn.over_sampling import SMOTE

# Set paths
base_path = os.path.dirname(os.path.abspath(__file__))

# Download NLTK data to local directory during build
nltk_data_dir = os.path.join(base_path, "nltk_data")
os.makedirs(nltk_data_dir, exist_ok=True)
print("Downloading NLTK resources to local directory...")
nltk.download('stopwords', download_dir=nltk_data_dir, quiet=True)
nltk.download('wordnet', download_dir=nltk_data_dir, quiet=True)
nltk.download('omw-1.4', download_dir=nltk_data_dir, quiet=True)
clean_csv_path = os.path.join(base_path, "data", "fake_job_postings_cleaned.csv")
models_dir = os.path.join(base_path, "models")

# Ensure models directory exists
os.makedirs(models_dir, exist_ok=True)

print("Loading cleaned dataset...")
df = pd.read_csv(clean_csv_path)

# Downsample on Render to stay within 512MB RAM and avoid build timeouts
if os.environ.get('RENDER'):
    print("  Detected Render environment. Downsampling dataset for memory and speed efficiency...")
    df = df.sample(n=min(3000, len(df)), random_state=53).reset_index(drop=True)

# Fill NaNs in text with empty string just in case
df['text'] = df['text'].fillna('')


# ============================================================
# 2026-Era Feature Engineering
# ============================================================
print("\n--- Computing 2026-era engineered features ---")

def compute_features(text_series):
    """Compute advanced NLP features from a text Series."""
    features = pd.DataFrame(index=text_series.index)

    # 1. Word count
    features['word_count'] = text_series.apply(lambda x: len(x.split()))

    # 2. Average word length
    def avg_word_len(text):
        words = text.split()
        if len(words) == 0:
            return 0
        return np.mean([len(w) for w in words])
    features['avg_word_length'] = text_series.apply(avg_word_len)

    # 3. Uppercase ratio — scams often over-use capitals
    def uppercase_ratio(text):
        if len(text) == 0:
            return 0
        return sum(1 for c in text if c.isupper()) / len(text)
    features['uppercase_ratio'] = text_series.apply(uppercase_ratio)

    # 4. URL count — suspicious job posts often include obfuscated URLs
    def count_urls(text):
        url_pattern = r'#URL_[a-f0-9]+#|https?://\S+|www\.\S+'
        return len(re.findall(url_pattern, text))
    features['url_count'] = text_series.apply(count_urls)

    # 5. Email count — presence of free email providers is a red flag
    def count_emails(text):
        email_pattern = r'#EMAIL_[a-f0-9]+#|[\w\.-]+@[\w\.-]+'
        return len(re.findall(email_pattern, text))
    features['email_count'] = text_series.apply(count_emails)

    # 6. Phone count — legitimate companies rarely embed phone numbers in descriptions
    def count_phones(text):
        phone_pattern = r'#PHONE_[a-f0-9]+#|\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
        return len(re.findall(phone_pattern, text))
    features['phone_count'] = text_series.apply(count_phones)

    # 7. Flesch Reading Ease — lower scores = more complex text
    #    Scam posts tend to have unusual readability patterns
    def flesch_score(text):
        try:
            score = textstat.flesch_reading_ease(text)
            return max(min(score, 100), -50)  # Clamp to reasonable range
        except Exception:
            return 50.0  # Default neutral
    features['flesch_reading_ease'] = text_series.apply(flesch_score)

    # 8. Sentence count
    def sentence_count(text):
        return max(textstat.sentence_count(text), 1)
    features['sentence_count'] = text_series.apply(sentence_count)

    # 9. Punctuation density — scam posts often have unusual punctuation patterns
    def punct_density(text):
        if len(text) == 0:
            return 0
        import string
        return sum(1 for c in text if c in string.punctuation) / len(text)
    features['punctuation_density'] = text_series.apply(punct_density)

    # 10. Exclamation/question mark count — clickbait scam signals
    features['exclamation_count'] = text_series.apply(lambda x: x.count('!'))
    features['question_count'] = text_series.apply(lambda x: x.count('?'))

    return features

# Compute features for the entire dataset
print("  Computing word statistics...")
engineered = compute_features(df['text'])

print(f"  Generated {len(engineered.columns)} new features: {list(engineered.columns)}")

# Show feature distributions for real vs fake
print("\n--- Feature means: Real vs Fake ---")
for col in engineered.columns:
    real_mean = engineered.loc[df.fraudulent == 0, col].mean()
    fake_mean = engineered.loc[df.fraudulent == 1, col].mean()
    diff_pct = ((fake_mean - real_mean) / real_mean * 100) if real_mean != 0 else 0
    marker = " <<<" if abs(diff_pct) > 20 else ""
    print(f"  {col:25s}  Real: {real_mean:8.3f}  Fake: {fake_mean:8.3f}  ({diff_pct:+.1f}%){marker}")


# ============================================================
# Prepare training data
# ============================================================
# Combine original numeric features with new engineered features
NUMERIC_FEATURES = ['telecommuting', 'ratio', 'character_count'] + list(engineered.columns)

X_num_full = pd.concat([df[['telecommuting', 'ratio', 'character_count']], engineered], axis=1)
y = df['fraudulent']

# We also keep the text column for the text classifier
X_text = df['text']

# Replicate split from notebook
indices = np.arange(len(df))
idx_train, idx_test = train_test_split(indices, test_size=0.33, random_state=53)

X_train_num = X_num_full.iloc[idx_train]
X_test_num = X_num_full.iloc[idx_test]
y_train = y.iloc[idx_train]
y_test = y.iloc[idx_test]

X_train_text = X_text.iloc[idx_train]
X_test_text = X_text.iloc[idx_test]

# Train TfidfVectorizer
print("\nVectorizing text data (TF-IDF)...")
tfidf_vectorizer = TfidfVectorizer(stop_words='english', max_features=10000)
count_train = tfidf_vectorizer.fit_transform(X_train_text.values)
count_test = tfidf_vectorizer.transform(X_test_text.values)

# ============================================================
# Apply SMOTE to handle class imbalance
# ============================================================
print("\n--- Applying SMOTE to balance training data ---")
print(f"Before SMOTE - Train set: Real={int((y_train == 0).sum())}, Fake={int((y_train == 1).sum())}")

# SMOTE on text features (sparse matrix)
smote_text = SMOTE(random_state=53)
count_train_balanced, y_train_text_balanced = smote_text.fit_resample(count_train, y_train)
print(f"After SMOTE (text) - Real={int((y_train_text_balanced == 0).sum())}, Fake={int((y_train_text_balanced == 1).sum())}")

# SMOTE on numeric features (now includes engineered features)
smote_num = SMOTE(random_state=53)
X_train_num_balanced, y_train_num_balanced = smote_num.fit_resample(X_train_num, y_train)
print(f"After SMOTE (numeric+engineered) - Real={int((y_train_num_balanced == 0).sum())}, Fake={int((y_train_num_balanced == 1).sum())}")

# ============================================================
# Train with class_weight='balanced' + SMOTE data
# ============================================================

# --- Text classifier ---
print("\n--- Training text SGD classifier (balanced + SMOTE) ---")
clf_log = SGDClassifier(
    loss='log_loss',
    class_weight='balanced',
    random_state=53,
    max_iter=1000
).fit(count_train_balanced, y_train_text_balanced)

pred_log = clf_log.predict(count_test)
text_accuracy = metrics.accuracy_score(y_test, pred_log)
text_f1 = metrics.f1_score(y_test, pred_log)
text_recall = metrics.recall_score(y_test, pred_log)
text_precision = metrics.precision_score(y_test, pred_log)
print(f"Text SGD - Accuracy: {text_accuracy:.4f}  F1: {text_f1:.4f}  Precision: {text_precision:.4f}  Recall: {text_recall:.4f}")

# --- Numeric + engineered features classifier (Random Forest) ---
print("\n--- Training numeric+engineered Random Forest classifier (balanced + SMOTE) ---")
clf_num = RandomForestClassifier(
    n_estimators=100,
    class_weight='balanced',
    random_state=53,
    n_jobs=-1
).fit(X_train_num_balanced, y_train_num_balanced)

pred_num = clf_num.predict(X_test_num)
num_accuracy = metrics.accuracy_score(y_test, pred_num)
num_f1 = metrics.f1_score(y_test, pred_num)
num_recall = metrics.recall_score(y_test, pred_num)
num_precision = metrics.precision_score(y_test, pred_num)
print(f"Numeric+Eng SGD - Accuracy: {num_accuracy:.4f}  F1: {num_f1:.4f}  Precision: {num_precision:.4f}  Recall: {num_recall:.4f}")

# ============================================================
# Evaluate Combined Ensemble Model
# ============================================================
prediction_array = []
for i, j in zip(pred_num, pred_log):
    if i == 0 and j == 0:
        prediction_array.append(0)
    else:
        prediction_array.append(1)

ensemble_accuracy = metrics.accuracy_score(y_test, prediction_array)
ensemble_f1 = metrics.f1_score(y_test, prediction_array)
ensemble_recall = metrics.recall_score(y_test, prediction_array)
ensemble_precision = metrics.precision_score(y_test, prediction_array)

print(f"\n{'='*60}")
print(f"  ENSEMBLE RESULTS (SMOTE + Balanced + Engineered Features)")
print(f"{'='*60}")
print(f"  Accuracy:  {ensemble_accuracy:.4f}")
print(f"  F1 Score:  {ensemble_f1:.4f}")
print(f"  Precision: {ensemble_precision:.4f}")
print(f"  Recall:    {ensemble_recall:.4f}  (ability to catch fake jobs)")
print(f"{'='*60}")

# Confusion matrix
cm = metrics.confusion_matrix(y_test, prediction_array)
print(f"\nConfusion Matrix:")
print(f"  True Negatives  (Real correctly identified):  {cm[0][0]}")
print(f"  False Positives (Real flagged as Fake):       {cm[0][1]}")
print(f"  False Negatives (Fake missed as Real):        {cm[1][0]}")
print(f"  True Positives  (Fake correctly caught):      {cm[1][1]}")

# Save models, vectorizer, and feature list
print("\nSaving models and vectorizer to models directory...")
joblib.dump(tfidf_vectorizer, os.path.join(models_dir, "tfidf_vectorizer.pkl"))
joblib.dump(clf_log, os.path.join(models_dir, "clf_log.pkl"))
joblib.dump(clf_num, os.path.join(models_dir, "clf_num.pkl"))
joblib.dump(NUMERIC_FEATURES, os.path.join(models_dir, "numeric_features.pkl"))

print("\nModel training and saving completed successfully!")
print(f"Numeric feature columns ({len(NUMERIC_FEATURES)}): {NUMERIC_FEATURES}")
