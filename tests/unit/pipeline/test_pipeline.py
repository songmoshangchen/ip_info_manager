import logging

from ip_info.pipeline.core.phase import PhaseResult
from ip_info.pipeline.core.pipeline import Pipeline, PipelineResult


class FakePhase:
    def __init__(self, name, result=None):
        self._name = name
        self._result = result or PhaseResult(message=f"{name} done")

    @property
    def name(self):
        return self._name

    def run(self):
        return self._result


class FakePhaseWithIps:
    """A phase that has _ips and _context attributes for filter testing."""

    def __init__(self, name, ips=None, context=None, result=None):
        self._name = name
        self._ips = ips or []
        self._context = context
        self._result = result or PhaseResult(message=f"{name} done")
        self._skip_ips = set()

    @property
    def name(self):
        return self._name

    def run(self):
        return self._result


class FakeContext:
    """Minimal context for filter testing."""

    def __init__(self, config=None):
        self.config = config


class TestRegister:
    def test_phases_stored_in_order(self):
        p = Pipeline()
        a = FakePhase("a")
        b = FakePhase("b")
        c = FakePhase("c")
        p.register(a)
        p.register(b)
        p.register(c)
        assert p._phases == [a, b, c]


class TestRun:
    def test_executes_all_phases_in_order(self):
        p = Pipeline()
        order = []

        class OrderedPhase:
            def __init__(self, name):
                self._name = name

            @property
            def name(self):
                return self._name

            def run(self):
                order.append(self._name)
                return PhaseResult(message=f"{self._name} done")

        p.register(OrderedPhase("first"))
        p.register(OrderedPhase("second"))
        p.register(OrderedPhase("third"))
        result = p.run()
        assert order == ["first", "second", "third"]
        assert isinstance(result, PipelineResult)
        assert result.success is True
        assert len(result.phase_results) == 3

    def test_returns_pipeline_result_with_all_phase_results(self):
        p = Pipeline()
        p.register(FakePhase("a"))
        p.register(FakePhase("b"))
        result = p.run()
        assert "a" in result.phase_results
        assert "b" in result.phase_results
        assert result.phase_results["a"].message == "a done"
        assert result.phase_results["b"].message == "b done"


class TestFromPhase:
    def test_skips_phases_before_given_number(self):
        p = Pipeline()
        order = []

        class OrderedPhase:
            def __init__(self, name):
                self._name = name

            @property
            def name(self):
                return self._name

            def run(self):
                order.append(self._name)
                return PhaseResult(message=f"{self._name} done")

        p.register(OrderedPhase("first"))
        p.register(OrderedPhase("second"))
        p.register(OrderedPhase("third"))
        result = p.run(from_phase=2)
        assert order == ["second", "third"]
        assert "first" not in result.phase_results
        assert "second" in result.phase_results
        assert "third" in result.phase_results


class TestOnlyPhase:
    def test_executes_only_given_phase_number(self):
        p = Pipeline()
        order = []

        class OrderedPhase:
            def __init__(self, name):
                self._name = name

            @property
            def name(self):
                return self._name

            def run(self):
                order.append(self._name)
                return PhaseResult(message=f"{self._name} done")

        p.register(OrderedPhase("first"))
        p.register(OrderedPhase("second"))
        p.register(OrderedPhase("third"))
        result = p.run(only_phase=2)
        assert order == ["second"]
        assert "second" in result.phase_results
        assert "first" not in result.phase_results
        assert "third" not in result.phase_results


class TestSkipPhases:
    def test_skips_specified_phase_numbers(self):
        p = Pipeline()
        order = []

        class OrderedPhase:
            def __init__(self, name):
                self._name = name

            @property
            def name(self):
                return self._name

            def run(self):
                order.append(self._name)
                return PhaseResult(message=f"{self._name} done")

        p.register(OrderedPhase("first"))
        p.register(OrderedPhase("second"))
        p.register(OrderedPhase("third"))
        result = p.run(skip_phases={1, 3})
        assert order == ["second"]
        assert "second" in result.phase_results
        assert "first" not in result.phase_results
        assert "third" not in result.phase_results


class TestFailureStopsExecution:
    def test_failure_stops_subsequent_phases(self):
        p = Pipeline()
        order = []

        class OrderedPhase:
            def __init__(self, name, result=None):
                self._name = name
                self._result = result or PhaseResult(message=f"{name} done")

            @property
            def name(self):
                return self._name

            def run(self):
                order.append(self._name)
                return self._result

        p.register(OrderedPhase("first"))
        p.register(OrderedPhase("second", PhaseResult(success=False, message="boom")))
        p.register(OrderedPhase("third"))
        result = p.run()
        assert order == ["first", "second"]
        assert result.success is False
        assert result.failed_phase == "second"
        assert "third" not in result.phase_results


class TestEmptyPipeline:
    def test_returns_success_with_empty_results(self):
        p = Pipeline()
        result = p.run()
        assert result.success is True
        assert result.phase_results == {}


