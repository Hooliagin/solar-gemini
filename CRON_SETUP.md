# Cron Service Setup Guide

## Overview
Since Render Free Tier spins down after 15 minutes of inactivity, we use an external cron service to trigger morning briefings.

## Setup Instructions

### 1. Generate API Key
Create a secure random API key:
```bash
# On Mac/Linux:
openssl rand -hex 32

# On Windows PowerShell:
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | % {[char]$_})
```

### 2. Add to Render Environment Variables
In your Render dashboard:
1. Go to your service → "Environment"
2. Add new environment variable:
   - **Key**: `CRON_API_KEY`
   - **Value**: `<your-generated-key>`
3. Click "Save Changes"

### 3. Register on cron-job.org
1. Go to [cron-job.org](https://cron-job.org)
2. Create free account
3. Click "Create cronjob"

### 4. Configure Cronjob
**Settings:**
- **Title**: "Daily Manager Morning Briefings"
- **URL**: `https://your-app-name.onrender.com/cron/morning-briefings`
- **Schedule**: 
  - Execution time: `07:00` (or your preferred time)
  - Days: `Every day`
- **Request Method**: `POST`
- **Custom Headers**: Click "Add header"
  - **Name**: `X-API-Key`
  - **Value**: `<your-generated-api-key>`

**Important:** All users will receive their briefing at this scheduled time (e.g., 7:00 AM).

### 5. Test the Endpoint
Test manually with curl:
```bash
curl -X POST https://your-app-name.onrender.com/cron/morning-briefings \
  -H "X-API-Key: your-api-key"
```

Expected response:
```json
{
  "status": "success",
  "message": "Morning briefing job completed"
}
```

## Alternative Cron Services

### easycron.com
- Free tier: 20 jobs/day
- Setup: Similar to cron-job.org
- URL: [easycron.com](https://www.easycron.com)

### GitHub Actions (Free)
Create `.github/workflows/morning-briefing.yml`:
```yaml
name: Morning Briefing
on:
  schedule:
    - cron: '0 6 * * *'  # 6:00 AM UTC
jobs:
  trigger:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger briefing
        run: |
          curl -X POST ${{ secrets.RENDER_URL }}/cron/morning-briefings \
            -H "X-API-Key: ${{ secrets.CRON_API_KEY }}"
```

## Monitoring

Check cron-job.org execution history to verify:
- ✅ Jobs are running on schedule
- ✅ Receiving 200 OK responses
- ❌ Any errors (check Render logs)

## Troubleshooting

**Issue**: 401 Unauthorized
- **Fix**: Verify API key matches in Render and cron service

**Issue**: 500 Internal Server Error
- **Fix**: Check Render logs for errors

**Issue**: Server not responding
- **Fix**: Render free tier may be sleeping. First request will wake it up (takes ~1 min)
