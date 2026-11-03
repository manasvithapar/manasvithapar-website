"""Render source-linked media cards into the static site for crawlers and visitors."""
import datetime as dt
import html
import json
import re
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / 'data' / 'media.json'
GOOGLE_DISCOVERY_HOSTS = {'news.google.com', 'www.google.com'}
PUBLISHED_TYPES = {'news', 'video'}
SECTIONS = (
    (ROOT / 'index.html', 'media-archive:home', 3),
    (ROOT / 'media' / 'index.html', 'media-archive:all', 30),
)
SCHEMA_SECTION = (ROOT / 'media' / 'index.html', 'media-archive:schema')


def direct_source(item):
    """Keep original-publisher and official-channel URLs; omit Google redirect URLs."""
    url = item.get('url', '')
    title = item.get('displayTitle') or item.get('title')
    source = item.get('source')
    try:
        host = urlparse(url).hostname or ''
    except (TypeError, ValueError):
        return False
    return bool(
        title
        and source
        and url.startswith('https://')
        and host.lower() not in GOOGLE_DISCOVERY_HOSTS
        and not item.get('discoveryOnly')
        and item.get('type') in PUBLISHED_TYPES
    )


def published_date(item):
    raw = item.get('published', '')
    if not raw:
        return None
    try:
        return dt.datetime.fromisoformat(raw.replace('Z', '+00:00')).date()
    except ValueError:
        return None


def sort_key(item):
    return published_date(item) or dt.date.min


def format_date(value):
    return f'{value.day} {value.strftime("%B %Y")}'


def appearance_date(item):
    """Use a date stated in an official-upload title without inventing a topic or date."""
    if item.get('source') != 'Official YouTube channel':
        return None
    match = re.search(r'\((\d{1,2})\.(\d{1,2})\.(\d{4})\)', str(item.get('title', '')))
    if not match:
        return None
    try:
        return dt.date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
    except ValueError:
        return None


def source_label(item):
    if item.get('source') == 'Official YouTube channel':
        return 'Official channel upload'
    return str(item['source'])


def card(item):
    title = html.escape(str(item.get('displayTitle') or item['title']), quote=True)
    source = html.escape(source_label(item), quote=True)
    url = html.escape(str(item['url']), quote=True)
    rendered = [
        '<article class="coverage-card">',
        f'<p class="eyebrow">{source}</p>',
        f'<h3><a href="{url}" target="_blank" rel="noopener noreferrer">{title}</a></h3>',
    ]
    date = appearance_date(item)
    if date:
        rendered.append(f'<time datetime="{date.isoformat()}">Appearance: {format_date(date)}</time>')
    else:
        date = published_date(item)
        if date:
            rendered.append(f'<time datetime="{date.isoformat()}">Published: {format_date(date)}</time>')
    rendered.append('</article>')
    return ''.join(rendered)


def replace_marked_section(path, marker, content):
    start = f'<!-- {marker}:start -->'
    end = f'<!-- {marker}:end -->'
    document = path.read_text()
    if document.count(start) != 1 or document.count(end) != 1:
        raise ValueError(f'Expected one {marker} marker pair in {path}')
    before, remainder = document.split(start, 1)
    _, after = remainder.split(end, 1)
    path.write_text(f'{before}{start}{content}{end}{after}')


def render_schema(items):
    entries = [
        {
            '@type': 'ListItem',
            'position': position,
            'url': item['url'],
            'name': item.get('displayTitle') or item['title'],
        }
        for position, item in enumerate(items, start=1)
    ]
    schema = {
        '@context': 'https://schema.org',
        '@type': 'CollectionPage',
        '@id': 'https://manasvithapar.com/media/#collection',
        'url': 'https://manasvithapar.com/media/',
        'name': 'Manasvi Thapar in the Media',
        'about': {'@id': 'https://manasvithapar.com/#person'},
        'mainEntity': {
            '@type': 'ItemList',
            'numberOfItems': len(entries),
            'itemListElement': entries,
        },
    }
    payload = json.dumps(schema, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    return f'<script type="application/ld+json">{payload}</script>'


def main():
    data = json.loads(DATA_PATH.read_text())
    records = sorted((item for item in data.get('items', []) if direct_source(item)), key=sort_key, reverse=True)
    if not records:
        raise RuntimeError('No direct publisher or official-channel records are available to render')
    for path, marker, limit in SECTIONS:
        replace_marked_section(path, marker, ''.join(card(item) for item in records[:limit]))
    path, marker = SCHEMA_SECTION
    replace_marked_section(path, marker, render_schema(records[:30]))
    print(f'Rendered {min(3, len(records))} homepage cards and {min(30, len(records))} archive cards')


if __name__ == '__main__':
    main()
