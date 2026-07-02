"""
가공 모듈 — 중복 제거 및 사전 중요도 점수 산정.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

import config
from collector import Article


def _normalize_title(title: str) -> str:
    t = title.lower()
    t = re.sub(r"[^0-9a-z가-힣 ]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def deduplicate(articles: list[Article]) -> list[Article]:
    """제목 유사도 기반 중복 제거. 발행 시각이 이른(=원본일 가능성) 기사를 유지."""
    # 최신순 정렬 후, 이미 채택된 것과 유사하면 스킵
    ordered = sorted(articles, key=lambda a: a.published_ts, reverse=True)
    kept: list[Article] = []
    kept_norms: list[str] = []

    for art in ordered:
        norm = _normalize_title(art.title)
        if not norm:
            continue
        is_dup = False
        for kn in kept_norms:
            if kn == norm:
                is_dup = True
                break
            if SequenceMatcher(None, kn, norm).ratio() >= config.DEDUP_THRESHOLD:
                is_dup = True
                break
        if not is_dup:
            kept.append(art)
            kept_norms.append(norm)

    print(f"  중복 제거 후 {len(kept)}건.")
    return kept


def score(articles: list[Article]) -> list[Article]:
    """키워드/출처/최신성 기반 사전 점수를 부여하고 내림차순 정렬."""
    if not articles:
        return articles
    max_ts = max(a.published_ts for a in articles) or 1.0
    min_ts = min(a.published_ts for a in articles if a.published_ts) if any(
        a.published_ts for a in articles
    ) else max_ts
    span = max(max_ts - min_ts, 1.0)

    for art in articles:
        text = f"{art.title} {art.snippet}".lower()
        kw_score = sum(w for kw, w in config.KEYWORD_WEIGHTS.items() if kw in text)

        src_weight = 1.0
        src_lower = art.source.lower()
        for name, w in config.SOURCE_WEIGHTS.items():
            if name in src_lower:
                src_weight = max(src_weight, w)

        # 최신성: 0~1
        recency = (art.published_ts - min_ts) / span if art.published_ts else 0.3

        art.base_score = round((kw_score + 1.0) * src_weight + recency * 2.0, 3)

    articles.sort(key=lambda a: a.base_score, reverse=True)
    return articles


def process(articles: list[Article]) -> list[Article]:
    return score(deduplicate(articles))
