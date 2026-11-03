"""Import human-reviewed historical appearances without copying broadcaster material.

Usage:
  python3 scripts/import_media_corpus.py path/to/approved-media.csv [--dry-run]
"""
import csv
import json
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / 'data' / 'manual-media.json'
REQUIRED_COLUMNS = {'source_url', 'source_type', 'publisher', 'title', 'reviewed'}
VALID_TYPES = {'news', 'video'}


def clean(value):
    return value.strip() if isinstance(value, str) else ''


def valid_url(value):
    parsed = urlsplit(value)
    return parsed.scheme == 'https' and bool(parsed.netloc)


def video_id_from_url(url):
    parsed = urlsplit(url)
    host = (parsed.hostname or '').lower()
    if host in {'youtube.com', 'www.youtube.com', 'm.youtube.com'} and parsed.path == '/watch':
        return parse_qs(parsed.query).get('v', [''])[0]
    if host == 'youtu.be':
        return parsed.path.strip('/').split('/')[0]
    return ''


def source_key(item):
    video_id = item.get('videoId')
    if video_id:
        return f'youtube:{video_id}'
    return item['url'].split('#', 1)[0]


def row_to_item(row, line_number):
    url = clean(row.get('source_url'))
    kind = clean(row.get('source_type')).lower()
    publisher = clean(row.get('publisher'))
    title = clean(row.get('title'))
    if not valid_url(url):
        raise ValueError(f'Row {line_number}: source_url must be an HTTPS URL')
    if kind not in VALID_TYPES:
        raise ValueError(f'Row {line_number}: source_type must be news or video')
    if not publisher or not title:
        raise ValueError(f'Row {line_number}: publisher and title are required')
    item = {'title': title, 'url': url, 'source': publisher, 'type': kind}
    optional_fields = {
        'display_title': 'displayTitle',
        'appearance_date': 'appearanceDate',
        'published': 'published',
        'original_broadcaster': 'originalBroadcaster',
        'programme': 'programme',
    }
    for column, field in optional_fields.items():
        value = clean(row.get(column))
        if value:
            item[field] = value
    video_id = clean(row.get('video_id')) or video_id_from_url(url)
    if video_id:
        if not re.fullmatch(r'[A-Za-z0-9_-]{11}', video_id):
            raise ValueError(f'Row {line_number}: video_id must be an 11-character YouTube ID')
        item['videoId'] = video_id
    return item


def main():
    args = [arg for arg in sys.argv[1:] if arg != '--dry-run']
    dry_run = '--dry-run' in sys.argv[1:]
    if len(args) != 1:
        raise SystemExit('Usage: python3 scripts/import_media_corpus.py path/to/approved-media.csv [--dry-run]')
    source_path = Path(args[0])
    with source_path.open(newline='') as handle:
        reader = csv.DictReader(handle)
        headers = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - headers
        if missing:
            raise SystemExit('Missing CSV columns: ' + ', '.join(sorted(missing)))
        imported = []
        skipped = 0
        for line_number, row in enumerate(reader, start=2):
            if clean(row.get('reviewed')).lower() not in {'1', 'true', 'yes', 'y'}:
                skipped += 1
                continue
            imported.append(row_to_item(row, line_number))

    existing = json.loads(MANUAL.read_text())
    by_key = {source_key(item): item for item in existing}
    for item in imported:
        by_key[source_key(item)] = item
    result = list(by_key.values())
    if not dry_run:
        MANUAL.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    action = 'Would import' if dry_run else 'Imported'
    print(f'{action} {len(imported)} reviewed records; skipped {skipped} unreviewed rows; manual archive now has {len(result)} records')


if __name__ == '__main__':
    main()
