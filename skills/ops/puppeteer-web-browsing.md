---
name: puppeteer-web-browsing
description: |
  Browser automation with Puppeteer — navigate, extract page content,
  and handle popups via JavaScript evaluation.
  DO NOT use for: API calls, data that is accessible via curl, or static HTML fetching.
category: ops
domain: automation
intent:
  - web-scraping
  - javascript-evaluation
  - popup-handling
exclusions:
  - api-calls
  - curl-scraping
  - static-html
requires:
  - puppeteer
  - node
phase: operations
compatible_with: []
conflicts_with: []
handoff_to: []
scope: local-only
data_access:
  mcp_servers: []
  secrets: []
  trust_level: standard
governed_by: []
version: 1.0.0
compatibility:
  min_runtime: hermes-1.0
deprecated: false
deprecation_notes: ""
examples:
  - "Navigate to a login page, fill credentials, and extract dashboard data"
  - "Scrape a multi-page search results site with JavaScript-rendered content"
  - "Handle a popup/modal before extracting main page content"
---
# Puppeteer Web Browsing Skill

## Key Insight
The `puppeteer_navigate` tool only moves the browser to the page — it does **NOT** return the text on the page! You are driving blind.

## Procedure

1. **Navigate to the URL** — use `browser__puppeteer_navigate` to load the page
2. **Extract content** — follow up immediately with `browser__puppeteer_evaluate` using a JavaScript snippet:

```javascript
// Basic text extraction
document.body.innerText

// Structured data extraction
Array.from(document.querySelectorAll('article')).map(el => el.textContent.trim())

// Full page HTML if needed
document.documentElement.outerHTML
```

3. **Handle popups** — if a popup appears (cookie consent, newsletter signup, etc.), use `browser__puppeteer_evaluate` to dismiss it:

```javascript
// Click cookie accept button
document.querySelector('[aria-label*="cookie" i], [aria-label*="accept" i], button:contains("Accept")')?.click()

// Close modal
document.querySelector('.modal-close, [aria-label="Close"]')?.click()
```

## Important Notes
- Pages may not load fully before navigation returns — add explicit waits if needed
- JavaScript-heavy sites (React, Vue, SPA) require Puppeteer for full rendering
- Always check for popups/modals first before main content extraction
- Use `browser__puppeteer_console` to debug JavaScript errors on the page
