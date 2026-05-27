# 测试样例与 PRD Story 对照表

> 本文档将 `tests/` 目录下每个测试方法与 `docs/prd-system-spec.md` 中的 Story 编号（S1-S173）一一对应。
> 标注说明：
> - ✅ = 已实现且有测试覆盖
> - ⚠️ = 有测试但行为与 PRD 不一致
> - ❌ = PRD 要求但无测试/无实现
>
> **测试总数**: 552
>
> **新增测试文件**: `test_ipinfo_free.py`, `test_writer_threadsafe.py`

---

## 1. 协议与接口 (S1-S17)

| PRD | 测试文件 | 测试类 | 测试方法 | 状态 |
|-----|---------|--------|---------|------|
| S1 | test_channel_protocol.py | TestChannelProtocolStructure | test_protocol_has_channel_name_attribute | ✅ |
| S1 | test_channel_protocol.py | TestChannelProtocolStructure | test_protocol_has_validate_method | ✅ |
| S1 | test_channel_protocol.py | TestChannelProtocolStructure | test_protocol_has_fetch_method | ✅ |
| S2 | test_channel_protocol.py | TestChannelProtocolStructure | test_protocol_is_runtime_checkable | ✅ |
| S3 | test_channel_protocol.py | TestInMemoryChannel | test_satisfies_channel_protocol | ✅ |
| S3 | test_protocol_conformance.py | TestIPWriterProtocolConformance | test_ipwriter_is_ipdatawriter | ✅ |
| S3 | test_protocol_conformance.py | TestIPReaderProtocolConformance | test_ipreader_is_ipdatareader | ✅ |
| S4 | test_channel_protocol.py | TestInMemoryChannel | test_default_channel_name | ✅ |
| S4 | test_channel_protocol.py | TestInMemoryChannel | test_validate_returns_true_by_default | ✅ |
| S4 | test_channel_protocol.py | TestInMemoryChannel | test_fetch_returns_configured_result | ✅ |
| S5 | test_protocol_conformance.py | TestIPWriterThroughProtocol | test_write_through_protocol_interface | ✅ |
| S5 | test_protocol_conformance.py | TestIPReaderThroughProtocol | test_read_through_protocol_interface | ✅ |
| S6 | test_in_memory_writer.py | TestInMemoryIPWriter | test_add_or_update_ip_overwrites_existing_channel | ✅ |
| S7 | test_in_memory_writer.py | TestInMemoryIPWriter | test_add_or_update_ip_appends_channel_to_existing_ip | ✅ |
| S8 | test_in_memory_reader.py | TestInMemoryIPReaderGetIPData | test_get_ip_data_returns_full_record | ✅ |
| S9 | test_in_memory_reader.py | TestInMemoryIPReaderGetChannelData | test_get_channel_data_returns_channel_dict | ✅ |
| S10 | test_in_memory_reader.py | TestInMemoryIPReaderListAllIPs | test_list_all_ips_returns_all_keys | ✅ |
| S11 | test_in_memory_reader.py | TestInMemoryIPReaderListIPChannels | test_list_ip_channels_excludes_ip_key | ✅ |
| S12 | test_channel_protocol.py | TestChannelProtocolStructure | test_non_conforming_class_fails_isinstance | ✅ |
| S13 | test_channel_protocol.py | TestFofaHostAdapter | test_validate_returns_false_on_exit | ✅ |
| S13 | test_channel_protocol.py | TestFofaHostAdapter | test_validate_returns_false_on_exception | ✅ |
| S13 | test_channel_protocol.py | TestAizhanAdapter | test_validate_returns_false_on_exit | ✅ |
| S13 | test_channel_protocol.py | TestAizhanAdapter | test_validate_returns_false_on_exception | ✅ |
| S13 | test_channel_protocol.py | TestPortScanAdapter | test_validate_returns_false_on_exception | ✅ |
| S14 | test_in_memory_writer.py | TestInMemoryIPWriter | test_delete_ip_returns_false_for_nonexistent | ✅ |
| S15 | test_in_memory_writer.py | TestInMemoryIPWriter | test_delete_channel_returns_false_for_nonexistent_ip | ✅ |
| S15 | test_in_memory_writer.py | TestInMemoryIPWriter | test_delete_channel_returns_false_for_nonexistent_channel | ✅ |
| S16 | test_in_memory_reader.py | TestInMemoryIPReaderGetIPData | test_get_ip_data_returns_none_for_nonexistent | ✅ |
| S16 | test_in_memory_reader.py | TestInMemoryIPReaderGetChannelData | test_get_channel_data_returns_none_for_nonexistent_ip | ✅ |
| S16 | test_in_memory_reader.py | TestInMemoryIPReaderGetChannelData | test_get_channel_data_returns_none_for_nonexistent_channel | ✅ |
| S17 | test_in_memory_reader.py | TestInMemoryIPReaderListIPChannels | test_list_ip_channels_returns_empty_for_nonexistent | ✅ |
| S17 | test_in_memory_reader.py | TestInMemoryIPReaderSearchByChannel | test_search_by_channel_returns_empty_for_no_match | ✅ |

