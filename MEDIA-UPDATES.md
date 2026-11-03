# News and video updates

The Media page is a static, source-linked archive generated from `data/media.json`. GitHub Actions refreshes public feeds daily, renders the archive into the homepage and Media page, and Cloudflare Pages deploys each commit. Run the workflow manually to refresh sooner.

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

The official YouTube uploads collection is `https://www.youtube.com/playlist?list=UUWBzJDiiXeg632cU3S3Ei7A`. Its RSS feed covers only recent uploads. A future full-channel import should use a restricted `YOUTUBE_API_KEY` in GitHub Actions to read the public uploads playlist; never commit an API key or treat YouTube upload dates as broadcast dates.
