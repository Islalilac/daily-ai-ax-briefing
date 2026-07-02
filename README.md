# Daily AI/AX Briefing Agent

매일 **AI · AX · AI Agent · 금융/보험** 관련 기사를 수집·정리해
**AX전략팀 관점의 브리핑 웹페이지**를 자동 생성하는 에이전트입니다.
**완전 무료**로 호스팅·자동 실행할 수 있습니다 (GitHub Pages + GitHub Actions + Gemini 무료 티어).

## 무엇을 하나요?

1. **수집** — Google News RSS 검색으로 주제별 최신 기사를 모읍니다. (무료·API 키 불필요)
2. **정리** — 제목·링크·날짜를 저장하고, 유사 제목 **중복 기사를 제거**합니다.
3. **점수** — 키워드·출처·최신성으로 사전 중요도를 매겨 상위 기사를 추립니다.
4. **분석** — AI가 각 기사를 **요약**하고, **"AX전략팀이 왜 알아야 하는가"**를 정리합니다.
5. **발행** — 업데이트되는 **웹페이지**(`docs/index.html`)와 날짜별 보관본을 만듭니다.

---

## 로컬에서 실행하기

```powershell
pip install -r requirements.txt
python agent.py
```

끝나면 `docs/index.html`을 브라우저로 엽니다. 매일 실행할 때마다 그날 브리핑이 최신 페이지가 되고,
이전 날짜는 `지난 브리핑` 목록에 보관됩니다.

### AI 요약 켜기 (무료 — Gemini)

키가 없어도 페이지는 생성되지만, **요약·AX전략팀 관점 분석**은 AI가 필요합니다.
Gemini 무료 티어는 신용카드 없이 발급됩니다.

1. https://aistudio.google.com/apikey 에서 API 키 발급 (Google 계정만 있으면 됨)
2. 키 설정 후 실행:

```powershell
$env:GEMINI_API_KEY = "AIza..."     # 현재 세션에만 적용
python agent.py

setx GEMINI_API_KEY "AIza..."        # 영구 등록(새 터미널부터 적용)
```

키가 설정되면 각 기사에 **요약 / AX전략팀 관점 / 중요도(1~5)**가 자동 생성되고 중요도순으로 정렬됩니다.

---

## 무료 웹사이트로 배포하기 (GitHub Pages + Actions)

한 번만 설정하면 **매일 아침 자동으로 갱신되는 무료 웹사이트**가 됩니다. 서버·비용 0원.

### 1) GitHub 저장소에 올리기

```powershell
git init
git add .
git commit -m "Daily AI/AX Briefing Agent"
# GitHub에서 새 저장소를 만든 뒤:
git remote add origin https://github.com/<your-id>/<repo>.git
git branch -M main
git push -u origin main
```

> 실행 시간 무료 무제한을 원하면 저장소를 **Public**으로 만드세요. (Private도 월 2,000분 무료)

### 2) Gemini 키를 GitHub Secret으로 등록

저장소 **Settings → Secrets and variables → Actions → New repository secret**
- Name: `GEMINI_API_KEY`
- Secret: 발급받은 키

(등록하지 않아도 사이트는 만들어지지만, AI 요약 대신 추출식 폴백으로 표시됩니다.)

### 3) GitHub Pages 켜기

저장소 **Settings → Pages**
- Source: **Deploy from a branch**
- Branch: **main** / 폴더: **/docs** → Save

몇 분 뒤 `https://<your-id>.github.io/<repo>/` 에서 사이트가 열립니다.

### 4) 자동 실행 확인

`.github/workflows/daily.yml` 이 **매일 08:00 KST**에 자동 실행되어 기사 수집→요약→커밋→사이트 갱신을 수행합니다.
저장소 **Actions** 탭에서 `Run workflow` 버튼으로 즉시 수동 실행도 가능합니다.

---

## 커스터마이징 (`config.py`)

| 항목 | 설명 |
|------|------|
| `SEARCH_QUERIES` | 수집할 주제·검색어. 관심사가 바뀌면 여기만 수정. |
| `KEYWORD_WEIGHTS` | 사전 중요도에 반영되는 키워드 가중치. |
| `SOURCE_WEIGHTS` | 신뢰 매체 가중치. |
| `MAX_AGE_HOURS` | 몇 시간 이내 기사만 볼지 (기본 36). |
| `MAX_ARTICLES_TO_SUMMARIZE` | AI로 분석할 최대 기사 수 (기본 30). |
| `PROVIDER` | `"gemini"`(무료·기본) / `"claude"`(유료) / `"none"`(LLM 미사용). |
| `GEMINI_MODEL` | 기본 `gemini-2.5-flash`. |
| `CLAUDE_MODEL` | `PROVIDER="claude"`일 때. `claude-sonnet-4-6` 등으로 비용 조절. |
| `AX_TEAM_CONTEXT` | 분석 관점(페르소나). 팀 상황에 맞게 다듬으세요. |

> Claude(유료)를 쓰려면 `requirements.txt`에서 `anthropic` 주석을 해제하고,
> `PROVIDER="claude"`, 환경변수 `ANTHROPIC_API_KEY`를 설정하세요.

---

## 파일 구조

```
config.py              설정 (수집 대상·키워드·엔진·경로)
collector.py           RSS 수집
processor.py           중복 제거 · 사전 점수
summarizer.py          AI 요약 + AX전략팀 관점 분석 (Gemini/Claude, 키 없으면 폴백)
renderer.py            HTML 웹페이지 생성
agent.py               전체 파이프라인 실행
requirements.txt       의존성
.github/workflows/     매일 자동 실행(GitHub Actions)
data/                  날짜별 브리핑 원본(JSON) — 아카이브 유지에 필요
docs/                  웹사이트 (index.html + archive/) — GitHub Pages가 서빙
```
