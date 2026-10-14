# yandex-seo — Yandex SEO for Claude Code

> **Not another Wordstat API client — a complete Yandex SEO workflow, from search demand to a P0/P1/P2 action plan.** Works without API keys.

[Русская версия](README.md) · [Real-site example (RU)](examples/shatinadesign-ru.md) · [Changelog](CHANGELOG.md)

Yandex is the leading search engine in Russia, yet popular SEO skills for coding agents target Google and AI search only. This plugin teaches Claude Code how SEO works in Yandex:

- **Wordstat** — volume operators (broad vs. `"exact"`), regions and, above all, **intent**: is the searcher a client or a consumer? (“сайт жк” has ~127k impressions, but those are apartment buyers, not developers who order websites.)
- **Yandex SERP analysis** — organic top-10 without ads in the target region, SERP features (Maps block, Yandex Services), what page type ranks.
- **Commercial factors** — the trust and business signals Yandex weighs for commercial queries.
- **Yandex Webmaster** — verification, sitemaps, region, site move (domain migration), recrawl, IKS; **IndexNow**.
- **Local search** — Yandex Business listings (service-area, no home address), Maps, 2GIS, marketplaces.
- **Yandex Neuro & Alice** — how pages become sources for Yandex AI answers.
- **Russian law** — personal data (152-FZ), cookie consent before Metrica, cross-border transfer.

It ships with a dependency-free Python checker (`yandex_tech_check.py`: mirrors and redirect chains, soft 404, robots.txt Clean-param/Host, sitemap sampling, meta, Schema.org, content visible without JavaScript, commercial signals, IndexNow key) and an IndexNow sender. Wordstat, SERP and Webmaster steps work through ready-made tasks for a browser agent (e.g. Claude in Chrome) — no OAuth needed. If you have a Yandex MCP server (e.g. [stufently/yandex-mcp](https://github.com/stufently/yandex-mcp)), the skill uses its data instead.

Tested on a live launch: mobile PageSpeed 24 → 95 in two days, soft 404s and JS-only navigation fixed.

## Install

```
/plugin marketplace add domovoy939/yandex-seo-skill
/plugin install yandex-seo@yandex-seo
```
or `npx skills add domovoy939/yandex-seo-skill`, or `git clone … && ./install.sh`.

## Commands

`/yandex demand` · `/yandex serp` · `/yandex commercial` · `/yandex tech` · `/yandex neuro` · `/yandex report` · `/yandex full`

The skill content is in Russian — it is meant for Russian-language sites and teams.

## License

MIT · Made by [Shatina Studio](https://shatinadesign.ru)
