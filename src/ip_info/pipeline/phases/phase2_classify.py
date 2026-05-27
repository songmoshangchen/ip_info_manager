from __future__ import annotations

import logging
import time

from ip_info.pipeline.context import PipelineContext
from ip_info.pipeline.phase import PhaseResult
from ip_info.processors.classifier.runner import BatchClassifier
from ip_info.processors.tagger.runner import BatchTagger

logger = logging.getLogger(__name__)


class ClassifyTagPhase:
    def __init__(
        self,
        ips: list[str],
        context: PipelineContext,
        rules_dir: str = "",
        tagger_config_dir: str = "",
        *,
        no_tagger: bool = False,
        tagger_level: int | None = None,
    ):
        self._ips = ips
        self._context = context
        self._writer = context.writer
        self._reader = context.reader
        self._rules_dir = rules_dir
        self._tagger_config_dir = tagger_config_dir
        self._no_tagger = no_tagger
        self._tagger_level = tagger_level

    @property
    def name(self) -> str:
        return "分类与标签"

    def run(self) -> PhaseResult:
        start_time = time.time()

        if not self._ips:
            return PhaseResult(success=True, message="无 IP 需分类", elapsed=time.time() - start_time)

        # 分类
        classifier = BatchClassifier(
            ips=self._ips,
            writer=self._writer,
            reader=self._reader,
            rules_dir=self._rules_dir,
        )
        classify_result = classifier.run()
        logger.info("分类完成: %d 成功, %d 跳过", classify_result.success_count, classify_result.skip_count)

        # 标签打标
        tagger_result = None
        if not self._no_tagger:
            tagger = BatchTagger(
                ips=self._ips,
                writer=self._writer,
                reader=self._reader,
                config_dir=self._tagger_config_dir,
                level=self._tagger_level,
            )
            tagger_result = tagger.run()
            logger.info("标签完成: %d 成功, %d 跳过", tagger_result.success_count, tagger_result.skip_count)

        elapsed = time.time() - start_time
        classify_ok = classify_result.success_count
        tagger_ok = tagger_result.success_count if tagger_result else 0
        return PhaseResult(
            success=True,
            message=f"分类: {classify_ok}成功, 标签: {tagger_ok}成功",
            elapsed=elapsed,
            data={"classify_result": classify_result, "tagger_result": tagger_result},
        )
