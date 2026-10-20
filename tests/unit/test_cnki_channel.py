from __future__ import annotations

from pathlib import Path

from scholar_search.channels.cnki.v2026_10 import get_channel, plan_search
from scholar_search.core.contracts import SearchQuery

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "cnki_search_2026_10.html"
DETAIL_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "cnki_detail_2026_10.html"
PRINT_FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "cnki_detail_print_2026_10.html"
)

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
    assert str(plan.actions[0].params["url"]).startswith("https://kns.cnki.net/kns8s/search")
    assert plan.actions[2].params["text"] == "人工智能"


def test_expression_plan_uses_expert_page() -> None:
    expression = "SU='IPMC' and KY='驱动器'"
    plan = plan_search.build(SearchQuery(text=expression, channel="cnki"))

    assert str(plan.actions[0].params["url"]).startswith(
        "https://kns.cnki.net/kns8s/AdvSearch?type=expert"
    )
    assert plan.actions[2].params["text"] == expression
    assert plan.actions[2].params["selector"] == "textarea.majorSearch"
    assert plan.actions[3].params["selector"] == "input.btn-search"


def test_all_documented_fields_route_to_expert_page() -> None:
    for field in (
        "SU", "TKA", "KY", "TI", "FT", "AU", "FI", "RP", "AF",
        "FU", "AB", "CO", "RF", "CLC", "LY", "DOI", "CF",
    ):
        plan = plan_search.build(SearchQuery(text=f"{field}='x'", channel="cnki"))
        assert str(plan.actions[0].params["url"]).startswith(
            "https://kns.cnki.net/kns8s/AdvSearch"
        ), field


def test_author_wildcard_routes_to_expert_page() -> None:
    plan = plan_search.build(SearchQuery(text="AU % '陈'", channel="cnki"))
    assert str(plan.actions[0].params["url"]).startswith(
        "https://kns.cnki.net/kns8s/AdvSearch"
    )


def test_page_two_adds_a_page_turn() -> None:
    plan = plan_search.build(SearchQuery(text="IPMC", channel="cnki", page=2))

    clicks = [action for action in plan.actions if action.verb == "click"]
    assert len(clicks) == 2
    assert clicks[1].params["selector"] == "#PageNext"
    assert plan.actions[-1].verb == "read_html"


def test_large_limit_switches_page_size() -> None:
    plan = plan_search.build(SearchQuery(text="IPMC", channel="cnki", limit=50))
    selectors = [action.params.get("selector") for action in plan.actions]
    assert "#perPageDiv li[data-val='50']" in selectors


def test_year_filters_do_not_touch_the_site_control() -> None:
    plan = plan_search.build(SearchQuery(text="IPMC", year_from=2020, year_to=2021))
    selectors = [action.params.get("selector") for action in plan.actions if action.verb == "click"]
    assert "#txtStartYear" not in selectors
    assert "#btnFilterYear" not in selectors


def test_sort_uses_result_grid_tabs() -> None:
    plan = plan_search.build(SearchQuery(text="IPMC", channel="cnki", sort="date"))
    selectors = [action.params.get("selector") for action in plan.actions if action.verb == "click"]
    assert "#orderList li[data-sort='PT']" in selectors

    plan = plan_search.build(SearchQuery(text="IPMC", channel="cnki", sort="citation"))
    selectors = [action.params.get("selector") for action in plan.actions if action.verb == "click"]
    assert "#orderList li[data-sort='CF']" in selectors


def test_unsupported_filters_fail_loudly() -> None:
    import pytest

    from scholar_search.core.errors import ChannelError

    with pytest.raises(ChannelError, match="source-type"):
        plan_search.build(SearchQuery(text="IPMC", source_types=("journal",)))


def test_plan_stays_within_budget() -> None:
    plan = plan_search.build(SearchQuery(text="IPMC", channel="cnki", page=3))
    assert sum(action.timeout_ms for action in plan.actions) <= 120_000


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


def test_parse_detail_from_recorded_page() -> None:
    html = DETAIL_FIXTURE.read_text(encoding="utf-8")
    record = get_channel().parse_detail(
        html, url="https://kns.cnki.net/kcms2/article/abstract?v=abc"
    )

    assert record.title.startswith("受马铃薯")
    assert not record.title.endswith("附视频")
    assert record.authors == ["王红", "郭小溪", "杨亮"]
    assert record.institution is not None and "延安大学" in record.institution
    assert record.source == "复合材料学报"
    assert record.doi == "10.13801/j.cnki.fhclxb.20261013.003"
    assert record.year == 2026
    assert len(record.keywords) == 6
    assert record.abstract and "IPMC" in record.abstract


def test_parse_detail_extracts_print_issue() -> None:
    html = PRINT_FIXTURE.read_text(encoding="utf-8")
    record = get_channel().parse_detail(html, url="https://kns.cnki.net/x")

    assert record.title.startswith("软体连续机械臂")
    assert record.source == "力学学报"
    assert record.year == 2022
    assert record.volume == "54"
    assert record.issue == "01"
    assert record.pages == "184-195"
