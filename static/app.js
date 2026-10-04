// ============================================================
// Genuire - Main Application Logic
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
    // DOM References
    const form = document.getElementById('prediction-form');
    const submitBtn = document.getElementById('btn-submit');
    const idleState = document.getElementById('results-idle');
    const loadingState = document.getElementById('results-loading');
    const activeState = document.getElementById('results-active');

    // Gauge variables
    const fillCircle = document.getElementById('gauge-fill-circle');
    const circumference = 2 * Math.PI * 50; // 314.159
    fillCircle.style.strokeDasharray = `${circumference} ${circumference}`;

    // ============================================================
    // Tab Switching Logic
    // ============================================================
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');
            
            // Toggle active buttons
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Toggle active contents
            tabContents.forEach(content => {
                if (content.id === targetTab) {
                    content.classList.add('active');
                } else {
                    content.classList.remove('active');
                }
            });
        });
    });

    // ============================================================
    // Linear Pipeline Animation Logic
    // ============================================================
    let pipelineInterval = null;
    
    function startPipelineLoading() {
        const steps = document.querySelectorAll('.pipeline-track .step');
        steps.forEach((step, idx) => {
            step.className = 'step';
            if (idx === 0) step.classList.add('active'); // Ingested active
        });

        let currentStep = 0;
        if (pipelineInterval) clearInterval(pipelineInterval);
        
        pipelineInterval = setInterval(() => {
            if (currentStep < 5) { // Stop at step 6 (Trust Score) during loading
                steps[currentStep].classList.remove('active');
                steps[currentStep].classList.add('completed');
                currentStep++;
                steps[currentStep].classList.add('active');
            } else {
                clearInterval(pipelineInterval);
            }
        }, 250);
    }

    function finalizePipelineStates(details, prediction) {
        if (pipelineInterval) clearInterval(pipelineInterval);
        const steps = document.querySelectorAll('.pipeline-track .step');
        
        // Step 1: Ingested always completed
        steps[0].className = 'step completed';
        
        // Step 2: NLP Analysis
        steps[1].className = `step ${getStepClass(details.nlp_status)}`;
        
        // Step 3: URL Scan
        steps[2].className = `step ${getStepClass(details.url_status)}`;
        
        // Step 4: Company Check
        steps[3].className = `step ${getStepClass(details.company_status)}`;
        
        // Step 5: Recruiter Check
        steps[4].className = `step ${getStepClass(details.recruiter_status)}`;
        
        // Step 6: Trust Score computed
        steps[5].className = 'step completed';
        
        // Step 7: Decision
        steps[6].className = prediction === 1 ? 'step failed' : 'step completed';
    }

    function getStepClass(status) {
        if (status === 'FAILED') return 'failed';
        if (status === 'WARNING') return 'warning';
        return 'completed';
    }

    // ============================================================
    // Trust Cards Content Rendering
    // ============================================================
    function updateTrustCard(cardId, badgeId, descId, status, reasons, defaultDesc) {
        const card = document.getElementById(cardId);
        const badge = document.getElementById(badgeId);
        const desc = document.getElementById(descId);

        badge.className = 'trust-badge';
        if (status === 'FAILED') {
            badge.classList.add('badge-failed');
            badge.innerHTML = '<i class="fa-solid fa-circle-xmark"></i> Failed';
            card.style.borderColor = 'var(--danger-color)';
        } else if (status === 'WARNING') {
            badge.classList.add('badge-warning-status');
            badge.innerHTML = '<i class="fa-solid fa-circle-exclamation"></i> Warning';
            card.style.borderColor = 'var(--warning-color)';
        } else {
            badge.classList.add('badge-passed');
            badge.innerHTML = '<i class="fa-solid fa-circle-check"></i> Passed';
            card.style.borderColor = '';
        }

        if (reasons && reasons.length > 0) {
            desc.innerHTML = reasons.map(r => `• ${r}`).join('<br>');
        } else {
            desc.textContent = defaultDesc;
        }
    }

    // ============================================================
    // Risk/Trust Gauge Animation (High Trust = Green, Low Trust = Red)
    // ============================================================
    function setTrustGauge(score) {
        document.getElementById('risk-percentage-val').innerText = `${score}%`;
        const offset = circumference - (score / 100) * circumference;
        fillCircle.style.strokeDashoffset = offset;

        // Set dynamic colors based on trust score (Inverted from Risk)
        const gaugeContainer = document.querySelector('.gauge-container');
        if (score >= 80) {
            fillCircle.style.stroke = 'var(--success-color)';
            gaugeContainer.style.setProperty('--glow-color', 'var(--success-bg)');
        } else if (score >= 50) {
            fillCircle.style.stroke = 'var(--warning-color)';
            gaugeContainer.style.setProperty('--glow-color', 'var(--warning-bg)');
        } else {
            fillCircle.style.stroke = 'var(--danger-color)';
            gaugeContainer.style.setProperty('--glow-color', 'var(--danger-bg)');
        }
    }

    // ============================================================
    // Common Dashboard Renderer
    // ============================================================
    window.renderDashboard = function(result, descriptionText, locationVal) {
        setTrustGauge(result.trust_score);
        finalizePipelineStates(result.details, result.prediction);

        const badge = document.getElementById('threat-badge');
        const threatTitle = document.getElementById('threat-title');
        const threatDesc = document.getElementById('threat-desc');
        const recBox = document.getElementById('rec-box');
        const recIcon = document.getElementById('rec-icon');
        const recTitle = document.getElementById('rec-title');
        const recDesc = document.getElementById('rec-desc');

        badge.className = 'badge';
        recBox.className = 'recommendation-box';

        if (result.prediction === 1) {
            badge.innerText = 'LOW TRUST';
            badge.classList.add('badge-danger');
            threatTitle.innerText = 'Scam Vulnerability Alert';
            threatDesc.innerText = 'Critical threat signals detected across NLP, company registration, and recruiter routing checks.';
            recBox.classList.add('rec-danger');
            recIcon.className = 'fa-solid fa-bell-slash rec-icon';
            recTitle.innerText = 'Application Blocked';
            recDesc.innerText = 'This job description exhibits confirmed phishing patterns. Do NOT submit personal credentials or payment details.';
        } else if (result.trust_score < 80) {
            badge.innerText = 'NEUTRAL RISK';
            badge.classList.add('badge-warning');
            threatTitle.innerText = 'Minor Warning Signs';
            threatDesc.innerText = 'Some parameters flagged minor warnings, but did not trigger low-trust blocking thresholds.';
            recBox.classList.add('rec-warning');
            recIcon.className = 'fa-solid fa-circle-exclamation rec-icon';
            recTitle.innerText = 'Cross-Verification Advised';
            recDesc.innerText = 'Conduct secondary verification on the official company portal before submitting an application.';
        } else {
            badge.innerText = 'HIGH TRUST';
            badge.classList.add('badge-success');
            threatTitle.innerText = 'Passed Verification';
            threatDesc.innerText = 'This posting satisfies all validation checks and matches legitimate hiring profile parameters.';
            recBox.classList.add('rec-success');
            recIcon.className = 'fa-solid fa-circle-check rec-icon';
            recTitle.innerText = 'Safe to Apply';
            recDesc.innerText = 'No threat signatures detected. Job description meets standard operational trust guidelines.';
        }

        updateTrustCard(
            'trust-card-nlp', 'trust-badge-nlp', 'trust-desc-nlp',
            result.details.nlp_status, result.details.nlp_reasons,
            "Language structures and vocabulary match secure patterns."
        );
        updateTrustCard(
            'trust-card-url', 'trust-badge-url', 'trust-desc-url',
            result.details.url_status, result.details.url_reasons,
            "SSL secure domain connection verified with no blacklist hits."
        );
        updateTrustCard(
            'trust-card-company', 'trust-badge-company', 'trust-desc-company',
            result.details.company_status, result.details.company_reasons,
            "Corporate details validated against registries and active profiles."
        );
        updateTrustCard(
            'trust-card-recruiter', 'trust-badge-recruiter', 'trust-desc-recruiter',
            result.details.recruiter_status, result.details.recruiter_reasons,
            "Recruitment routing paths and listing templates are within compliance."
        );

        document.getElementById('stat-text-model').innerText = result.details.text_classification_fraud ? 'SUSPICIOUS' : 'CLEAN';
        document.getElementById('stat-text-model').className = result.details.text_classification_fraud ? 'text-danger' : 'text-success';
        document.getElementById('stat-meta-model').innerText = result.details.numerical_features_fraud ? 'SUSPICIOUS' : 'CLEAN';
        document.getElementById('stat-meta-model').className = result.details.numerical_features_fraud ? 'text-danger' : 'text-success';
        document.getElementById('stat-location-ratio').innerText = `${result.details.location_ratio.toFixed(2)}:1`;
        document.getElementById('stat-location-ratio').className = result.details.location_ratio >= 1.0 ? 'text-danger' : (result.details.location_ratio > 0 ? 'text-warning' : 'text-success');
        document.getElementById('stat-char-count').innerText = result.details.character_count;

        const reasonsList = document.getElementById('reasons-list');
        reasonsList.innerHTML = '';
        if (result.reasons.length === 0) {
            reasonsList.innerHTML = '<li><i class="fa-solid fa-shield-check text-success"></i> All trust engine parameters successfully cleared validation checks.</li>';
        } else {
            result.reasons.forEach(reason => {
                const li = document.createElement('li');
                li.innerHTML = `<i class="fa-solid fa-triangle-exclamation text-warning"></i> ${reason}`;
                reasonsList.appendChild(li);
            });
        }

        const highlightHtml = highlightText(
            descriptionText, 
            result.details.free_emails, 
            result.details.corp_emails, 
            result.details.location_ratio, 
            locationVal, 
            result.details.telecommuting
        );
        document.getElementById('highlighted-doc-box').innerHTML = highlightHtml;
    }

    // ============================================================
    // Form Submission & Prediction
    // ============================================================
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        // Toggle loading and launch pipeline tracking
        idleState.classList.remove('active');
        activeState.classList.remove('active');
        loadingState.classList.add('active');
        startPipelineLoading();

        // Gather parameters
        const payload = {
            title: document.getElementById('title').value,
            location: document.getElementById('location').value,
            required_experience: document.getElementById('required_experience').value,
            required_education: document.getElementById('required_education').value,
            industry: document.getElementById('industry').value,
            function: document.getElementById('function').value,
            company_profile: document.getElementById('company_profile').value,
            description: document.getElementById('description').value,
            requirements: document.getElementById('requirements').value,
            benefits: document.getElementById('benefits').value,
            telecommuting: document.getElementById('telecommuting').checked ? 1 : 0,
            url: document.getElementById('url-input').value.trim()
        };

        try {
            const response = await fetch('/predict', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const result = await response.json();

            if (result.status === 'success') {
                renderDashboard(result, descriptionText, payload.location);
                // Switch states
                loadingState.classList.remove('active');
                activeState.classList.add('active');
            } else {
                alert('Prediction failed. Error: ' + result.message);
                loadingState.classList.remove('active');
                idleState.classList.add('active');
            }
        } catch (err) {
            console.error(err);
            alert('Connection to server lost. Make sure backend app is running.');
            loadingState.classList.remove('active');
            idleState.classList.add('active');
        }
    });

    // ============================================================
    // Dataset Templates
    // ============================================================
    const realTemplate = {
        title: "Software Engineer, Backend Systems",
        location: "US, CA, Mountain View",
        required_experience: "Mid-Senior level",
        required_education: "Bachelor's Degree",
        industry: "Information Technology and Services",
        function: "Engineering",
        company_profile: "Google LLC is an American multinational technology company focusing on artificial intelligence, online advertising, search engine technology, cloud computing, computer software, quantum computing, e-commerce, and consumer electronics. Founded in 1998 by Larry Page and Sergey Brin, Google is one of the most valuable companies in the world, consistently ranked among the top employers globally. Our mission is to organize the world's information and make it universally accessible and useful.",
        description: "As a Software Engineer at Google, you will work on a specific project critical to Google's needs with opportunities to switch teams and projects as you and our fast-paced business grow and evolve. You will design, develop, test, deploy, maintain, and improve software across Google's stack. You will manage project priorities, deadlines, and deliverables and work in an Agile environment. You will collaborate with cross-functional teams spanning infrastructure, product, and data engineering.",
        requirements: "Bachelor's degree in Computer Science or related technical field, or equivalent practical experience. 3+ years of software development experience in one or more general-purpose programming languages (Java, Python, Go, C++). Experience with distributed systems, large-scale data processing, or cloud-based architectures. Strong problem-solving skills and a passion for building high-quality software. Excellent communication and collaboration abilities.",
        benefits: "Competitive salary and equity compensation. Comprehensive health, dental, and vision insurance. 401(k) with company match. Generous parental leave. On-site wellness and fitness centers. Free meals and snacks. Professional development and learning opportunities.",
        telecommuting: false,
        url: "https://careers.google.com/jobs/results/software-engineer"
    };

    const fakeTemplate = {
        title: "Home-Based Data Entry Clerk - Earn $5000/Week!",
        location: "US, Anywhere, Remote",
        required_experience: "Not Applicable",
        required_education: "Unspecified",
        industry: "Internet",
        function: "Administrative",
        company_profile: "We are a global leader in innovative solutions. Our dynamic team is expanding rapidly and we are looking for motivated individuals to join us from the comfort of their own homes. No prior experience needed — we provide full training!",
        description: "URGENT HIRING! Work from home and earn up to $5000 per week doing simple data entry tasks. No experience required. Start immediately! All you need is a computer and internet connection. This is a once-in-a-lifetime opportunity for anyone looking to make serious money online. Flexible hours, be your own boss. Thousands of people have already joined our program and are making a full-time income from home. Apply NOW before positions fill up! Send your resume and a $50 processing fee to our HR department to get started.",
        requirements: "Must be 18 years or older. Must have a computer and internet access. No experience or degree needed. Must be willing to learn. Send application fee of $50 via wire transfer to confirm your spot.",
        benefits: "Unlimited earning potential. Work from anywhere in the world. Set your own schedule. Full training provided. Weekly payments via direct deposit or wire transfer.",
        telecommuting: true,
        url: "http://easy-home-jobs-apply-now.blogspot.com/data-entry"
    };

    document.getElementById('btn-load-real').addEventListener('click', () => {
        loadTemplate(realTemplate);
    });

    document.getElementById('btn-load-fake').addEventListener('click', () => {
        loadTemplate(fakeTemplate);
    });

    function loadTemplate(data) {
        document.getElementById('title').value = data.title;
        document.getElementById('location').value = data.location;
        document.getElementById('required_experience').value = data.required_experience;
        document.getElementById('required_education').value = data.required_education;
        document.getElementById('industry').value = data.industry;
        document.getElementById('function').value = data.function;
        document.getElementById('company_profile').value = data.company_profile;
        document.getElementById('description').value = data.description;
        document.getElementById('requirements').value = data.requirements;
        document.getElementById('benefits').value = data.benefits;
        document.getElementById('telecommuting').checked = data.telecommuting;
        document.getElementById('url-input').value = data.url;

        // Switch to the form input tab so the user sees the template load
        const manualTabBtn = document.querySelector('[data-tab="manual-form-tab"]');
        if (manualTabBtn) {
            manualTabBtn.click();
        }

        // Flash effect to show it loaded
        const card = document.querySelector('.form-card');
        card.style.borderColor = 'var(--primary-accent)';
        setTimeout(() => {
            card.style.borderColor = '';
        }, 600);
    }

    // ============================================================
    // URL Scanner Logic
    // ============================================================
    const urlInput = document.getElementById('url-input');
    const btnScan = document.getElementById('btn-scan-url');
    const urlStatus = document.getElementById('url-scanner-status');
    const urlStatusText = document.getElementById('url-status-text');

    btnScan.addEventListener('click', async () => {
        const url = urlInput.value.trim();
        if (!url) {
            urlInput.focus();
            urlInput.style.borderColor = 'var(--danger-color)';
            setTimeout(() => { urlInput.style.borderColor = ''; }, 1500);
            return;
        }
        // Hide previous telemetry details if open
        const scrapeDetails = document.getElementById('url-scrape-details');
        if (scrapeDetails) scrapeDetails.style.display = 'none';

        // Show loading state
        btnScan.disabled = true;
        btnScan.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Scanning...';
        urlStatus.style.display = 'flex';
        urlStatus.className = 'url-scanner-status status-loading';

        // Dynamic Loading Indicators
        const loadingTexts = ['Connecting...', 'Parsing HTML...', 'Extracting Profile...'];
        let currentTextIdx = 0;
        urlStatusText.textContent = loadingTexts[currentTextIdx];
        const statusTextInterval = setInterval(() => {
            currentTextIdx = (currentTextIdx + 1) % loadingTexts.length;
            urlStatusText.textContent = loadingTexts[currentTextIdx];
        }, 850);

        try {
            const response = await fetch('/scrape', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: url })
            });
            const result = await response.json();

            if (result.status === 'success') {
                const d = result.data;

                // Auto-fill the form fields
                document.getElementById('title').value = d.title || '';
                document.getElementById('location').value = d.location || '';
                document.getElementById('company_profile').value = d.company_profile || '';
                document.getElementById('description').value = d.description || '';
                document.getElementById('requirements').value = d.requirements || '';
                document.getElementById('benefits').value = d.benefits || '';
                document.getElementById('industry').value = d.industry || '';
                document.getElementById('function').value = d.function || '';
                document.getElementById('telecommuting').checked = !!d.telecommuting;

                // Try to match experience/education selects
                if (d.required_experience) {
                    const expSelect = document.getElementById('required_experience');
                    for (let opt of expSelect.options) {
                        if (opt.value && d.required_experience.toLowerCase().includes(opt.value.toLowerCase())) {
                            expSelect.value = opt.value;
                            break;
                        }
                    }
                }
                if (d.required_education) {
                    const eduSelect = document.getElementById('required_education');
                    for (let opt of eduSelect.options) {
                        if (opt.value && d.required_education.toLowerCase().includes(opt.value.toLowerCase())) {
                            eduSelect.value = opt.value;
                            break;
                        }
                    }
                }

                // Populate Scrape Telemetry UI
                document.getElementById('scrape-title-val').textContent = d.title || 'Not Detected';
                document.getElementById('scrape-company-val').textContent = d.company_profile || 'Not Detected';
                document.getElementById('scrape-location-val').textContent = d.location || 'Not Detected';

                // SSL Status check based on scheme
                const isHttps = url.toLowerCase().startsWith('https://');
                if (isHttps) {
                    document.getElementById('scrape-security-val').innerHTML = '<span class="text-success"><i class="fa-solid fa-lock"></i> HTTPS Secure</span>';
                } else {
                    document.getElementById('scrape-security-val').innerHTML = '<span class="text-warning"><i class="fa-solid fa-unlock"></i> Unsafe HTTP / No SSL</span>';
                }

                // Work Model remote check
                document.getElementById('scrape-remote-val').textContent = d.telecommuting ? 'Remote (WFH)' : 'On-site / Hybrid';

                if (scrapeDetails) {
                    scrapeDetails.style.display = 'block';
                }

                // Success state
                urlStatus.className = 'url-scanner-status status-success';
                urlStatusText.textContent = `Page scraped successfully! Fields auto-filled from: ${d.source_url}`;

                // Switch to manual input tab to show the filled form fields
                const manualTabBtn = document.querySelector('[data-tab="manual-form-tab"]');
                if (manualTabBtn) {
                    manualTabBtn.click();
                }

                // Flash the form
                const card = document.querySelector('.form-card');
                card.style.borderColor = 'var(--success-color)';
                setTimeout(() => { card.style.borderColor = ''; }, 1200);

                // Auto-trigger analysis after short delay
                setTimeout(() => {
                    form.dispatchEvent(new Event('submit'));
                }, 800);
            } else {
                urlStatus.className = 'url-scanner-status status-error';
                urlStatusText.textContent = result.message || 'Failed to scrape the URL.';
            }
        } catch (err) {
            console.error(err);
            urlStatus.className = 'url-scanner-status status-error';
            urlStatusText.textContent = 'Connection error. Make sure the backend is running.';
        } finally {
            clearInterval(statusTextInterval);
            btnScan.disabled = false;
            btnScan.innerHTML = '<i class="fa-solid fa-satellite-dish"></i> Scan Link';
        }
    });

    // Allow Enter key in URL input to trigger scan
    urlInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            btnScan.click();
        }
    });
});

