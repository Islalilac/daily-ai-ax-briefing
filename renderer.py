"""
렌더링 모듈 — 브리핑 데이터(JSON)를 모던 SaaS(사이드바) 스타일 HTML로 생성.

docs/index.html          : 최신 브리핑
docs/archive/<date>.html : 날짜별 보관본

레이아웃: 좌측 고정 사이드바(날짜 달력 · 카테고리 · 검색) + 우측 본문(총평 · 카드).
"""

from __future__ import annotations

import html
import json
import datetime as dt
from pathlib import Path

import config

CSS = """
:root{
  --bg:#f4f5f7; --side:#ffffff; --paper:#ffffff; --ink:#1a1d23; --mut:#6b7280;
  --line:#e6e8ec; --accent:#4f46e5; --accent-soft:#eef0ff; --star:#e0a80d;
  --tag:#eef1f6; --tagink:#3a4658;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);
  font-family:"Pretendard","Malgun Gothic","Segoe UI",system-ui,sans-serif;
  line-height:1.7;font-size:16px;-webkit-font-smoothing:antialiased}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}

.app{display:flex;max-width:1240px;margin:0 auto;min-height:100vh}

/* 사이드바 */
.sidebar{width:256px;flex:none;background:var(--side);border-right:1px solid var(--line);
  padding:22px 18px;position:sticky;top:0;align-self:flex-start;height:100vh;overflow-y:auto}
.brand{display:flex;align-items:center;gap:9px;font-weight:800;font-size:17px;margin-bottom:6px}
.brand .dot{width:11px;height:11px;border-radius:50%;
  background:linear-gradient(135deg,#6366f1,#4f46e5)}
.brand small{display:block;font-weight:500;font-size:11px;color:var(--mut);letter-spacing:1px}
.side-label{font-size:11px;letter-spacing:1px;text-transform:uppercase;color:var(--mut);
  margin:22px 0 9px;font-weight:700}
input[type=date],.search{width:100%;padding:9px 11px;border:1px solid var(--line);
  border-radius:9px;font-family:inherit;font-size:13px;background:#fff;color:var(--ink)}
.search::placeholder{color:#9aa1ac}
.date-row{display:flex;gap:6px;margin-top:8px}
.date-row a{flex:1;text-align:center;font-size:12px;padding:7px 4px;border:1px solid var(--line);
  border-radius:8px;color:var(--ink);background:#fff}
.date-row a:hover{border-color:var(--accent);text-decoration:none}
.date-row a.disabled{opacity:.35;pointer-events:none}
.date-row a.latest{background:var(--accent);color:#fff;border-color:var(--accent)}
.catlist{display:flex;flex-direction:column;gap:3px}
.cat-item{cursor:pointer;text-align:left;font-size:13.5px;padding:9px 12px;border:none;
  border-radius:9px;background:none;color:var(--tagink);display:flex;
  justify-content:space-between;align-items:center;font-family:inherit;width:100%}
.cat-item:hover{background:#f3f4f6}
.cat-item.active{background:var(--accent-soft);color:var(--accent);font-weight:700}
.cat-item .n{color:var(--mut);font-size:12px;background:#f0f1f4;border-radius:20px;
  padding:1px 8px}
.cat-item.active .n{color:#fff;background:var(--accent)}

/* 본문 */
.main{flex:1;min-width:0;padding:28px 34px 80px}
.main-head h1{font-size:22px;margin:0}
.main-head .sub{color:var(--mut);font-size:13px;margin-top:5px}
.overview{background:var(--paper);border:1px solid var(--line);border-left:4px solid var(--accent);
  border-radius:11px;padding:18px 22px;margin:22px 0 8px}
.overview h2{margin:0 0 8px;font-size:12px;letter-spacing:1px;color:var(--accent);
  text-transform:uppercase;font-weight:700}
.overview p{margin:0;color:#2b3138;font-size:15.5px}
.count{color:var(--mut);font-size:13px;margin:18px 2px 4px}

.card{background:var(--paper);border:1px solid var(--line);border-radius:13px;
  padding:20px 22px;margin:14px 0;transition:box-shadow .15s,border-color .15s}
.card:hover{box-shadow:0 6px 22px rgba(30,30,80,.08);border-color:#d6daf3}
.card .top{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:9px}
.num{font-family:Georgia,serif;font-size:14px;color:var(--mut);min-width:24px}
.tag{background:var(--tag);color:var(--tagink);font-size:11.5px;font-weight:600;
  padding:3px 9px;border-radius:6px}
.stars{color:var(--star);font-size:13px;letter-spacing:1px}
.stars .off{color:#d7dbe2}
.src{color:var(--mut);font-size:12.5px;margin-left:auto}
.card h3{margin:2px 0 10px;font-size:18px;line-height:1.45;font-weight:700}
.summary{margin:0 0 14px;color:#333a42;font-size:15px}
.why{background:var(--accent-soft);border-radius:9px;padding:12px 15px;font-size:14px;color:#25324e}
.why b{color:var(--accent)}
.readmore{display:inline-block;margin-top:12px;font-size:13px;font-weight:600}
.readmore:after{content:" \\2192"}
#noresult{display:none;color:var(--mut);text-align:center;padding:40px 0}

footer{margin-top:46px;padding-top:20px;border-top:1px solid var(--line);
  color:var(--mut);font-size:12px}

@media (max-width:820px){
  .app{flex-direction:column}
  .sidebar{width:auto;height:auto;position:static;border-right:none;
    border-bottom:1px solid var(--line)}
  .catlist{flex-direction:row;flex-wrap:wrap}
  .cat-item{width:auto;border:1px solid var(--line)}
  .main{padding:22px 18px 60px}
}
@media print{
  .sidebar,.readmore{display:none}
  .app{display:block}.card{break-inside:avoid;box-shadow:none}
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
    search_text = " ".join([
        art.get("title", ""), art.get("summary", ""),
        art.get("why_it_matters", ""), cat, art.get("source", ""),
    ]).lower()
    return f"""
    <article class="card" data-category="{_esc(cat)}" data-text="{_esc(search_text)}">
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


