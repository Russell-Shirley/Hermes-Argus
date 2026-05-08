# Puppeteer Web Browsing Skill

When using Puppeteer to browse the web, the `puppeteer_navigate` tool only moves the browser to the page—it does NOT return the text on the page! You are driving blind.

To actually read data (like stock prices, news, or articles):
1. Use `browser__puppeteer_navigate` to load the URL.
2. Follow up immediately with `browser__puppeteer_evaluate`.
3. Provide a JavaScript snippet to extract the text you need. For example: `return document.body.innerText;`

If you get stuck with cookie banners or popups, you may need to use `puppeteer_evaluate` to run `document.querySelector('.accept-btn').click();` or similar before reading the page.
