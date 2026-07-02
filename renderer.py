"""
렌더링 모듈 — 브리핑 데이터(JSON)를 매거진 스타일 HTML로 생성.

docs/index.html          : 최신 브리핑
docs/archive/<date>.html : 날짜별 보관본

디자인: 신문 느낌의 세리프 제호(masthead) + 2열 매거진 카드 그리드.
기능: 상단 툴바에 날짜 달력·이전/다음·검색, 그 아래 카테고리 필터.
"""

from __future__ import annotations

import html
import json
import datetime as dt
from pathlib import Path

import config

CSS = """
:root{
  --bg:#f3f4f6; --paper:#ffffff; --ink:#17181c; --mut:#6b7280;
  --line:#e7e8ec; --accent:#4f46e5; --accent-soft:#eef0ff; --star:#e0a80d;
  --tag:#eef1f6; --tagink:#3f4657;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);
  font-family:"Pretendard","Malgun Gothic","Segoe UI",system-ui,sans-serif;
  line-height:1.65;font-size:16px;-webkit-font-smoothing:antialiased}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
.wrap{max-width:1060px;margin:0 auto;padding:0 22px 80px}

/* 신문 제호 */
.masthead{text-align:center;padding:40px 0 18px;border-bottom:3px double var(--ink)}
.masthead .kicker{font-size:12px;letter-spacing:4px;color:var(--mut);
  text-transform:uppercase;margin-bottom:12px}
.masthead h1{font-family:Georgia,"Times New Roman",serif;font-size:44px;font-weight:700;
  margin:0;letter-spacing:-1px}
.masthead .date{margin-top:12px;color:#333;font-size:14px;font-family:Georgia,serif;
  font-style:italic}
.masthead .date b{font-style:normal;font-weight:600}

/* 상단 툴바 */
.toolbar{display:flex;align-items:center;justify-content:space-between;gap:12px;
  flex-wrap:wrap;padding:14px 0;border-bottom:1px solid var(--line)}
.tools{display:flex;align-items:center;gap:7px;flex-wrap:wrap}
.toolbar input[type=date],.search{font-family:inherit;font-size:13px;padding:7px 11px;
  border:1px solid var(--line);border-radius:8px;background:var(--paper);color:var(--ink)}
.search{min-width:210px}
.tools a{font-size:13px;padding:7px 12px;border:1px solid var(--line);border-radius:8px;
  background:var(--paper);color:var(--ink)}
.tools a:hover{border-color:var(--accent);text-decoration:none}
.tools a.disabled{opacity:.35;pointer-events:none}
.tools a.latest{background:var(--ink);color:#fff;border-color:var(--ink)}

/* 카테고리 필터 */
.filters{display:flex;gap:8px;flex-wrap:wrap;margin:18px 0 4px}
.filter-btn{cursor:pointer;font-size:13px;padding:6px 13px;border:1px solid var(--line);
  border-radius:999px;background:var(--paper);color:var(--tagink);font-family:inherit;transition:.12s}
.filter-btn:hover{border-color:var(--accent)}
.filter-btn.active{background:var(--accent);color:#fff;border-color:var(--accent)}

/* 총평 */
.overview{background:var(--paper);border:1px solid var(--line);border-left:4px solid var(--accent);
  border-radius:14px;padding:20px 24px;margin:22px 0 6px}
.overview h2{margin:0 0 8px;font-size:12px;letter-spacing:1px;text-transform:uppercase;
  color:var(--accent);font-weight:700}
.overview p{margin:0;color:#2c2c2c;font-size:15.5px}
.count{color:var(--mut);font-size:13px;margin:16px 2px 8px}

/* 매거진 2열 그리드 */
.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:18px}
.card{background:var(--paper);border:1px solid var(--line);border-radius:16px;
  padding:20px 22px;display:flex;flex-direction:column;transition:box-shadow .15s,border-color .15s}
.card:hover{box-shadow:0 8px 26px rgba(30,30,70,.09);border-color:#d6d9f0}
.card .top{display:flex;align-items:center;gap:9px;flex-wrap:wrap;margin-bottom:9px}
.tag{background:var(--tag);color:var(--tagink);font-size:11px;font-weight:700;
  padding:3px 9px;border-radius:4px;letter-spacing:.3px;text-transform:uppercase}
.stars{color:var(--star);font-size:13px;letter-spacing:1px}
.stars .off{color:#dcd9d0}
.card h3{margin:2px 0 10px;font-size:19px;line-height:1.4;font-weight:800;letter-spacing:-.01em}
.summary{margin:0 0 14px;color:#3a3a3a;font-size:14.5px;flex:1}
.why{background:var(--accent-soft);border-left:3px solid var(--accent);border-radius:0 10px 10px 0;
  padding:11px 14px;font-size:13.5px;color:#33385a}
.why b{color:var(--accent)}
.meta{display:flex;justify-content:space-between;align-items:center;margin-top:13px;
  padding-top:12px;border-top:1px solid var(--line)}
.src{color:var(--mut);font-size:12px}
.readmore{font-size:12.5px;font-weight:700}
.readmore:after{content:" \\2192"}
#noresult{display:none;color:var(--mut);text-align:center;padding:40px 0}

footer{margin-top:44px;padding-top:20px;border-top:3px double var(--ink);
  color:var(--mut);font-size:12px;text-align:center}

@media (max-width:760px){
  .masthead h1{font-size:32px}
  .grid{grid-template-columns:1fr}
  .search{min-width:140px;flex:1}
}
@media print{
  .toolbar,.filters,.readmore{display:none}
  .grid{grid-template-columns:1fr 1fr}
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
        return f"{d.year}년 {d.month}월 {d.day}일 {_WEEKDAY_KO[d.weekday()]}요일"
    except Exception:
        return date_str


def _render_card(art: dict) -> str:
    cat = art.get("category") or art.get("topic") or "기타"
    imp = int(art.get("importance") or 1)
    date_str = (art.get("published") or "")[:10]
    search_text = " ".join([
        art.get("title", ""), art.get("summary", ""),
        art.get("why_it_matters", ""), cat, art.get("source", ""),
    ]).lower()
    return f"""
    <article class="card" data-category="{_esc(cat)}" data-text="{_esc(search_text)}">
      <div class="top">
        <span class="tag">{_esc(cat)}</span>
        {_stars(imp)}
      </div>
      <h3>{_esc(art.get('title',''))}</h3>
      <p class="summary">{_esc(art.get('summary',''))}</p>
      <div class="why"><b>AX전략팀 관점</b> · {_esc(art.get('why_it_matters',''))}</div>
      <div class="meta">
        <span class="src">{_esc(art.get('source',''))} · {_esc(date_str)}</span>
        <a class="readmore" href="{_esc(art.get('link','#'))}" target="_blank" rel="noopener">원문</a>
      </div>
    </article>"""


def _render_toolbar(current: str, all_dates: list[str], archive_base: str, home_href: str) -> str:
    idx = all_dates.index(current) if current in all_dates else 0
    newer = all_dates[idx - 1] if idx > 0 else None      # 최신순 정렬
    older = all_dates[idx + 1] if idx < len(all_dates) - 1 else None

    def nav(label: str, date: str | None) -> str:
        if date:
            return f'<a href="{archive_base}{date}.html">{label}</a>'
        return f'<a class="disabled">{label}</a>'

    dmin, dmax = all_dates[-1], all_dates[0]
    dates_json = json.dumps(all_dates)
    return f"""
    <div class="toolbar">
      <div class="tools">
        <input type="date" value="{current}" min="{dmin}" max="{dmax}" onchange="goDate(this.value)">
        {nav("◀ 이전", older)}
        {nav("다음 ▶", newer)}
        <a class="latest" href="{home_href}">최신</a>
      </div>
      <div class="tools">
        <input type="text" class="search" id="q" placeholder="🔍 키워드 검색..." oninput="applyFilters()">
      </div>
    </div>
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
  let curCat = 'all';
  function applyFilters(){
    const q = (document.getElementById('q').value || '').toLowerCase().trim();
    let shown = 0;
    document.querySelectorAll('.card').forEach(function(c){
      const okCat = curCat === 'all' || c.dataset.category === curCat;
      const okQ = !q || (c.dataset.text || '').includes(q);
      const show = okCat && okQ;
      c.style.display = show ? '' : 'none';
      if(show) shown++;
    });
    document.getElementById('noresult').style.display = shown ? 'none' : 'block';
  }
  document.querySelectorAll('.filter-btn').forEach(function(b){
    b.addEventListener('click', function(){
      document.querySelectorAll('.filter-btn').forEach(x=>x.classList.remove('active'));
      b.classList.add('active');
      curCat = b.dataset.cat;
      applyFilters();
    });
  });
