# Ruben Hassid's Claude Token Optimization Guide

**Source:** https://ruben.substack.com/ (Substack: "How to AI")
**Published:** April 11, 2026
**Author:** Ruben Hassid (https://www.linkedin.com/in/ruben-hassid/)
**Original Title:** "How to stop hitting Claude usage limits. 23 tricks to use Claude better and not spend too much money"

## Summary
A practical guide with 23 habits to reduce Claude token consumption, ranked from most unknown to obvious. Designed for Claude users on $20 and $100 plans who hit usage limits frequently.

## The 23 Habits

### Habits You (Probably) Don't Know About

1. **Convert files before uploading** — PDF page = 1,500-3,000 tokens. Paste text into doc.new → download as .md file. 15-page PDF → ~2,000 clean tokens.

2. **Plan in Chat. Build in Cowork** — File creation eats more limit. Think in cheap product (Chat), build in expensive one (Cowork).

3. **Say "ask me questions"** — 30-word prompt: "I want to [task] to [success criteria]. Read my folder. Ask me questions using AskUserQuestion before you start."

4. **Use Wispr Flow (voice input)** — Voice gives richer context in one shot → fewer messages → fewer rereads.

5. **Fix only the broken section** — "Only redo section 3. Keep everything else to save tokens." Add "No commentary. No explanations. Just the output."

6. **Batch tasks into one message** — Three separate prompts = three full context reloads. One prompt with three tasks = one reload.

7. **Use the same prompt structure** — Similar prompts get partially cached. Keep a stable prompt library, swap only variables.

8. **Edit your message instead of follow-ups** — In Chat, click Edit on original. Old exchange is replaced, not stacked.

9. **Pick the right product** — Quick Q? Chat+Haiku. Report from files? Cowork+Opus. Chart from data? Code+Sonnet.

### The Basics That Still Matter

10. **Keep ABOUT ME under 2,000 words** — Cowork reads folder before every task. Trim bloated files.

11. **Restart conversations** — 20-message session = ~105K tokens. 30 messages = 232K. Restart from earlier point or fresh.

12. **Summarize every 15-20 messages** — 98.5% of tokens spent re-reading history, only 1.5% on output. Summarize → new session.

13. **Sonnet/Haiku for simple, Opus for deep** — Grammar checks don't need Opus. 2 clicks to switch.

14. **Don't dump folders** — Every file = tokens spent. If task doesn't need files, select zero folders.

15. **New topic = new chat** — Old messages are dead weight. Always start fresh on topic change.

16. **Turn off unused features** — Web search, connectors, tools add tokens even when unused. Default: everything off, turn on per task.

17. **Use Projects for recurring files** — Upload once, cached. RAG retrieves only relevant chunks.

18. **Turn off Memory, set Preferences** — Settings → General → Personal preferences. Use Styles (Concise or custom).

19. **Use scheduled tasks** — /schedule plugin for recurring reports, digests, research.

20. **Clear Claude Code scope** — Be specific. Don't leave room for exploration. "Create bar chart from CSV showing monthly revenue. Save as chart.png."

21. **Use CLAUDE.md for permanent context** — Write recurring instructions once. Keep it short. Skills load on demand, CLAUDE.md loads every time.

22. **Spread sessions across the day** — Claude uses rolling 5-hour window. Morning + afternoon + evening.

23. **Don't use Claude for things it's bad at** — Images → Gemini. Real-time search → Grok. 5 messages on impossible tasks = wasted tokens.

## Where to Start
- **Cowork daily:** Start with habits 1, 2, 5
- **Chat mostly:** Start with 8, 15, 17
- **$20 plan hitting limits:** Start with 6, 13, 22
