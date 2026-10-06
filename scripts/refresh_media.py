"""Refresh public, attributed coverage without copying articles."""
import datetime as dt
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
NAME = re.compile(r'manasvi\s+(?:m\.?\s+)?thapar|मानस्वी\s+थापर|मनस्वी\s+थापर', re.I)

def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'ManasviThaparWebsite/1.0'})
    with urllib.request.urlopen(request, timeout=30) as response:
        return ET.fromstring(response.read())

def valid_url(url):
    return isinstance(url, str) and url.startswith('https://')

def refresh():
    old_path = DATA / 'media.json'
    old = json.loads(old_path.read_text()) if old_path.exists() else {'items': []}
    items = {x['url']: x for x in old.get('items', []) if valid_url(x.get('url'))}
    successful = []
    failures = []
    feeds = [
        ('news', 'https://news.google.com/rss/search?q=%22Manasvi%20Thapar%22&hl=en-IN&gl=IN&ceid=IN:en'),
        ('news', 'https://news.google.com/rss/search?q=%22Manasvi%20Thapar%22%20site%3Ayoutube.com&hl=en-IN&gl=IN&ceid=IN:en'),
        ('official', 'https://www.youtube.com/feeds/videos.xml?channel_id=UCWBzJDiiXeg632cU3S3Ei7A'),
    ]
    atom = {'a': 'http://www.w3.org/2005/Atom', 'yt': 'http://www.youtube.com/xml/schemas/2015'}
    for kind, url in feeds:
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
                else:
                    video = entry.findtext('yt:videoId', '', atom)
                    if not re.fullmatch(r'[A-Za-z0-9_-]{11}', video):
                        continue
                    item = {'title': entry.findtext('a:title', '', atom), 'url': 'https://www.youtube.com/watch?v=' + video,
                            'source': 'Official YouTube channel', 'published': entry.findtext('a:published', '', atom),
                            'type': 'video', 'videoId': video}
                if valid_url(item['url']):
                    items[item['url']] = item
            successful.append(url)
        except Exception as exc:
            failures.append({'feed': url, 'error': str(exc)[:300]})
    manual = json.loads((DATA / 'manual-media.json').read_text())
    for item in manual:
        if not valid_url(item.get('url')) or not item.get('title'):
            raise ValueError('Manual media requires a title and HTTPS URL')
        item = dict(item, manual=True)
        items[item['url']] = item
    if not successful:
        raise RuntimeError('All feeds failed; existing published data retained: ' + str(failures))
    result = {'updated': dt.datetime.now(dt.timezone.utc).isoformat(), 'sourcesChecked': successful,
              'sourceErrors': failures, 'items': sorted(items.values(), key=lambda x: x.get('published', ''), reverse=True)[:200]}
    DATA.mkdir(exist_ok=True)
    old_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(f"Saved {len(result['items'])} items; {len(successful)} feeds checked; {len(failures)} unavailable")

if __name__ == '__main__':
    refresh()