---

## 2. 渠道注册与发现 (S18-S28)

| PRD | 测试文件 | 测试类 | 测试方法 | 状态 |
|-----|---------|--------|---------|------|
| S18 | test_channel_registry.py | TestChannelRegistryRegister | test_register_channel | ✅ |
| S19 | test_channel_registry.py | TestCreateDefaultRegistry | test_contains_all_builtin_channels | ✅ |
| S19 | test_channel_registry.py | TestCreateDefaultRegistry | test_registry_contains_no_extra_channels | ✅ |
| S20 | test_channel_registry.py | TestCreateDefaultRegistry | test_all_registered_are_channel_protocol | ✅ |
| S21 | test_channel_registry.py | TestChannelRegistryGet | test_get_returns_registered_channel | ✅ |
| S21 | test_channel_registry.py | TestChannelRegistryList | test_list_names_returns_all_registered | ✅ |
| S21 | test_channel_registry.py | TestChannelRegistryList | test_list_channels_returns_all_instances | ✅ |
| S22 | test_channel_registry.py | TestChannelRegistryValidate | test_validate_all_returns_dict | ✅ |
| S23 | test_channel_registry.py | TestChannelRegistryFetch | test_fetch_delegates_to_channel | ✅ |
| S24 | test_channel_registry.py | TestChannelRegistryRegister | test_register_requires_channel_protocol | ✅ |
| S25 | test_channel_registry.py | TestChannelRegistryRegister | test_register_replaces_existing | ✅ |
| S26 | test_channel_registry.py | TestChannelRegistryGet | test_get_returns_none_for_unknown | ✅ |
| S27 | test_channel_registry.py | TestChannelRegistryFetch | test_fetch_unknown_channel_raises | ✅ |
| S28 | test_channel_registry.py | TestChannelRegistryValidate | test_validate_single_nonexistent_returns_false | ✅ |

---

## 3. 通用渠道行为 — 连续失败保护 (S29-S32)

| PRD | 测试文件 | 测试类 | 测试方法 | 状态 |
|-----|---------|--------|---------|------|
| S29 | test_batch_run.py | TestCircuitBreaking | test_skips_remaining_after_5_consecutive_network_failures | ✅ |
| S29 | test_batch_run.py | TestCircuitBreaking | test_non_network_error_does_not_count_towards_circuit_breaker | ✅ |
| S30 | test_batch_run.py | TestCircuitBreaking | test_counter_resets_on_new_run | ✅ |
| S30 | test_batch_run.py | TestCircuitBreaking | test_success_resets_consecutive_failure_counter | ✅ |
| S31 | test_batch_run.py | TestDependencyCheck | test_skips_all_queries_when_dependency_unavailable | ✅ |
| S31 | test_batch_run.py | TestDependencyCheck | test_logs_warning_when_dependency_unavailable | ✅ |
| S32 | test_batch_run.py | TestDependencyCheck | test_dependency_rechecked_on_new_instance | ✅ |
| S32 | test_batch_run.py | TestDependencyCheck | test_dependency_check_defaults_to_available | ✅ |

---

## 4. FOFA Host 聚合渠道 (S33-S39)

