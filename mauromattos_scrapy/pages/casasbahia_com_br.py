from typing import Optional, List, Dict
import html

from web_poet import Returns, WebPage, field, handle_urls
from zyte_common_items import ProductList


@handle_urls("casasbahia.com.br")
class CasasbahiaComBrProductListPage(WebPage, Returns[ProductList]):
    @field
    def url(self) -> Optional[str]:
        if not hasattr(self, "response") or self.response is None:
            return None
        page_url = getattr(self.response, "url", None)
        if not page_url:
            return None
        return str(page_url)

    @field
    def breadcrumbs(self) -> Optional[List[Dict[str, Optional[str]]]]:
        selector = 'div.dsvia-breadcrumb[data-testid="categorias-breadcrumb"] a'
        links = self.css(selector)
        if not links:
            links = self.css('div.dsvia-breadcrumb a')
        if not links:
            return None

        items: List[Dict[str, Optional[str]]] = []
        for link in links:
            text = link.css('::text').get()
            name = text.strip() if text and text.strip() else None

            href = link.attrib.get('href')
            if href:
                href = html.unescape(href)
                try:
                    href = self.urljoin(href)
                except Exception:
                    href = None

            items.append({"name": name, "url": href})

        return items if items else None

    @field
    def categoryName(self) -> Optional[str]:
        text = self.css('h1[class*="TermSearch"]::text').get()
        if not text:
            text = self.css('h1::text').get()
        if text:
            return text.strip()
        return None
