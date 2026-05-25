from unittest.mock import patch

from ip_info.processors.dns_verify.verifier import (
    add_verify_stats,
    batch_verify,
    build_verify_results,
    resolve_domain,
    verify_one,
)


class TestResolveDomain:
    def test_returns_ip_list_on_success(self):
        with patch("ip_info.processors.dns_verify.verifier.socket.gethostbyname_ex") as mock_resolve:
            mock_resolve.return_value = ("example.com", [], ["1.2.3.4", "5.6.7.8"])
            result = resolve_domain("example.com")
        assert result == ["1.2.3.4", "5.6.7.8"]

    def test_returns_empty_list_on_gaierror(self):
        import socket

        with patch("ip_info.processors.dns_verify.verifier.socket.gethostbyname_ex") as mock_resolve:
            mock_resolve.side_effect = socket.gaierror("DNS resolution failed")
            result = resolve_domain("nonexistent.example")
        assert result == []

    def test_returns_none_on_timeout(self):
        import socket

        with patch("ip_info.processors.dns_verify.verifier.socket.gethostbyname_ex") as mock_resolve:
            mock_resolve.side_effect = socket.timeout("DNS timeout")
            result = resolve_domain("slow.example")
        assert result is None

    def test_returns_empty_list_on_generic_exception(self):
        with patch("ip_info.processors.dns_verify.verifier.socket.gethostbyname_ex") as mock_resolve:
            mock_resolve.side_effect = RuntimeError("unexpected")
            result = resolve_domain("error.example")
        assert result == []

    def test_passes_timeout_to_socket(self):
        with patch("ip_info.processors.dns_verify.verifier.socket") as mock_socket:
            mock_socket.gethostbyname_ex.return_value = ("example.com", [], ["1.2.3.4"])
            mock_socket.gaierror = Exception
            mock_socket.timeout = Exception
            resolve_domain("example.com", timeout=5.0)
            mock_socket.setdefaulttimeout.assert_called_with(5.0)


class TestVerifyOne:
    def test_matched_status(self):
        with patch("ip_info.processors.dns_verify.verifier.resolve_domain") as mock_resolve:
            mock_resolve.return_value = ["1.2.3.4", "5.6.7.8"]
            result = verify_one("example.com", "1.2.3.4")
        assert result["domain"] == "example.com"
        assert result["status"] == "matched"
        assert result["resolved_ips"] == ["1.2.3.4", "5.6.7.8"]

    def test_changed_status(self):
        with patch("ip_info.processors.dns_verify.verifier.resolve_domain") as mock_resolve:
            mock_resolve.return_value = ["9.9.9.9"]
            result = verify_one("example.com", "1.2.3.4")
        assert result["status"] == "changed"
        assert result["resolved_ips"] == ["9.9.9.9"]

    def test_unresolved_status(self):
        with patch("ip_info.processors.dns_verify.verifier.resolve_domain") as mock_resolve:
            mock_resolve.return_value = []
            result = verify_one("example.com", "1.2.3.4")
        assert result["status"] == "unresolved"
        assert result["resolved_ips"] == []

    def test_timeout_status(self):
        with patch("ip_info.processors.dns_verify.verifier.resolve_domain") as mock_resolve:
            mock_resolve.return_value = None
            result = verify_one("example.com", "1.2.3.4")
        assert result["status"] == "timeout"
        assert result["resolved_ips"] == []


class TestBatchVerify:
    def test_batch_verify_multiple_candidates(self):
        candidates = [
            {"domain": "a.com", "target_ip": "1.1.1.1"},
            {"domain": "b.com", "target_ip": "2.2.2.2"},
            {"domain": "c.com", "target_ip": "3.3.3.3"},
        ]

        def fake_resolve_side_effect(domain, timeout=3.0):
            mapping = {
                "a.com": ["1.1.1.1"],
                "b.com": ["9.9.9.9"],
                "c.com": [],
            }
            return mapping.get(domain, [])

        with patch("ip_info.processors.dns_verify.verifier.resolve_domain") as mock_resolve:
            mock_resolve.side_effect = fake_resolve_side_effect
            results = batch_verify(candidates)
        assert len(results) == 3
        assert results[0]["status"] == "matched"
        assert results[1]["status"] == "changed"
        assert results[2]["status"] == "unresolved"

    def test_batch_verify_preserves_order(self):
        candidates = [
            {"domain": "z.com", "target_ip": "1.1.1.1"},
            {"domain": "a.com", "target_ip": "2.2.2.2"},
            {"domain": "m.com", "target_ip": "3.3.3.3"},
        ]

        with patch("ip_info.processors.dns_verify.verifier.resolve_domain") as mock_resolve:
            mock_resolve.return_value = ["1.1.1.1"]
            results = batch_verify(candidates)
        assert results[0]["domain"] == "z.com"
        assert results[1]["domain"] == "a.com"
        assert results[2]["domain"] == "m.com"

    def test_batch_verify_progress_callback(self):
        candidates = [
            {"domain": "a.com", "target_ip": "1.1.1.1"},
            {"domain": "b.com", "target_ip": "2.2.2.2"},
        ]
        progress_calls = []

        def on_progress(done, total):
            progress_calls.append((done, total))

        with patch("ip_info.processors.dns_verify.verifier.resolve_domain") as mock_resolve:
            mock_resolve.return_value = ["1.1.1.1"]
            batch_verify(candidates, progress_callback=on_progress)
        assert len(progress_calls) == 2
        assert progress_calls[-1] == (2, 2)

    def test_batch_verify_handles_exception(self):
        candidates = [
            {"domain": "a.com", "target_ip": "1.1.1.1"},
        ]

        with patch("ip_info.processors.dns_verify.verifier.verify_one") as mock_verify:
            mock_verify.side_effect = RuntimeError("boom")
            results = batch_verify(candidates)
        assert len(results) == 1
        assert results[0]["status"] == "error"
        assert results[0]["resolved_ips"] == []

    def test_batch_verify_empty_candidates(self):
        results = batch_verify([])
        assert results == []


