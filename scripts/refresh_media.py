"""Refresh public, attributed coverage without copying articles."""
import datetime as dt
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
PUBLISHED = DATA / 'media.json'
CANDIDATES = DATA / 'media-candidates.json'
OFFICIAL_YOUTUBE = DATA / 'official-youtube.json'
NAME = re.compile(r'manasvi\s+(?:m\.?\s+)?thapar|मानस्वी\s+थापर|मनस्वी\s+थापर', re.I)
GOOGLE_DISCOVERY_HOSTS = {'news.google.com', 'www.google.com'}

def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'ManasviThaparWebsite/1.0'})
    with urllib.request.urlopen(request, timeout=30) as response:
        return ET.fromstring(response.read())

def valid_url(url):
    if not isinstance(url, str):
        return False
    parsed = urlsplit(url)
    return parsed.scheme == 'https' and bool(parsed.netloc)

def discovery_url(url):
    return (urlsplit(url).hostname or '').lower() in GOOGLE_DISCOVERY_HOSTS


def canonical_url(url):
    """Create stable deduplication keys without changing the public source URL."""
    parsed = urlsplit(url)
    host = (parsed.hostname or '').lower()
    params = parse_qsl(parsed.query, keep_blank_values=True)
    if host in {'youtube.com', 'www.youtube.com', 'm.youtube.com'} and parsed.path == '/watch':
        params = [(key, value) for key, value in params if key == 'v']
    else:
        params = [(key, value) for key, value in params if not key.lower().startswith('utm_')]
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path, urlencode(params), ''))


def youtube_video_id(url):
    parsed = urlsplit(url)
    host = (parsed.hostname or '').lower()
    if host in {'youtube.com', 'www.youtube.com', 'm.youtube.com'}:
        if parsed.path == '/watch':
            return dict(parse_qsl(parsed.query)).get('v', '')
        parts = [part for part in parsed.path.split('/') if part]
        if len(parts) >= 2 and parts[0] in {'shorts', 'live'}:
            return parts[1]
    if host == 'youtu.be':
        return parsed.path.strip('/').split('/')[0]
    return ''


def record_key(item):
    video = item.get('videoId') or youtube_video_id(item.get('url', ''))
    if isinstance(video, str) and re.fullmatch(r'[A-Za-z0-9_-]{11}', video):
        return f'youtube:{video}'
    return canonical_url(item['url'])


def publishable(item):
    return (
        valid_url(item.get('url'))
        and not discovery_url(item['url'])
        and item.get('type') in {'news', 'video'}
        and bool(item.get('title'))
        and bool(item.get('source'))
    )

def read_json(path, fallback):
    return json.loads(path.read_text()) if path.exists() else fallback


