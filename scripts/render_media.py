"""Render a source-linked media archive into static, crawlable pages."""
import datetime as dt
import html
import json
import math
import re
import shutil
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / 'data' / 'media.json'
HOME_INDEX = ROOT / 'index.html'
MEDIA_INDEX = ROOT / 'media' / 'index.html'
SITEMAP = ROOT / 'sitemap.xml'
GENERATED_PAGES = MEDIA_INDEX.parent / 'page'
GENERATED_MARKER = '.media-archive-generated'
SITE_URL = 'https://manasvithapar.com'
MEDIA_URL = f'{SITE_URL}/media/'
GOOGLE_DISCOVERY_HOSTS = {'news.google.com', 'www.google.com'}
PUBLISHED_TYPES = {'news', 'video'}
HOME_LIMIT = 3
PAGE_SIZE = 24


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


def date_value(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        return dt.date.fromisoformat(value[:10])
    except ValueError:
        return None


def published_date(item):
    return date_value(item.get('published', ''))


def appearance_date(item):
    """Only display a human-verified appearance date, never one inferred from a title."""
    return date_value(item.get('appearanceDate', ''))


def stated_title_date(item):
    explicit = date_value(item.get('dateStatedInTitle', ''))
    if explicit:
        return explicit
    match = re.search(r'\((\d{1,2})\.(\d{1,2})\.(\d{4})\)', str(item.get('title', '')))
    if not match:
        return None
    try:
        return dt.date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
    except ValueError:
        return None


def sort_key(item):
    return (appearance_date(item) or published_date(item) or dt.date.min, str(item.get('url', '')))


def format_date(value):
    return f'{value.day} {value.strftime("%B %Y")}'


def source_label(item):
    if item.get('source') == 'Official YouTube channel':
        return 'YouTube · Official channel upload'
    return str(item['source'])


def card(item):
    title = html.escape(str(item.get('displayTitle') or item['title']), quote=True)
    source = html.escape(source_label(item), quote=True)
    url = html.escape(str(item['url']), quote=True)
    dates = []
    appearance = appearance_date(item)
    stated = stated_title_date(item)
    published = published_date(item)
    if appearance:
        dates.append(f'<time datetime="{appearance.isoformat()}">Appearance: {format_date(appearance)}</time>')
    if stated and stated != appearance:
        dates.append(
            f'<time datetime="{stated.isoformat()}">Date stated in video title: {format_date(stated)}</time>'
        )
    if published:
        label = 'Official upload' if item.get('source') == 'Official YouTube channel' else 'Published'
        dates.append(f'<time datetime="{published.isoformat()}">{label}: {format_date(published)}</time>')
    metadata = f'<div class="coverage-meta">{"".join(dates)}</div>' if dates else ''
    return ''.join((
        '<article class="coverage-card">',
        f'<p class="eyebrow">{source}</p>',
        f'<h3><a href="{url}" target="_blank" rel="noopener noreferrer">{title}</a></h3>',
        metadata,
        '</article>',
    ))


def replace_marked(document, marker, content):
    start = f'<!-- {marker}:start -->'
    end = f'<!-- {marker}:end -->'
    if document.count(start) != 1 or document.count(end) != 1:
        raise ValueError(f'Expected one {marker} marker pair')
    before, remainder = document.split(start, 1)
    _, after = remainder.split(end, 1)
    return f'{before}{start}{content}{end}{after}'


def archive_url(page_number):
    return MEDIA_URL if page_number == 1 else f'{MEDIA_URL}page/{page_number}/'


def archive_path(page_number):
    if page_number == 1:
        return MEDIA_INDEX
    return GENERATED_PAGES / str(page_number) / 'index.html'


def page_numbers(current, total):
    if total <= 9:
        return list(range(1, total + 1))
    visible = {1, total, current}
    visible.update(number for number in range(current - 2, current + 3) if 1 <= number <= total)
    ordered = sorted(visible)
    result = []
    previous = None
    for number in ordered:
        if previous is not None and number > previous + 1:
            result.append(None)
        result.append(number)
        previous = number
    return result


def pagination(page_number, total_pages):
    if total_pages <= 1:
        return ''
    links = []
    if page_number > 1:
        links.append(f'<a class="pagination-previous" href="{archive_url(page_number - 1)}" rel="prev">Previous</a>')
    for number in page_numbers(page_number, total_pages):
        if number is None:
            links.append('<span class="pagination-gap" aria-hidden="true">…</span>')
        elif number == page_number:
            links.append(f'<span class="pagination-current" aria-current="page">{number}</span>')
        else:
            links.append(f'<a href="{archive_url(number)}">{number}</a>')
    if page_number < total_pages:
        links.append(f'<a class="pagination-next" href="{archive_url(page_number + 1)}" rel="next">Next</a>')
    return ''.join((
        '<div class="media-pagination" role="navigation" aria-label="Media archive pages">',
        f'<p>Page {page_number} of {total_pages}</p>',
        f'<div class="media-pagination-links">{"".join(links)}</div>',
        '</div>',
    ))


def render_schema(items, page_number, total_pages):
    start = (page_number - 1) * PAGE_SIZE
    entries = [
        {
            '@type': 'ListItem',
            'position': start + position,
            'url': item['url'],
            'name': item.get('displayTitle') or item['title'],
        }
        for position, item in enumerate(items, start=1)
    ]
    url = archive_url(page_number)
    schema = {
        '@context': 'https://schema.org',
        '@type': 'CollectionPage',
        '@id': f'{url}#collection',
        'url': url,
        'name': 'Manasvi Thapar in the Media' if page_number == 1 else f'Manasvi Thapar in the Media — Page {page_number}',
        'description': 'Source-linked coverage and official-channel uploads featuring Manasvi Thapar.',
        'about': {'@id': f'{SITE_URL}/#person'},
        'mainEntity': {
            '@type': 'ItemList',
            'numberOfItems': len(entries),
            'itemListOrder': 'https://schema.org/ItemListOrderDescending',
            'itemListElement': entries,
        },
    }
    if page_number > 1:
        schema['isPartOf'] = {'@id': f'{MEDIA_URL}#collection'}
        schema['pagination'] = f'{page_number} of {total_pages}'
    payload = json.dumps(schema, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    return f'<script type="application/ld+json">{payload}</script>'


def replace_one(document, pattern, replacement, label):
    result, count = re.subn(pattern, replacement, document, count=1, flags=re.DOTALL)
    if count != 1:
        raise ValueError(f'Expected one {label} element in Media template')
    return result


def with_page_metadata(document, page_number, total_pages):
    url = archive_url(page_number)
    if page_number == 1:
        title = 'Manasvi Thapar in the Media | News, Interviews & Appearances'
        description = 'Selected news coverage, interviews and public appearances featuring Manasvi Thapar, with links to original publisher sources.'
    else:
        title = f'Manasvi Thapar in the Media — Page {page_number} | Source-linked appearances'
        description = f'Source-linked coverage and official-channel uploads featuring Manasvi Thapar — page {page_number} of {total_pages}.'
    escaped_title = html.escape(title, quote=True)
    escaped_description = html.escape(description, quote=True)
    document = replace_one(document, r'<title>.*?</title>', f'<title>{escaped_title}</title>', 'title')
    document = replace_one(
        document,
        r'(<meta name="description" content=")[^"]*(">)',
        rf'\1{escaped_description}\2',
        'description',
    )
    document = replace_one(
        document,
        r'(<meta property="og:title" content=")[^"]*(">)',
        rf'\1{escaped_title}\2',
        'Open Graph title',
    )
    document = replace_one(
        document,
        r'(<meta property="og:description" content=")[^"]*(">)',
        rf'\1{escaped_description}\2',
        'Open Graph description',
    )
    document = replace_one(
        document,
        r'(<meta property="og:url" content=")[^"]*(">)',
        rf'\1{url}\2',
        'Open Graph URL',
    )
    relation_links = ''
    if page_number > 1:
        relation_links += f'<link rel="prev" href="{archive_url(page_number - 1)}">'
    if page_number < total_pages:
        relation_links += f'<link rel="next" href="{archive_url(page_number + 1)}">'
    document = replace_one(
        document,
        r'<link rel="canonical" href="[^"]+">',
        f'<link rel="canonical" href="{url}">{relation_links}',
        'canonical URL',
    )
    return document


def feed_note():
    return (
        '<p class="feed-note">Links open the original publisher or official channel. '
        '“YouTube · Official channel upload” identifies a video hosted on Manasvi Thapar’s official YouTube channel; '
        'it is not presented as broadcaster-hosted coverage. Dates stated in video titles are not presented as broadcast dates. '
        '<a class="text-link" href="https://www.youtube.com/playlist?list=UUWBzJDiiXeg632cU3S3Ei7A" '
        'target="_blank" rel="noopener noreferrer">Browse the official video archive <span aria-hidden="true">↗</span></a></p>'
    )


def page_content(items, page_number, total_pages):
    return ''.join((
        '<section class="page-banner"><div class="wrap"><p class="eyebrow">MEDIA ARCHIVE</p>'
        '<h1>Source-linked appearances</h1>'
        '<p>Original publisher links and official-channel uploads, organised for reference.</p></div></section>',
        '<section class="wrap section" aria-labelledby="coverage-heading"><div class="section-head"><div>'
        '<p class="eyebrow">NEWS &amp; APPEARANCES</p><h2 id="coverage-heading">Source-linked coverage</h2>'
        '</div></div>',
        f'<p id="coverage-status" role="status">Archive page {page_number} of {total_pages}.</p>',
        f'<div id="latest-coverage" class="coverage-grid">{"".join(card(item) for item in items)}</div>',
        pagination(page_number, total_pages),
        feed_note(),
        '</section>',
    ))


def archive_shell(document):
    try:
        prefix, remainder = document.split('<main id="main">', 1)
        _, suffix = remainder.split('</main>', 1)
    except ValueError as error:
        raise ValueError('Expected a main element in Media template') from error
    return prefix, suffix


def render_root(document, records, total_pages):
    document = replace_marked(document, 'media-archive:all', ''.join(card(item) for item in records[:PAGE_SIZE]))
    document = replace_marked(document, 'media-archive:schema', render_schema(records[:PAGE_SIZE], 1, total_pages))
    document = replace_marked(document, 'media-archive:note', feed_note())
    document = replace_marked(document, 'media-archive:pagination', pagination(1, total_pages))
    return with_page_metadata(document, 1, total_pages)


def render_home(document, records):
    return replace_marked(document, 'media-archive:home', ''.join(card(item) for item in records[:HOME_LIMIT]))


def render_archive_page(base, records, page_number, total_pages):
    start = (page_number - 1) * PAGE_SIZE
    page_records = records[start:start + PAGE_SIZE]
    prefix, suffix = archive_shell(base)
    document = f'{prefix}<main id="main">{page_content(page_records, page_number, total_pages)}</main>{suffix}'
    document = replace_marked(document, 'media-archive:schema', render_schema(page_records, page_number, total_pages))
    return with_page_metadata(document, page_number, total_pages)


def write_page(page_number, document):
    path = archive_path(page_number)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(document)
    if page_number > 1:
        (path.parent / GENERATED_MARKER).write_text('Generated by scripts/render_media.py. Do not edit this directory.\n')


def remove_stale_pages(total_pages):
    if not GENERATED_PAGES.exists():
        return
    for path in GENERATED_PAGES.iterdir():
        if not path.is_dir() or not path.name.isdigit():
            continue
        page_number = int(path.name)
        if page_number <= total_pages or not (path / GENERATED_MARKER).exists():
            continue
        shutil.rmtree(path)
    try:
        GENERATED_PAGES.rmdir()
    except OSError:
        pass


def render_sitemap(total_pages):
    entries = ''.join(
        f'\n  <url>\n    <loc>{archive_url(page_number)}</loc>\n  </url>'
        for page_number in range(2, total_pages + 1)
    )
    SITEMAP.write_text(replace_marked(SITEMAP.read_text(), 'media-archive:pages', entries))


def main():
    data = json.loads(DATA_PATH.read_text())
    records = sorted(
        (item for item in data.get('items', []) if direct_source(item)),
        key=sort_key,
        reverse=True,
    )
    if not records:
        raise RuntimeError('No direct publisher or official-channel records are available to render')
    total_pages = math.ceil(len(records) / PAGE_SIZE)
    base = MEDIA_INDEX.read_text()
    HOME_INDEX.write_text(render_home(HOME_INDEX.read_text(), records))
    write_page(1, render_root(base, records, total_pages))
    for page_number in range(2, total_pages + 1):
        write_page(page_number, render_archive_page(base, records, page_number, total_pages))
    remove_stale_pages(total_pages)
    render_sitemap(total_pages)
    print(
        f'Rendered {min(HOME_LIMIT, len(records))} homepage cards and {len(records)} archive records '
        f'across {total_pages} static archive page(s)'
    )


if __name__ == '__main__':
    main()
