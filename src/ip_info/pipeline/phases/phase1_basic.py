import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from ip_info.batch.core.concurrent import run_concurrent
from ip_info.channel.adapter import BaseChannelAdapter
from ip_info.pipeline.phase import PhaseResult
from ip_info.store.protocols import IPDataReader, IPDataWriter

logger = logging.getLogger(__name__)


class BasicCollectPhase:
    def __init__(
        self,
        ips: list[str],
        writer: IPDataWriter,
        reader: IPDataReader,
        ipinfo_channel: BaseChannelAdapter,
        rdns_channel: BaseChannelAdapter,
        *,
        no_validate: bool = False,
        ipinfo_workers: int = 1,
        rdns_workers: int = 1,
    ):
        self._ips = ips
        self._writer = writer
        self._reader = reader
        self._ipinfo_channel = ipinfo_channel
        self._rdns_channel = rdns_channel
        self._no_validate = no_validate
        self._ipinfo_workers = ipinfo_workers
        self._rdns_workers = rdns_workers

    @property
    def name(self) -> str:
        return "基础情报采集"

    def run(self) -> PhaseResult:
        start_time = time.time()

        if not self._ips:
            return PhaseResult(success=True, message="无 IP 需处理", elapsed=time.time() - start_time)

        # 渠道验证
        if not self._no_validate:
            self._ipinfo_channel.validate()
            self._rdns_channel.validate()

        ipinfo_result = None
        rdns_result = None

        def run_ipinfo():
            if self._ipinfo_channel.disabled:
                logger.warning("ipinfo_api 渠道已禁用，跳过")
                return None
            return run_concurrent(
                ips=self._ips,
                channel=self._ipinfo_channel,
                writer=self._writer,
                channel_name="ipinfo_api",
                workers=self._ipinfo_workers,
                no_validate=True,
            )

        def run_rdns():
            if self._rdns_channel.disabled:
                logger.warning("rdns_ptr 渠道已禁用，跳过")
                return None
            return run_concurrent(
                ips=self._ips,
                channel=self._rdns_channel,
                writer=self._writer,
                channel_name="rdns_ptr",
                workers=self._rdns_workers,
                no_validate=True,
            )

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {
                executor.submit(run_ipinfo): "ipinfo",
                executor.submit(run_rdns): "rdns",
            }
            for future in as_completed(futures):
                label = futures[future]
                result = future.result()
                if label == "ipinfo":
                    ipinfo_result = result
                else:
                    rdns_result = result

        # 汇总结果
        ipinfo_ok = ipinfo_result.success_count if ipinfo_result else 0
        rdns_ok = rdns_result.success_count if rdns_result else 0
        success = ipinfo_ok > 0 or rdns_ok > 0

        elapsed = time.time() - start_time
        return PhaseResult(
            success=success,
            message=f"ipinfo_api: {ipinfo_ok}成功, rdns_ptr: {rdns_ok}成功",
            elapsed=elapsed,
            data={"ipinfo_result": ipinfo_result, "rdns_result": rdns_result},
        )