| PRD | 测试文件 | 测试类 | 测试方法 | 状态 |
|-----|---------|--------|---------|------|
| S33 | test_fofa_host.py | TestRequestChannel | test_normal_response_returns_json | ✅ |
| S34 | test_fofa_host.py | TestRequestChannel | test_api_error_response_not_wrapped | ✅ |
| S35 | test_fofa_host.py | TestFetchChannel | test_normal_flow_adds_query_time | ✅ |
| S35 | test_fofa_host.py | TestFormatOutput | test_adds_query_time_if_missing | ✅ |
| S36 | test_fofa_host.py | TestBaseBatchQueryWriteResult | test_temporary_error_not_written | ✅ |
| S37 | test_fofa_host.py | TestRequestChannel | test_timeout_returns_error_dict | ✅ |
| S37 | test_fofa_host.py | TestRequestChannel | test_connection_error_returns_error_dict | ✅ |
| S38 | test_fofa_host.py | TestFofaHostChannelDisabled | test_api_key_empty_sets_disabled | ✅ |
| S39 | test_fofa_host.py | TestRequestChannel | test_api_error_response_not_wrapped | ✅ |



---

## 5. 爱站网渠道 (S40-S49)

| PRD | 测试文件 | 测试类 | 测试方法 | 状态 |
|-----|---------|--------|---------|------|
| S40 | test_aizhan.py | TestRequestChannel | test_normal_returns_html_text | ✅ |
| S41 | test_aizhan.py | TestParseResponse | test_china_location_parsed | ✅ |
| S41 | test_aizhan.py | TestParseResponse | test_foreign_location_parsed | ✅ |
| S42 | test_aizhan.py | TestParseResponse | test_domain_deduplication | ✅ |
| S43 | test_aizhan.py | TestFetchChannel | test_normal_flow | ✅ |
| S44 | test_aizhan.py | TestParseResponse | test_domain_deduplication | ✅ |
| S44 | test_aizhan.py | TestParseResponse | test_domain_max_20 | ✅ |
| S44 | test_aizhan.py | TestParseResponse | test_short_domain_filtered_out | ✅ |
| S45 | test_aizhan.py | TestParseResponse | test_no_domains_message_returns_empty_list | ✅ |
| S46 | test_aizhan.py | TestAizhanMainIsNetworkError | test_temporary_error_not_written | ✅ |
| S47 | test_aizhan.py | TestParseResponse | test_missing_dns_infos_returns_error | ✅ |
| S47 | test_aizhan.py | TestParseResponse | test_missing_dns_content_returns_error | ✅ |
| S47 | test_aizhan.py | TestParseResponse | test_missing_tbody_returns_error | ✅ |
| S48 | test_aizhan.py | TestRequestChannel | test_read_timeout_classified_as_network_timeout | ✅ |
| S49 | test_aizhan.py | TestAizhanChannelDisabled | test_cookie_expired_sets_disabled | ✅ |



---

## 6. 站长之家渠道 (S50-S59)

| PRD | 测试文件 | 测试类 | 测试方法 | 状态 |
|-----|---------|--------|---------|------|
| S50 | test_chinaz.py | TestRequestChannel | test_normal_returns_html | ✅ |
| S51 | test_chinaz.py | TestParseResponse | test_normal_parse_with_location_and_isp | ✅ |
| S52 | test_chinaz.py | TestParseResponse | test_domains_parsed_with_dates | ✅ |
| S53 | test_chinaz.py | TestFetchChannel | test_normal_flow | ✅ |
| S54 | test_chinaz.py | TestParseResponse | test_domain_deduplication | ✅ |
| S54 | test_chinaz.py | TestParseResponse | test_domain_max_20 | ✅ |
| S54 | test_chinaz.py | TestParseResponse | test_short_domain_filtered | ✅ |
| S55 | test_chinaz.py | TestParseResponse | test_no_result_message_returns_empty_domains | ✅ |
| S56 | test_chinaz.py | TestChinazMainIsNetworkError | test_temporary_error_not_written | ✅ |
| S57 | test_chinaz.py | TestParseResponse | test_missing_info_div_returns_error | ✅ |
| S57 | test_chinaz.py | TestParseResponse | test_missing_domain_div_returns_error | ✅ |
| S58 | test_chinaz.py | TestRequestChannel | test_read_timeout_classified_as_network_timeout | ✅ |
| S59 | test_chinaz.py | TestChinazChannelDisabled | test_cookie_empty_sets_disabled | ✅ |



---

## 7. IPInfo 认证渠道 ipinfo_api (S60-S65)

