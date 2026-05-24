from ip_info.processors.tagger.matcher import (
    _process_batch,
    ip_to_int,
    match_sorted_ips_streaming,
    parse_entry_to_range,
)


class TestIpToInt:
    def test_valid_ipv4_returns_correct_int(self):
        assert ip_to_int("1.2.3.4") == 16909060

    def test_valid_ipv4_zero(self):
        assert ip_to_int("0.0.0.0") == 0

    def test_valid_ipv4_max(self):
        assert ip_to_int("255.255.255.255") == 4294967295

    def test_invalid_ip_returns_none(self):
        assert ip_to_int("999.1.1.1") is None

    def test_invalid_format_returns_none(self):
        assert ip_to_int("not_an_ip") is None

    def test_none_input_returns_none(self):
        assert ip_to_int(None) is None

    def test_empty_string_returns_none(self):
        assert ip_to_int("") is None


class TestParseEntryToRange:
    def test_single_ip_returns_same_start_end(self):
        result = parse_entry_to_range("10.0.0.1")
        assert result == (167772161, 167772161)

    def test_cidr_24_returns_correct_range(self):
        result = parse_entry_to_range("10.0.0.0/24")
        assert result == (167772160, 167772415)

    def test_cidr_16_returns_correct_range(self):
        result = parse_entry_to_range("192.168.0.0/16")
        assert result == (3232235520, 3232301055)

    def test_cidr_32_single_host(self):
        result = parse_entry_to_range("10.0.0.1/32")
        assert result == (167772161, 167772161)

    def test_invalid_entry_returns_none(self):
        assert parse_entry_to_range("invalid") is None

    def test_empty_string_returns_none(self):
        assert parse_entry_to_range("") is None