class TestLogging:
    def test_logs_phase_start_and_completion(self, caplog):
        p = Pipeline()
        p.register(FakePhase("alpha"))
        with caplog.at_level(logging.INFO, logger="ip_info.pipeline.core.pipeline"):
            p.run()
        assert any("阶段" in r.message and "alpha" in r.message for r in caplog.records)
        assert any("完成" in r.message for r in caplog.records)


class TestInterPhaseFilters:
    def test_filter_runs_after_named_phase(self):
        ctx = FakeContext()
        p = Pipeline()
        p.register(FakePhaseWithIps("first", ips=["1.1.1.1", "2.2.2.2", "3.3.3.3"], context=ctx))
        p.register(FakePhaseWithIps("second", ips=["1.1.1.1", "2.2.2.2", "3.3.3.3"], context=ctx))

        def remove_first(ips, context):
            return [ip for ip in ips if ip != "1.1.1.1"]

        remove_first.__name__ = "remove_first"
        p.add_filter("first", remove_first)

        result = p.run()
        assert result.success is True
        # Filter should have modified second phase's _ips
        assert p._phases[1]._ips == ["2.2.2.2", "3.3.3.3"]

    def test_filter_results_stored_in_pipeline_result(self):
        ctx = FakeContext()
        p = Pipeline()
        p.register(FakePhaseWithIps("first", ips=["1.1.1.1", "2.2.2.2"], context=ctx))

        def keep_second(ips, context):
            return [ip for ip in ips if ip == "2.2.2.2"]

        keep_second.__name__ = "keep_second"
        p.add_filter("first", keep_second)

        result = p.run()
        assert "first:keep_second" in result.filter_results
        assert result.filter_results["first:keep_second"] == ["2.2.2.2"]

    def test_multiple_filters_on_same_phase(self):
        ctx = FakeContext()
        p = Pipeline()
        p.register(FakePhaseWithIps("first", ips=["1.1.1.1", "2.2.2.2", "3.3.3.3"], context=ctx))
        p.register(FakePhaseWithIps("second", ips=["1.1.1.1", "2.2.2.2", "3.3.3.3"], context=ctx))

        def remove_first(ips, context):
            return [ip for ip in ips if ip != "1.1.1.1"]

        remove_first.__name__ = "remove_first"

        def remove_second(ips, context):
            return [ip for ip in ips if ip != "2.2.2.2"]

        remove_second.__name__ = "remove_second"

        p.add_filter("first", remove_first)
        p.add_filter("first", remove_second)

        result = p.run()
        assert result.success is True
        # Both filters applied sequentially: first removes 1.1.1.1, then removes 2.2.2.2
        assert p._phases[1]._ips == ["3.3.3.3"]

    def test_filter_propagates_skip_ips_from_context(self):
        """Test Option C: Pipeline propagates dynamic_ips from context.config to later phases' _skip_ips."""
        ctx = FakeContext(config={})
        p = Pipeline()
        p.register(FakePhaseWithIps("分类与标签", ips=["1.1.1.1", "2.2.2.2"], context=ctx))
        p.register(FakePhaseWithIps("深度查询", ips=["1.1.1.1", "2.2.2.2"], context=ctx))
        p.register(FakePhaseWithIps("验证与扫描", ips=["1.1.1.1", "2.2.2.2"], context=ctx))

        def filter_dynamic(ips, context):
            context.config["dynamic_ips"] = {"1.1.1.1"}
            return [ip for ip in ips if ip != "1.1.1.1"]

        filter_dynamic.__name__ = "filter_dynamic"
        p.add_filter("分类与标签", filter_dynamic)

        result = p.run()
        assert result.success is True
        # Phase 3 and 4 should have skip_ips set
        assert p._phases[1]._skip_ips == {"1.1.1.1"}
        assert p._phases[2]._skip_ips == {"1.1.1.1"}
        # Phase 3 and 4 ips should be filtered
        assert p._phases[1]._ips == ["2.2.2.2"]
        assert p._phases[2]._ips == ["2.2.2.2"]

    def test_no_filter_for_phase_is_noop(self):
        p = Pipeline()
        p.register(FakePhase("alpha"))
        p.register(FakePhase("beta"))
        result = p.run()
        assert result.success is True
        assert result.filter_results == {}

    def test_filters_via_constructor(self):
        ctx = FakeContext()

        def remove_first(ips, context):
            return [ip for ip in ips if ip != "1.1.1.1"]

        remove_first.__name__ = "remove_first"
        p = Pipeline(filters=[("first", remove_first)])
        p.register(FakePhaseWithIps("first", ips=["1.1.1.1", "2.2.2.2"], context=ctx))
        p.register(FakePhaseWithIps("second", ips=["1.1.1.1", "2.2.2.2"], context=ctx))

        result = p.run()
        assert result.success is True
        assert p._phases[1]._ips == ["2.2.2.2"]
