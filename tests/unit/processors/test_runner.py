import json
import logging

from ip_info.batch.core.query import BatchResult
from ip_info.batch.core.runner import BatchRunner
from ip_info.processors.tagger.runner import CHANNEL_NAME, BatchTagger
from ip_info.store.in_memory import InMemoryIPWriter
from ip_info.utils.progress import InMemoryProgressTracker


def _write_manifest(path, data):
    """辅助函数：写入 manifest JSON 文件。"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def _setup_config_dir(tmp_path, manifest_items, ipset_contents):
    """辅助函数：创建配置目录，包含 manifest.json 和 .ipset 文件。

    Args:
        tmp_path: 临时目录
        manifest_items: manifest 条目列表，如 [{"file": "a.ipset", "label": "标签A", "level": 1}]
        ipset_contents: dict，key 为文件名，value 为文件内容字符串

    Returns:
        config_dir 路径字符串
    """
    config_dir = tmp_path / "tagger_config"
    config_dir.mkdir()
    _write_manifest(config_dir / "manifest.json", manifest_items)
    for filename, content in ipset_contents.items():
        (config_dir / filename).write_text(content, encoding="utf-8")
    return str(config_dir)


class TestBatchRunnerProtocolConformance:
    """BatchTagger 实现 BatchRunner Protocol 的测试。"""

    def test_isinstance_batch_runner(self):
        """BatchTagger 实例应通过 isinstance 检查为 BatchRunner。"""
        writer = InMemoryIPWriter()
        tagger = BatchTagger(ips=[], writer=writer, config_dir=".")
        assert isinstance(tagger, BatchRunner)

    def test_has_run_method(self):
        """BatchTagger 应有 run 方法。"""
        writer = InMemoryIPWriter()
        tagger = BatchTagger(ips=[], writer=writer, config_dir=".")
        assert hasattr(tagger, "run")
        assert callable(tagger.run)


class TestNormalBatchTagging:
    """正常批量打标测试。"""

    def test_matching_ip_gets_tag(self, tmp_path):
        """匹配的 IP 应写入正确的标签数据。"""
        config_dir = _setup_config_dir(
            tmp_path,
            manifest_items=[{"file": "malware.ipset", "label": "恶意软件", "level": 1}],
            ipset_contents={"malware.ipset": "10.0.0.0/24\n"},
        )
        writer = InMemoryIPWriter()
        tagger = BatchTagger(ips=["10.0.0.1"], writer=writer, config_dir=config_dir)

        result = tagger.run()

        assert result.success_count == 1
        channel_data = writer.get_channel_data("10.0.0.1", CHANNEL_NAME)
        assert channel_data is not None
        assert "tags" in channel_data
        assert "恶意软件" in channel_data["tags"]

    def test_non_matching_ip_not_tagged(self, tmp_path):
        """不匹配的 IP 不应写入标签数据。"""
        config_dir = _setup_config_dir(
            tmp_path,
            manifest_items=[{"file": "malware.ipset", "label": "恶意软件", "level": 1}],
            ipset_contents={"malware.ipset": "10.0.0.0/24\n"},
        )
        writer = InMemoryIPWriter()
        tagger = BatchTagger(ips=["192.168.1.1"], writer=writer, config_dir=config_dir)

        result = tagger.run()

        assert result.success_count == 0
        assert writer.get_channel_data("192.168.1.1", CHANNEL_NAME) is None

    def test_multiple_tags_from_different_sources(self, tmp_path):
        """同一 IP 可从多个标签源获得多个标签。"""
        config_dir = _setup_config_dir(
            tmp_path,
            manifest_items=[
                {"file": "malware.ipset", "label": "恶意软件", "level": 1},
                {"file": "proxy.ipset", "label": "代理", "level": 2},
            ],
            ipset_contents={
                "malware.ipset": "10.0.0.0/24\n",
                "proxy.ipset": "10.0.0.1\n",
            },
        )
        writer = InMemoryIPWriter()
        tagger = BatchTagger(ips=["10.0.0.1"], writer=writer, config_dir=config_dir)

        result = tagger.run()

        assert result.success_count == 1
        channel_data = writer.get_channel_data("10.0.0.1", CHANNEL_NAME)
        assert set(channel_data["tags"]) == {"恶意软件", "代理"}

    def test_batch_result_has_correct_counts(self, tmp_path):
        """BatchResult 的计数应正确。"""
        config_dir = _setup_config_dir(
            tmp_path,
            manifest_items=[{"file": "malware.ipset", "label": "恶意软件", "level": 1}],
            ipset_contents={"malware.ipset": "10.0.0.0/24\n"},
        )
        writer = InMemoryIPWriter()
        tagger = BatchTagger(
            ips=["10.0.0.1", "10.0.0.2", "192.168.1.1"],
            writer=writer,
            config_dir=config_dir,
        )

        result = tagger.run()

        assert result.success_count == 2  # 10.0.0.1, 10.0.0.2
        assert result.skip_count == 0
        assert result.fail_count == 0
        assert result.total_elapsed > 0

    def test_add_or_update_ip_called_with_correct_channel(self, tmp_path):
        """add_or_update_ip 应以 'tagger' 作为 channel 名调用。"""
        config_dir = _setup_config_dir(
            tmp_path,
            manifest_items=[{"file": "test.ipset", "label": "测试", "level": 1}],
            ipset_contents={"test.ipset": "10.0.0.1\n"},
        )
        writer = InMemoryIPWriter()
        tagger = BatchTagger(ips=["10.0.0.1"], writer=writer, config_dir=config_dir)

        tagger.run()

        ip_data = writer.get_ip_data("10.0.0.1")
        assert ip_data is not None
        assert CHANNEL_NAME in ip_data


class TestAccumulateMode:
    """累加模式测试：新标签与已有标签合并。"""

    def test_new_tags_merged_with_existing(self, tmp_path):
        """累加模式下，新标签应与已有标签合并（去重）。"""
        config_dir = _setup_config_dir(
            tmp_path,
            manifest_items=[{"file": "proxy.ipset", "label": "代理", "level": 1}],
            ipset_contents={"proxy.ipset": "10.0.0.1\n"},
        )
        writer = InMemoryIPWriter()
        # 预设已有标签
        writer.add_or_update_ip("10.0.0.1", CHANNEL_NAME, {"tags": ["恶意软件"]})

        tagger = BatchTagger(
            ips=["10.0.0.1"],
            writer=writer,
            config_dir=config_dir,
            mode="accumulate",
        )

        result = tagger.run()

        assert result.success_count == 1
        channel_data = writer.get_channel_data("10.0.0.1", CHANNEL_NAME)
        assert set(channel_data["tags"]) == {"恶意软件", "代理"}

    def test_duplicate_tags_deduplicated(self, tmp_path):
        """累加模式下，重复标签应去重。"""
        config_dir = _setup_config_dir(
            tmp_path,
            manifest_items=[{"file": "malware.ipset", "label": "恶意软件", "level": 1}],
            ipset_contents={"malware.ipset": "10.0.0.1\n"},
        )
        writer = InMemoryIPWriter()
        # 预设已有相同标签
        writer.add_or_update_ip("10.0.0.1", CHANNEL_NAME, {"tags": ["恶意软件"]})

        tagger = BatchTagger(
            ips=["10.0.0.1"],
            writer=writer,
            config_dir=config_dir,
            mode="accumulate",
        )

        result = tagger.run()

        assert result.success_count == 1
        channel_data = writer.get_channel_data("10.0.0.1", CHANNEL_NAME)
        assert channel_data["tags"] == ["恶意软件"]

    def test_no_existing_tags_just_sets_new(self, tmp_path):
        """累加模式下，无已有标签时直接设置新标签。"""
        config_dir = _setup_config_dir(
            tmp_path,
            manifest_items=[{"file": "malware.ipset", "label": "恶意软件", "level": 1}],
            ipset_contents={"malware.ipset": "10.0.0.1\n"},
        )
        writer = InMemoryIPWriter()

        tagger = BatchTagger(
            ips=["10.0.0.1"],
            writer=writer,
            config_dir=config_dir,
            mode="accumulate",
        )

        result = tagger.run()

        assert result.success_count == 1
        channel_data = writer.get_channel_data("10.0.0.1", CHANNEL_NAME)
        assert channel_data["tags"] == ["恶意软件"]


class TestOverwriteMode:
    """覆写模式测试：已有标签被替换。"""

    def test_existing_tags_replaced(self, tmp_path):
        """覆写模式下，已有标签应被新标签替换。"""
        config_dir = _setup_config_dir(
            tmp_path,
            manifest_items=[{"file": "proxy.ipset", "label": "代理", "level": 1}],
            ipset_contents={"proxy.ipset": "10.0.0.1\n"},
        )
        writer = InMemoryIPWriter()
        # 预设已有标签
        writer.add_or_update_ip("10.0.0.1", CHANNEL_NAME, {"tags": ["恶意软件"]})

        tagger = BatchTagger(
            ips=["10.0.0.1"],
            writer=writer,
            config_dir=config_dir,
            mode="overwrite",
        )

        result = tagger.run()

        assert result.success_count == 1
        channel_data = writer.get_channel_data("10.0.0.1", CHANNEL_NAME)
        assert channel_data["tags"] == ["代理"]
        assert "恶意软件" not in channel_data["tags"]


class TestProgressTrackerSkip:
    """ProgressTracker 跳过测试。"""

    def test_already_processed_ips_are_skipped(self, tmp_path):
        """已处理的 IP 应被跳过，计入 skip_count。"""
        config_dir = _setup_config_dir(
            tmp_path,
            manifest_items=[{"file": "malware.ipset", "label": "恶意软件", "level": 1}],
            ipset_contents={"malware.ipset": "10.0.0.0/24\n"},
        )
        writer = InMemoryIPWriter()
        tracker = InMemoryProgressTracker()
        tracker.mark_processed("10.0.0.1")

        tagger = BatchTagger(
            ips=["10.0.0.1", "10.0.0.2"],
            writer=writer,
            config_dir=config_dir,
            progress_tracker=tracker,
        )

        result = tagger.run()

        assert result.skip_count == 1
        assert result.success_count == 1  # 只有 10.0.0.2 被处理

    def test_all_processed_ips_skipped(self, tmp_path):
        """所有 IP 都已处理时，全部跳过。"""
        config_dir = _setup_config_dir(
            tmp_path,
            manifest_items=[{"file": "malware.ipset", "label": "恶意软件", "level": 1}],
            ipset_contents={"malware.ipset": "10.0.0.0/24\n"},
        )
        writer = InMemoryIPWriter()
        tracker = InMemoryProgressTracker()
        tracker.mark_processed("10.0.0.1")

        tagger = BatchTagger(
            ips=["10.0.0.1"],
            writer=writer,
            config_dir=config_dir,
            progress_tracker=tracker,
        )

        result = tagger.run()

        assert result.skip_count == 1
        assert result.success_count == 0

    def test_matched_ips_marked_as_processed(self, tmp_path):
        """匹配的 IP 处理后应标记为已处理。"""
        config_dir = _setup_config_dir(
            tmp_path,
            manifest_items=[{"file": "malware.ipset", "label": "恶意软件", "level": 1}],
            ipset_contents={"malware.ipset": "10.0.0.1\n"},
        )
        writer = InMemoryIPWriter()
        tracker = InMemoryProgressTracker()

        tagger = BatchTagger(
            ips=["10.0.0.1"],
            writer=writer,
            config_dir=config_dir,
            progress_tracker=tracker,
        )

        tagger.run()

        assert tracker.is_processed("10.0.0.1")

    def test_unmatched_ips_also_marked_processed(self, tmp_path):
        """未匹配的 IP 也应标记为已处理（已处理过，只是没有命中）。"""
        config_dir = _setup_config_dir(
            tmp_path,
            manifest_items=[{"file": "malware.ipset", "label": "恶意软件", "level": 1}],
            ipset_contents={"malware.ipset": "10.0.0.0/24\n"},
        )
        writer = InMemoryIPWriter()
        tracker = InMemoryProgressTracker()

        tagger = BatchTagger(
            ips=["192.168.1.1"],
            writer=writer,
            config_dir=config_dir,
            progress_tracker=tracker,
        )

        tagger.run()

        assert tracker.is_processed("192.168.1.1")


class TestEmptyInput:
    """空输入测试。"""

    def test_empty_ip_list_returns_zero_counts(self, tmp_path):
        """空 IP 列表应返回 success_count=0, skip_count=0。"""
        config_dir = _setup_config_dir(
            tmp_path,
            manifest_items=[{"file": "malware.ipset", "label": "恶意软件", "level": 1}],
            ipset_contents={"malware.ipset": "10.0.0.0/24\n"},
        )
        writer = InMemoryIPWriter()
        tagger = BatchTagger(ips=[], writer=writer, config_dir=config_dir)

        result = tagger.run()

        assert result.success_count == 0
        assert result.skip_count == 0
        assert isinstance(result, BatchResult)


class TestInvalidIPs:
    """无效 IP 测试。"""

    def test_invalid_ips_are_skipped_with_warning(self, tmp_path, caplog):
        """无效 IP 应被跳过并记录警告日志，不计入 success 或 fail。"""
        config_dir = _setup_config_dir(
            tmp_path,
            manifest_items=[{"file": "malware.ipset", "label": "恶意软件", "level": 1}],
            ipset_contents={"malware.ipset": "10.0.0.0/24\n"},
        )
        writer = InMemoryIPWriter()

        with caplog.at_level(logging.WARNING, logger="ip_info.processors.tagger.runner"):
            tagger = BatchTagger(
                ips=["not_an_ip", "999.1.1.1", "10.0.0.1"],
                writer=writer,
                config_dir=config_dir,
            )
            result = tagger.run()

        assert result.success_count == 1  # 只有 10.0.0.1 成功
        assert result.fail_count == 0
        assert result.skip_count == 0
        # 检查有警告日志
        assert any("无效 IP" in record.message for record in caplog.records)

    def test_all_invalid_ips_returns_zero_success(self, tmp_path, caplog):
        """全部无效 IP 时 success_count 应为 0。"""
        config_dir = _setup_config_dir(
            tmp_path,
            manifest_items=[{"file": "malware.ipset", "label": "恶意软件", "level": 1}],
            ipset_contents={"malware.ipset": "10.0.0.0/24\n"},
        )
        writer = InMemoryIPWriter()

        with caplog.at_level(logging.WARNING, logger="ip_info.processors.tagger.runner"):
            tagger = BatchTagger(
                ips=["not_an_ip", "999.1.1.1"],
                writer=writer,
                config_dir=config_dir,
            )
            result = tagger.run()

        assert result.success_count == 0
        assert result.fail_count == 0


class TestLevelFiltering:
    """级别过滤测试。"""

    def test_only_manifest_items_with_level_le_given_are_used(self, tmp_path):
        """仅使用 level <= 给定值的 manifest 条目。"""
        config_dir = _setup_config_dir(
            tmp_path,
            manifest_items=[
                {"file": "malware.ipset", "label": "恶意软件", "level": 1},
                {"file": "proxy.ipset", "label": "代理", "level": 2},
                {"file": "spam.ipset", "label": "垃圾邮件", "level": 3},
            ],
            ipset_contents={
                "malware.ipset": "10.0.0.1\n",
                "proxy.ipset": "10.0.0.1\n",
                "spam.ipset": "10.0.0.1\n",
            },
        )
        writer = InMemoryIPWriter()
        tagger = BatchTagger(
            ips=["10.0.0.1"],
            writer=writer,
            config_dir=config_dir,
            level=2,
        )

        result = tagger.run()

        assert result.success_count == 1
        channel_data = writer.get_channel_data("10.0.0.1", CHANNEL_NAME)
        assert set(channel_data["tags"]) == {"恶意软件", "代理"}
        assert "垃圾邮件" not in channel_data["tags"]

    def test_level_none_uses_all_items(self, tmp_path):
        """level=None 时使用所有 manifest 条目。"""
        config_dir = _setup_config_dir(
            tmp_path,
            manifest_items=[
                {"file": "malware.ipset", "label": "恶意软件", "level": 1},
                {"file": "spam.ipset", "label": "垃圾邮件", "level": 3},
            ],
            ipset_contents={
                "malware.ipset": "10.0.0.1\n",
                "spam.ipset": "10.0.0.1\n",
            },
        )
        writer = InMemoryIPWriter()
        tagger = BatchTagger(
            ips=["10.0.0.1"],
            writer=writer,
            config_dir=config_dir,
            level=None,
        )

        result = tagger.run()

        assert result.success_count == 1
        channel_data = writer.get_channel_data("10.0.0.1", CHANNEL_NAME)
        assert set(channel_data["tags"]) == {"恶意软件", "垃圾邮件"}
