from pathlib import Path

import scrapy

from mauromattos_scrapy.pages.americanas_com_br import AmericanasComBrAmericanasProductItemPage


class AmericanasProductsPageObjectSpider(scrapy.Spider):
    name = "americanas_products_po"
    allowed_domains = ["americanas.com.br"]
    default_start_urls = [
        "https://www.americanas.com.br/ar-condicionado-de-janela-hisense-8-500-btus-frio-aw-08cw2rvg-com-wifi-127v-u17i66490g842905/p",
        "https://www.americanas.com.br/smartphone-motorola-moto-g15-256gb-12gb-ram-boost-camera-50mp-com-ai-tela-6-7-nfc-verde-7513301760/p",
        "https://www.americanas.com.br/sofa-3-lugares-retratil-e-reclinavel-pascal-linho-cinza-7476291132/p",
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

    async def parse(self, response, page: AmericanasComBrAmericanasProductItemPage):
        yield await page.to_item()