| PRD | 测试文件 | 测试类 | 测试方法 | 状态 |
|-----|---------|--------|---------|------|
| S60 | test_ipinfo_api.py | TestRequestChannelApiMode | test_api_mode_normal_response | ✅ |
| S61 | test_ipinfo_api.py | TestValidateChannelKey | test_with_valid_token | ✅ |
| S62 | test_ipinfo_api.py | TestFetchChannel | test_api_mode_adds_query_time | ✅ |
| S63 | test_ipinfo_api.py | TestIpinfoApiMainIsNetworkError | test_temporary_error_not_written | ✅ |
| S64 | test_ipinfo_api.py | TestRequestChannelApiMode | test_api_mode_timeout_returns_error | ✅ |
| S65 | test_ipinfo_api.py | TestIpinfoApiChannelDisabled | test_token_empty_sets_disabled | ✅ |



---

## 8. IPInfo 免费渠道 ipinfo_free (S66-S71)

| PRD | 测试文件 | 测试类 | 测试方法 | 状态 |
|-----|---------|--------|---------|------|
| S66 | test_ipinfo_free.py | TestIpinfoFreeChannel | test_independent_channel_name | ✅ |
| S67 | test_ipinfo_free.py | TestIpinfoFreeChannel | test_independent_registration | ✅ |
| S68 | test_ipinfo_free.py | TestRequestChannel | test_noapi_returns_different_fields_than_api | ✅ |
| S69 | test_ipinfo_free.py | TestIpinfoFreeMainIsNetworkError | test_temporary_error_not_written | ✅ |
| S70 | test_ipinfo_free.py | TestRequestChannel | test_noapi_mode_rate_limit_returns_error | ✅ |
| S71 | test_ipinfo_free.py | TestIpinfoFreeChannel | test_temporary_error_logged | ✅ |



---

## 9. DNS 反向解析渠道 rdns_ptr (S72-S78)

| PRD | 测试文件 | 测试类 | 测试方法 | 状态 |
|-----|---------|--------|---------|------|
| S72 | test_rdns_ptr.py | TestRequestChannel | test_single_ptr_record | ✅ |
| S73 | test_rdns_ptr.py | TestRequestChannel | test_no_ptr_record_herror | ✅ |
| S74 | test_rdns_ptr.py | TestRequestChannel | test_multiple_ptr_records | ✅ |
| S74 | test_rdns_ptr.py | TestRequestChannel | test_result_contains_query_ip | ✅ |
| S75 | test_rdns_ptr.py | TestRequestChannel | test_no_ptr_record_herror | ✅ |
| S76 | test_rdns_ptr.py | TestRequestChannel | test_network_timeout | ✅ |
| S77 | test_rdns_ptr.py | TestRequestChannel | test_gaierror | ✅ |
| S78 | test_rdns_ptr.py | TestRdnsPtrNetworkUnavailable | test_network_unavailable_not_written_and_circuit_break | ✅ |



---

## 10. WHOIS 查询渠道 (S79-S85)

| PRD | 测试文件 | 测试类 | 测试方法 | 状态 |
|-----|---------|--------|---------|------|
| S79 | test_whois_query.py | TestRequestChannel | test_normal_query | ✅ |
| S80 | test_whois_query.py | TestParseResponse | test_normal_parse | ✅ |
| S81 | test_whois_query.py | TestParseResponse | test_list_fields_take_first | ✅ |
| S82 | test_whois_query.py | TestParseResponse | test_datetime_fields_isoformat | ✅ |
| S83 | test_whois_query.py | TestRequestChannel | test_none_result_returns_error | ✅ |
| S84 | test_whois_query.py | TestWhoisQueryMainIsNetworkError | test_temporary_error_not_written | ✅ |
| S85 | test_whois_query.py | TestRequestChannel | test_timeout_returns_error | ✅ |



---

## 11. SSL 证书渠道 (S86-S93)

| PRD | 测试文件 | 测试类 | 测试方法 | 状态 |
|-----|---------|--------|---------|------|
| S86 | test_ssl_cert.py | TestRequestChannel | test_normal_cert | ✅ |
| S87 | test_ssl_cert.py | TestParseDomains | test_cn_and_san_extracted | ✅ |
| S87 | test_ssl_cert.py | TestParseDomains | test_deduplication | ✅ |
| S88 | test_ssl_cert.py | TestRequestChannel | test_normal_cert | ✅ |
| S89 | test_ssl_cert.py | TestFormatOutput | test_success_result_basic_fields | ✅ |
| S90 | test_ssl_cert.py | TestParseDomains | test_cn_and_san_extracted | ✅ |
| S91 | test_ssl_cert.py | TestRequestChannel | test_no_cert | ✅ |
| S92 | test_ssl_cert.py | TestSslCertMainIsNetworkError | test_temporary_error_not_written | ✅ |
| S93 | test_ssl_cert.py | TestRequestChannel | test_connection_timeout | ✅ |



