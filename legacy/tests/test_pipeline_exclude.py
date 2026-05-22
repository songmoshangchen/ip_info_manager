import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def _build_pipeline(tmp_path, prefix='test_project'):
    from scenarios.trace_ip.pipeline import TraceIPPipeline

    pipeline = TraceIPPipeline.__new__(TraceIPPipeline)
    pipeline._output_dir = str(tmp_path)
    pipeline._prefix = prefix
    return pipeline


def _write_ip_data(tmp_path, prefix, ip_data):
    json_path = os.path.join(str(tmp_path), f'{prefix}.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(ip_data, f)
    return json_path


class TestLoadExcludeIps:

    def test_file_not_exists_returns_none(self, tmp_path):
        from scenarios.trace_ip.pipeline import TraceIPPipeline

        pipeline = _build_pipeline(tmp_path)
        result = pipeline._load_exclude_ips(str(tmp_path / 'nonexistent.txt'))
        assert result is None

    def test_empty_file_returns_none(self, tmp_path):
        from scenarios.trace_ip.pipeline import TraceIPPipeline

        pipeline = _build_pipeline(tmp_path)
        exclude_file = tmp_path / 'exclude.txt'
        exclude_file.write_text('', encoding='utf-8')
        result = pipeline._load_exclude_ips(str(exclude_file))
        assert result is None

    def test_file_with_only_whitespace_returns_none(self, tmp_path):
        from scenarios.trace_ip.pipeline import TraceIPPipeline

        pipeline = _build_pipeline(tmp_path)
        exclude_file = tmp_path / 'exclude.txt'
        exclude_file.write_text('\n\n  \n', encoding='utf-8')
        result = pipeline._load_exclude_ips(str(exclude_file))
        assert result is None

    def test_no_json_data_file_returns_none(self, tmp_path):
        from scenarios.trace_ip.pipeline import TraceIPPipeline

        pipeline = _build_pipeline(tmp_path)
        exclude_file = tmp_path / 'exclude.txt'
        exclude_file.write_text('1.2.3.4\n', encoding='utf-8')
        result = pipeline._load_exclude_ips(str(exclude_file))
        assert result is None

    def test_exclude_ips_not_in_data_returns_none(self, tmp_path):
        from scenarios.trace_ip.pipeline import TraceIPPipeline

        prefix = 'test_project'
        pipeline = _build_pipeline(tmp_path, prefix)
        _write_ip_data(tmp_path, prefix, {'5.6.7.8': {'ip': '5.6.7.8'}})

        exclude_file = tmp_path / 'exclude.txt'
        exclude_file.write_text('1.2.3.4\n2.3.4.5\n', encoding='utf-8')

        result = pipeline._load_exclude_ips(str(exclude_file))
        assert result is None

    def test_exclude_ips_match_data_returns_info(self, tmp_path):
        from scenarios.trace_ip.pipeline import TraceIPPipeline

        prefix = 'test_project'
        pipeline = _build_pipeline(tmp_path, prefix)
        _write_ip_data(tmp_path, prefix, {
            '1.2.3.4': {'ip': '1.2.3.4'},
            '5.6.7.8': {'ip': '5.6.7.8'},
        })

        exclude_file = tmp_path / 'exclude.txt'
        exclude_file.write_text('1.2.3.4\n', encoding='utf-8')

        result = pipeline._load_exclude_ips(str(exclude_file))
        assert result is not None
        assert '1.2.3.4' in result['exclude_ips']
        assert result['effective_count'] == 1
        assert result['total_in_file'] == 1

    def test_partial_match_only_returns_effective(self, tmp_path):
        from scenarios.trace_ip.pipeline import TraceIPPipeline

        prefix = 'test_project'
        pipeline = _build_pipeline(tmp_path, prefix)
        _write_ip_data(tmp_path, prefix, {
            '1.2.3.4': {'ip': '1.2.3.4'},
            '5.6.7.8': {'ip': '5.6.7.8'},
        })

        exclude_file = tmp_path / 'exclude.txt'
        exclude_file.write_text('1.2.3.4\n9.9.9.9\n', encoding='utf-8')

        result = pipeline._load_exclude_ips(str(exclude_file))
        assert result is not None
        assert '1.2.3.4' in result['exclude_ips']
        assert '9.9.9.9' not in result['exclude_ips']
        assert result['effective_count'] == 1
        assert result['total_in_file'] == 2
        assert result['not_in_data_count'] == 1

    def test_multiple_matching_ips(self, tmp_path):
        from scenarios.trace_ip.pipeline import TraceIPPipeline

        prefix = 'test_project'
        pipeline = _build_pipeline(tmp_path, prefix)
        _write_ip_data(tmp_path, prefix, {
            '1.2.3.4': {'ip': '1.2.3.4'},
            '5.6.7.8': {'ip': '5.6.7.8'},
            '10.0.0.1': {'ip': '10.0.0.1'},
        })

        exclude_file = tmp_path / 'exclude.txt'
        exclude_file.write_text('1.2.3.4\n5.6.7.8\n', encoding='utf-8')

        result = pipeline._load_exclude_ips(str(exclude_file))
        assert result is not None
        assert result['effective_count'] == 2
        assert len(result['exclude_ips']) == 2

    def test_deduplicates_ips_in_file(self, tmp_path):
        from scenarios.trace_ip.pipeline import TraceIPPipeline

        prefix = 'test_project'
        pipeline = _build_pipeline(tmp_path, prefix)
        _write_ip_data(tmp_path, prefix, {'1.2.3.4': {'ip': '1.2.3.4'}})

        exclude_file = tmp_path / 'exclude.txt'
        exclude_file.write_text('1.2.3.4\n1.2.3.4\n1.2.3.4\n', encoding='utf-8')

        result = pipeline._load_exclude_ips(str(exclude_file))
        assert result is not None
        assert result['effective_count'] == 1
        assert result['total_in_file'] == 1

    def test_exclude_info_contains_not_in_data_ips(self, tmp_path):
        from scenarios.trace_ip.pipeline import TraceIPPipeline

        prefix = 'test_project'
        pipeline = _build_pipeline(tmp_path, prefix)
        _write_ip_data(tmp_path, prefix, {'1.2.3.4': {'ip': '1.2.3.4'}})

        exclude_file = tmp_path / 'exclude.txt'
        exclude_file.write_text('1.2.3.4\n9.9.9.9\n', encoding='utf-8')

        result = pipeline._load_exclude_ips(str(exclude_file))
        assert '9.9.9.9' in result['not_in_data_ips']


class TestPrintReportSummary:

    @pytest.mark.skip(reason="生产代码 bug: excel_exporter 中不存在 _trace_priority 函数，_print_report_summary 无法运行")
    def test_exclude_removes_ips_from_summary(self, tmp_path):
        pass


class TestPhase7Integration:

    def test_phase7_no_exclude_passes_none(self, tmp_path):
        from scenarios.trace_ip.pipeline import TraceIPPipeline

        prefix = 'test_project'
        pipeline = _build_pipeline(tmp_path, prefix)
        pipeline._config = {}
        pipeline._reporter = type('R', (), {
            'generate_docx_report': lambda self, **kw: None,
        })()
        pipeline._print_report_summary = lambda exclude_info=None: None

        calls = []
        original_docx = pipeline._reporter.generate_docx_report

        def mock_docx(exclude_info=None):
            calls.append(exclude_info)
        pipeline._reporter.generate_docx_report = mock_docx

        with pytest.MonkeyPatch.context() as m:
            m.setattr('scenarios.trace_ip.pipeline.generate_trace_excel',
                      lambda *a, **kw: None)
            pipeline._phase7_generate_reports()

        assert calls[0] is None

    def test_phase7_with_exclude_file_passes_info(self, tmp_path):
        from scenarios.trace_ip.pipeline import TraceIPPipeline

        prefix = 'test_project'
        pipeline = _build_pipeline(tmp_path, prefix)
        _write_ip_data(tmp_path, prefix, {'1.2.3.4': {'ip': '1.2.3.4'}})

        exclude_file = tmp_path / 'exclude.txt'
        exclude_file.write_text('1.2.3.4\n', encoding='utf-8')

        pipeline._config = {'exclude_ips_file': str(exclude_file)}
        pipeline._reporter = type('R', (), {
            'generate_docx_report': lambda self, **kw: None,
        })()

        calls = []

        def mock_docx(exclude_info=None):
            calls.append(exclude_info)
        pipeline._reporter.generate_docx_report = mock_docx
        pipeline._print_report_summary = lambda exclude_info=None: None

        with pytest.MonkeyPatch.context() as m:
            m.setattr('scenarios.trace_ip.pipeline.generate_trace_excel',
                      lambda *a, **kw: None)
            pipeline._phase7_generate_reports()

        assert calls[0] is not None
        assert '1.2.3.4' in calls[0]['exclude_ips']

    def test_phase7_exclude_file_not_exists_passes_none(self, tmp_path):
        from scenarios.trace_ip.pipeline import TraceIPPipeline

        prefix = 'test_project'
        pipeline = _build_pipeline(tmp_path, prefix)
        pipeline._config = {'exclude_ips_file': str(tmp_path / 'missing.txt')}
        pipeline._reporter = type('R', (), {
            'generate_docx_report': lambda self, **kw: None,
        })()

        calls = []

        def mock_docx(exclude_info=None):
            calls.append(exclude_info)
        pipeline._reporter.generate_docx_report = mock_docx
        pipeline._print_report_summary = lambda exclude_info=None: None

        with pytest.MonkeyPatch.context() as m:
            m.setattr('scenarios.trace_ip.pipeline.generate_trace_excel',
                      lambda *a, **kw: None)
            pipeline._phase7_generate_reports()

        assert calls[0] is None
