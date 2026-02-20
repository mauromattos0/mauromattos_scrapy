# mauromattos_scrapy

Scrapy project for scraping product data from Brazilian e-commerce sites. Uses **scrapy-poet** (Page Object pattern) and **scrapy-zyte-api** for structured, maintainable extraction. Currently supports [americanas.com.br](https://www.americanas.com.br).

## Features

- Page Object architecture — spiders are minimal, all extraction logic lives in dedicated Page Objects
- Extracts structured product data: name, price, brand, images, GTIN, breadcrumbs, availability, and more
- Primary extraction from JSON-LD (`<script type="application/ld+json">`), with fallbacks to meta tags and CSS selectors
- Regression tests via web-poet fixtures (saved HTML + expected JSON output)
- Flexible URL input: hardcoded defaults, comma-separated CLI argument, or file

## Setup

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Set the Zyte API key as an environment variable:

```bash
export ZYTE_API_KEY=your_key_here
```

## Usage

### Run the spider

```bash
# Default URLs
.venv/bin/scrapy crawl americanas_products_po -o products.json

# Custom URLs (comma-separated)
.venv/bin/scrapy crawl americanas_products_po -a urls="https://www.americanas.com.br/product1/p,https://www.americanas.com.br/product2/p" -o products.json

# URLs from a file (one per line, # for comments)
.venv/bin/scrapy crawl americanas_products_po -a urls_file=urls.txt -o products.json
```

### Run tests

```bash
.venv/bin/pytest fixtures/
```

## Project Structure

```
mauromattos_scrapy/
├── spiders/
│   └── americanas_products_po.py   # Spider — accepts URLs, delegates to Page Object
├── pages/
│   └── americanas_com_br.py        # Page Object — extracts all product fields
├── items.py                        # AmericanasProductItem (extends zyte_common_items.Product)
└── settings.py                     # Scrapy settings, addons config

fixtures/                           # Web-poet test fixtures
├── test-1/                         # Air conditioner product
├── test-2/                         # Smartphone product
└── test-3/                         # Sofa product
```

## Architecture

**Spiders** (`spiders/`) are thin entry points. They build the URL list and delegate all parsing to Page Objects via scrapy-poet dependency injection.

**Page Objects** (`pages/`) contain the extraction logic. Each Page Object is a `WebPage` subclass decorated with `@handle_urls` and defines `@field` methods for each product attribute. Fields return `Optional` types — `None` when data is unavailable, no exceptions raised.

**Items** (`items.py`) are thin subclasses of `zyte_common_items.Product`, providing a standardized product schema.

**Fixtures** (`fixtures/`) store saved HTML responses alongside expected JSON output for regression testing with pytest.

## Extracted Fields

| Field | Source |
|---|---|
| name | `og:title` meta tag, LD+JSON fallback |
| price | `product:price:amount` meta tag, LD+JSON Offer |
| currency | Meta tags (`product:price:currency`, `og:price:currency`) |
| brand | LD+JSON Product |
| availability | LD+JSON Offer (`InStock` / `OutOfStock`) |
| sku, productId | LD+JSON Product, URL pattern fallback |
| gtin | LD+JSON, validated with `zyte-parsers` |
| images | LD+JSON Product image array |
| description | LD+JSON Product, meta description fallback |
| breadcrumbs | LD+JSON BreadcrumbList |
| canonicalUrl | `og:url` meta tag, `<link rel="canonical">` fallback |

## Key Dependencies

- [Scrapy](https://scrapy.org/) — web scraping framework
- [scrapy-poet](https://github.com/scrapinghub/scrapy-poet) — Page Object pattern integration
- [scrapy-zyte-api](https://github.com/scrapy-plugins/scrapy-zyte-api) — Zyte Smart Proxy / API integration
- [zyte-common-items](https://github.com/zytedata/zyte-common-items) — standardized item schemas
- [web-poet](https://github.com/scrapinghub/web-poet) — Page Object base classes and fixture testing
