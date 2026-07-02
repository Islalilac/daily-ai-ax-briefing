"""
렌더링 모듈 — 브리핑 데이터(JSON)를 밝은 리포트/뉴스레터 스타일 HTML로 생성.

docs/index.html          : 최신 브리핑
docs/archive/<date>.html : 날짜별 보관본

기능: 상단 달력 날짜 선택 + 이전/다음 이동, 카테고리 필터.
"""

from __future__ import annotations

import html
import json
import datetime as dt
from pathlib import Path

import config

CSS = """
:root{
  --bg:#f5f6f8; --paper:#ffffff; --ink:#1b1f24; --mut:#6b7280;
  --line:#e6e8ec; --accent:#1e4fd6; --accent-soft:#eaf0ff;
  --star:#e0a80d; --tag:#eef1f6; --tagink:#3a4658;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);
  font-family:"Pretendard","Malgun Gothic","Segoe UI",system-ui,sans-serif;
  line-height:1.7;font-size:16px;-webkit-font-smoothing:antialiased}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
.wrap{max-width:860px;margin:0 auto;padding:0 20px 80px}

/* 마스트헤드 */
.masthead{text-align:center;padding:40px 0 22px;border-bottom:2px solid var(--ink);
  margin-bottom:0}
.masthead .kicker{font-size:12px;letter-spacing:3px;color:var(--mut);
  text-transform:uppercase;margin-bottom:10px}
.masthead h1{font-family:Georgia,"Times New Roman",serif;font-size:34px;
  font-weight:700;margin:0;letter-spacing:-.5px}
.masthead .date{margin-top:10px;color:var(--mut);font-size:14px}

/* 날짜 내비게이션 */
.datenav{display:flex;align-items:center;justify-content:center;gap:10px;
  flex-wrap:wrap;padding:14px 0;border-bottom:1px solid var(--line)}
.datenav a,.datenav span.btn{font-size:13px;padding:6px 12px;border:1px solid var(--line);
  border-radius:8px;background:var(--paper);color:var(--ink)}
.datenav a:hover{border-color:var(--accent);text-decoration:none}
.datenav .disabled{opacity:.35;pointer-events:none}
.datenav input[type=date]{font-size:13px;padding:5px 10px;border:1px solid var(--line);
  border-radius:8px;background:var(--paper);color:var(--ink);font-family:inherit}
.datenav .latest{background:var(--accent);color:#fff;border-color:var(--accent)}

/* 총평 */
.overview{background:var(--paper);border:1px solid var(--line);
  border-left:4px solid var(--accent);border-radius:10px;padding:18px 22px;margin:26px 0}
.overview h2{margin:0 0 8px;font-size:13px;letter-spacing:1px;color:var(--accent);
  text-transform:uppercase}
.overview p{margin:0;color:#2b3138;font-size:15.5px}

/* 필터 */
.filters{display:flex;gap:8px;flex-wrap:wrap;margin:22px 0 6px}
.filter-btn{cursor:pointer;font-size:13px;padding:7px 14px;border:1px solid var(--line);
  border-radius:999px;background:var(--paper);color:var(--tagink);transition:.12s}
.filter-btn:hover{border-color:var(--accent)}
.filter-btn.active{background:var(--accent);color:#fff;border-color:var(--accent)}

/* 기사 카드 */
.count{color:var(--mut);font-size:13px;margin:16px 0 4px}
.card{background:var(--paper);border:1px solid var(--line);border-radius:12px;
  padding:20px 22px;margin:14px 0;transition:box-shadow .15s,border-color .15s}
.card:hover{box-shadow:0 4px 18px rgba(20,30,60,.07);border-color:#d3d8e0}
.card .top{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:10px}
.num{font-family:Georgia,serif;font-size:15px;color:var(--mut);min-width:26px}
.tag{background:var(--tag);color:var(--tagink);font-size:11.5px;font-weight:600;
  padding:3px 9px;border-radius:6px}
.stars{color:var(--star);font-size:13px;letter-spacing:1px}
.stars .off{color:#d7dbe2}
.src{color:var(--mut);font-size:12.5px;margin-left:auto}
.card h3{margin:2px 0 10px;font-size:18px;line-height:1.45;font-weight:700}
.summary{margin:0 0 14px;color:#333a42;font-size:15px}
.why{background:var(--accent-soft);border-radius:8px;padding:12px 15px;
  font-size:14px;color:#25324e}
.why b{color:var(--accent)}
.readmore{display:inline-block;margin-top:12px;font-size:13px;font-weight:600}
.readmore:after{content:" \\2192"}
.empty{color:var(--mut);text-align:center;padding:50px 0}

footer{margin-top:46px;padding-top:20px;border-top:1px solid var(--line);
  color:var(--mut);font-size:12px;text-align:center}

@media (max-width:600px){
  .masthead h1{font-size:26px}
  .card{padding:16px 16px}
  .src{margin-left:0;width:100%}
}
@media print{
  body{background:#fff}
  .datenav,.filters,.readmore{display:none}
  .card{break-inside:avoid;box-shadow:none}
}
"""


def _esc(s: str) -> str:
    return html.escape(s or "")


def _stars(n: int) -> str:
    n = max(0, min(5, int(n or 0)))
    return f'<span class="stars">{"★" * n}<span class="off">{"★" * (5 - n)}</span></span>'


_WEEKDAY_KO = ["월", "화", "수", "목", "금", "토", "일"]


def _fmt_date_ko(date_str: str) -> str:
    try:
        d = dt.date.fromisoformat(date_str)
        return f"{d.year}년 {d.month}월 {d.day}일 ({_WEEKDAY_KO[d.weekday()]})"
    except Exception:
        return date_str


