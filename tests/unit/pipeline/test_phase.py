from ip_info.pipeline.core.phase import Phase, PhaseResult


class HasNameAndRun:
    @property
    def name(self) -> str:
        return "valid"

    def run(self) -> PhaseResult:
        return PhaseResult()


class HasNameOnly:
    @property
    def name(self) -> str:
        return "no-run"


class HasRunOnly:
    def run(self) -> PhaseResult:
        return PhaseResult()


class TestPhaseResult:
    def test_default_values(self):
        result = PhaseResult()
        assert result.success is True
        assert result.message == ""
        assert result.elapsed == 0.0
        assert result.data == {}

    def test_custom_values(self):
        result = PhaseResult(success=False, message="fail", elapsed=1.5, data={"key": "val"})
        assert result.success is False
        assert result.message == "fail"
        assert result.elapsed == 1.5
        assert result.data == {"key": "val"}

    def test_data_independent_between_instances(self):
        r1 = PhaseResult()
        r2 = PhaseResult()
        r1.data["x"] = 1
        assert "x" not in r2.data


class TestPhaseProtocol:
    def test_valid_class_is_instance(self):
        obj = HasNameAndRun()
        assert isinstance(obj, Phase)

    def test_class_without_run_fails_isinstance(self):
        obj = HasNameOnly()
        assert not isinstance(obj, Phase)

    def test_class_without_name_fails_isinstance(self):
        obj = HasRunOnly()
        assert not isinstance(obj, Phase)
