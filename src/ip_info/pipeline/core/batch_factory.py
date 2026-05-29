from __future__ import annotations

import importlib
import logging

from ip_info.pipeline.core.batch_step import BatchStep
from ip_info.pipeline.core.channel_batch_step import ChannelBatchStep

logger = logging.getLogger(__name__)

_CHANNEL_MAP: dict[str, tuple[str, str]] = {
    "ipinfo_api": ("ip_info.channel.ipinfo_api", "IpinfoApiChannel"),
    "ipinfo_free": ("ip_info.channel.ipinfo_free", "IpinfoFreeChannel"),
    "rdns_ptr": ("ip_info.channel.rdns_ptr", "RdnsPtrChannel"),
    "aizhan": ("ip_info.channel.aizhan", "AizhanChannel"),
    "chinaz": ("ip_info.channel.chinaz", "ChinazChannel"),
    "fofa_host": ("ip_info.channel.fofa_host", "FofaHostChannel"),
    "fofa_search": ("ip_info.channel.fofa_search", "FofaSearchChannel"),
    "whois": ("ip_info.channel.whois_query", "WhoisChannel"),
    "ssl_cert": ("ip_info.channel.ssl_cert", "SslCertChannel"),
    "port_scan": ("ip_info.channel.port_scan", "PortScanChannel"),
}

_PROCESSOR_MAP: dict[str, tuple[str, str]] = {
    "classify": ("ip_info.processors.classifier.runner", "BatchClassifier"),
    "tagger": ("ip_info.processors.tagger.runner", "BatchTagger"),
    "dns_verify": ("ip_info.processors.dns_verify.runner", "BatchDnsVerify"),
}


class BatchFactory:
    @staticmethod
    def try_create(
        name: str,
        *,
        ips=None,
        writer=None,
        reader=None,
        progress_tracker=None,
        **kwargs,
    ) -> BatchStep | None:
        if name in _CHANNEL_MAP:
            return BatchFactory._try_create_channel(
                name,
                ips=ips,
                writer=writer,
                progress_tracker=progress_tracker,
                **kwargs,
            )
        if name in _PROCESSOR_MAP:
            return BatchFactory._try_create_processor(
                name,
                ips=ips,
                writer=writer,
                reader=reader,
                progress_tracker=progress_tracker,
                **kwargs,
            )
        return None

    @staticmethod
    def _try_create_channel(
        name: str,
        *,
        ips=None,
        writer=None,
        progress_tracker=None,
        **kwargs,
    ) -> ChannelBatchStep | None:
        module_path, class_name = _CHANNEL_MAP[name]
        try:
            module = importlib.import_module(module_path)
            channel_cls = getattr(module, class_name)
            channel = channel_cls()
        except Exception:
            logger.debug("渠道 %s 初始化失败", name, exc_info=True)
            return None

        workers = kwargs.pop("workers", 1)
        delay = kwargs.pop("delay", None)
        no_validate = kwargs.pop("no_validate", False)

        return ChannelBatchStep(
            channel_name=name,
            channel=channel,
            ips=ips or [],
            writer=writer,
            workers=workers,
            delay=delay,
            progress_tracker=progress_tracker,
            no_validate=no_validate,
        )

    @staticmethod
    def _try_create_processor(
        name: str,
        *,
        ips=None,
        writer=None,
        reader=None,
        progress_tracker=None,
        **kwargs,
    ):
        module_path, class_name = _PROCESSOR_MAP[name]
        try:
            module = importlib.import_module(module_path)
            processor_cls = getattr(module, class_name)
        except Exception:
            logger.debug("处理器 %s 初始化失败", name, exc_info=True)
            return None

        return processor_cls(
            ips=ips or [],
            writer=writer,
            reader=reader,
            progress_tracker=progress_tracker,
            **kwargs,
        )

    @staticmethod
    def list_channel_names() -> list[str]:
        return sorted(_CHANNEL_MAP.keys())

    @staticmethod
    def list_processor_names() -> list[str]:
        return sorted(_PROCESSOR_MAP.keys())

    @staticmethod
    def list_all_names() -> list[str]:
        return sorted(set(_CHANNEL_MAP.keys()) | set(_PROCESSOR_MAP.keys()))
