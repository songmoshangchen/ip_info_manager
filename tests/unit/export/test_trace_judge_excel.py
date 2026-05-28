import json
import os

import pytest

from ip_info.export.trace_judge_excel import generate_trace_judge_excel


@pytest.fixture
def output_dir(tmp_path):
    return str(tmp_path)


def _make_ip_info(
    ip,
    country="CN",
    country_code="CN",
    as_name="TestOrg",
    category="cloud_provider",
    need_deep_query=True,
    has_domains=True,
    has_fofa_ports=False,
    has_port_scan=False,
    has_rdns=False,
    tags=None,
):
    info = {
        "ipinfo_api": {
            "country": country,
            "country_code": country_code,
            "as_name": as_name,
        },
        "classifier": {
            "category": category,
            "need_deep_query": need_deep_query,
            "matched_by": [],
        },
    }
    if has_domains:
        info["chinaz"] = {
            "success": True,
            "domains": [{"domain": f"example-{ip}.com"}],
        }
    if has_fofa_ports:
        info["fofa_host"] = {"ports": [{"port": 80, "protocol": "http", "products": []}]}
    if has_port_scan:
        info["port_scan"] = {"open_ports": [{"port": 443, "service": "https"}]}
    if has_rdns:
        info["rdns_ptr"] = {"has_ptr": True, "hostname": f"host-{ip}"}
    if tags:
        info["tagger"] = {"tags": tags}
    return ip, info


def _read_xlsx(xlsx_path):
    from openpyxl import load_workbook

    wb = load_workbook(xlsx_path)
    sheets = {}
    for ws in wb.worksheets:
        rows = []
        for row in ws.iter_rows(values_only=True):
            rows.append(list(row))
        sheets[ws.title] = rows
    wb.close()
    return sheets


