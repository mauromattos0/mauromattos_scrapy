from pathlib import Path

import scrapy

from mauromattos_scrapy.pages.macmagazine_com_br import MacmagazineComBrArticlePage


class MacmagazineArticlesPageObjectSpider(scrapy.Spider):
    name = "macmagazine_articles_po"
    allowed_domains = ["macmagazine.com.br"]
    default_start_urls = [
        "https://macmagazine.com.br/post/2026/02/26/instagram-alertara-pais-sobre-buscas-de-adolescentes-envolvendo-suicidio/",
        "https://macmagazine.com.br/post/2026/02/25/apple-pode-lancar-um-macbook-mais-barato-com-chip-a18-pro-em-2026/",
        "https://macmagazine.com.br/post/2026/02/25/mercado-brasileiro-de-futebol-eletroeafc-25-e-fifa-25/",
    ]

    def __init__(self, urls: str | None = None, urls_file: str | None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if urls:
            self.start_urls = [url.strip() for url in urls.split(",") if url.strip()]
        elif urls_file:
            file_path = Path(urls_file)
            if not file_path.is_absolute():
                file_path = Path.cwd() / file_path
            if not file_path.exists():
                raise ValueError(f"urls_file not found: {file_path}")
            file_urls = [line.strip() for line in file_path.read_text(encoding="utf-8").splitlines()]
            self.start_urls = [line for line in file_urls if line and not line.startswith("#")]
            if not self.start_urls:
                raise ValueError(f"urls_file has no valid URLs: {file_path}")
        else:
            self.start_urls = list(self.default_start_urls)

    async def parse(self, response, page: MacmagazineComBrArticlePage):
        yield await page.to_item()