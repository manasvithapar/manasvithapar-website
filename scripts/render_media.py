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
SOURCE_CLASS_LABELS = {
    'publisher_hosted': 'Publisher-hosted coverage',
    'broadcaster_upload': 'Broadcaster upload',
    'official_archive': 'Official archive',
    'institutional_record': 'Institutional record',
    'event_organiser': 'Event-organiser record',
}
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
        broadcaster = str(item.get('originalBroadcaster', '')).strip()
        if item.get('sourceClass') == 'official_archive' and broadcaster:
            return f'YouTube · Official archive of a {broadcaster} appearance'
        return 'YouTube · Official channel upload'
    return str(item['source'])


def coverage_context(item):
    context = []
    source_class = item.get('sourceClass')
    if source_class in SOURCE_CLASS_LABELS:
        context.append(SOURCE_CLASS_LABELS[source_class])
    broadcaster = str(item.get('originalBroadcaster', '')).strip()
    if broadcaster and not (item.get('source') == 'Official YouTube channel' and source_class == 'official_archive'):
        context.append(f'Original broadcaster: {broadcaster}')
    programme = str(item.get('programme', '')).strip()
    if programme:
        context.append(f'Programme: {programme}')
    if not context:
        return ''
    return ''.join(f'<p class="coverage-context">{html.escape(value, quote=True)}</p>' for value in context)


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
    context = coverage_context(item)
    return ''.join((
        '<article class="coverage-card">',
        f'<p class="eyebrow">{source}</p>',
        f'<h3><a href="{url}" target="_blank" rel="noopener noreferrer">{title}</a></h3>',
        context,
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
        'description': 'Source-linked broadcaster, publisher, institutional and official-channel records featuring Manasvi Thapar.',
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
    document = document.replace(
        '<p>Lawyer. Entrepreneur. Public Speaker.<br>TEDx Speaker. Angel Investor. Mentor.</p>',
        '<p>Official website · source-linked public record.</p>',
    )
    url = archive_url(page_number)
    if page_number == 1:
        title = 'Manasvi Thapar in the Media | News, Interviews & Appearances'
        description = 'Selected broadcaster, publisher, institutional and official-channel records featuring Manasvi Thapar, with original-source links.'
    else:
        title = f'Manasvi Thapar in the Media — Page {page_number} | Source-linked appearances'
        description = (
            f'Source-linked broadcaster, publisher, institutional and official-channel records featuring Manasvi Thapar '
            f'— page {page_number} of {total_pages}.'
        )
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
    # A re-render must replace, rather than accumulate, pagination relationships.
    document = re.sub(r'<link rel="(?:prev|next)" href="[^"]+">', '', document)
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
    if '<link rel="stylesheet" href="/editorial.css">' not in document:
        document = replace_one(
            document,
            r'<link rel="stylesheet" href="/style.css">',
            '<link rel="stylesheet" href="/style.css"><link rel="stylesheet" href="/editorial.css">',
            'editorial stylesheet insertion point',
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
        '<p class="eyebrow">NEWS &amp; APPEARANCES</p><h2 id="coverage-heading">Source-linked records</h2>'
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


def media_context_body():
    """Keep the root archive's supporting context neutral and source-led."""
    return ''.join((
        '<section class="blue-section" aria-labelledby="record-context-heading"><div class="wrap section">',
        '<div class="section-head"><div><p class="eyebrow">PUBLIC RECORD</p>',
        '<h2 id="record-context-heading">Use the original record.</h2></div>',
        '<a class="text-link" href="/public-profile/">Open public profile <span aria-hidden="true">↗</span></a>',
        '</div><div class="initiative-grid">',
        '<a class="initiative" href="/public-profile/"><img src="/assets/924b106e10f7.jpeg" ',
        'alt="Portrait of Manasvi Thapar" loading="lazy" width="480" height="614"><div>',
        '<p class="eyebrow">Source-linked profile</p><h3>Roles and work</h3>',
        '<p>Read dated roles, talks and public-record statements alongside their original sources.</p>',
        '</div></a>',
        '<a class="initiative" href="/media/"><img src="/assets/4c9a7b8b7959.jpeg" ',
        'alt="Manasvi Thapar speaking at TEDxHLCC" loading="lazy" width="1193" height="1800"><div>',
        '<p class="eyebrow">Source archive</p><h3>Coverage and appearances</h3>',
        '<p>Browse broadcaster uploads, publisher coverage and institutional records by source type.</p>',
        '</div></a>',
        '<a class="initiative" href="/gallery/"><img src="/assets/03b6d9631bde.jpeg" ',
        'alt="Manasvi Thapar at a university engagement" loading="lazy" width="1600" height="1066"><div>',
        '<p class="eyebrow">Selected photographs</p><h3>A curated visual archive</h3>',
        '<p>Venue labels are used only where the supporting record is independently clear.</p>',
        '</div></a></div></div></section>',
    ))


def media_context():
    return f'<!-- media-archive:context:start -->{media_context_body()}<!-- media-archive:context:end -->'


def replace_media_context(document):
    marker = 'media-archive:context'
    if f'<!-- {marker}:start -->' in document:
        return replace_marked(document, marker, media_context_body())
    legacy_pattern = (
        r'<section class="blue-section"><div class="wrap section"><div class="section-head"><div>'
        r'<p class="eyebrow">PUBLIC SPEAKING</p>.*?</section>'
        r'(?=<section class="wrap section"><div class="section-head"><div><p class="eyebrow">LATEST TWEETS</p>)'
    )
    result, count = re.subn(legacy_pattern, media_context(), document, count=1, flags=re.DOTALL)
    if count != 1:
        raise ValueError('Expected one legacy public-speaking section in Media template')
    return result


def render_root(document, records, total_pages):
    document = replace_marked(document, 'media-archive:all', ''.join(card(item) for item in records[:PAGE_SIZE]))
    document = replace_marked(document, 'media-archive:schema', render_schema(records[:PAGE_SIZE], 1, total_pages))
    document = replace_marked(document, 'media-archive:note', feed_note())
    document = replace_marked(document, 'media-archive:pagination', pagination(1, total_pages))
    document = replace_media_context(document)
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