function highlightText(text, freeEmails, corpEmails, locationRatio, locationName, telecommuting) {
    if (!text) return "<em>No description text provided.</em>";

    // Escape HTML to prevent XSS
    let escapedText = text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");

    // Define Highlight Patterns
    // Category 1: High Risk (Payment, crypto, wire transfer, buy equipment, Telegram, WhatsApp, Sign-up fee, etc.)
    const highRiskKeywords = [
        /\b(telegram|whatsapp|signal|kik|google hangouts)\b/gi,
        /\b(wire transfer|bank account|bank details|credit card|upfront fee|processing fee|sign-up fee|security deposit|refundable fee)\b/gi,
        /\b(buy equipment|reimburse|cashier\'s check|money transfer|western union|moneygram)\b/gi,
        /\b(package handler|re-shipper|envelope stuffer|work from home agent)\b/gi,
        /\b(bitcoin|cryptocurrency|crypto|cash app|venmo|paypal)\b/gi
    ];

    // Category 2: Warning (Urgency, free emails, pressure words, blogspot/free domains)
    const warningKeywords = [
        /\b(urgent|urgently|immediate|immediately|act now|apply today|fast cash|quick cash)\b/gi,
        /\b(no experience required|no experience needed|make money fast|easy money)\b/gi
    ];

    // Apply Free Email highlights if any are present
    if (freeEmails && freeEmails.length > 0) {
        freeEmails.forEach(email => {
            const escapedDomain = email.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
            const regex = new RegExp(`[\\w\\.-]+@${escapedDomain}`, 'gi');
            escapedText = escapedText.replace(regex, (match) => {
                return `<span class="hl-warning" title="Warning: Suspicious free contact domain">${match}</span>`;
            });
        });
    }

    // Apply Corporate Email highlights
    if (corpEmails && corpEmails.length > 0) {
        corpEmails.forEach(email => {
            const escapedDomain = email.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
            const regex = new RegExp(`[\\w\\.-]+@${escapedDomain}`, 'gi');
            escapedText = escapedText.replace(regex, (match) => {
                return `<span class="hl-info" title="Verified Corporate domain">${match}</span>`;
            });
        });
    }

    // Highlight High Risk phrases
    highRiskKeywords.forEach(regex => {
        escapedText = escapedText.replace(regex, (match) => {
            return `<span class="hl-danger" title="High Risk: Fraud-associated term">${match}</span>`;
        });
    });

    // Highlight Warning phrases
    warningKeywords.forEach(regex => {
        escapedText = escapedText.replace(regex, (match) => {
            return `<span class="hl-warning" title="Warning: Urgency or low-effort signal">${match}</span>`;
        });
    });

    // Category 3: Info Highlights (Telecommuting, location if ratio is high)
    if (telecommuting === 1) {
        const telecommuteRegex = /\b(remote|work from home|telecommute|work-from-home|wfh)\b/gi;
        escapedText = escapedText.replace(telecommuteRegex, (match) => {
            return `<span class="hl-info" title="Info: Telecommuting is allowed (elevated correlation to scams)">${match}</span>`;
        });
    }

    if (locationRatio >= 1.0 && locationName) {
        const locClean = locationName.split(',').map(s => s.trim().replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&')).filter(s => s.length > 2);
        locClean.forEach(locPart => {
            const locRegex = new RegExp(`\\b${locPart}\\b`, 'gi');
            escapedText = escapedText.replace(locRegex, (match) => {
                return `<span class="hl-info" title="Info: High-Scam Location (${locationRatio.toFixed(1)}:1 ratio)">${match}</span>`;
            });
        });
    }

    return escapedText;
}

// ============================================================
// Gemma Image Scanner Logic
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('image-upload');
    const fileNameDisplay = document.getElementById('file-name-display');
    const imageForm = document.getElementById('image-scan-form');
    const imageStatus = document.getElementById('image-scanner-status');
    const imageStatusText = document.getElementById('image-status-text');
    const imageLoadingIcon = document.getElementById('image-loading-icon');
    const imageResultBox = document.getElementById('image-analysis-result');
    const btnScanImage = document.getElementById('btn-scan-image');

    if (!fileInput || !imageForm) return;

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            fileNameDisplay.textContent = "Selected: " + e.target.files[0].name;
            fileNameDisplay.style.color = "#10a37f";
            fileNameDisplay.style.fontWeight = "bold";
        } else {
            fileNameDisplay.textContent = "Click to browse or drag and drop an image";
            fileNameDisplay.style.color = "";
            fileNameDisplay.style.fontWeight = "";
        }
    });

    imageForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        if (fileInput.files.length === 0) {
            alert('Please select an image first.');
            return;
        }

        // Show loading state on both the button and the main right-side dashboard
        btnScanImage.disabled = true;
        btnScanImage.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Analyzing...';
        imageStatus.style.display = 'flex';
        imageStatus.style.borderLeftColor = '#10a37f';
        imageLoadingIcon.style.display = 'inline-block';
        imageLoadingIcon.className = 'fa-solid fa-spinner fa-spin';
        imageStatusText.textContent = 'Gemma is analyzing the image. This may take a few seconds...';
        imageResultBox.textContent = '';
        
        const idleState = document.getElementById('results-idle');
        const activeState = document.getElementById('results-active');
        const loadingState = document.getElementById('results-loading');
        
        idleState.classList.remove('active');
        activeState.classList.remove('active');
        loadingState.classList.add('active');
        
        // Start pipeline animation
        const steps = document.querySelectorAll('.pipeline-track .step');
        steps.forEach((step, idx) => {
            step.className = 'step';
            if (idx === 0) step.classList.add('active'); // Ingested active
        });

        let currentStep = 0;
        let pipelineInterval = setInterval(() => {
            if (currentStep < 5) { // Stop at step 6 (Trust Score) during loading
                steps[currentStep].classList.remove('active');
                steps[currentStep].classList.add('completed');
                currentStep++;
                steps[currentStep].classList.add('active');
            } else {
                clearInterval(pipelineInterval);
            }
        }, 250);

        const formData = new FormData();
        formData.append('image', fileInput.files[0]);

        try {
            const response = await fetch('/gemma-scan-image', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();

            imageLoadingIcon.style.display = 'none';

            if (result.status === 'success') {
                imageStatus.style.borderLeftColor = 'var(--success-color)';
                imageStatusText.textContent = 'Scan Complete! See dashboard for details.';
                imageStatusText.style.color = 'var(--success-color)';
                imageResultBox.textContent = "Gemma successfully analyzed the image and updated the Risk Analysis Dashboard.";
                
                // Clear animation
                clearInterval(pipelineInterval);
                
                // Render the right dashboard
                renderDashboard(result, "Image scan results provided via Gemma Multimodal Analysis.", "");
                
                loadingState.classList.remove('active');
                activeState.classList.add('active');
            } else {
                imageStatus.style.borderLeftColor = 'var(--danger-color)';
                imageStatusText.textContent = 'Error:';
                imageStatusText.style.color = 'var(--danger-color)';
                imageResultBox.textContent = result.message || 'Failed to scan image.';
                
                clearInterval(pipelineInterval);
                loadingState.classList.remove('active');
                idleState.classList.add('active');
            }
        } catch (err) {
            console.error(err);
            imageLoadingIcon.style.display = 'none';
            imageStatus.style.borderLeftColor = 'var(--danger-color)';
            imageStatusText.textContent = 'Connection Error:';
            imageStatusText.style.color = 'var(--danger-color)';
            imageResultBox.textContent = 'Could not reach the server. Make sure the backend is running.';
            
            clearInterval(pipelineInterval);
            loadingState.classList.remove('active');
            idleState.classList.add('active');
        } finally {
            btnScanImage.disabled = false;
            btnScanImage.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Scan Image with Gemma';
        }
    });
});
