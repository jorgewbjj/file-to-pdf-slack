import os
import json
import requests
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def create_pdf_summary(file_path, pdf_path):
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    width, height = letter
    margin = 40
    y = height - margin
    c.setFont("Helvetica-Bold", 14)
    c.drawString(margin, y, f"File uploaded: {file_path.name}")
    y -= 20
    c.setFont("Helvetica", 12)
    c.drawString(margin, y, f"Repository: {os.environ.get('GITHUB_REPOSITORY')}")
    y -= 20
    c.drawString(margin, y, f"File path: {file_path}")
    y -= 30
    c.setFont("Helvetica", 12)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        c.drawString(margin, y, "File contents:")
        y -= 20
        for line in lines:
            if y < margin:
                c.showPage()
                y = height - margin
            c.drawString(margin, y, line.strip()[:100])
            y -= 15
    except Exception:
        c.drawString(margin, y, "Binary file or could not read contents.")
    c.save()


def send_file_to_slack(pdf_path, filename):
    token = os.environ.get('SLACK_BOT_TOKEN')
    channel = os.environ.get('SLACK_CHANNEL_ID')
    if not token or not channel:
        print("Missing Slack token or channel ID.")
        return
    with open(pdf_path, 'rb') as f:
        response = requests.post(
            'https://slack.com/api/files.upload',
            headers={'Authorization': f'Bearer {token}'},
            files={'file': (filename, f, 'application/pdf')},
            data={'channels': channel, 'title': filename, 'filename': filename}
        )
    print('Slack upload response:', response.status_code, response.text)


def main():
    event_path = os.environ.get('GITHUB_EVENT_PATH')
    if not event_path:
        print('No GitHub event path set.')
        return
    with open(event_path, 'r') as f:
        event = json.load(f)
    repo_root = Path('.')
    processed = set()
    commits = event.get('commits', [])
    for commit in commits:
        for file in commit.get('added', []) + commit.get('modified', []):
            if not file.startswith('uploads/'):
                continue
            if file.endswith('.pdf'):
                continue
            file_path = repo_root / file
            if not file_path.exists() or file_path in processed:
                continue
            pdf_output = file_path.with_suffix('.pdf')
            create_pdf_summary(file_path, pdf_output)
            send_file_to_slack(pdf_output, pdf_output.name)
            processed.add(file_path)


if __name__ == "__main__":
    main()
