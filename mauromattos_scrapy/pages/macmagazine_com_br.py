from typing import Optional, Any, List, Dict
import json
import re
import html
from urllib.parse import urlparse
import posixpath

from web_poet import Returns, WebPage, field, handle_urls
from zyte_common_items.items.article import Article
from extruct.jsonld import JsonLdExtractor
from parsel import Selector


def _extract_urls_from_srcset(srcset: str) -> List[str]:
    if not srcset:
        return []
    parts = [p.strip() for p in srcset.split(",") if p.strip()]
    urls = []
    for part in parts:
        tokens = part.split()
        if tokens:
            urls.append(tokens[0].strip())
    return urls


def _normalize_url(url: Optional[str], page) -> Optional[str]:
    if not url:
        return None
    u = html.unescape(url).strip()
    if not u or u.lower().startswith("data:"):
        return None
    try:
        return page.urljoin(u)
    except Exception:
        return None


def _group_key_from_url(url: str) -> str:
    parsed = urlparse(url)
    filename = posixpath.basename(parsed.path)
    filename_nosize = re.sub(r"-\d+x\d+(?=\.)", "", filename)
    key = filename_nosize.split(".", 1)[0]
    return key


@handle_urls("macmagazine.com.br")
class MacmagazineComBrArticlePage(WebPage, Returns[Article]):
    @field
    def url(self) -> str:
        return str(self.response.url)

    @field
    def headline(self) -> Optional[str]:
        title = self.css("h1.cs-entry__title span::text").get()
        if not title:
            title = self.css("h1.cs-entry__title::text").get()
        if not title:
            title = self.css("h1::text").get()
        if not title:
            title = self.css("title::text").get()
        if title:
            return title.strip()
        return None

    @field
    def datePublished(self) -> Optional[str]:
        meta_time = self.css('meta[property="article:published_time"]::attr(content)').get()
        if meta_time:
            return meta_time

        try:
            jslde = JsonLdExtractor()
            data = jslde.extract(self.response.body)
        except Exception:
            data = None

        if data:
            for entry in data:
                if not isinstance(entry, dict):
                    continue
                if entry.get("datePublished"):
                    return entry.get("datePublished")
                graph = entry.get("@graph")
                if isinstance(graph, list):
                    for g in graph:
                        if isinstance(g, dict) and g.get("datePublished"):
                            return g.get("datePublished")

        time_val = (
            self.css("time.post-date::attr(data-published)").get()
            or self.css("time.post-date::attr(datetime)").get()
        )
        if time_val:
            return time_val

        try:
            dm = getattr(self, "dateModified", None)
            if dm:
                return dm
        except Exception:
            pass

        return None

    @field
    def datePublishedRaw(self) -> Optional[str]:
        dt = self.css("time.post-date::attr(datetime)").get()
        if dt:
            return dt.strip()

        dt = self.css('meta[property="article:published_time"]::attr(content)').get()
        if dt:
            return dt.strip()

        scripts = self.css('script[type="application/ld+json"]::text').getall()
        for script in scripts:
            if not script:
                continue
            try:
                data = json.loads(script)
            except (json.JSONDecodeError, TypeError):
                continue

            candidates = []
            if isinstance(data, list):
                candidates.extend(data)
            elif isinstance(data, dict):
                candidates.append(data)
                graph = data.get("@graph")
                if isinstance(graph, list):
                    candidates.extend(graph)

            for entry in candidates:
                if not isinstance(entry, dict):
                    continue
                dp = entry.get("datePublished")
                if dp:
                    return dp.strip()

        return None

    @field
    def dateModified(self) -> Optional[str]:
        extractor = JsonLdExtractor()
        data = extractor.extract(self.response.body) or []
        for entry in data:
            if isinstance(entry, dict):
                dm = entry.get("dateModified")
                if isinstance(dm, str) and dm:
                    return dm
                graph = entry.get("@graph")
                if isinstance(graph, list):
                    for node in graph:
                        if isinstance(node, dict):
                            dm2 = node.get("dateModified")
                            if isinstance(dm2, str) and dm2:
                                return dm2
        meta = self.css('meta[property="article:modified_time"]::attr(content)').get()
        if meta:
            return meta
        og = self.css('meta[property="og:updated_time"]::attr(content)').get()
        if og:
            return og
        return None

    @field
    def dateModifiedRaw(self) -> Optional[str]:
        meta = self.css('meta[property="article:modified_time"]::attr(content)').get()
        if meta:
            meta = meta.strip()
            if meta:
                return meta

        scripts = self.css('script[type="application/ld+json"]::text').getall()
        for script in scripts:
            if not script or not script.strip():
                continue
            try:
                data = json.loads(script)
            except json.JSONDecodeError:
                continue

            def _find_date(obj):
                if isinstance(obj, dict):
                    if obj.get("dateModified"):
                        return obj.get("dateModified")
                    graph = obj.get("@graph")
                    if isinstance(graph, list):
                        for item in graph:
                            result = _find_date(item)
                            if result:
                                return result
                elif isinstance(obj, list):
                    for item in obj:
                        result = _find_date(item)
                        if result:
                            return result
                return None

            date = _find_date(data)
            if date:
                return date.strip() if isinstance(date, str) else None

        return None

    @field
    def authors(self) -> Optional[List[Dict]]:
        def _clean(text: Optional[str]) -> Optional[str]:
            if not text:
                return None
            text = text.strip()
            return text or None

        primary_selectors = [
            ".cs-entry__author .cs-entry__author-name",
            ".cs-meta-author a.cs-meta-author-inner",
            ".cs-meta-author a",
        ]

        authors: List[Dict] = []
        seen = set()
        for sel in primary_selectors:
            elems = self.css(sel)
            if not elems:
                continue
            for el in elems:
                href = el.attrib.get("href") if el.attrib and "href" in el.attrib else el.xpath("@href").get()
                author_url = self.urljoin(href) if href else None
                name_raw = el.xpath("string()").get()
                name_raw = _clean(name_raw)
                name = name_raw
                key = (author_url, name)
                if key in seen:
                    continue
                seen.add(key)
                authors.append({"email": None, "url": author_url, "name": name, "nameRaw": name_raw})
            if authors:
                return authors

        meta_author = self.css('meta[name="author"]::attr(content)').get()
        if meta_author:
            name_raw = _clean(meta_author)
            return [{"email": None, "url": None, "name": name_raw, "nameRaw": name_raw}]

        return None

    @field
    def breadcrumbs(self) -> Optional[List[Dict[str, Optional[str]]]]:
        scripts = self.css('script[type="application/ld+json"]::text').getall()
        if not scripts:
            return None

        def _extract_from_obj(obj):
            results: List[Dict[str, Optional[str]]] = []

            def _search(node):
                if isinstance(node, dict):
                    t = node.get("@type") or node.get("type")
                    if isinstance(t, str) and t.lower() == "breadcrumblist" or (
                        isinstance(t, list) and "BreadcrumbList" in t
                    ):
                        items = node.get("itemListElement") or node.get("itemList")
                        if isinstance(items, list):
                            for item in items:
                                if not isinstance(item, dict):
                                    continue
                                name = item.get("name")
                                url = item.get("item") or item.get("url")
                                if isinstance(url, dict):
                                    url = url.get("@id") or url.get("url")
                                results.append(
                                    {"name": name if name is not None else None,
                                     "url": str(url) if url is not None else None}
                                )
                            return True
                    for v in node.values():
                        _search(v)
                elif isinstance(node, list):
                    for el in node:
                        _search(el)
                return False

            _search(obj)
            return results

        for text in scripts:
            try:
                data = json.loads(text)
            except Exception:
                continue
            found = _extract_from_obj(data)
            if found:
                return found

        return None

    @field
    def inLanguage(self) -> Optional[str]:
        def _find_in_language(obj: Any) -> Optional[str]:
            if isinstance(obj, dict):
                if "inLanguage" in obj and isinstance(obj["inLanguage"], str):
                    return obj["inLanguage"]
                for v in obj.values():
                    res = _find_in_language(v)
                    if res:
                        return res
            elif isinstance(obj, list):
                for item in obj:
                    res = _find_in_language(item)
                    if res:
                        return res
            return None

        try:
            extractor = JsonLdExtractor()
            data = extractor.extract(self.response.body)
            lang = _find_in_language(data)
        except Exception:
            lang = None

        if not lang:
            og_locale = self.css('meta[property="og:locale"]::attr(content)').get()
            if og_locale:
                lang = og_locale

        if not lang:
            html_lang = self.css("html::attr(lang)").get()
            if html_lang:
                lang = html_lang

        if not lang:
            return None

        if isinstance(lang, str):
            normalized = lang.lower().replace("_", "-").split("-", 1)[0].strip()
            return normalized or None

        return None

    @field
    def mainImage(self) -> Optional[Dict[str, str]]:
        content = self.css('meta[property="og:image"]::attr(content)').get()
        if not content:
            return None
        content = html.unescape(content).strip()
        if not content or content.lower().startswith("data:"):
            return None
        return {"url": self.urljoin(content)}

    @field
    def images(self) -> Optional[List[Dict[str, str]]]:
        selectors = (
            "picture source, picture img, "
            "figure.cs-entry__post-media source, figure.cs-entry__post-media img, "
            "figure.wp-block-image source, figure.wp-block-image img, "
            ".entry-content source, .entry-content img"
        )
        elems = self.css(selectors)
        groups: Dict[str, Dict[str, List[str]]] = {}
        order: List[str] = []

        def add_candidate(raw_url: Optional[str]):
            final = _normalize_url(raw_url, self)
            if not final:
                return
            key = _group_key_from_url(final)
            if key not in groups:
                groups[key] = {}
                order.append(key)
            m = re.search(r"\.([a-zA-Z0-9]+)(?:$|\?)", final)
            ext = m.group(1).lower() if m else ""
            lst = groups[key].setdefault(ext, [])
            if final not in lst:
                lst.append(final)

        for el in elems:
            tag = getattr(el.root, "tag", "").lower()
            if tag == "source":
                srcset = el.attrib.get("srcset") or el.attrib.get("data-srcset")
                for u in _extract_urls_from_srcset(srcset or ""):
                    add_candidate(u)
            else:
                candidates = [
                    el.attrib.get("data-orig-file"),
                    el.attrib.get("data-large-file"),
                    el.attrib.get("data-medium-file"),
                    el.attrib.get("data-src"),
                    el.attrib.get("data-srcset"),
                    el.attrib.get("srcset"),
                    el.attrib.get("src"),
                ]
                for cand in candidates:
                    if not cand:
                        continue
                    if "," in cand:
                        for u in _extract_urls_from_srcset(cand):
                            add_candidate(u)
                    else:
                        add_candidate(cand)

        if not order:
            og = self.css('meta[property="og:image"]::attr(content)').get()
            final = _normalize_url(og, self)
            if final:
                key = _group_key_from_url(final)
                groups[key] = {final.split(".")[-1].lower(): [final]}
                order = [key]

        if not order:
            return None

        images: List[Dict[str, str]] = []
        preferred_ext_order = ("avif", "jpg", "jpeg", "png", "webp", "gif")
        for key in order:
            ext_map = groups.get(key, {})

            def sort_pref(urls: List[str]) -> List[str]:
                no_size = [u for u in urls if not re.search(r"-\d+x\d+(?:[\.\?]|$)", u)]
                sized = [u for u in urls if re.search(r"-\d+x\d+(?:[\.\?]|$)", u)]
                return no_size + sized

            for ext in preferred_ext_order:
                urls = ext_map.get(ext, [])
                for u in sort_pref(urls):
                    images.append({"url": u})
            for ext in sorted(k for k in ext_map.keys() if k not in preferred_ext_order):
                for u in sort_pref(ext_map[ext]):
                    images.append({"url": u})

        return images or None

    @field
    def description(self) -> Optional[str]:
        desc = self.css('meta[name="description"]::attr(content)').get()
        if not desc:
            desc = self.css('meta[property="og:description"]::attr(content)').get()
        if not desc:
            desc = self.css('meta[itemprop="description"]::attr(content)').get()
        if not desc:
            return None
        cleaned = html.unescape(desc).strip()
        return cleaned or None

    @field
    def articleBody(self) -> Optional[str]:
        container = self.css("div.entry-content")
        if not container:
            return None

        parts: List[str] = []
        nodes = container.xpath(
            "./p|./h1|./h2|./h3|./h4|./h5|./h6|./blockquote|./ul|./ol"
        )
        for node in nodes:
            tag = node.xpath("name()").get()
            if not tag:
                continue
            if tag in ("ul", "ol"):
                items = []
                for li in node.xpath(".//li"):
                    text = li.xpath("string(.)").get() or ""
                    text_clean = " ".join(text.split())
                    if text_clean:
                        items.append(text_clean)
                if items:
                    parts.append(" ".join(items))
            else:
                text = node.xpath("string(.)").get() or ""
                text_clean = " ".join(text.split())
                if text_clean:
                    parts.append(text_clean)

        if not parts:
            return None
        return "\n".join(parts).strip()

    @field
    def canonicalUrl(self) -> Optional[str]:
        href = self.css('link[rel="canonical"]::attr(href)').get()
        if href:
            return self.urljoin(href)

        og_url = self.css('meta[property="og:url"]::attr(content)').get()
        if og_url:
            return self.urljoin(og_url)

        jsonld_url = self._extract_url_from_jsonld()
        if jsonld_url:
            return self.urljoin(jsonld_url)

        return None

    def _extract_url_from_jsonld(self) -> Optional[str]:
        extractor = JsonLdExtractor()
        data = extractor.extract(self.response.body) or []
        for entry in data:
            if not isinstance(entry, dict):
                continue
            at_type = entry.get("@type")
            types = at_type if isinstance(at_type, list) else [at_type] if at_type else []
            if any(t in ("WebPage", "Article") for t in types):
                for key in ("url", "@id"):
                    val = entry.get(key)
                    if isinstance(val, str) and val:
                        return val
                me = entry.get("mainEntityOfPage")
                if isinstance(me, dict):
                    for key in ("@id", "url"):
                        val = me.get(key)
                        if isinstance(val, str) and val:
                            return val
        for entry in data:
            if isinstance(entry, dict):
                for key in ("url", "@id"):
                    val = entry.get(key)
                    if isinstance(val, str) and val:
                        return val
        return None
