from __future__ import annotations

from pathlib import Path

from scholar_search.channels.cnki.v2026_10 import get_channel, plan_search
from scholar_search.core.contracts import SearchQuery

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "cnki_search_2026_10.html"

SEARCH_HTML = """
<html><body>
  <div class="pagerTitleCell">共找到 1,234 条结果</div>
  <div class="countPageMark">1/62</div>
  <table class="result-table-list"><tbody>
    <tr>
      <td class="name">
        <a class="fz14" href="/kcms2/article/abstract?v=abc">测试论文标题</a>
      </td>
      <td class="author">
        <a class="KnowledgeNetLink">张三</a><a class="KnowledgeNetLink">李四</a>
      </td>
      <td class="source"><a>测试期刊</a></td>
      <td class="date">2026-10-14 11:22</td>
      <td class="quote">12</td>
      <td class="download">34</td>
      <td><input class="cbItem" value="EXP1"></td>
    </tr>
    <tr>
      <td class="name"><a class="fz14" href="/kcms2/article/abstract?v=def">第二篇</a></td>
      <td class="author"><a class="KnowledgeNetLink">王五</a></td>
      <td class="source"><a>另一期刊</a></td>
      <td class="date">2024-03-01</td>
      <td class="quote">0</td>
      <td class="download"></td>
      <td><input class="cbItem" value="EXP2"></td>
    </tr>
  </tbody></table>
</body></html>
"""

DETAIL_HTML = """
<html><body>
  <h1>测试论文标题</h1>
  <div class="author"><a>张三</a><a>李四</a></div>
  <div class="orgn">某大学某学院</div>
  <div id="ChDivSummary">这是摘要正文。</div>
  <p class="keywords"><a>关键词一</a><a>关键词二</a></p>
  <p class="doi">DOI：10.16290/j.cnki.1674-5205.2026.06.008</p>
  <div class="top-tip">《测试期刊》2026年06期</div>
</body></html>
"""


def test_manifest_declares_search_and_detail() -> None:
    channel = get_channel()
    assert channel.manifest.channel == "cnki"
    assert "search" in channel.manifest.capabilities
    assert "detail" in channel.manifest.capabilities
    assert "journal" not in channel.manifest.capabilities


def test_search_plan_drives_the_search_box() -> None:
    plan = plan_search.build(SearchQuery(text="人工智能", channel="cnki"))
    assert plan.purpose == "search"
    assert [action.verb for action in plan.actions] == [
        "goto",
        "wait_for",
        "type",
        "click",
        "wait_for",
        "read_html",
    ]
    assert plan.actions[0].params["url"] == "https://kns.cnki.net/kns8s/search"
    assert plan.actions[2].params["text"] == "人工智能"


def test_parses_recorded_live_page() -> None:
    html = FIXTURE.read_text(encoding="utf-8")
    page = get_channel().parse_search(html, query=SearchQuery(text="IPMC"))

    assert page.total == 595
    assert page.page == 1
    assert page.page_count == 30
    assert len(page.records) == 2
    assert page.records[0].title
    assert page.records[0].url is not None
    assert page.records[0].url.startswith("https://kns.cnki.net/kcms2/article/abstract")
    assert page.records[0].source


def test_parse_search_extracts_rows() -> None:
    channel = get_channel()
    page = channel.parse_search(SEARCH_HTML, query=SearchQuery(text="x"))

    assert page.total == 1234
    assert page.page == 1
    assert page.page_count == 62
    assert len(page.records) == 2

    first = page.records[0]
    assert first.title == "测试论文标题"
    assert first.authors == ["张三", "李四"]
    assert first.source == "测试期刊"
    assert first.year == 2026
    assert first.citations == 12
    assert first.downloads == 34
    assert first.url == "https://kns.cnki.net/kcms2/article/abstract?v=abc"

    assert page.records[1].url == "https://kns.cnki.net/kcms2/article/abstract?v=def"


def test_parse_detail_extracts_metadata() -> None:
    channel = get_channel()
    record = channel.parse_detail(
        DETAIL_HTML, url="https://kns.cnki.net/kcms2/article/abstract?v=abc"
    )

    assert record.title == "测试论文标题"
    assert record.authors == ["张三", "李四"]
    assert record.institution == "某大学某学院"
    assert record.abstract == "这是摘要正文。"
    assert record.keywords == ["关键词一", "关键词二"]
    assert record.doi == "10.16290/j.cnki.1674-5205.2026.06.008"
    assert record.source == "测试期刊"
    assert record.year == 2026
    assert record.issue == "06"