def _render_card(art: dict, num: int) -> str:
    cat = art.get("category") or art.get("topic") or "기타"
    imp = int(art.get("importance") or 1)
    date_str = (art.get("published") or "")[:10]
    return f"""
    <article class="card" data-category="{_esc(cat)}">
      <div class="top">
        <span class="num">{num:02d}</span>
        <span class="tag">{_esc(cat)}</span>
        {_stars(imp)}
        <span class="src">{_esc(art.get('source',''))} · {_esc(date_str)}</span>
      </div>
      <h3>{_esc(art.get('title',''))}</h3>
      <p class="summary">{_esc(art.get('summary',''))}</p>
      <div class="why"><b>AX전략팀 관점</b> · {_esc(art.get('why_it_matters',''))}</div>
      <a class="readmore" href="{_esc(art.get('link','#'))}" target="_blank" rel="noopener">원문 보기</a>
    </article>"""


def _render_datenav(current: str, all_dates: list[str], archive_base: str, home_href: str) -> str:
    """이전/다음 이동 + 달력 날짜 선택."""
    idx = all_dates.index(current) if current in all_dates else 0
    # all_dates는 최신순(내림차순)
    newer = all_dates[idx - 1] if idx > 0 else None
    older = all_dates[idx + 1] if idx < len(all_dates) - 1 else None

    def link(label: str, date: str | None) -> str:
        if date:
            return f'<a href="{archive_base}{date}.html">{label}</a>'
        return f'<span class="btn disabled">{label}</span>'

    dmin, dmax = all_dates[-1], all_dates[0]
    dates_json = json.dumps(all_dates)

    return f"""
    <nav class="datenav">
      {link("◀ 이전", older)}
      <input type="date" value="{current}" min="{dmin}" max="{dmax}"
             onchange="goDate(this.value)">
      {link("다음 ▶", newer)}
      <a class="latest" href="{home_href}">최신</a>
    </nav>
    <script>
      const DATES = {dates_json};
      const BASE = "{archive_base}";
      function goDate(d){{
        if(!d) return;
        if(DATES.includes(d)){{ location.href = BASE + d + ".html"; }}
        else {{ alert("해당 날짜의 브리핑이 없습니다."); }}
      }}
    </script>"""


def _render_filters(articles: list[dict]) -> str:
    counts: dict[str, int] = {}
    for a in articles:
        c = a.get("category") or a.get("topic") or "기타"
        counts[c] = counts.get(c, 0) + 1
    btns = [f'<button class="filter-btn active" data-cat="all">전체 {len(articles)}</button>']
    for c, n in sorted(counts.items(), key=lambda x: -x[1]):
        btns.append(f'<button class="filter-btn" data-cat="{_esc(c)}">{_esc(c)} {n}</button>')
    return f'<div class="filters">{"".join(btns)}</div>'


FILTER_JS = """
<script>
  document.querySelectorAll('.filter-btn').forEach(function(b){
    b.addEventListener('click', function(){
      document.querySelectorAll('.filter-btn').forEach(x=>x.classList.remove('active'));
      b.classList.add('active');
      var cat = b.dataset.cat;
      document.querySelectorAll('.card').forEach(function(c){
        c.style.display = (cat==='all' || c.dataset.category===cat) ? '' : 'none';
      });
    });
  });
</script>
"""


def _render_page(briefing: dict, all_dates: list[str], *, is_index: bool) -> str:
    articles = briefing.get("articles", [])
    date = briefing.get("date", "")

    # index.html 은 /docs 루트, archive 페이지는 /docs/archive 안에 위치
    archive_base = "archive/" if is_index else ""
    home_href = "index.html" if is_index else "../index.html"

    cards = "\n".join(_render_card(a, i + 1) for i, a in enumerate(articles)) or (
        '<div class="empty">표시할 기사가 없습니다.</div>'
    )

    return f"""<!doctype html>
<html lang="ko"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Daily AI/AX Briefing — {_esc(date)}</title>
<style>{CSS}</style>
</head><body><div class="wrap">

<header class="masthead">
  <div class="kicker">AX Strategy · Daily Intelligence</div>
  <h1>AI · AX Briefing</h1>
  <div class="date">{_fmt_date_ko(date)}</div>
</header>

{_render_datenav(date, all_dates, archive_base, home_href)}

<section class="overview">
  <h2>오늘의 총평</h2>
  <p>{_esc(briefing.get('overview',''))}</p>
</section>

{_render_filters(articles)}
<div class="count">중요도순 정렬 · 총 {len(articles)}건</div>

{cards}

<footer>
  Daily AI/AX Briefing Agent · 매일 자동 갱신 · powered by Gemini<br>
  최종 생성 {_esc(briefing.get('generated_at','')[:16].replace('T',' '))}
</footer>

{FILTER_JS}
</div></body></html>"""


def render_all(data_dir: Path = config.DATA_DIR, output_dir: Path = config.OUTPUT_DIR) -> None:
    """data_dir의 모든 브리핑 JSON을 읽어 index.html과 archive 페이지를 생성."""
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "archive").mkdir(parents=True, exist_ok=True)

    files = sorted(data_dir.glob("*.json"), reverse=True)
    if not files:
        print("  [경고] 렌더링할 데이터가 없습니다.")
        return

    all_dates = [f.stem for f in files]
    briefings = {f.stem: json.loads(f.read_text(encoding="utf-8")) for f in files}

    latest = briefings[all_dates[0]]
    (output_dir / "index.html").write_text(
        _render_page(latest, all_dates, is_index=True), encoding="utf-8"
    )
    for date, briefing in briefings.items():
        (output_dir / "archive" / f"{date}.html").write_text(
            _render_page(briefing, all_dates, is_index=False), encoding="utf-8"
        )

    print(f"  웹페이지 생성 완료 → {output_dir / 'index.html'}")
