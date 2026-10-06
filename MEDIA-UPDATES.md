# News and video updates

The Media page loads data/media.json. GitHub Actions checks the public feeds approximately every 48 hours and commits refreshed data; Cloudflare Pages automatically deploys each commit. Run the workflow manually to refresh sooner.

Sources: Google News exact-name results (including indexed YouTube coverage) and the official YouTube channel UCWBzJDiiXeg632cU3S3Ei7A. The public feeds cannot find every online mention. X's profile embed remains on the page; searching all X mentions is not configured. Additional news-channel feeds or an authenticated YouTube search integration can expand coverage.

To publish supplied information immediately, add an entry to data/manual-media.json on main:

```json
[{"title":"Interview title","url":"https://www.youtube.com/watch?v=VIDEO_ID","source":"News channel","published":"2026-10-06T09:00:00+00:00","type":"video","videoId":"VIDEO_ID"}]
```

Replace VIDEO_ID with an actual 11-character YouTube ID. For articles, omit videoId and use type news. A commit to manual-media.json triggers the refresh immediately. You can ask Codex to add links or information you provide; ordinary chat messages are not automatically read by GitHub.

The updater publishes titles, source links and permitted video embeds, rather than copying articles. Exact-name matches are required for search results. Official channel uploads are included directly. Older results survive temporary source failures. All-feed failure stops publishing rather than replacing data with an empty feed.

Schedule runs can be delayed by GitHub. Check Actions > Refresh news and videos for failures and Media page's last refreshed date.
