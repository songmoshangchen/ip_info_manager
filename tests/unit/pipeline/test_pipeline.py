import logging

from ip_info.pipeline.phase import PhaseResult
from ip_info.pipeline.pipeline import Pipeline, PipelineResult


class FakePhase:
    def __init__(self, name, result=None):
        self._name = name
        self._result = result or PhaseResult(message=f"{name} done")

    @property
    def name(self):
        return self._name

    def run(self):
        return self._result


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
        with caplog.at_level(logging.INFO, logger="ip_info.pipeline.pipeline"):
            p.run()
        assert any("阶段" in r.message and "alpha" in r.message for r in caplog.records)
        assert any("完成" in r.message for r in caplog.records)
