# Contributing to Genuire

Thank you for your interest in contributing to Genuire! We welcome contributions from developers, researchers, designers, and anyone interested in making the recruitment landscape safer for job seekers.

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

---

## How Can I Contribute?

### 1. Reporting Bugs
* Check the existing issues in our GitHub repository to ensure the bug hasn't already been reported.
* Open a new issue with a clear title, description, steps to reproduce, and any relevant error logs or screenshots.

### 2. Suggesting Enhancements
* Check the existing issues to ensure the feature hasn't been proposed yet.
* Open a new issue detailing the feature, why it is useful, and how it should behave.

### 3. Submitting Code Changes
* **Fork** the repository and create your branch from `main`.
* **Set up** the development environment (see instructions below).
* **Train** the models if you modify the classification pipeline or features.
* **Verify** your changes by running the verification scripts and checking the Web UI locally.
* **Commit** your changes with clear, descriptive commit messages.
* **Submit a Pull Request (PR)** targeting the `main` branch. Provide a comprehensive summary of what your changes accomplish.

---

## Local Development Setup

### Prerequisites
* Python 3.10+ installed on your system.
* Git installed.

### Installation & Run Steps
1. **Clone your fork:**
   ```bash
   git clone https://github.com/YOUR-USERNAME/Genuire.git
   cd Genuire
   ```

2. **Set up a Virtual Environment:**
   ```bash
   python -m venv .venv
   # On Windows
   .venv\Scripts\activate
   # On macOS/Linux
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Train the ML Models locally:**
   Before running the app, train the vectorizers and Random Forest classifiers on the balanced EMSCAD dataset:
   ```bash
   python train_model.py
   ```
   This will train the models and generate serialization binaries in the `models/` directory:
   * `tfidf_vectorizer.pkl`
   * `clf_log.pkl` (text NLP model)
   * `clf_num.pkl` (tabular features model)
   * `numeric_features.pkl`

5. **Start the Development Server:**
   Launch the Flask application:
   ```bash
   python app.py
   ```
   Open **`http://127.0.0.1:5000`** in your browser.

---

## Coding Standards

### 1. Backend Code
* Maintain standard Python guidelines (PEP 8 style).
* Document functions and class structures.
* Keep model feature extractors in sync between `train_model.py` and `app.py`.

### 2. Frontend Layout & Design
* Use **Vanilla CSS** for all styling. Avoid adding framework dependencies (like TailwindCSS) unless explicitly approved.
* Make sure components support **both Light Mode and Dark Mode**.
* Test responsiveness across mobile, tablet, and desktop views.
* Include smooth animations (micro-interactions on hover/active states) to make the UX feel premium.

---

## Testing Your Changes
* Run local dry-runs using the manual and URL scanning features.
* If you write new heuristic checks, verify them with both mock real and mock fake jobs (you can use `btn-load-real` and `btn-load-fake` helper templates inside `static/app.js` for testing).

---

## Contact
If you have any questions, feel free to open a GitHub issue or contact us at **[dasouvik122005@gmail.com](mailto:dasouvik122005@gmail.com)**.
