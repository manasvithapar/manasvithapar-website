"""Validate records that can appear in the public media archive."""
import datetime as dt
import json
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
OFFICIAL_YOUTUBE = DATA / 'official-youtube.json'
OFFICIAL_CHANNEL_ID = 'UCWBzJDiiXeg632cU3S3Ei7A'
CATALOG_MAX_AGE = dt.timedelta(days=28)
PUBLISHED_TYPES = {'news', 'video'}
VALID_TYPES = PUBLISHED_TYPES | {'social'}
VALID_SOURCE_CLASSES = {
    'publisher_hosted', 'broadcaster_upload', 'official_archive', 'institutional_record', 'event_organiser',
}
GOOGLE_DISCOVERY_HOSTS = {'news.google.com', 'www.google.com'}


def is_https_url(value):
    if not isinstance(value, str):
        return False
    parsed = urlsplit(value)
    return parsed.scheme == 'https' and bool(parsed.netloc)


def is_discovery_url(value):
    return (urlsplit(value).hostname or '').lower() in GOOGLE_DISCOVERY_HOSTS


def parse_timestamp(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.timezone.utc)


def is_iso_date(value):
    if not isinstance(value, str) or not value:
        return False
    try:
        dt.date.fromisoformat(value)
        return True
    except ValueError:
        return False


def canonical_youtube_url(item):
    video_id = item.get('videoId')
    parsed = urlsplit(item.get('url', ''))
    if (parsed.hostname or '').lower() != 'www.youtube.com' or parsed.path != '/watch':
        return False
    return parse_qs(parsed.query).get('v', [''])[0] == video_id


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
    for field in ('appearanceDate', 'dateStatedInTitle'):
        if field in item and not is_iso_date(item[field]):
            errors.append(f'{label}: {field} must be an ISO date')
    if item.get('published') and not parse_timestamp(item['published']):
        errors.append(f'{label}: published must be an ISO timestamp')
    if item.get('reviewedOn') and not is_iso_date(item['reviewedOn']):
        errors.append(f'{label}: reviewedOn must be an ISO date')
    source_class = item.get('sourceClass')
    if source_class is not None and source_class not in VALID_SOURCE_CLASSES:
        errors.append(f'{label}: sourceClass is not recognised')
    for field in ('originalBroadcaster', 'programme'):
        if field in item and (not isinstance(item[field], str) or not item[field].strip()):
            errors.append(f'{label}: {field} must be non-empty when present')
    if source_class == 'official_archive':
        if item.get('type') != 'video':
            errors.append(f'{label}: official_archive entries must be video records')
        if not item.get('originalBroadcaster'):
            errors.append(f'{label}: official_archive entries require originalBroadcaster')


def main():
    errors = []
    manual = json.loads((DATA / 'manual-media.json').read_text())
    published = json.loads((DATA / 'media.json').read_text())
    candidates_path = DATA / 'media-candidates.json'
    candidates = json.loads(candidates_path.read_text()) if candidates_path.exists() else {'items': []}
    official_youtube = json.loads(OFFICIAL_YOUTUBE.read_text()) if OFFICIAL_YOUTUBE.exists() else {'items': []}

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
    catalog_items = official_youtube.get('items', [])
    if not isinstance(catalog_items, list):
        errors.append('official YouTube catalog: items must be an array')
        catalog_items = []
    if official_youtube.get('items'):
        if official_youtube.get('channelId') != OFFICIAL_CHANNEL_ID:
            errors.append('official YouTube catalog: channelId does not match the official channel')
        if not isinstance(official_youtube.get('uploadsPlaylistId'), str) or not official_youtube['uploadsPlaylistId']:
            errors.append('official YouTube catalog: uploadsPlaylistId is required')
        updated = parse_timestamp(official_youtube.get('updated', ''))
        if not updated:
            errors.append('official YouTube catalog: updated must be an ISO timestamp')
        elif dt.datetime.now(dt.timezone.utc) - updated > CATALOG_MAX_AGE:
            errors.append('official YouTube catalog: public metadata is older than 28 days')
    video_ids = set()
    for index, item in enumerate(catalog_items, start=1):
        validate_record(item, f'official YouTube record {index}', errors)
        if item.get('type') != 'video':
            errors.append(f'official YouTube record {index}: type must be video')
        if item.get('source') != 'Official YouTube channel':
            errors.append(f'official YouTube record {index}: source must be Official YouTube channel')
        if item.get('channelId') != OFFICIAL_CHANNEL_ID:
            errors.append(f'official YouTube record {index}: channelId does not match the official channel')
        if item.get('sourceType') != 'official_youtube_upload':
            errors.append(f'official YouTube record {index}: sourceType must be official_youtube_upload')
        if item.get('managedBy') != 'youtube-data-api':
            errors.append(f'official YouTube record {index}: managedBy must be youtube-data-api')
        if not parse_timestamp(item.get('metadataRefreshedAt', '')):
            errors.append(f'official YouTube record {index}: metadataRefreshedAt must be an ISO timestamp')
        if not canonical_youtube_url(item):
            errors.append(f'official YouTube record {index}: URL must match its videoId')
        video_id = item.get('videoId')
        if isinstance(video_id, str):
            if video_id in video_ids:
                errors.append(f'official YouTube record {index}: duplicate videoId')
            video_ids.add(video_id)

    if errors:
        raise SystemExit('\n'.join(errors))
    print(
        f"Validated {len(published.get('items', []))} published records, "
        f"{len(candidates.get('items', []))} discovery candidates, {len(catalog_items)} official YouTube records, and {len(manual)} manual records"
    )


if __name__ == '__main__':
    main()
