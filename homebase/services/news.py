import xml.etree.ElementTree as ET
from datetime import datetime
from time import mktime

import feedparser
import requests
from django.core.cache import cache

LEAGUE_FEED_URL = 'https://www.mlb.com/feeds/news/rss.xml'
TEAM_FEED_URL_TEMPLATE = 'https://www.mlb.com/{slug}/feeds/news/rss.xml'
TTL_SECONDS = 600


def _fetch(url, limit):
    cache_key = 'rss:' + url
    cached = cache.get(cache_key)
    if cached is not None:
        return cached[:limit]

    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    xml = resp.content
    feed = feedparser.parse(xml)
    images_by_link = _extract_images_by_link(xml)
    items = [_normalize(entry, images_by_link) for entry in feed.entries]
    cache.set(cache_key, items, TTL_SECONDS)
    return items[:limit]


def _extract_images_by_link(xml_bytes):
    images = {}
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return images
    for item in root.iter('item'):
        link_elem = item.find('link')
        image_elem = item.find('image')
        if link_elem is not None and image_elem is not None:
            href = image_elem.get('href')
            if href and link_elem.text:
                images[link_elem.text] = href
    return images


def _normalize(entry, images_by_link):
    published = None
    if getattr(entry, 'published_parsed', None):
        published = datetime.fromtimestamp(mktime(entry.published_parsed))
    return {
        'title': getattr(entry, 'title', ''),
        'link': getattr(entry, 'link', ''),
        'author': getattr(entry, 'author', ''),
        'summary': getattr(entry, 'summary', ''),
        'published': published,
        'image': images_by_link.get(getattr(entry, 'link', '')),
    }


def league_news(limit=4):
    return _fetch(LEAGUE_FEED_URL, limit)


def team_news(team_slug, limit=4):
    return _fetch(TEAM_FEED_URL_TEMPLATE.format(slug=team_slug), limit)
