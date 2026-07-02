"""
Daily AI/AX Briefing Agent — 메인 파이프라인.

실행:  python agent.py

단계:
  1) 수집(collector)   : Google News RSS 검색으로 기사 수집
  2) 가공(processor)   : 중복 제거 + 사전 중요도 점수
  3) 분석(summarizer)  : Claude로 요약 + AX전략팀 관점 시사점
  4) 저장(data/)       : 날짜별 JSON 보관
  5) 렌더(renderer)    : output/index.html 및 archive 페이지 생성
"""

from __future__ import annotations

import datetime as dt
import json
import sys

# Windows 콘솔에서 이모지/특수문자 출력 시 인코딩 오류 방지
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

import config
import collector
import processor
import summarizer
import renderer


def run() -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    today = dt.date.today().isoformat()
    now_iso = dt.datetime.now().isoformat()
    print(f"=== Daily AI/AX Briefing — {today} ===")

    print("[1/5] 기사 수집...")
    raw = collector.collect()

    print("[2/5] 중복 제거 및 점수 산정...")
    processed = processor.process(raw)

    print("[3/5] 요약 및 AX전략팀 관점 분석...")
    articles, overview = summarizer.summarize(processed)

    print("[4/5] 결과 저장...")
    briefing = {
        "date": today,
        "generated_at": now_iso,
        "overview": overview,
        "articles": [a.to_dict() for a in articles],
    }
    out_json = config.DATA_DIR / f"{today}.json"
    out_json.write_text(
        json.dumps(briefing, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  저장 완료 → {out_json}")

    print("[5/5] 웹페이지 생성...")
    renderer.render_all()

    print("=== 완료 ===")
    print(f"브라우저에서 열기: {config.OUTPUT_DIR / 'index.html'}")


if __name__ == "__main__":
    run()