class TestBasicGeneration:
    def test_creates_xlsx_with_five_sheets(self, output_dir):
        ip1, info1 = _make_ip_info("1.1.1.1", has_domains=True, has_fofa_ports=True)
        ip2, info2 = _make_ip_info("2.2.2.2", country="US", country_code="US", has_domains=False, has_fofa_ports=True)
        ip3, info3 = _make_ip_info("3.3.3.3", category="crawler_scanner", need_deep_query=False, has_domains=False)
        json_path = os.path.join(output_dir, "test.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({ip1: info1, ip2: info2, ip3: info3}, f)

        result = generate_trace_judge_excel(output_dir, "test")
        assert result is True
        xlsx_path = os.path.join(output_dir, "test.trace_judge.xlsx")
        assert os.path.exists(xlsx_path)
        sheets = _read_xlsx(xlsx_path)
        assert list(sheets.keys()) == ["P1 核心溯源", "P2 重点溯源", "P3 辅助溯源", "P4 暂缓", "P5 不需溯源"]

    def test_returns_false_when_no_json(self, output_dir):
        result = generate_trace_judge_excel(output_dir, "missing")
        assert result is False


class TestP5Grouping:
    def test_crawler_scanner_goes_to_p5(self, output_dir):
        ip, info = _make_ip_info("1.1.1.1", category="crawler_scanner", need_deep_query=False, has_domains=False)
        json_path = os.path.join(output_dir, "test.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({ip: info}, f)

        generate_trace_judge_excel(output_dir, "test")
        sheets = _read_xlsx(os.path.join(output_dir, "test.trace_judge.xlsx"))
        assert len(sheets["P5 不需溯源"]) == 2
        assert sheets["P5 不需溯源"][1][0] == "1.1.1.1"
        for lvl in ["P1 核心溯源", "P2 重点溯源", "P3 辅助溯源", "P4 暂缓"]:
            assert len(sheets[lvl]) == 1

    def test_cdn_goes_to_p5(self, output_dir):
        ip, info = _make_ip_info("1.1.1.1", category="cdn", need_deep_query=False, has_domains=False)
        json_path = os.path.join(output_dir, "test.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({ip: info}, f)

        generate_trace_judge_excel(output_dir, "test")
        sheets = _read_xlsx(os.path.join(output_dir, "test.trace_judge.xlsx"))
        assert len(sheets["P5 不需溯源"]) == 2

    def test_exclude_ips_stays_in_priority_groups(self, output_dir):
        ip, info = _make_ip_info("1.1.1.1", has_domains=True, has_fofa_ports=True)
        json_path = os.path.join(output_dir, "test.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({ip: info}, f)

        generate_trace_judge_excel(output_dir, "test", exclude_ips={"1.1.1.1"})
        sheets = _read_xlsx(os.path.join(output_dir, "test.trace_judge.xlsx"))
        assert len(sheets["P1 核心溯源"]) == 2
        assert sheets["P1 核心溯源"][1][0] == "1.1.1.1"
        assert sheets["P1 核心溯源"][1][1] == "否"
        assert len(sheets["P5 不需溯源"]) == 1


class TestNeedsTraceColumn:
    def test_normal_ip_marked_yes(self, output_dir):
        ip, info = _make_ip_info("1.1.1.1", has_domains=True)
        json_path = os.path.join(output_dir, "test.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({ip: info}, f)

        generate_trace_judge_excel(output_dir, "test")
        sheets = _read_xlsx(os.path.join(output_dir, "test.trace_judge.xlsx"))
        assert sheets["P1 核心溯源"][1][1] == "是"

    def test_crawler_scanner_marked_no(self, output_dir):
        ip, info = _make_ip_info("1.1.1.1", category="crawler_scanner", need_deep_query=False, has_domains=False)
        json_path = os.path.join(output_dir, "test.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({ip: info}, f)

        generate_trace_judge_excel(output_dir, "test")
        sheets = _read_xlsx(os.path.join(output_dir, "test.trace_judge.xlsx"))
        assert sheets["P5 不需溯源"][1][1] == "否"


class TestPriorityGrouping:
    def test_cn_ip_with_domains_is_p1(self, output_dir):
        ip, info = _make_ip_info("1.1.1.1", has_domains=True)
        json_path = os.path.join(output_dir, "test.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({ip: info}, f)

        generate_trace_judge_excel(output_dir, "test")
        sheets = _read_xlsx(os.path.join(output_dir, "test.trace_judge.xlsx"))
        assert len(sheets["P1 核心溯源"]) == 2

    def test_foreign_ip_with_domains_is_p2(self, output_dir):
        ip, info = _make_ip_info("2.2.2.2", country="US", country_code="US", has_domains=True)
        json_path = os.path.join(output_dir, "test.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({ip: info}, f)

        generate_trace_judge_excel(output_dir, "test")
        sheets = _read_xlsx(os.path.join(output_dir, "test.trace_judge.xlsx"))
        assert len(sheets["P2 重点溯源"]) == 2

    def test_foreign_ip_with_ports_is_p3(self, output_dir):
        ip, info = _make_ip_info("4.4.4.4", country="US", country_code="US", has_domains=False, has_fofa_ports=True)
        json_path = os.path.join(output_dir, "test.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({ip: info}, f)

        generate_trace_judge_excel(output_dir, "test")
        sheets = _read_xlsx(os.path.join(output_dir, "test.trace_judge.xlsx"))
        assert len(sheets["P3 辅助溯源"]) == 2

    def test_foreign_ip_nothing_is_p4(self, output_dir):
        ip, info = _make_ip_info("5.5.5.5", country="US", country_code="US", has_domains=False)
        json_path = os.path.join(output_dir, "test.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({ip: info}, f)

        generate_trace_judge_excel(output_dir, "test")
        sheets = _read_xlsx(os.path.join(output_dir, "test.trace_judge.xlsx"))
        assert len(sheets["P4 暂缓"]) == 2


class TestRowContent:
    def test_full_row(self, output_dir):
        ip, info = _make_ip_info(
            "1.1.1.1",
            as_name="TestASN",
            has_domains=True,
            has_fofa_ports=True,
            has_port_scan=True,
            has_rdns=True,
            tags=["tor", "botnet"],
        )
        json_path = os.path.join(output_dir, "test.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({ip: info}, f)

        generate_trace_judge_excel(output_dir, "test")
        sheets = _read_xlsx(os.path.join(output_dir, "test.trace_judge.xlsx"))
        row = sheets["P1 核心溯源"][1]
        assert row[0] == "1.1.1.1"
        assert row[1] == "是"
        assert row[2] == "CN"
        assert row[3] == "TestASN"
        assert row[6] == "1"
        assert "example-1.1.1.1.com" in row[7]
        assert row[8] == "1"
        assert row[10] == "1"
        assert row[12] == "tor, botnet"
        assert row[13] == "host-1.1.1.1"


class TestStyling:
    def test_p5_header_is_gray(self, output_dir):
        ip, info = _make_ip_info("1.1.1.1", category="crawler_scanner", need_deep_query=False, has_domains=False)
        json_path = os.path.join(output_dir, "test.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({ip: info}, f)

        generate_trace_judge_excel(output_dir, "test")
        from openpyxl import load_workbook

        wb = load_workbook(os.path.join(output_dir, "test.trace_judge.xlsx"))
        cell = wb["P5 不需溯源"].cell(row=1, column=1)
        assert cell.fill.start_color.rgb == "00A6A6A6"
        wb.close()

    def test_needs_trace_yes_green(self, output_dir):
        ip, info = _make_ip_info("1.1.1.1", has_domains=True)
        json_path = os.path.join(output_dir, "test.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({ip: info}, f)

        generate_trace_judge_excel(output_dir, "test")
        from openpyxl import load_workbook

        wb = load_workbook(os.path.join(output_dir, "test.trace_judge.xlsx"))
        cell = wb["P1 核心溯源"].cell(row=2, column=2)
        assert cell.fill.start_color.rgb == "00E2EFDA"
        wb.close()
