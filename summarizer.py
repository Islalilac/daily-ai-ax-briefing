"""
요약/분석 모듈 — Claude API로 각 기사를 요약하고 AX전략팀 관점의 시사점을 생성.

ANTHROPIC_API_KEY 환경변수가 있으면 자동 실행되며,
없으면 추출식(스니펫 발췌) 폴백으로 최소한의 결과를 채웁니다.
"""

from __future__ import annotations

import os

from pydantic import BaseModel, Field

import config
from collector import Article


# --- 구조화 출력 스키마 -----------------------------------------------------
class ArticleAnalysis(BaseModel):
    index: int = Field(description="입력 기사 목록의 번호")
    category: str = Field(description="AI / AI Agent / AX / 금융 AI / 보험 AI / 규제·정책 / 기타 중 하나")
    summary: str = Field(description="기사 핵심 요약(한국어 2~3문장)")
    why_it_matters: str = Field(
        description="AX전략팀이 왜 이 기사를 알아야 하는지, 전략·실행 관점의 시사점(한국어 1~2문장)"
    )
    importance: int = Field(description="AX전략팀 관점의 중요도 1(낮음)~5(매우 높음)")


class BriefingResult(BaseModel):
    overview: str = Field(description="오늘 전체 동향을 3~4문장으로 요약한 데일리 총평(한국어)")
    items: list[ArticleAnalysis]


# --- LLM 경로 ---------------------------------------------------------------
def _build_prompt(articles: list[Article]) -> str:
    lines = ["다음은 오늘 수집된 AI/AX/금융·보험 관련 기사 목록입니다.\n"]
    for i, art in enumerate(articles):
        lines.append(
            f"[{i}] 제목: {art.title}\n"
            f"    출처: {art.source} / 주제: {art.topic}\n"
            f"    발췌: {art.snippet or '(발췌 없음)'}\n"
        )
    lines.append(
        "\n각 기사에 대해 index, category, summary, why_it_matters, importance를 작성하고, "
        "전체 동향을 담은 overview도 작성하세요. "
        "요약은 사실 위주로, why_it_matters는 반드시 AX전략팀 관점에서 작성하세요. "
        "모든 출력은 한국어로 작성합니다."
    )
    return "\n".join(lines)


def _summarize_with_gemini(articles: list[Article]) -> BriefingResult | None:
    """Google Gemini 무료 티어로 구조화 요약을 생성."""
    try:
        from google import genai
    except ImportError:
        print("  [경고] google-genai 패키지가 없습니다. (pip install google-genai)")
        return None

    try:
        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        response = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=_build_prompt(articles),
            config={
                "system_instruction": config.AX_TEAM_CONTEXT,
                "response_mime_type": "application/json",
                "response_schema": BriefingResult,
                "temperature": 0.4,
            },
        )
    except Exception as exc:
        print(f"  [경고] Gemini 호출 실패: {exc}\n         폴백을 사용합니다.")
        return None

    result = getattr(response, "parsed", None)
    if isinstance(result, BriefingResult):
        return result
    # parsed가 비어 있으면 원문 JSON을 직접 파싱 시도
    try:
        import json

        return BriefingResult(**json.loads(response.text))
    except Exception as exc:
        print(f"  [경고] Gemini 출력 파싱 실패: {exc}\n         폴백을 사용합니다.")
        return None


def _summarize_with_claude(articles: list[Article]) -> BriefingResult | None:
    try:
        import anthropic
    except ImportError:
        print("  [경고] anthropic 패키지가 없습니다. 폴백을 사용합니다.")
        return None

    try:
        client = anthropic.Anthropic()
        response = client.messages.parse(
            model=config.CLAUDE_MODEL,
            max_tokens=config.MAX_TOKENS,
            thinking={"type": "adaptive"},
            system=config.AX_TEAM_CONTEXT,
            messages=[{"role": "user", "content": _build_prompt(articles)}],
            output_format=BriefingResult,
        )
    except Exception as exc:
        print(f"  [경고] Claude 호출 실패: {exc}\n         폴백을 사용합니다.")
        return None

    if response.parsed_output is None:
        print("  [경고] 구조화 출력 파싱 실패. 폴백을 사용합니다.")
        return None
    return response.parsed_output


# --- 폴백 경로(키 없음/실패 시) --------------------------------------------
def _fallback(articles: list[Article]) -> BriefingResult:
    scores = [a.base_score for a in articles] or [1.0]
    hi = max(scores)
    items = []
    for i, art in enumerate(articles):
        # base_score를 1~5로 대략 매핑
        imp = max(1, min(5, round(1 + 4 * (art.base_score / hi))))
        items.append(
            ArticleAnalysis(
                index=i,
                category=art.topic,
                summary=(art.snippet or art.title)[:200],
                why_it_matters="(자동 분석 미실행) 제목·출처 기준 관련 기사입니다. "
                "ANTHROPIC_API_KEY 설정 시 AX전략팀 관점 분석이 생성됩니다.",
                importance=imp,
            )
        )
    return BriefingResult(
        overview="자동 요약이 실행되지 않아 수집·정렬 결과만 표시합니다. "
        "ANTHROPIC_API_KEY를 설정하면 Claude가 각 기사 요약과 AX전략팀 관점 분석을 생성합니다.",
        items=items,
    )


def summarize(articles: list[Article]) -> tuple[list[Article], str]:
    """상위 기사를 요약/분석하고, (분석 적용된 기사 리스트, overview)를 반환."""
    targets = articles[: config.MAX_ARTICLES_TO_SUMMARIZE]
    if not targets:
        return [], "수집된 기사가 없습니다."

    result = None
    provider = config.PROVIDER.lower()

    if provider == "gemini":
        if os.getenv("GEMINI_API_KEY"):
            print(f"  Gemini({config.GEMINI_MODEL})로 {len(targets)}건 요약/분석 중...")
            result = _summarize_with_gemini(targets)
        else:
            print("  [정보] GEMINI_API_KEY 없음 → 추출식 폴백 사용.")
    elif provider == "claude":
        if os.getenv("ANTHROPIC_API_KEY"):
            print(f"  Claude({config.CLAUDE_MODEL})로 {len(targets)}건 요약/분석 중...")
            result = _summarize_with_claude(targets)
        else:
            print("  [정보] ANTHROPIC_API_KEY 없음 → 추출식 폴백 사용.")
    else:
        print("  [정보] PROVIDER='none' → 추출식 폴백 사용.")

    if result is None:
        result = _fallback(targets)

    # 분석 결과를 기사에 병합
    by_index = {item.index: item for item in result.items}
    for i, art in enumerate(targets):
        item = by_index.get(i)
        if item:
            art.category = item.category
            art.summary = item.summary
            art.why_it_matters = item.why_it_matters
            art.importance = item.importance
        else:
            art.category = art.topic
            art.summary = art.snippet[:200]
            art.importance = 1

    # 중요도 내림차순, 동점은 사전점수순
    targets.sort(key=lambda a: (a.importance, a.base_score), reverse=True)
    return targets, result.overview