def refresh(offline=False):
    old = read_json(PUBLISHED, {'items': []})
    old_candidates = read_json(CANDIDATES, {'items': []})
    official_youtube = read_json(OFFICIAL_YOUTUBE, {'items': []})
    catalog_items = official_youtube.get('items', [])
    catalog_available = (
        official_youtube.get('channelId') == 'UCWBzJDiiXeg632cU3S3Ei7A'
        and isinstance(catalog_items, list)
    )
    manual = json.loads((DATA / 'manual-media.json').read_text())
    social_urls = {
        canonical_url(item['url'])
        for item in manual
        if item.get('type') == 'social' and valid_url(item.get('url'))
    }
    items = {
        record_key(item): item
        for item in old.get('items', [])
        if (
            publishable(item)
            and canonical_url(item['url']) not in social_urls
            and not item.get('manual')
            # A successful full YouTube catalog is authoritative for API-managed uploads.
            # Manual records remain eligible below and take final precedence.
            and not (catalog_available and item.get('managedBy') == 'youtube-data-api')
        )
    }
    candidate_records = [*old_candidates.get('items', []), *old.get('items', [])]
    candidates = {
        canonical_url(item['url']): {**item, 'discoveryOnly': True}
        for item in candidate_records
        if valid_url(item.get('url')) and discovery_url(item['url'])
    }
    successful = list(old.get('sourcesChecked', [])) if offline else []
    failures = list(old.get('sourceErrors', [])) if offline else []
    feeds = [
        ('news', 'https://news.google.com/rss/search?q=%22Manasvi%20Thapar%22&hl=en-IN&gl=IN&ceid=IN:en'),
        ('news', 'https://news.google.com/rss/search?q=%22Manasvi%20Thapar%22%20site%3Ayoutube.com&hl=en-IN&gl=IN&ceid=IN:en'),
        ('official', 'https://www.youtube.com/feeds/videos.xml?channel_id=UCWBzJDiiXeg632cU3S3Ei7A'),
    ]
    atom = {'a': 'http://www.w3.org/2005/Atom', 'yt': 'http://www.youtube.com/xml/schemas/2015'}
    for kind, url in ([] if offline else feeds):
        try:
            root = fetch(url)
            entries = root.findall('.//item') if kind == 'news' else root.findall('a:entry', atom)
            for entry in entries:
                if kind == 'news':
                    title = entry.findtext('title', '')
                    if not NAME.search(title):
                        continue
                    link = entry.findtext('link', '')
                    source = entry.findtext('source', 'News coverage')
                    raw_date = entry.findtext('pubDate', '')
                    from email.utils import parsedate_to_datetime
                    published = parsedate_to_datetime(raw_date).isoformat() if raw_date else ''
                    item = {'title': title, 'url': link, 'source': source, 'published': published, 'type': 'news'}
                    if discovery_url(link):
                        item['discoveryOnly'] = True
                        item['lastSeen'] = dt.datetime.now(dt.timezone.utc).isoformat()
                        candidates[canonical_url(link)] = item
                        continue
                else:
                    video = entry.findtext('yt:videoId', '', atom)
                    if not re.fullmatch(r'[A-Za-z0-9_-]{11}', video):
                        continue
                    item = {'title': entry.findtext('a:title', '', atom), 'url': 'https://www.youtube.com/watch?v=' + video,
                            'source': 'Official YouTube channel', 'published': entry.findtext('a:published', '', atom),
                            'type': 'video', 'videoId': video}
                if valid_url(item['url']):
                    items[record_key(item)] = item
            successful.append(url)
        except Exception as exc:
            failures.append({'feed': url, 'error': str(exc)[:300]})
    for item in catalog_items:
        if publishable(item):
            items[record_key(item)] = item
    for item in manual:
        if not valid_url(item.get('url')) or not item.get('title'):
            raise ValueError('Manual media requires a title and HTTPS URL')
        item = dict(item, manual=True)
        if publishable(item):
            items[record_key(item)] = item
    if not successful and not offline:
        raise RuntimeError('All feeds failed; existing published data retained: ' + str(failures))
    result = {
        'updated': old.get('updated') if offline else dt.datetime.now(dt.timezone.utc).isoformat(),
        'sourcesChecked': successful,
        'sourceErrors': failures,
        'items': sorted(items.values(), key=lambda x: x.get('published', ''), reverse=True),
    }
    candidate_result = {
        'updated': old_candidates.get('updated') if offline else dt.datetime.now(dt.timezone.utc).isoformat(),
        'items': sorted(candidates.values(), key=lambda x: x.get('published', ''), reverse=True)[:200],
    }
    DATA.mkdir(exist_ok=True)
    PUBLISHED.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    CANDIDATES.write_text(json.dumps(candidate_result, ensure_ascii=False, indent=2) + '\n')
    mode = 'offline migration' if offline else 'refresh'
    print(f"Saved {len(result['items'])} published records and {len(candidate_result['items'])} candidates; {mode}")

if __name__ == '__main__':
    refresh(offline='--offline' in sys.argv[1:])
