# News and video updates

The Media page is a static, source-linked archive generated from `data/media.json`. GitHub Actions refreshes public feeds daily, renders the archive into the homepage and Media page, and Cloudflare Pages deploys each commit. Run the workflow manually to refresh sooner. The archive is paginated into 24-record static pages when it exceeds one page; every generated page has its own canonical URL, navigation, `ItemList` markup and sitemap entry.

Only direct publisher, broadcaster or official-channel URLs are published in the archive. Google News links are retained separately in `data/media-candidates.json` as discovery signals and are not shown until a direct source URL is confirmed. This keeps the public archive attributable and avoids presenting Google redirect URLs as evidence.

Sources: Google News exact-name results (for discovery) and the official YouTube channel UCWBzJDiiXeg632cU3S3Ei7A. The public feeds cannot find every online mention. X's profile embed remains on the page; searching all X mentions is not configured. Additional news-channel feeds or an authenticated YouTube search integration can expand coverage.

To publish supplied information immediately, add an entry to data/manual-media.json on main:

```json
[{"title":"Interview title","displayTitle":"Manasvi Thapar on [Network]: [specific topic]","url":"https://www.youtube.com/watch?v=VIDEO_ID","source":"News channel","published":"2026-10-06T09:00:00+00:00","type":"video","videoId":"VIDEO_ID"}]
```

Replace VIDEO_ID with an actual 11-character YouTube ID. `displayTitle` is optional and should only be used when its topic is verified from the original source. For articles, omit videoId and use type news. A commit to manual-media.json triggers the refresh immediately. You can ask Codex to add links or information you provide; ordinary chat messages are not automatically read by GitHub.

The updater publishes titles and source links, rather than copying articles. Exact-name matches are required for search results. Official channel uploads are included directly and labelled as such, rather than being presented as broadcaster-hosted clips. Older results survive temporary source failures. All-feed failure stops publishing rather than replacing data with an empty feed.

Schedule runs can be delayed by GitHub. Check Actions > Refresh news and videos for failures and Media page's last refreshed date.

For the historical 1,000+ appearance backlog, use `data/media-corpus-template.csv` as the review sheet. Each row needs an original source URL and a human-verified title; it can then be imported with `python3 scripts/import_media_corpus.py path/to/approved.csv`. The importer accepts only reviewed rows, keeps the original link, and does not upload or copy broadcaster videos.

The official YouTube uploads collection is `https://www.youtube.com/playlist?list=UUWBzJDiiXeg632cU3S3Ei7A`. Its RSS feed covers only recent uploads. `scripts/sync_official_youtube.py` is a prepared, public-metadata-only full-channel importer. It resolves the channel's uploads playlist through the YouTube Data API, reads public videos only, and validates the exact official channel ID. It does not download, copy or re-upload video files.

The full API catalog is intentionally **not enabled** in the current GitHub commit-to-deploy workflow. YouTube's data policies require refresh or deletion of public API metadata within 30 days, while Git history cannot provide that deletion lifecycle. Before any `YOUTUBE_API_KEY` is created or used, the full-catalog build must run in a non-versioned deployment environment, use the `/privacy/` disclosure, show clear YouTube attribution, and have a documented refresh/delete process. `data/official-youtube.json` is ignored by Git for this reason. Do not add an API key to source code, a URL, a chat message or an ordinary repository variable.

For manually reviewed records, `appearanceDate` is reserved for a human-verified appearance date. A date found only in an official upload title is shown as “Date stated in video title,” never asserted as a broadcast date. Official YouTube cards are labelled “YouTube · Official channel upload”; they are not counted as independent broadcaster coverage.
