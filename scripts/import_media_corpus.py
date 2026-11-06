"""Import human-reviewed historical appearances without copying broadcaster material.

Usage:
  python3 scripts/import_media_corpus.py path/to/approved-media.csv [--dry-run]
"""
import csv
import datetime as dt
import json
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / 'data' / 'manual-media.json'
GOOGLE_DISCOVERY_HOSTS = {'news.google.com', 'www.google.com'}
REQUIRED_COLUMNS = {
    'source_url', 'source_type', 'source_class', 'publisher', 'title', 'reviewed', 'reviewed_on', 'reviewer',
}
VALID_TYPES = {'news', 'video'}
VALID_SOURCE_CLASSES = {
    'publisher_hosted', 'broadcaster_upload', 'official_archive', 'institutional_record', 'event_organiser',
}


def clean(value):
    return value.strip() if isinstance(value, str) else ''


def valid_url(value):
    parsed = urlsplit(value)
    return parsed.scheme == 'https' and bool(parsed.netloc)


def discovery_url(value):
    return (urlsplit(value).hostname or '').lower() in GOOGLE_DISCOVERY_HOSTS


def iso_date(value):
    try:
        dt.date.fromisoformat(value)
        return True
    except ValueError:
        return False


def iso_timestamp(value):
    if not value:
        return True
    try:
        dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
        return True
    except ValueError:
        try:
            dt.date.fromisoformat(value)
            return True
        except ValueError:
            return False


def video_id_from_url(url):
    parsed = urlsplit(url)
    host = (parsed.hostname or '').lower()
    if host in {'youtube.com', 'www.youtube.com', 'm.youtube.com'}:
        if parsed.path == '/watch':
            return parse_qs(parsed.query).get('v', [''])[0]
        parts = [part for part in parsed.path.split('/') if part]
        if len(parts) >= 2 and parts[0] in {'shorts', 'live'}:
            return parts[1]
    if host == 'youtu.be':
        return parsed.path.strip('/').split('/')[0]
    return ''


def source_key(item):
    video_id = item.get('videoId') or video_id_from_url(item['url'])
    if re.fullmatch(r'[A-Za-z0-9_-]{11}', video_id or ''):
        return f'youtube:{video_id}'
    return item['url'].split('#', 1)[0]


def row_to_item(row, line_number):
    url = clean(row.get('source_url'))
    kind = clean(row.get('source_type')).lower()
    source_class = clean(row.get('source_class')).lower()
    publisher = clean(row.get('publisher'))
    title = clean(row.get('title'))
    reviewed_on = clean(row.get('reviewed_on'))
    reviewer = clean(row.get('reviewer'))
    if not valid_url(url) or discovery_url(url):
        raise ValueError(f'Row {line_number}: source_url must be a direct, non-Google HTTPS URL')
    if kind not in VALID_TYPES:
        raise ValueError(f'Row {line_number}: source_type must be news or video')
    if source_class not in VALID_SOURCE_CLASSES:
        raise ValueError(f'Row {line_number}: source_class is not recognised')
    if not publisher or not title:
        raise ValueError(f'Row {line_number}: publisher and title are required')
    if not iso_date(reviewed_on):
        raise ValueError(f'Row {line_number}: reviewed_on must be an ISO date')
    if not reviewer:
        raise ValueError(f'Row {line_number}: reviewer is required')

    original_broadcaster = clean(row.get('original_broadcaster'))
    if source_class == 'official_archive':
        if kind != 'video':
            raise ValueError(f'Row {line_number}: official_archive entries must be video records')
        if not original_broadcaster:
            raise ValueError(f'Row {line_number}: official_archive entries require original_broadcaster')

    item = {
        'title': title,
        'url': url,
        'source': publisher,
        'type': kind,
        'sourceClass': source_class,
        'reviewedOn': reviewed_on,
    }
    optional_fields = {
        'display_title': 'displayTitle',
        'appearance_date': 'appearanceDate',
        'date_stated_in_title': 'dateStatedInTitle',
        'published': 'published',
        'original_broadcaster': 'originalBroadcaster',
        'programme': 'programme',
    }
    for column, field in optional_fields.items():
        value = clean(row.get(column))
        if not value:
            continue
        if field in {'appearanceDate', 'dateStatedInTitle'} and not iso_date(value):
            raise ValueError(f'Row {line_number}: {column} must be an ISO date')
        if field == 'published' and not iso_timestamp(value):
            raise ValueError(f'Row {line_number}: published must be an ISO date or timestamp')
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