def _render_sidebar(current: str, all_dates: list[str], archive_base: str,
                    home_href: str, articles: list[dict]) -> str:
    idx = all_dates.index(current) if current in all_dates else 0
    newer = all_dates[idx - 1] if idx > 0 else None      # 최신순 정렬
    older = all_dates[idx + 1] if idx < len(all_dates) - 1 else None

    def nav(label: str, date: str | None) -> str:
        if date:
            return f'<a href="{archive_base}{date}.html">{label}</a>'
        return f'<a class="disabled">{label}</a>'

    dmin, dmax = all_dates[-1], all_dates[0]
    dates_json = json.dumps(all_dates)

    counts: dict[str, int] = {}
    for a in articles:
        c = a.get("category") or a.get("topic") or "기타"
        counts[c] = counts.get(c, 0) + 1
    cat_items = [
        f'<button class="cat-item active" data-cat="all">전체'
        f'<span class="n">{len(articles)}</span></button>'
    ]
    for c, n in sorted(counts.items(), key=lambda x: -x[1]):
        cat_items.append(
            f'<button class="cat-item" data-cat="{_esc(c)}">{_esc(c)}'
            f'<span class="n">{n}</span></button>'
        )

    return f"""
    <aside class="sidebar">
      <div class="brand"><span class="dot"></span>
        <div>AI · AX Briefing<small>AX STRATEGY DAILY</small></div>
      </div>

      <div class="side-label">날짜</div>
      <input type="date" value="{current}" min="{dmin}" max="{dmax}" onchange="goDate(this.value)">
      <div class="date-row">
        {nav("◀ 이전", older)}
        {nav("다음 ▶", newer)}
        <a class="latest" href="{home_href}">최신</a>
      </div>

      <div class="side-label">검색</div>
      <input type="text" class="search" id="q" placeholder="키워드로 검색..."
             oninput="applyFilters()">

      <div class="side-label">카테고리</div>
      <div class="catlist">{"".join(cat_items)}</div>
    </aside>
    <script>
      const DATES = {dates_json};
      const BASE = "{archive_base}";
      function goDate(d){{
        if(!d) return;
        if(DATES.includes(d)){{ location.href = BASE + d + ".html"; }}
        else {{ alert("해당 날짜의 브리핑이 없습니다."); }}
      }}
    </script>"""


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
  document.querySelectorAll('.cat-item').forEach(function(b){
    b.addEventListener('click', function(){
      document.querySelectorAll('.cat-item').forEach(x=>x.classList.remove('active'));
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

    cards = "\n".join(_render_card(a, i + 1) for i, a in enumerate(articles))

    return f"""<!doctype html>
<html lang="ko"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Daily AI/AX Briefing — {_esc(date)}</title>
<style>{CSS}</style>
</head><body>
<div class="app">
{_render_sidebar(date, all_dates, archive_base, home_href, articles)}

<main class="main">
  <div class="main-head">
    <h1>{_fmt_date_ko(date)} 브리핑</h1>
    <div class="sub">AI · AX · AI Agent · 금융/보험 · 총 {len(articles)}건 · 중요도순</div>
  </div>

  <section class="overview">
    <h2>오늘의 총평</h2>
    <p>{_esc(briefing.get('overview',''))}</p>
  </section>

  <div class="count">기사 {len(articles)}건</div>
  {cards or '<div class="empty">표시할 기사가 없습니다.</div>'}
  <div id="noresult">조건에 맞는 기사가 없습니다.</div>

  <footer>
    Daily AI/AX Briefing Agent · 매일 자동 갱신 · powered by Gemini ·
    최종 생성 {_esc(briefing.get('generated_at','')[:16].replace('T',' '))}
  </footer>
</main>
</div>
{FILTER_JS}
</body></html>"""


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
