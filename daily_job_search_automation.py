# daily_job_search_automation.py
"""
Daily Job Search Automation

What this does:
- Uses Google Custom Search JSON API to search for "entry level cyber security jobs" at top startups (search query customizable)
- Filters and deduplicates results, formats a short HTML email
- Sends the email via SMTP (Gmail example) or via any SMTP server

How to use:
1. Create a Google Custom Search Engine (CSE) and get:
   - API key (CSE API key)
   - Search engine ID (cx)
   See: https://developers.google.com/custom-search/docs/overview

2. Store secrets (recommended):
   - CSE_API_KEY
   - CSE_CX
   - EMAIL_USER (sender email)
   - EMAIL_PASS (SMTP password or app password)
   - RECIPIENT_EMAIL

3. Run locally or in CI (GitHub Actions) daily at 13:00 IST (07:30 UTC). A sample GitHub Actions workflow is included below in README section.

Notes & limitations:
- Google CSE may return results from many sites; you can tune the CSE to prioritize well-known startup job boards (Wellfound/AngelList, Built In, Indeed, Stack Overflow, etc.).
- You must provide API keys and SMTP credentials. For Gmail, create an app password or enable OAuth (the script uses SMTP/app password for simplicity).
- I cannot run this on your behalf or send emails myself from this chat.

"""

import os
import requests
import smtplib
import textwrap
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone, timedelta
from html import escape

# === Configuration (via environment variables) ===
CSE_API_KEY = os.getenv('CSE_API_KEY')
CSE_CX = os.getenv('CSE_CX')
EMAIL_USER = os.getenv('EMAIL_USER')
EMAIL_PASS = os.getenv('EMAIL_PASS')
RECIPIENT_EMAIL = os.getenv('RECIPIENT_EMAIL')
QUERY = os.getenv('JOB_QUERY', 'entry level cyber security jobs startups')
MAX_RESULTS = int(os.getenv('MAX_RESULTS', '10'))

# === Helpers ===

def search_google_cse(query, api_key, cx, num=10, start=1):
    """Call Google Custom Search JSON API and return items list."""
    url = 'https://www.googleapis.com/customsearch/v1'
    params = {
        'key': api_key,
        'cx': cx,
        'q': query,
        'num': min(num, 10),  # API returns up to 10 per request
        'start': start
    }
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    return r.json().get('items', [])


def gather_results(query, api_key, cx, max_total=10):
    results = []
    start = 1
    while len(results) < max_total:
        items = search_google_cse(query, api_key, cx, num=min(10, max_total - len(results)), start=start)
        if not items:
            break
        for it in items:
            results.append({
                'title': it.get('title'),
                'link': it.get('link'),
                'snippet': it.get('snippet')
            })
        start += len(items)
    return results


def format_email_html(results, query):
    now = datetime.now(timezone(timedelta(hours=5, minutes=30)))  # IST
    lines = []
    lines.append(f"<h2>Job search results: {escape(query)}</h2>")
    lines.append(f"<p>Search run at {now.strftime('%Y-%m-%d %H:%M %Z')} (IST)</p>")
    if not results:
        lines.append('<p>No results found.</p>')
    else:
        lines.append('<ol>')
        for r in results:
            title = escape(r.get('title') or 'No title')
            link = escape(r.get('link') or '')
            snippet = escape((r.get('snippet') or '').strip())
            lines.append(f'<li><a href="{link}">{title}</a><br/><small>{snippet}</small></li>')
        lines.append('</ol>')
    lines.append('<hr/><p>Automation generated - tweak the queries or sources in the script as needed.</p>')
    return '\n'.join(lines)


def send_email_smtp(sender, password, recipient, subject, html_body, smtp_server='smtp.gmail.com', smtp_port=587):
    msg = MIMEMultipart('alternative')
    msg['From'] = sender
    msg['To'] = recipient
    msg['Subject'] = subject
    part = MIMEText(html_body, 'html')
    msg.attach(part)

    s = smtplib.SMTP(smtp_server, smtp_port)
    s.ehlo()
    s.starttls()
    s.login(sender, password)
    s.sendmail(sender, [recipient], msg.as_string())
    s.quit()


# === Main entrypoint ===

def main():
    if not (CSE_API_KEY and CSE_CX and EMAIL_USER and EMAIL_PASS and RECIPIENT_EMAIL):
        print('Missing one of required environment variables: CSE_API_KEY, CSE_CX, EMAIL_USER, EMAIL_PASS, RECIPIENT_EMAIL')
        return

    print('Gathering job results...')
    results = gather_results(QUERY, CSE_API_KEY, CSE_CX, max_total=MAX_RESULTS)
    print(f'Found {len(results)} results')

    html = format_email_html(results, QUERY)
    subject = f"Daily job digest — {QUERY} — {datetime.now().strftime('%Y-%m-%d')}"

    print('Sending email...')
    send_email_smtp(EMAIL_USER, EMAIL_PASS, RECIPIENT_EMAIL, subject, html)
    print('Email sent.')


if __name__ == '__main__':
    main()


# ---------------------------
# GitHub Actions workflow (save as .github/workflows/daily-job-search.yml)
# Schedule: daily at 13:00 IST -> 07:30 UTC (cron uses UTC)
# ---------------------------
# name: Daily Job Search
#
# on:
#   schedule:
#     - cron: '30 7 * * *'  # runs daily at 07:30 UTC (13:00 IST)
#   workflow_dispatch: {}
#
# jobs:
#   run-search:
#     runs-on: ubuntu-latest
#     steps:
#       - uses: actions/checkout@v4
#       - name: Set up Python
#         uses: actions/setup-python@v4
#         with:
#           python-version: '3.11'
#       - name: Install requirements
#         run: |
#           python -m pip install --upgrade pip
#           pip install requests
#       - name: Run script
#         env:
#           CSE_API_KEY: ${{ secrets.CSE_API_KEY }}
#           CSE_CX: ${{ secrets.CSE_CX }}
#           EMAIL_USER: ${{ secrets.EMAIL_USER }}
#           EMAIL_PASS: ${{ secrets.EMAIL_PASS }}
#           RECIPIENT_EMAIL: ${{ secrets.RECIPIENT_EMAIL }}
#           JOB_QUERY: 'entry level cyber security jobs startups'
#           MAX_RESULTS: '10'
#         run: |
#           python daily_job_search_automation.py


# ---------------------------
# Tips & next steps (in brief):
# - Create Google CSE and tune sites (wellfound.com, angel.co, indeed.com, builtin.com, etc.)
# - Put secrets into GitHub Secrets if using Actions, or export env vars locally for cron
# - For Gmail, create an app password and use EMAIL_PASS=app_password (recommended)
# - You can adapt the script to fetch RSS feeds or specific job-board APIs instead of Google CSE
# - If you'd like, I can modify the query or add filters (e.g., location, remote, '0-2 years')
