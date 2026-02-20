# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Scrapy project using **scrapy-poet** and **scrapy-zyte-api** to scrape product data from Brazilian e-commerce sites. Page Objects (in `mauromattos_scrapy/pages/`) parse HTML into `zyte-common-items` Product items. The spider delegates all extraction logic to these Page Objects.

## Commands

### Run a spider (default URLs)
```
.venv/bin/scrapy crawl americanas_products_po -o products.json
```

### Run a spider with custom URLs
```
.venv/bin/scrapy crawl americanas_products_po -a urls="https://example.com/p1,https://example.com/p2" -o out.json
.venv/bin/scrapy crawl americanas_products_po -a urls_file=urls.txt -o out.json
```

### Run page object tests (web-poet fixtures)
```
.venv/bin/pytest fixtures/
```

### Install dependencies
```
.venv/bin/pip install -r requirements.txt
```

## Architecture

- **Spiders** (`mauromattos_scrapy/spiders/`) — minimal; accept URLs via `-a urls=` or `-a urls_file=`, delegate parsing to Page Objects via scrapy-poet injection.
- **Page Objects** (`mauromattos_scrapy/pages/`) — `WebPage` subclasses decorated with `@handle_urls`. Each `@field` method extracts one product attribute from HTML (LD+JSON, meta tags, CSS selectors). Return `zyte-common-items` Product items.
- **Items** (`mauromattos_scrapy/items.py`) — thin subclasses of `zyte_common_items.Product`.
- **Fixtures** (`fixtures/`) — web-poet test fixtures: saved HTML responses + expected JSON output. Tested with `pytest` via web-poet's fixture testing support.
- **Settings** (`mauromattos_scrapy/settings.py`) — addons: `scrapy_poet.Addon` and `scrapy_zyte_api.Addon`; auto-discovers page objects from `mauromattos_scrapy.pages`.

## Key Patterns

- Page Objects extract data primarily from `<script type="application/ld+json">` blocks, falling back to `<meta>` tags and CSS selectors.
- Fields use `Optional` return types — return `None` when data is not found rather than raising.
- The `ZYTE_API_KEY` in settings.py should be moved to an environment variable before committing.
