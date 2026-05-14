---
name: gmail-api-integration
description: |
  Setup and usage guide for read-only Gmail API integration — covers Google Cloud
  project setup, OAuth 2.0 flow, and email reading.
  DO NOT use for: sending emails, modifying mailbox, or non-Gmail email providers.
category: ops
domain: email
intent:
  - gmail-setup
  - oauth-configuration
  - email-reading
exclusions:
  - email-sending
  - mailbox-modification
  - non-gmail
requires:
  - google-cloud-project
  - oauth-credentials
phase: setup
compatible_with: []
conflicts_with: []
handoff_to: []
scope: local-only
data_access:
  mcp_servers: []
  secrets: [GMAIL_CREDENTIALS, GMAIL_TOKEN]
  trust_level: user-data
governed_by: []
version: 1.0.0
compatibility:
  min_runtime: hermes-1.0
deprecated: false
deprecation_notes: ""
examples:
  - "Set up Gmail API for reading invoices from a client's inbox"
  - "Troubleshoot expired OAuth token during email fetch"
  - "Read unread emails from a Gmail label"
---
# Gmail API Integration (Read-Only)

## Overview
This skill describes how to set up Gmail API access so the assistant can read emails from a user's Gmail account. Access is limited to **read-only** scope.

## Google Cloud Project Setup

### 1. Create a Google Cloud Project
1. Go to https://console.cloud.google.com/
2. Create a new project or select existing
3. Note the Project ID

### 2. Enable Gmail API
1. Go to APIs & Services > Library
2. Search for "Gmail API"
3. Click Enable

### 3. Configure OAuth Consent Screen
1. Go to APIs & Services > OAuth consent screen
2. Choose "External" user type
3. Fill required fields (App name, support email, developer contact)
4. Add scopes: `https://www.googleapis.com/auth/gmail.readonly`
5. Add test users (your Gmail address)
6. Publish app (required for refresh tokens to last beyond 7 days)

### 4. Create OAuth 2.0 Credentials
1. Go to APIs & Services > Credentials
2. Click Create Credentials > OAuth client ID
3. Choose "Desktop application"
4. Download the JSON file as `credentials.json`

### 5. Generate Token
```python
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
creds = flow.run_local_server(port=0)

# Save token
with open('token.json', 'w') as token:
    token.write(creds.to_json())
```

## Reading Emails
```python
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Load credentials
creds = Credentials.from_authorized_user_file('token.json', SCOPES)
service = build('gmail', 'v1', credentials=creds)

# List messages
results = service.users().messages().list(userId='me', maxResults=10).execute()
messages = results.get('messages', [])

# Get full message
msg = service.users().messages().get(userId='me', id=messages[0]['id'], format='full').execute()
```

## Important Notes
- Refresh tokens expire if app is in testing mode and not used for 7 days
- Store both `credentials.json` and `token.json` securely (these are sensitive credentials)
- For production, consider using a service account with domain-wide delegation instead
