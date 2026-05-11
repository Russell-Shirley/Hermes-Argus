---
name: puppeteer-web-browsing
description: Browser automation with Puppeteer — navigate, extract page content, and handle popups via JavaScript evaluation.
trigger: When using Puppeteer to browse the web or extract content from web pages.
category: ops
metadata:
  hermes:
    tags: [puppeteer, browser, automation, scraping]
    related_skills: []
---

# Puppeteer Web Browsing Skill

## Key Insight
The `puppeteer_navigate` tool only moves the browser to the page — it does **NOT** return the text on the page! You are driving blind.

## Procedure

1. **Navigate to the URL** — use `browser__puppeteer_navigate` to load the page
2. **Extract content** — follow up immediately with `browser__puppeteer_evaluate` using a JavaScript snippet:
   - Full page text: `return document.body.innerText;`
   - Specific element: `return document.querySelector('.content').innerText;`
   - Links: `return Array.from(document.querySelectorAll('a')).map(a => ({text: a.innerText, href: a.href}));`

## Handling Interstitials
If you encounter cookie banners, popups, or modals:
1. Use `puppeteer_evaluate` to dismiss them
2. Common dismiss patterns:
   ```javascript
   document.querySelector('.accept-btn').click();
   // or
   document.querySelector('[aria-label="Close"]').click();
   // or
   document.querySelector('.cookie-banner button').click();
   ```
3. Then re-evaluate to extract content

## Pitfalls
- Navigation alone gives you nothing — always pair with evaluate
- Page may take time to render — add a brief delay if elements aren't found
- Cookie banners block content — handle them first
- Some sites detect automated browsing and may serve CAPTCHAs
