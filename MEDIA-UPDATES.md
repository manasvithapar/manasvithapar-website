# News and video updates

The Media page is a static, source-linked archive generated from `data/media.json`. GitHub Actions refreshes public feeds daily, renders the archive into the homepage and Media page, and Cloudflare Pages deploys each commit. Run the workflow manually to refresh sooner. The archive is paginated into 24-record static pages when it exceeds one page; every generated page has its own canonical URL, navigation, `ItemList` markup and sitemap entry.

Only direct publisher, broadcaster or official-channel URLs are published in the archive. Google News links are retained separately in `data/media-candidates.json` as discovery signals and are not shown until a direct source URL is confirmed. This keeps the public archive attributable and avoids presenting Google redirect URLs as evidence.

Sources: Google News exact-name results (for discovery) and the official YouTube channel UCWBzJDiiXeg632cU3S3Ei7A. The public feeds cannot find every online mention. X's profile embed remains on the page; searching all X mentions is not configured. Additional news-channel feeds or an authenticated YouTube search integration can expand coverage.

To publish supplied information immediately, add an entry to data/manual-media.json on main:

```json
[{"title":"Interview title","displayTitle":"Manasvi Thapar on [Network]: [specific topic]","url":"https://www.youtube.com/watch?v=VIDEO_ID","source":"News channel","published":"2026-10-06T09:00:00+00:00","type":"video","sourceClass":"broadcaster_upload","videoId":"VIDEO_ID","reviewedOn":"2026-11-06"}]
```

Replace VIDEO_ID with an actual 11-character YouTube ID. `displayTitle` is optional and should only be used when its topic is verified from the original source. Use `broadcaster_upload` only for a direct upload on the broadcaster's own channel or site. For articles, omit videoId and use type news with the appropriate source class. A commit to manual-media.json triggers the refresh immediately. You can ask Codex to add links or information you provide; ordinary chat messages are not automatically read by GitHub.

The updater publishes titles and source links, rather than copying articles. Exact-name matches are required for search results. Official channel uploads are included directly and labelled as such, rather than being presented as broadcaster-hosted clips. Older results survive temporary source failures. All-feed failure stops publishing rather than replacing data with an empty feed.

Schedule runs can be delayed by GitHub. Check Actions > Refresh news and videos for failures and Media page's last refreshed date.

For the historical 1,000+ appearance backlog, use `data/media-corpus-template.csv` as the review sheet. Each row needs an original source URL and a human-verified title; it can then be imported with `python3 scripts/import_media_corpus.py path/to/approved.csv`. The importer accepts only reviewed rows, keeps the original link, and does not upload or copy broadcaster videos.

## Coverage-review workflow

Discovery candidates are not evidence. To turn a Google News lead into a public record, export a local reviewer queue first:

```text
python3 scripts/export_media_review_queue.py /safe/local/path/media-review.csv
```

The queue includes the discovery title and URL only as a lead. Before a row can be imported, a reviewer must replace it with a direct original-source URL, select a source class, add an ISO `reviewed_on` date and reviewer, and set `reviewed=yes`. The importer rejects Google/News redirect URLs, unreviewed rows, invalid dates and official archives that do not identify the original broadcaster.

Use these source classes consistently:

- `publisher_hosted` — original publisher-hosted reporting or interview page.
- `broadcaster_upload` — the broadcaster's own video upload.
- `official_archive` — a Manasvi Thapar official-channel archive of a named broadcaster appearance.
- `institutional_record` — university, company, regulator or other institutional record.
- `event_organiser` — conference or event organiser record.

The live Media page exposes those distinctions, including programme and original-broadcaster details when the reviewer has supplied them. A date in a video title is not an appearance date unless independently reviewed.

The official YouTube uploads collection is `https://www.youtube.com/playlist?list=UUWBzJDiiXeg632cU3S3Ei7A`. Its RSS feed covers only recent uploads. `scripts/sync_official_youtube.py` is a prepared, public-metadata-only full-channel importer. It resolves the channel's uploads playlist through the YouTube Data API, reads public videos only, and validates the exact official channel ID. It does not download, copy or re-upload video files.

The full API catalog is intentionally **not enabled** in the current GitHub commit-to-deploy workflow. YouTube's data policies require refresh or deletion of public API metadata within 30 days, while Git history cannot provide that deletion lifecycle. Before any `YOUTUBE_API_KEY` is created or used, the full-catalog build must run in a non-versioned deployment environment, use the `/privacy/` disclosure, show clear YouTube attribution, and have a documented refresh/delete process. `data/official-youtube.json` is ignored by Git for this reason. Do not add an API key to source code, a URL, a chat message or an ordinary repository variable.

For manually reviewed records, `appearanceDate` is reserved for a human-verified appearance date. A date found only in an official upload title is shown as “Date stated in video title,” never asserted as a broadcast date. Official YouTube cards are labelled “YouTube · Official channel upload”; they are not counted as independent broadcaster coverage.