</script>
"""


def _render_page(briefing: dict, all_dates: list[str], *, is_index: bool) -> str:
    articles = briefing.get("articles", [])
    date = briefing.get("date", "")
    archive_base = "archive/" if is_index else ""
    home_href = "index.html" if is_index else "../index.html"

    cards = "\n".join(_render_card(a) for a in articles)

    return f"""<!doctype html>
<html lang="ko"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Daily AI/AX Briefing — {_esc(date)}</title>
<link rel="preconnect" href="https://cdn.jsdelivr.net">
<link href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@latest/dist/web/static/pretendard.min.css" rel="stylesheet">
<style>{CSS}</style>
</head><body><div class="wrap">

<header class="masthead">
  <div class="kicker">AX Strategy · Daily Intelligence</div>
  <h1>The AI · AX Briefing</h1>
  <div class="date"><b>{_fmt_date_ko(date)}</b> · 총 {len(articles)}건 · 중요도순</div>
</header>

{_render_toolbar(date, all_dates, archive_base, home_href)}
{_render_filters(articles)}

<section class="overview">
  <h2>오늘의 총평</h2>
  <p>{_esc(briefing.get('overview',''))}</p>
</section>

<div class="count">기사 {len(articles)}건</div>
<div class="grid">
{cards or '<div class="empty">표시할 기사가 없습니다.</div>'}
</div>
<div id="noresult">조건에 맞는 기사가 없습니다.</div>

<footer>
  THE AI · AX BRIEFING · 매일 자동 갱신 · powered by Gemini<br>
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