---

## 12. nmap 端口扫描渠道 (S94-S106)

| PRD | 测试文件 | 测试类 | 测试方法 | 状态 |
|-----|---------|--------|---------|------|
| S94 | test_port_scan.py | TestRequestChannel | test_normal_scan | ✅ |
| S95 | test_port_scan.py | TestParseNmapXml | test_normal_parse | ✅ |
| S96 | test_port_scan.py | TestRequestChannel | test_empty_port_string | ✅ |
| S97 | test_port_scan.py | TestParseNmapXml | test_normal_parse | ✅ |
| S98 | test_port_scan.py | TestParseNmapXml | test_normal_parse | ✅ |
| S99 | test_port_scan.py | TestParseNmapXml | test_no_open_ports | ✅ |
| S100 | test_port_scan.py | TestParseNmapXml | test_invalid_xml | ✅ |
| S100 | test_port_scan.py | TestParseNmapXml | test_malformed_port_id | ⚠️ xfail: BUG |
| S101 | test_port_scan.py | TestValidateEngine | test_nmap_not_found | ✅ |
| S102 | test_port_scan.py | TestValidateEngine | test_nmap_absolute_path_exists | ✅ |
| S103 | test_port_scan.py | TestPortScanMainIsNetworkError | test_temporary_error_not_written_and_circuit_break | ✅ |
| S104 | test_port_scan.py | TestRequestChannel | test_nmap_timeout | ✅ |
| S105 | test_port_scan.py | TestFetchChannel | test_normal_flow | ✅ |
| S106 | test_port_scan.py | TestFetchChannel | test_nonzero_returncode_included | ✅ |



---

## 13. FOFA 搜索渠道 (S107-S116)

| PRD | 测试文件 | 测试类 | 测试方法 | 状态 |
|-----|---------|--------|---------|------|
| S107 | test_fofa_search.py | TestRequestChannel | test_normal_response | ✅ |
| S108 | test_fofa_search.py | TestRequestChannel | test_query_suffix_encoded | ✅ |
| S109 | test_fofa_search.py | TestRequestChannel | test_empty_results | ✅ |
| S110 | test_fofa_search.py | TestFormatOutput | test_adds_query_time_and_fields | ✅ |
| S111 | test_fofa_search.py | TestFormatOutput | test_preserves_existing_query_time | ✅ |
| S112 | test_fofa_search.py | TestFofaSearchChannelDisabled | test_api_key_empty_sets_disabled | ✅ |
| S113 | test_fofa_search.py | TestFofaSearchChannelDisabled | test_api_key_invalid_sets_disabled | ✅ |
| S114 | test_fofa_search.py | TestFofaSearchMainIsNetworkError | test_temporary_error_not_written_and_circuit_break | ✅ |
| S115 | test_fofa_search.py | TestRequestChannel | test_timeout_returns_error | ✅ |
| S116 | test_fofa_search.py | TestRequestChannel | test_invalid_json_returns_error | ✅ |



---

## 14. ZoomEye 渠道 (S117-S125)

| PRD | 测试文件 | 测试类 | 测试方法 | 状态 |
|-----|---------|--------|---------|------|
| S117 | test_zoomeye.py | TestRequestChannel | test_normal_response | ✅ |
| S118 | test_zoomeye.py | TestRequestChannel | test_sub_type_passed | ✅ |
| S119 | test_zoomeye.py | TestRequestChannel | test_empty_results | ✅ |
| S120 | test_zoomeye.py | TestFetchChannel | test_normal_flow | ✅ |
| S121 | test_zoomeye.py | TestRequestChannel | test_api_error_message | ✅ |
| S122 | test_zoomeye.py | TestZoomeyeChannelDisabled | test_api_key_empty_sets_disabled | ✅ |
| S123 | test_zoomeye.py | TestZoomeyeMainIsNetworkError | test_temporary_error_not_written_and_circuit_break | ✅ |
| S124 | test_zoomeye.py | TestRequestChannel | test_timeout_returns_error | ✅ |
| S125 | test_zoomeye.py | TestValidateChannelKey | test_valid_key_succeeds | ✅ |



---

## 15. 批量查询框架 (S126-S140)

