# Gmail API Integration (Read-Only)

## Overview
This skill describes how to set up Gmail API access so the assistant can read emails from a user's Gmail account. Access is limited to **read-only** scope.

## Google Cloud Project Setup

### 1. Create a Google Cloud Project
1. Go to https://console.cloud.google.com/
2. Create a new project (or select existing)
3. Enable the **Gmail API**:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Gmail API" and enable it

### 2. Configure OAuth Consent Screen
1. Go to "APIs & Services" > "OAuth consent screen"
2. Choose **External** (or Internal if using Google Workspace)
3. Fill in:
   - App name
   - User support email
   - Developer contact info
4. Add **scopes**:
   - `https://www.googleapis.com/auth/gmail.readonly`
5. Add test users (your email address)
6. Publish app (if External)

### 3. Create OAuth 2.0 Credentials
1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. Choose **Desktop application** (or Web application)
4. Download the JSON credentials file

## Authentication Flow (OAuth 2.0)

### Step 1: Get Authorization URL
```python
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

flow = InstalledAppFlow.from_client_secrets_file(
    'credentials.json', SCOPES)
auth_url, _ = flow.authorization_url(
    access_type='offline',
    include_granted_scopes='true')
print(f'Go to: {auth_url}')
```

### Step 2: User Authorizes
User visits the URL, logs into their Google account, grants read-only access, and gets an authorization code.

### Step 3: Exchange Code for Tokens
```python
flow.fetch_token(code=AUTHORIZATION_CODE)
# Tokens are now stored in flow.credentials
# Includes: access_token, refresh_token, token_expiry
```

## Reading Emails (Read-Only)

### List Messages
```python
from googleapiclient.discovery import build

service = build('gmail', 'v1', credentials=creds)

# List recent 10 messages
results = service.users().messages().list(
    userId='me', maxResults=10).execute()
messages = results.get('messages', [])
```

### Get Full Message Content
```python
msg = service.users().messages().get(
    userId='me', id=msg_id, format='full').execute()

# Extract headers
headers = msg['payload']['headers']
subject = next(h['value'] for h in headers if h['name'] == 'Subject')
from_email = next(h['value'] for h in headers if h['name'] == 'From')
date = next(h['value'] for h in headers if h['name'] == 'Date')

# Extract body (handle multipart)
def get_body(payload):
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                return base64.urlsafe_b64decode(
                    part['body']['data']).decode('utf-8')
    elif 'data' in payload['body']:
        return base64.urlsafe_b64decode(
            payload['body']['data']).decode('utf-8')
    return ''
```

## Security Notes
- Use **read-only scope** only (`gmail.readonly`)
- Store refresh tokens securely (encrypted)
- Never hardcode credentials in code
- Rotate client secrets periodically
- Use environment variables or secure vault for tokens

## Required Python Packages
```
google-auth
google-auth-oauthlib
google-auth-httplib2
google-api-python-client
```