class TestBuildVerifyResults:
    def test_group_by_ip(self):
        candidates = [
            {"domain": "a.com", "target_ip": "1.1.1.1", "sources": ["aizhan"]},
            {"domain": "b.com", "target_ip": "1.1.1.1", "sources": ["chinaz"]},
            {"domain": "c.com", "target_ip": "2.2.2.2", "sources": ["aizhan"]},
        ]
        verify_results = [
            {"domain": "a.com", "status": "matched", "resolved_ips": ["1.1.1.1"]},
            {"domain": "b.com", "status": "changed", "resolved_ips": ["9.9.9.9"]},
            {"domain": "c.com", "status": "unresolved", "resolved_ips": []},
        ]
        grouped = build_verify_results(candidates, verify_results)
        assert "1.1.1.1" in grouped
        assert "2.2.2.2" in grouped
        assert len(grouped["1.1.1.1"]) == 2
        assert len(grouped["2.2.2.2"]) == 1

    def test_preserves_sources(self):
        candidates = [
            {"domain": "a.com", "target_ip": "1.1.1.1", "sources": ["aizhan", "chinaz"]},
        ]
        verify_results = [
            {"domain": "a.com", "status": "matched", "resolved_ips": ["1.1.1.1"]},
        ]
        grouped = build_verify_results(candidates, verify_results)
        assert grouped["1.1.1.1"][0]["sources"] == ["aizhan", "chinaz"]

    def test_default_empty_sources(self):
        candidates = [
            {"domain": "a.com", "target_ip": "1.1.1.1"},
        ]
        verify_results = [
            {"domain": "a.com", "status": "matched", "resolved_ips": ["1.1.1.1"]},
        ]
        grouped = build_verify_results(candidates, verify_results)
        assert grouped["1.1.1.1"][0]["sources"] == []


class TestAddVerifyStats:
    def test_stats_calculation(self):
        grouped = {
            "1.1.1.1": [
                {"domain": "a.com", "status": "matched", "resolved_ips": ["1.1.1.1"]},
                {"domain": "b.com", "status": "changed", "resolved_ips": ["9.9.9.9"]},
                {"domain": "c.com", "status": "unresolved", "resolved_ips": []},
                {"domain": "d.com", "status": "timeout", "resolved_ips": []},
                {"domain": "e.com", "status": "error", "resolved_ips": []},
            ]
        }
        stats = add_verify_stats(grouped)
        ip_stats = stats["1.1.1.1"]
        assert ip_stats["total_domains"] == 5
        assert ip_stats["matched"] == 1
        assert ip_stats["changed"] == 1
        assert ip_stats["unresolved"] == 1
        assert ip_stats["timeout"] == 1
        assert ip_stats["error"] == 1
        assert "verify_time" in ip_stats
        assert len(ip_stats["results"]) == 5

    def test_empty_grouped(self):
        stats = add_verify_stats({})
        assert stats == {}

    def test_multiple_ips(self):
        grouped = {
            "1.1.1.1": [
                {"domain": "a.com", "status": "matched", "resolved_ips": ["1.1.1.1"]},
            ],
            "2.2.2.2": [
                {"domain": "b.com", "status": "changed", "resolved_ips": ["9.9.9.9"]},
                {"domain": "c.com", "status": "matched", "resolved_ips": ["2.2.2.2"]},
            ],
        }
        stats = add_verify_stats(grouped)
        assert len(stats) == 2
        assert stats["1.1.1.1"]["total_domains"] == 1
        assert stats["2.2.2.2"]["total_domains"] == 2