class TestMatchSortedIpsStreaming:
    def test_empty_ip_list_returns_empty_set(self, tmp_path):
        dataset = tmp_path / "test.ipset"
        dataset.write_text("10.0.0.0/24\n", encoding="utf-8")
        result = match_sorted_ips_streaming([], str(dataset))
        assert result == set()

    def test_matching_ips_return_indices(self, tmp_path):
        dataset = tmp_path / "test.ipset"
        dataset.write_text("10.0.0.0/24\n", encoding="utf-8")
        # 10.0.0.1 = 167772161, 在 10.0.0.0/24 范围内
        sorted_ips = [("10.0.0.1", 167772161)]
        result = match_sorted_ips_streaming(sorted_ips, str(dataset))
        assert result == {0}

    def test_non_matching_ips_return_empty_set(self, tmp_path):
        dataset = tmp_path / "test.ipset"
        dataset.write_text("10.0.0.0/24\n", encoding="utf-8")
        # 192.168.1.1 = 3232235777, 不在范围内
        sorted_ips = [("192.168.1.1", 3232235777)]
        result = match_sorted_ips_streaming(sorted_ips, str(dataset))
        assert result == set()

    def test_comment_lines_are_skipped(self, tmp_path):
        dataset = tmp_path / "test.ipset"
        dataset.write_text("# comment\n10.0.0.0/24\n# another comment\n", encoding="utf-8")
        sorted_ips = [("10.0.0.1", 167772161)]
        result = match_sorted_ips_streaming(sorted_ips, str(dataset))
        assert result == {0}

    def test_empty_lines_are_skipped(self, tmp_path):
        dataset = tmp_path / "test.ipset"
        dataset.write_text("\n10.0.0.0/24\n\n", encoding="utf-8")
        sorted_ips = [("10.0.0.1", 167772161)]
        result = match_sorted_ips_streaming(sorted_ips, str(dataset))
        assert result == {0}

    def test_invalid_lines_are_skipped(self, tmp_path):
        dataset = tmp_path / "test.ipset"
        dataset.write_text("not_valid\n10.0.0.0/24\n", encoding="utf-8")
        sorted_ips = [("10.0.0.1", 167772161)]
        result = match_sorted_ips_streaming(sorted_ips, str(dataset))
        assert result == {0}

    def test_multiple_ranges_all_matched(self, tmp_path):
        dataset = tmp_path / "test.ipset"
        dataset.write_text("10.0.0.0/24\n192.168.0.0/16\n", encoding="utf-8")
        # 10.0.0.1 和 192.168.1.1 分别命中两个范围
        sorted_ips = [
            ("10.0.0.1", 167772161),
            ("192.168.1.1", 3232235777),
        ]
        result = match_sorted_ips_streaming(sorted_ips, str(dataset))
        assert result == {0, 1}

    def test_multiple_ips_in_same_range(self, tmp_path):
        dataset = tmp_path / "test.ipset"
        dataset.write_text("10.0.0.0/24\n", encoding="utf-8")
        sorted_ips = [
            ("10.0.0.1", 167772161),
            ("10.0.0.2", 167772162),
            ("10.0.0.100", 167772260),
        ]
        result = match_sorted_ips_streaming(sorted_ips, str(dataset))
        assert result == {0, 1, 2}

    def test_partial_match_only_matching_ips_returned(self, tmp_path):
        dataset = tmp_path / "test.ipset"
        dataset.write_text("10.0.0.0/24\n", encoding="utf-8")
        # IP 列表必须按整数值排序，这是函数的前置条件
        sorted_ips = [
            ("10.0.0.1", 167772161),
            ("10.0.0.100", 167772260),
            ("192.168.1.1", 3232235777),
        ]
        result = match_sorted_ips_streaming(sorted_ips, str(dataset))
        assert result == {0, 1}

    def test_empty_dataset_returns_empty_set(self, tmp_path):
        dataset = tmp_path / "test.ipset"
        dataset.write_text("", encoding="utf-8")
        sorted_ips = [("10.0.0.1", 167772161)]
        result = match_sorted_ips_streaming(sorted_ips, str(dataset))
        assert result == set()

    def test_single_ip_entry_in_dataset(self, tmp_path):
        dataset = tmp_path / "test.ipset"
        dataset.write_text("10.0.0.1\n", encoding="utf-8")
        sorted_ips = [("10.0.0.1", 167772161)]
        result = match_sorted_ips_streaming(sorted_ips, str(dataset))
        assert result == {0}

    def test_batch_size_triggers_batch_processing(self, tmp_path):
        dataset = tmp_path / "test.ipset"
        lines = [f"10.0.{i}.0/24\n" for i in range(10)]
        dataset.write_text("".join(lines), encoding="utf-8")
        sorted_ips = [("10.0.0.1", 167772161)]
        result = match_sorted_ips_streaming(sorted_ips, str(dataset), batch_size=3)
        assert result == {0}


class TestProcessBatch:
    def test_matching_ip_in_range(self):
        batch = [(167772160, 167772415)]
        sorted_ips = [("10.0.0.1", 167772161)]
        matched = set()
        ip_ptr = _process_batch(batch, sorted_ips, 0, 1, matched)
        assert ip_ptr == 1
        assert matched == {0}

    def test_ip_below_range_advances_ptr(self):
        batch = [(167772160, 167772415)]
        # 1.0.0.0 = 16777216, 低于 10.0.0.0
        sorted_ips = [("1.0.0.0", 16777216)]
        matched = set()
        ip_ptr = _process_batch(batch, sorted_ips, 0, 1, matched)
        assert ip_ptr == 1
        assert matched == set()

    def test_ip_above_range_stops(self):
        batch = [(167772160, 167772415)]
        # 192.168.1.1 = 3232235777, 高于 10.0.0.0/24
        sorted_ips = [("192.168.1.1", 3232235777)]
        matched = set()
        ip_ptr = _process_batch(batch, sorted_ips, 0, 1, matched)
        assert ip_ptr == 0
        assert matched == set()

    def test_multiple_ranges_sequential(self):
        batch = [(167772160, 167772415), (3232235520, 3232301055)]
        sorted_ips = [
            ("10.0.0.1", 167772161),
            ("192.168.1.1", 3232235777),
        ]
        matched = set()
        ip_ptr = _process_batch(batch, sorted_ips, 0, 2, matched)
        assert ip_ptr == 2
        assert matched == {0, 1}
