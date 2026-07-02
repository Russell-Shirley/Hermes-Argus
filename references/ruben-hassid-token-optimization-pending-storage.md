Cognee and OpenBrain storage for Ruben Hassid's guide is pending because Docker/WSL appears to be unresponsive. The guide content is saved to disk at:
/mnt/c/Users/Russell/Documents/GitHub/Hermes-Argus/references/ruben-hassid-token-optimization-guide.md

To complete Cognee/OpenBrain storage, restart Docker and run:
1. docker start $(docker ps -aq)  # or docker compose up -d in Hermes-Argus
2. curl -X POST http://localhost:8000/memorize -H "Content-Type: application/json" -d @- <<'COG'
{"text": "Ruben Hassid token optimization guide: 23 habits for Claude usage. Source: https://ruben.substack.com/ Apr 11 2026. Key techniques include convert PDFs to .md, plan in Chat/build in Cowork, ask questions instead of writing long prompts, voice input via Wispr Flow, batch tasks, consistent prompt structure, edit over follow-up, restart conversations every 15-20 messages, Projects for recurring files, match model to task, turn off unused features, spread sessions across 5-hour window."}
COG
3. For OpenBrain (Postgres): psql -h localhost -U postgres -d openbrain -c "INSERT INTO knowledge_entries (source, title, content, created_at) VALUES ('ruben_hassid_substack', 'Ruben Hassid Token Optimization Guide (23 habits)', '[content]', NOW());"
