"""Synchronise the public uploads catalog for Manasvi Thapar's official YouTube channel.

This reads public metadata only. It never downloads, embeds, or re-uploads video
files. Set YOUTUBE_API_KEY to a restricted YouTube Data API v3 key to enable it.
"""
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'data' / 'official-youtube.json'
CHANNEL_ID = 'UCWBzJDiiXeg632cU3S3Ei7A'
API_ROOT = 'https://www.googleapis.com/youtube/v3/'
TITLE_DATE = re.compile(r'\((\d{1,2})\.(\d{1,2})\.(\d{4})\)')
MAX_CATALOG_AGE = dt.timedelta(days=28)


def utc_now():
    return dt.datetime.now(dt.timezone.utc)


def parse_timestamp(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.timezone.utc)


def read_existing():
    if not OUTPUT.exists():
        return None
    try:
        payload = json.loads(OUTPUT.read_text())
    except json.JSONDecodeError as error:
        raise RuntimeError('The official YouTube catalog is not valid JSON') from error
    if not isinstance(payload, dict):
        raise RuntimeError('The official YouTube catalog must be a JSON object')
    return payload


def catalog_is_stale(existing, now):
    refreshed = parse_timestamp(existing.get('updated', '')) if existing else None
    return not refreshed or now - refreshed > MAX_CATALOG_AGE


def api_get(endpoint, params, api_key):
    query = urllib.parse.urlencode({**params, 'key': api_key})
    request = urllib.request.Request(
        API_ROOT + endpoint + '?' + query,
        headers={'User-Agent': 'ManasviThaparWebsite/1.0'},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as error:
        # Do not include a request URL or response body in logs: either may expose a key.
        raise RuntimeError(f'YouTube Data API returned HTTP {error.code}') from error
    except urllib.error.URLError as error:
        raise RuntimeError('YouTube Data API could not be reached') from error


def date_stated_in_title(title):
    """Return a literal dd.mm.yyyy date stated in a title, without calling it an appearance date."""
    match = TITLE_DATE.search(title)
    if not match:
        return ''
    try:
        return dt.date(int(match.group(3)), int(match.group(2)), int(match.group(1))).isoformat()
    except ValueError:
        return ''


def channel_details(api_key):
    response = api_get('channels', {'part': 'snippet,contentDetails', 'id': CHANNEL_ID}, api_key)
    channels = response.get('items', [])
    if len(channels) != 1 or channels[0].get('id') != CHANNEL_ID:
        raise RuntimeError('Official YouTube channel could not be resolved')
    channel = channels[0]
    uploads = channel.get('contentDetails', {}).get('relatedPlaylists', {}).get('uploads')
    if not uploads:
        raise RuntimeError('Official YouTube uploads playlist was not available')
    title = str(channel.get('snippet', {}).get('title', 'Manasvi Thapar')).strip()
    return uploads, title or 'Manasvi Thapar'


def playlist_entries(api_key, playlist_id):
    """Read every public upload from the API-provided uploads playlist."""
    entries = []
    page_token = None
    seen = set()
    while True:
        params = {
            'part': 'snippet,contentDetails,status',
            'playlistId': playlist_id,
            'maxResults': 50,
        }
        if page_token:
            params['pageToken'] = page_token
        response = api_get('playlistItems', params, api_key)
        for item in response.get('items', []):
            snippet = item.get('snippet', {})
            content = item.get('contentDetails', {})
            status = item.get('status', {})
            video_id = content.get('videoId') or snippet.get('resourceId', {}).get('videoId')
            title = str(snippet.get('title', '')).strip()
            published = str(content.get('videoPublishedAt', '')).strip()
            owner = snippet.get('videoOwnerChannelId')
            if (
                not isinstance(video_id, str)
                or not re.fullmatch(r'[A-Za-z0-9_-]{11}', video_id)
                or video_id in seen
                or status.get('privacyStatus') != 'public'
                or owner not in (None, '', CHANNEL_ID)
                or not title
                or title.lower() in {'private video', 'deleted video'}
                or not published
            ):
                continue
            seen.add(video_id)
            entries.append({
                'videoId': video_id,
                'title': title,
                'published': published,
                'playlistPosition': item.get('snippet', {}).get('position', len(entries)),
            })
        page_token = response.get('nextPageToken')
        if not page_token:
            break
    return entries


def record(entry, channel_title, refreshed_at):
    result = {
        'title': entry['title'],
        'url': f"https://www.youtube.com/watch?v={entry['videoId']}",
        'source': 'Official YouTube channel',
        'type': 'video',
        'videoId': entry['videoId'],
        'published': entry['published'],
        'sourceType': 'official_youtube_upload',
        'managedBy': 'youtube-data-api',
        'channelId': CHANNEL_ID,
        'channelTitle': channel_title,
        'playlistPosition': entry['playlistPosition'],
        'metadataRefreshedAt': refreshed_at,
    }
    stated_date = date_stated_in_title(entry['title'])
    if stated_date:
        result['dateStatedInTitle'] = stated_date
    return result


def sync(dry_run=False):
    now = utc_now()
    existing = read_existing()
    api_key = os.environ.get('YOUTUBE_API_KEY', '').strip()
    if not api_key:
        if existing and catalog_is_stale(existing, now):
            raise RuntimeError(
                'YOUTUBE_API_KEY is not set and the existing official YouTube catalog is older than 28 days'
            )
        print('YOUTUBE_API_KEY is not set; retaining the existing official YouTube catalog')
        return False

    playlist_id, channel_title = channel_details(api_key)
    entries = playlist_entries(api_key, playlist_id)
    records = [record(entry, channel_title, now.isoformat()) for entry in entries]
    if not records:
        raise RuntimeError('No public records were returned from the official YouTube uploads playlist')
    payload = {
        'channelId': CHANNEL_ID,
        'channelTitle': channel_title,
        'uploadsPlaylistId': playlist_id,
        'updated': now.isoformat(),
        'items': records,
    }
    if not dry_run:
        OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
    action = 'Would refresh' if dry_run else 'Refreshed'
    print(f'{action} {len(records)} public videos from the official YouTube uploads playlist')
    return True


if __name__ == '__main__':
    sync(dry_run='--dry-run' in sys.argv[1:])
