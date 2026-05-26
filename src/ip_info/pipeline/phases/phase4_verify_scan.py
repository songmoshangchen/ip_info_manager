import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from ip_info.batch.core.concurrent import run_concurrent
from ip_info.channel.port_scan import PortScanChannel
from ip_info.pipeline.phase import PhaseResult
from ip_info.processors.dns_verify.runner import BatchDnsVerify
from ip_info.store.protocols import IPDataReader, IPDataWriter
from ip_info.utils.progress import ProgressTracker

logger = logging.getLogger(__name__)


class VerifyScanPhase:
    def __init__(
        self,
        ips: list[str],
        writer: IPDataWriter,
        reader: IPDataReader,
        nmap_channel: PortScanChannel,
        *,
        domain_cache=None,
        force_days: int | None = None,
        max_age_days: int = 7,
        dns_timeout: float = 3.0,
        dns_concurrency: int = 10,
        nmap_workers: int = 1,
        no_validate: bool = False,
        progress_tracker: ProgressTracker | None = None,
    ):
        self._ips = ips
        self._writer = writer
        self._reader = reader
        self._nmap_channel = nmap_channel
        self._domain_cache = domain_cache
        self._force_days = force_days
        self._max_age_days = max_age_days
        self._dns_timeout = dns_timeout
        self._dns_concurrency = dns_concurrency
        self._nmap_workers = nmap_workers
        self._no_validate = no_validate
        self._progress_tracker = progress_tracker

    @property
    def name(self) -> str:
        return "验证与扫描"

    def run(self) -> PhaseResult:
        start_time = time.time()

        if not self._ips:
            return PhaseResult(success=True, message="无 IP 需验证/扫描", elapsed=time.time() - start_time)

        # 渠道验证（与其他 Phase 保持一致：先验证，再传 no_validate=True）
        if not self._no_validate:
            self._nmap_channel.validate()

        dns_result = None
        scan_result = None

        def run_dns_verify():
            dns_verify = BatchDnsVerify(
                ips=self._ips,
                writer=self._writer,
                reader=self._reader,
                domain_cache=self._domain_cache,
                force_days=self._force_days,
                max_age_days=self._max_age_days,
                timeout=self._dns_timeout,
                concurrency=self._dns_concurrency,
            )
            return dns_verify.run()

        def run_port_scan():
            return run_concurrent(
                ips=self._ips,
                channel=self._nmap_channel,
                writer=self._writer,
                channel_name="port_scan",
                workers=self._nmap_workers,
                delay=self._nmap_channel.default_delay,
                no_validate=True,
                progress_tracker=self._progress_tracker,
            )

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {
                executor.submit(run_dns_verify): "dns",
                executor.submit(run_port_scan): "scan",
            }
            for future in as_completed(futures):
                label = futures[future]
                result = future.result()
                if label == "dns":
                    dns_result = result
                else:
                    scan_result = result

        dns_ok = dns_result.success_count if dns_result else 0
        scan_ok = scan_result.success_count if scan_result else 0
        elapsed = time.time() - start_time

        return PhaseResult(
            success=True,
            message=f"DNS验证: {dns_ok}成功, Nmap扫描: {scan_ok}成功",
            elapsed=elapsed,
            data={"dns_result": dns_result, "scan_result": scan_result},
        )
