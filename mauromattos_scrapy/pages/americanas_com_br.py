import html
import json
import re
from typing import Dict, List, Optional

from html_text import extract_text
from zyte_parsers.gtin import extract_gtin

from mauromattos_scrapy.items import AmericanasProductItem
from web_poet import Returns, WebPage, field, handle_urls


@handle_urls("americanas.com.br")
class AmericanasComBrAmericanasProductItemPage(WebPage, Returns[AmericanasProductItem]):
    @field
    def url(self) -> str:
        return str(self.response.url)

    @field
    def availability(self) -> Optional[str]:
        scripts = self.css('script[type="application/ld+json"]::text').getall()
        found = set()
        for text in scripts:
            if not text:
                continue
            try:
                data = json.loads(text)
            except ValueError:
                continue
            entries = data if isinstance(data, list) else [data]
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                if entry.get("@type") == "Offer":
                    offers_list = [entry]
                else:
                    offers = entry.get("offers")
                    if offers is None:
                        continue
                    offers_list = offers if isinstance(offers, list) else [offers]
                for offer in offers_list:
                    if not isinstance(offer, dict):
                        continue
                    avail = offer.get("availability")
                    if not isinstance(avail, str):
                        continue
                    label = avail.rsplit("/", 1)[-1]
                    if label in ("InStock", "OutOfStock"):
                        found.add(label)
        if "InStock" in found:
            return "InStock"
        if "OutOfStock" in found:
            return "OutOfStock"
        return None

    @field
    def brand(self) -> Optional[dict]:
        scripts = self.css('script[type="application/ld+json"]::text').getall()
        parsed: list[dict] = []
        for text in scripts:
            if not text:
                continue
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(data, list):
                parsed.extend([d for d in data if isinstance(d, dict)])
            elif isinstance(data, dict):
                parsed.append(data)

        def _get_brand_from_obj(obj: dict) -> Optional[str]:
            brand = obj.get("brand")
            if isinstance(brand, str):
                name = brand.strip()
                return name or None
            if isinstance(brand, dict):
                name = brand.get("name")
                if isinstance(name, str) and name.strip():
                    return name.strip()
            return None

        for obj in parsed:
            obj_type = obj.get("@type")
            types = obj_type if isinstance(obj_type, list) else [obj_type] if obj_type is not None else []
            if any(isinstance(type_name, str) and type_name.lower() == "product" for type_name in types):
                name = _get_brand_from_obj(obj)
                if name:
                    return {"name": name}

        for obj in parsed:
            name = _get_brand_from_obj(obj)
            if name:
                return {"name": name}

        return None

    @field
    def breadcrumbs(self) -> Optional[List[Dict[str, Optional[str]]]]:
        scripts = self.css('script[type="application/ld+json"]::text').getall()
        for text in scripts:
            try:
                data = json.loads(text)
            except (json.JSONDecodeError, TypeError):
                continue
            entries = data if isinstance(data, list) else [data]
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                obj_type = entry.get("@type") or entry.get("type")
                if obj_type != "BreadcrumbList":
                    continue
                items = entry.get("itemListElement") or entry.get("itemListElements") or []
                if not isinstance(items, list):
                    continue
                try:
                    items_sorted = sorted(items, key=lambda item: int(item.get("position", 0)))
                except Exception:
                    items_sorted = items
                result: List[Dict[str, Optional[str]]] = []
                for elem in items_sorted:
                    if not isinstance(elem, dict):
                        continue
                    name = elem.get("name")
                    if isinstance(name, str):
                        name = html.unescape(name)
                    url = elem.get("item")
                    if isinstance(url, dict):
                        url = url.get("@id") or url.get("id")
                    if url:
                        try:
                            url = self.urljoin(url)
                        except Exception:
                            pass
                    result.append({"name": name if name is not None else None, "url": url if url is not None else None})
                if result:
                    return result
        return None

    @field
    def canonicalUrl(self) -> Optional[str]:
        og_url = self.css('meta[property="og:url"]::attr(content)').get()
        if og_url:
            return self.urljoin(og_url)
        canonical_href = self.css('link[rel="canonical"]::attr(href)').get()
        if canonical_href:
            return self.urljoin(canonical_href)
        return str(self.response.url) or None

    @field
    def currency(self) -> Optional[str]:
        currency = self.css('meta[property="product:price:currency"]::attr(content)').get()
        if not currency:
            currency = self.css('meta[itemprop="priceCurrency"]::attr(content)').get()
        if not currency:
            return None
        currency = currency.strip()
        return currency if currency else None

    @field
    def currencyRaw(self) -> Optional[str]:
        value = self.css('meta[property="product:price:currency"]::attr(content)').get()
        if not value:
            value = self.css('meta[itemprop="priceCurrency"]::attr(content)').get()
        if not value:
            value = self.css('meta[name="currency"]::attr(content)').get()
        if not value:
            return None
        value = value.strip()
        return value if value and value != "-" else None

    @field
    def description(self) -> Optional[str]:
        ld_texts = self.css('script[type="application/ld+json"]::text').getall()
        for ld in ld_texts:
            if not ld:
                continue
            try:
                parsed = json.loads(ld)
            except (json.JSONDecodeError, TypeError):
                continue
            entries = parsed if isinstance(parsed, list) else [parsed]
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                obj_type = entry.get("@type")
                if (isinstance(obj_type, str) and obj_type.lower() == "product") or (
                    isinstance(obj_type, (list, tuple))
                    and any(isinstance(type_name, str) and type_name.lower() == "product" for type_name in obj_type)
                ):
                    desc = entry.get("description")
                    if desc:
                        out = extract_text(str(desc)).strip()
                        if out:
                            return out

        meta_desc = self.css('meta[name="description"]::attr(content)').get()
        if meta_desc:
            out = extract_text(meta_desc).strip()
            if out:
                return out
        og_desc = self.css('meta[property="og:description"]::attr(content)').get()
        if og_desc:
            out = extract_text(og_desc).strip()
            if out:
                return out
        return None

    @field
    def gtin(self) -> Optional[List[Dict[str, str]]]:
        scripts = self.css('script[type="application/ld+json"]::text').getall()

        def _find_gtin(node):
            if isinstance(node, dict):
                if node.get("gtin"):
                    return node.get("gtin")
                for value in node.values():
                    found = _find_gtin(value)
                    if found:
                        return found
            elif isinstance(node, list):
                for item in node:
                    found = _find_gtin(item)
                    if found:
                        return found
            return None

        for script_text in scripts:
            try:
                data = json.loads(script_text)
            except json.JSONDecodeError:
                continue
            candidate = _find_gtin(data)
            if candidate:
                gtin_obj = extract_gtin(str(candidate))
                if gtin_obj:
                    return [{"type": gtin_obj.type, "value": gtin_obj.value}]
        return None

    @field
    def images(self) -> Optional[List[Dict[str, str]]]:
        scripts = self.css('script[type="application/ld+json"]::text').getall()
        for text in scripts:
            try:
                data = json.loads(text)
            except (json.JSONDecodeError, TypeError):
                continue
            entries = data if isinstance(data, list) else [data]
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                image_data = entry.get("image")
                if not image_data:
                    continue
                urls = image_data if isinstance(image_data, list) else [image_data]
                result = []
                for value in urls:
                    if not isinstance(value, str):
                        continue
                    clean = html.unescape(value).strip()
                    if not clean:
                        continue
                    result.append({"url": self.urljoin(clean)})
                if result:
                    return result
        return None

    @field
    def mainImage(self) -> Optional[dict]:
        image_list = self.images
        if image_list:
            return image_list[0]
        img = self.css('meta[property="og:image"]::attr(content)').get()
        if not img:
            return None
        img = html.unescape(img).strip()
        if not img or img.lower().startswith("data:"):
            return None
        return {"url": self.urljoin(img)}

    @field
    def name(self) -> Optional[str]:
        og_title = self.css('meta[property="og:title"]::attr(content)').get()
        if og_title:
            value = extract_text(og_title).strip()
            if value:
                return value

        scripts = self.css('script[type="application/ld+json"]::text').getall()
        for text in scripts:
            try:
                data = json.loads(text)
            except (json.JSONDecodeError, TypeError):
                continue
            entries = data if isinstance(data, list) else [data]
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                name = entry.get("name")
                if isinstance(name, str) and name.strip():
                    return name.strip()
        return None

    @field
    def price(self) -> Optional[str]:
        price = self.css('meta[property="product:price:amount"]::attr(content)').get()
        if price:
            parsed = price.strip()
            if "," in parsed and "." not in parsed:
                parsed = parsed.replace(",", ".")
            return parsed

        scripts = self.css('script[type="application/ld+json"]::text').getall()
        for script in scripts:
            try:
                data = json.loads(script)
            except json.JSONDecodeError:
                continue
            entries = data if isinstance(data, list) else [data]
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                offers = entry.get("offers")
                if not offers:
                    continue
                offers_list = offers if isinstance(offers, list) else [offers]
                for offer in offers_list:
                    if not isinstance(offer, dict):
                        continue
                    price_val = offer.get("price")
                    if price_val is not None:
                        parsed = str(price_val).strip()
                        if "," in parsed and "." not in parsed:
                            parsed = parsed.replace(",", ".")
                        return parsed
        return None

    @field
    def productId(self) -> Optional[str]:
        sku = self.sku
        if sku:
            return sku
        og_url = self.css('meta[property="og:url"]::attr(content)').get() or ""
        if og_url:
            match = re.search(r"-(\d+)/p/?$", og_url)
            if match:
                return match.group(1)
        return None

    @field
    def sku(self) -> Optional[str]:
        scripts = self.css('script[type="application/ld+json"]::text').getall()
        for script in scripts:
            if not script:
                continue
            try:
                data = json.loads(script)
            except (json.JSONDecodeError, TypeError):
                continue

            candidates = data if isinstance(data, list) else [data]
            queue = list(candidates)
            while queue:
                entry = queue.pop(0)
                if not isinstance(entry, dict):
                    continue
                graph = entry.get("@graph")
                if isinstance(graph, list):
                    queue.extend(graph)
                if entry.get("@type") == "Product":
                    sku_val = entry.get("sku")
                    if isinstance(sku_val, (str, int)):
                        return str(sku_val)
        return None