| PRD | 测试文件 | 测试类 | 测试方法 | 状态 |
|-----|---------|--------|---------|------|
| S126 | test_base_batch.py | TestBaseBatchQueryLoadIPFile | test_load_ip_file_deduplicates | ✅ |
| S126 | test_base_batch.py | TestBaseBatchQueryLoadIPFile | test_load_ip_file_skips_empty_lines | ✅ |
| S127 | test_batch_run.py | TestBatchMode | test_single_cross_standalone_modes | ✅ |
| S128 | test_base_batch.py | TestBaseBatchQueryGetDelay | test_get_delay_from_settings | ✅ |
| S128 | test_base_batch.py | TestBaseBatchQueryGetDelay | test_get_delay_default_when_missing | ✅ |
| S129 | test_batch_run.py | TestBaseBatchRunStats | test_run_counts_success_and_failure | ✅ |
| S129 | test_batch_run.py | TestBaseBatchRunStats | test_run_stats_tracks_total_elapsed | ✅ |
| S130 | test_batch_run.py | TestBaseBatchRunBasic | test_run_writes_data_for_each_ip | ✅ |
| S131 | test_batch_run.py | TestBaseBatchRunBasic | test_run_saves_progress_for_each_ip | ✅ |
| S132 | test_base_batch.py | TestBaseBatchQueryProgress | test_load_pending_ips_excludes_processed | ✅ |
| S133 | test_writer_threadsafe.py | TestIPWriterLock | test_concurrent_writes_threadsafe | ✅ |
| S134 | test_batch_run.py | TestBaseBatchRunPid | test_run_writes_pid_on_start | ✅ |
| S134 | test_batch_run.py | TestBaseBatchRunPid | test_run_removes_pid_on_completion | ✅ |
| S135 | test_batch_run.py | TestBaseBatchRunPid | test_run_updates_heartbeat_per_ip | ✅ |
| S136 | test_base_batch.py | TestEstimateEta | test_estimate_eta_independent_method | ✅ |
| S137 | test_batch_run.py | TestBaseBatchValidateHook | test_run_calls_do_validate_when_not_skipped | ✅ |
| S137 | test_batch_run.py | TestBaseBatchValidateHook | test_run_skips_validate_when_flag_set | ✅ |
| S138 | test_base_batch.py | TestBaseBatchQueryIsError | test_is_error_detects_raw_error | ✅ |
| S138 | test_base_batch.py | TestBaseBatchQueryIsError | test_is_error_detects_error | ✅ |
| S139 | — | — | — | ⚠️ 由子类决定，无框架级测试 |
| S140 | — | — | — | ⚠️ 由子类决定，无框架级测试 |



---

## 16. 分类引擎 (S141-S146) — 范围外，暂不处理

| PRD | 状态 |
|-----|------|
| S141-S146 | ⏳ 范围外 |

---

## 17. 阶段执行与断点续传 (S147-S155) — 范围外，暂不处理

| PRD | 状态 |
|-----|------|
| S147-S155 | ⏳ 范围外 |

---

## 18. 工具函数 (S156-S160) — 范围外，暂不处理

| PRD | 状态 |
|-----|------|
| S156-S160 | ⏳ 范围外 |

---

## 19. 配置 (S161-S163) — 范围外，暂不处理

| PRD | 状态 |
|-----|------|
| S161-S163 | ⏳ 范围外 |

---

## 20. 管线集成 (S164-S173) — 范围外，暂不处理

| PRD | 状态 |
|-----|------|
| S164-S173 | ⏳ 范围外 |

---

## 缺失汇总（S1-S140 范围内）

> 以下系统性缺失已全部修复（2025-05-20 更新）：
> - "临时性错误不写入存储" → BaseBatchQuery._write_result + 各渠道 main 函数 is_network_error
> - "渠道禁用标志" → 各渠道 Channel.disabled 属性
> - "ipinfo_free 独立渠道" → 新文件 channel/ipinfo_free.py + test_ipinfo_free.py
> - "批量框架三种模式" → batch_mode: single/cross/standalone + _write_result
> - "线程安全写入接口" → IPWriter._lock, test_writer_threadsafe.py
> - "ETA估算独立方法" → estimate_eta() 独立方法

### 框架级待完善

| Story | 说明 |
|-------|------|
| S139 | 由子类决定，无框架级测试 |
| S140 | 由子类决定，无框架级测试 |
