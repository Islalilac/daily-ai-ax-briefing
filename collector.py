"""
기사 수집 모듈 — Google News RSS 검색으로 최신 기사를 수집합니다.
"""

from __future__ import annotations

import datetime as dt
import html
import re
import urllib.parse
from dataclasses import dataclass, field, asdict

import feedparser
import requests

import config


@dataclass
class Article:
    title: str
    link: str
    source: str
    topic: str
    published: str          # ISO 8601 문자열
    published_ts: float     # 정렬용 epoch seconds
    snippet: str = ""
    # 파이프라인 후반에서 채워지는 필드
    base_score: float = 0.0
    summary: str = ""
    why_it_matters: str = ""
    importance: int = 0
    category: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


_TAG_RE = re.compile(r"<[^>]+>")


def _clean(text: str) -> str:
    if not text:
        return ""
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _strip_source_suffix(title: str, source: str) -> str:
    """'제목 - 매체명' 형태에서 매체명 접미사를 제거."""
    title = _clean(title)
    if source and title.endswith(f"- {source}"):
        title = title[: -(len(source) + 2)].strip()
    # 일반적인 ' - XXX' 꼬리 제거
    return re.sub(r"\s+-\s+[^-]{1,25}$", "", title).strip()


def _build_query_url(query: str) -> str:
    params = {"q": query, **config.NEWS_LANG_PARAMS}
    return f"{config.GOOGLE_NEWS_BASE}?{urllib.parse.urlencode(params)}"


def _fetch_feed(url: str) -> feedparser.FeedParserDict:
    """requests로 받아 feedparser에 넘긴다(안정적인 User-Agent 확보)."""
    headers = {"User-Agent": "Mozilla/5.0 (DailyAX-Briefing-Agent)"}
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()
        return feedparser.parse(resp.content)
    except Exception as exc:  # 개별 피드 실패는 전체를 막지 않음
        print(f"  [경고] 피드 수집 실패: {url}\n         {exc}")
        return feedparser.parse(b"")


def collect() -> list[Article]:
    """설정된 모든 검색어에 대해 기사를 수집하여 Article 리스트로 반환."""
    now = dt.datetime.now(dt.timezone.utc)
    cutoff = now - dt.timedelta(hours=config.MAX_AGE_HOURS)
    articles: list[Article] = []

    for topic, query in config.SEARCH_QUERIES:
        url = _build_query_url(query)
        feed = _fetch_feed(url)
        for entry in feed.entries:
            source = ""
            if getattr(entry, "source", None) and getattr(entry.source, "title", None):
                source = entry.source.title
            title = _strip_source_suffix(getattr(entry, "title", ""), source)
            if not title:
                continue

            # 발행 시각
            published_ts = 0.0
            published_iso = ""
            if getattr(entry, "published_parsed", None):
                published_ts = dt.datetime(
                    *entry.published_parsed[:6], tzinfo=dt.timezone.utc
                ).timestamp()
                published_iso = dt.datetime.fromtimestamp(
                    published_ts, dt.timezone.utc
                ).isoformat()

            # 오래된 기사 제외 (발행 시각이 있는 경우에만)
            if published_ts and published_ts < cutoff.timestamp():
                continue

            articles.append(
                Article(
                    title=title,
                    link=getattr(entry, "link", ""),
                    source=source or "출처 미상",
                    topic=topic,
                    published=published_iso,
                    published_ts=published_ts,
                    snippet=_clean(getattr(entry, "summary", ""))[:400],
                )
            )

    print(f"  총 {len(articles)}건 수집(중복 포함).")
    return articles
