from __future__ import annotations

import logging
import os
import time

from ip_info.batch.core.query import BatchResult
from ip_info.pipeline.core.batch_step import BatchStep
from ip_info.pipeline.core.context import PipelineContext
from ip_info.pipeline.core.phase import PhaseResult
from ip_info.processors.tagger.update_check import check_tagger_update_status, format_update_warning

logger = logging.getLogger(__name__)


class ClassifyTagPhase:
    def __init__(
        self,
        ips: list[str],
        context: PipelineContext,
        classify_step: BatchStep | None = None,
        tagger_step: BatchStep | None = None,
        rules_dir: str = "",
        tagger_config_dir: str = "",
        output_dir: str = "",
        prefix: str = "",
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
        self._output_dir = output_dir
        self._prefix = prefix
        self._no_tagger = no_tagger
        self._tagger_level = tagger_level

        self._classify_step = classify_step
        self._tagger_step = tagger_step

        if self._classify_step is None and rules_dir:
            from ip_info.processors.classifier.runner import BatchClassifier

            self._classify_step = BatchClassifier(
                ips=ips,
                writer=self._writer,
                reader=self._reader,
                rules_dir=rules_dir,
            )

        if self._tagger_step is None and not no_tagger and tagger_config_dir:
            from ip_info.processors.tagger.runner import BatchTagger

            self._tagger_step = BatchTagger(
                ips=ips,
                writer=self._writer,
                reader=self._reader,
                config_dir=tagger_config_dir,
                level=tagger_level,
            )

    @property
    def name(self) -> str:
        return "分类与标签"

    def run(self) -> PhaseResult:
        start_time = time.time()

        if not self._ips:
            return PhaseResult(success=True, message="无 IP 需分类", elapsed=time.time() - start_time)

        classify_result = self._classify_step.run() if self._classify_step else BatchResult()
        logger.info("分类完成: %d 成功, %d 跳过", classify_result.success_count, classify_result.skip_count)

        tagger_result = None
        if self._tagger_step:
            # 检查标签数据源更新状态
            if self._tagger_config_dir:
                update_status = check_tagger_update_status(self._tagger_config_dir)
                if update_status["status"] != "up_to_date":
                    warning = format_update_warning(update_status)
                    # 使用 print 而非 logger，确保醒目显示
                    print(warning)

            tagger_result = self._tagger_step.run()
            logger.info("标签完成: %d 成功, %d 跳过", tagger_result.success_count, tagger_result.skip_count)

        elapsed = time.time() - start_time
        classify_ok = classify_result.success_count
        tagger_ok = tagger_result.success_count if tagger_result else 0

        if self._output_dir and self._prefix and self._rules_dir:
            from ip_info.export.rdns_classify_excel import export_unclassified_rdns

            unclassified_count = export_unclassified_rdns(
                reader=self._reader,
                output_dir=self._output_dir,
                prefix=self._prefix,
                rules_dir=self._rules_dir,
            )
            if unclassified_count > 0:
                excel_path = os.path.join(self._output_dir, f"{self._prefix}.unclassified_rdns.xlsx")
                logger.info("还有 %d 个未处理 RDNS，报表位于 %s，请处理", unclassified_count, excel_path)

        return PhaseResult(
            success=True,
            message=f"分类: {classify_ok}成功, 标签: {tagger_ok}成功",
            elapsed=elapsed,
            data={"classify_result": classify_result, "tagger_result": tagger_result},
        )
