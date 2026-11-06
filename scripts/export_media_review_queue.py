"""Export Google News discovery candidates into a reviewer-only CSV queue.

The output is intentionally not a public archive and cannot be imported until a
reviewer replaces the discovery URL with a direct original-source URL.

Usage:
  python3 scripts/export_media_review_queue.py path/to/review-queue.csv [--dry-run]
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / 'data' / 'media-candidates.json'
HEADERS = [
    'candidate_title',
    'candidate_url',
    'candidate_source',
    'candidate_published',
    'source_url',
    'source_type',
    'source_class',
    'publisher',
    'original_broadcaster',
    'programme',
    'appearance_date',
    'date_stated_in_title',
    'published',
    'title',
    'display_title',
    'video_id',
    'reviewed',
    'reviewed_on',
    'reviewer',
    'notes',
]


def candidate_type(item):
    title = str(item.get('title', '')).lower()
    source = str(item.get('source', '')).lower()
    return 'video' if 'youtube' in source or title.endswith(' - youtube') else 'news'


def queue_row(item):
    return {
        'candidate_title': item.get('title', ''),
        'candidate_url': item.get('url', ''),
        'candidate_source': item.get('source', ''),
        'candidate_published': item.get('published', ''),
        'source_url': '',
        'source_type': candidate_type(item),
        'source_class': '',
        'publisher': '',
        'original_broadcaster': '',
        'programme': '',
        'appearance_date': '',
        'date_stated_in_title': '',
        'published': '',
        'title': item.get('title', ''),
        'display_title': '',
        'video_id': '',
        'reviewed': 'no',
        'reviewed_on': '',
        'reviewer': '',
        'notes': 'Replace the discovery URL with a direct original-source URL before approval.',
    }


def main():
    args = [arg for arg in sys.argv[1:] if arg != '--dry-run']
    dry_run = '--dry-run' in sys.argv[1:]
    if len(args) != 1:
        raise SystemExit('Usage: python3 scripts/export_media_review_queue.py path/to/review-queue.csv [--dry-run]')
    output = Path(args[0])
    payload = json.loads(CANDIDATES.read_text())
    candidates = payload.get('items', [])
    rows = [queue_row(item) for item in candidates if item.get('discoveryOnly')]
    rows.sort(key=lambda row: row['candidate_published'], reverse=True)
    if not dry_run:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=HEADERS)
            writer.writeheader()
            writer.writerows(rows)
    action = 'Would export' if dry_run else 'Exported'
    print(f'{action} {len(rows)} discovery candidates for human review')


if __name__ == '__main__':
    main()
