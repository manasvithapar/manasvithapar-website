"""Validate records that can appear in the public media archive."""
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
PUBLISHED_TYPES = {'news', 'video'}
VALID_TYPES = PUBLISHED_TYPES | {'social'}
GOOGLE_DISCOVERY_HOSTS = {'news.google.com', 'www.google.com'}


def is_https_url(value):
    if not isinstance(value, str):
        return False
    parsed = urlsplit(value)
    return parsed.scheme == 'https' and bool(parsed.netloc)


def is_discovery_url(value):
    return (urlsplit(value).hostname or '').lower() in GOOGLE_DISCOVERY_HOSTS


def validate_record(item, label, errors, allow_discovery=False):
    if not isinstance(item, dict):
        errors.append(f'{label}: record must be an object')
        return
    if not isinstance(item.get('title'), str) or not item['title'].strip():
        errors.append(f'{label}: title is required')
    if not isinstance(item.get('source'), str) or not item['source'].strip():
        errors.append(f'{label}: source is required')
    if not is_https_url(item.get('url')):
        errors.append(f'{label}: URL must be a direct HTTPS URL')
    elif is_discovery_url(item['url']) and not allow_discovery:
        errors.append(f'{label}: Google discovery links cannot be in the public archive')
    if item.get('type') not in VALID_TYPES:
        errors.append(f'{label}: type must be news, video, or social')
    video_id = item.get('videoId')
    if video_id is not None and not (isinstance(video_id, str) and re.fullmatch(r'[A-Za-z0-9_-]{11}', video_id)):
        errors.append(f'{label}: videoId must be an 11-character YouTube ID')


def main():
    errors = []
    manual = json.loads((DATA / 'manual-media.json').read_text())
    published = json.loads((DATA / 'media.json').read_text())
    candidates_path = DATA / 'media-candidates.json'
    candidates = json.loads(candidates_path.read_text()) if candidates_path.exists() else {'items': []}

    for index, item in enumerate(manual, start=1):
        validate_record(item, f'manual record {index}', errors)
    for index, item in enumerate(published.get('items', []), start=1):
        validate_record(item, f'published record {index}', errors)
        if item.get('type') not in PUBLISHED_TYPES:
            errors.append(f'published record {index}: social posts belong outside the media archive')
    for index, item in enumerate(candidates.get('items', []), start=1):
        validate_record(item, f'candidate {index}', errors, allow_discovery=True)
        if not is_discovery_url(item.get('url', '')):
            errors.append(f'candidate {index}: expected a Google discovery URL')

    if errors:
        raise SystemExit('\n'.join(errors))
    print(
        f"Validated {len(published.get('items', []))} published records, "
        f"{len(candidates.get('items', []))} discovery candidates, and {len(manual)} manual records"
    )


if __name__ == '__main__':
    main()
