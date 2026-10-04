# Security Policy

We take the security of Genuire seriously. If you believe you've found a security vulnerability, please read this document to learn how to report it responsibly.

---

## Supported Versions

Currently, we active maintain and provide security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

---

## Reporting a Vulnerability

Please **do not** report security vulnerabilities via public GitHub issues. Instead, report them privately using the following steps:

1. **Email the details:** Send an email to **[dasouvik122005@gmail.com](mailto:dasouvik122005@gmail.com)** with the subject line **"Security Vulnerability Report"**.
2. **Provide detailed information:**
   * A description of the vulnerability and its potential impact.
   * Steps to reproduce the issue (PoC scripts, screenshots, or screen recordings are highly appreciated).
   * Any potential fix or mitigation strategies you suggest.
3. **Wait for confirmation:** We will acknowledge receipt of your report within **72 hours** and keep you updated on our progress toward resolving it.

---

## Disclosure Process

* Once a vulnerability is reported, we will investigate and verify it.
* We aim to resolve security issues within **14 days** of confirmation.
* Once a fix is ready, we will merge the patch, release a new version, and post a security advisory.
* We ask that you coordinate disclosure with us and refrain from releasing details publicly until a fix is available to protect users.

---

## Security Practices in Genuire

Genuire implements several key principles to keep scanning safe:
* **Zero Data Retention:** Job posting descriptions, titles, companies, and URL links are processed in memory during the HTTP request lifecycle and immediately discarded.
* **Input Sanitization:** User forms and fetched URL structures are sanitized before parsing to prevent Cross-Site Scripting (XSS) and injection threats.
* **Controlled Scrapes:** Scraping client features are rate-limited, enforce connection timeouts, and utilize standard user-agents to avoid SSRF (Server-Side Request Forgery) exploits.
