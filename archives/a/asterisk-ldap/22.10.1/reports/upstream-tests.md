# 上游测试清单（asterisk 22.10.1）— 取证

来源：`https://codeload.github.com/asterisk/asterisk/tar.gz/refs/tags/22.10.1`
（sha256 `373c98f4d4a1b923b42def0aee03f4e36aca9d1c244a8eeda646da8a97f89663`，实测）

## 真实测试入口

- 构建（打开测试框架）：`tests/CI/buildAsterisk.sh`
  → `menuselect/menuselect --enable DONT_OPTIMIZE BETTER_BACKTRACES` +
  `--enable TEST_FRAMEWORK` + `--enable-category MENUSELECT_TESTS`
- 运行：`tests/CI/runUnittests.sh` → `asterisk -rx "test execute all"`
  （随后 `test show results failed` / `test generate results xml <file>`）

## 清点结果

**口径声明（重要）**：上游用例数按**全树源码清点口径**申报——统计源码树内所有 `*.c`
中以行首 `AST_TEST_DEFINE(` 注册的用例数。只统计 `tests/` 子集会被平台按「少报」驳回
（pc-pr-review rule4：上游实测 N=707 > 声明 N）。

```bash
$ grep -rh "^AST_TEST_DEFINE(" --include="*.c" . | wc -l              # 707  ← 申报口径
$ grep -rho "AST_TEST_DEFINE([A-Za-z0-9_]*)" --include="*.c" . | wc -l # 707  ← 等价写法
$ grep -rh "^AST_TEST_DEFINE(" tests/*.c | wc -l                       # 633  ← 仅 tests/ 子集
```

- **上游用例总数：707**（全树源码清点口径）
  - `tests/*.c`：**633** 个（95 个文件）
  - 其余 **74** 个：分布在 `res/`、`main/`、`funcs/`、`bridges/`、`apps/` 共 **25** 个
    `.c` 文件（明细见文末「非 tests/ 目录的注册明细」）
- `tests/test_*.c`：**95** 个文件
- 与 LDAP 相关的上游用例：**0** 个（`grep -ril ldap tests/` 仅命中
  `tests/CI/buildAsterisk.sh` 这个构建脚本；95 个 test_*.c 无一涉及 LDAP，上述
  707 个注册中也无一服务于 `res_config_ldap`）
- 本模块（`res/res_config_ldap.c`）无专属 deps/测试注册 → **本模块相关上游用例数 = 0**

## 结论

本包交付的 `res_config_ldap.so` **没有上游自动化用例**（本模块相关 = 0）；而上游
**用例总数 = 707**（清点口径见上）。这 707 个用例属于完整的 asterisk 核心（需
`-o asterisk/*:with_test_framework=True` 构建核心 + 运行中的 PBX 才能执行），本模块包
不构建核心，故**未执行**——如实声明（非跳过、不计入通过率）。两个数字口径不同，
申报表须分别列清，不得把「本模块 0」写成上游合计。

## 逐文件用例数（file, cases, case names）

| file | cases | case names |
|---|---:|---|
| tests/test_abstract_jb.c | 0 | (no AST_TEST_DEFINE) |
| tests/test_acl.c | 2 | invalid_acl, acl |
| tests/test_aeap.c | 4 | create_and_connect, send_msg_handle_string, send_msg_handle_response, send_msg_handle_request |
| tests/test_aeap_speech.c | 1 | res_speech_aeap_test |
| tests/test_aeap_transaction.c | 2 | transaction_exec, transaction_exec_timeout |
| tests/test_aeap_transport.c | 6 | transport_create_invalid, transport_create, transport_connect, transport_connect_fail, transport_binary, transport_string |
| tests/test_amihooks.c | 1 | amihook_cli_send |
| tests/test_aoc.c | 2 | aoc_event_generation_test, aoc_encode_decode_test |
| tests/test_app.c | 2 | options_parsing, app_group |
| tests/test_ari.c | 12 | get_docs, get_docs_nohost, get_docs_notfound, get_docs_hackerz, invoke_get, invoke_wildcard, invoke_delete, invoke_delete_forbidden, invoke_post, invoke_bad_post, invoke_no_user, invoke_not_found |
| tests/test_ari_model.c | 7 | validate_byte, validate_boolean, validate_int, validate_long, validate_string, validate_date, validate_list |
| tests/test_ast_format_str_reduce.c | 1 | ast_format_str_reduce_test_1 |
| tests/test_astobj2.c | 5 | astobj2_test_1, astobj2_test_2, astobj2_test_3, astobj2_test_4, astobj2_test_perf |
| tests/test_astobj2_thrash.c | 1 | hash_test |
| tests/test_astobj2_weaken.c | 2 | astobj2_weak1, astobj2_weak_container |
| tests/test_bridging.c | 1 | test_bridging_deferred_queue |
| tests/test_bucket.c | 20 | bucket_scheme_register, bucket_alloc, bucket_create, bucket_clone, bucket_delete, bucket_is_stale, bucket_json, bucket_retrieve, bucket_file_alloc, bucket_file_create, bucket_file_clone, bucket_file_copy, bucket_file_retrieve, bucket_file_update, bucket_file_delete, bucket_file_is_stale, bucket_file_metadata_set, bucket_file_metadata_unset, bucket_file_metadata_get, bucket_file_json |
| tests/test_callerid.c | 2 | parse_nominal, parse_off_nominal |
| tests/test_capture.c | 5 | test_capture_true, test_capture_false, test_capture_with_stdin, test_capture_with_dynamic, test_capture_stdout_stderr |
| tests/test_cdr.c | 24 | test_cdr_channel_creation, test_cdr_unanswered_inbound_call, test_cdr_unanswered_outbound_call, test_cdr_outbound_bridged_call, test_cdr_single_party, test_cdr_single_bridge, test_cdr_single_bridge_continue, test_cdr_single_twoparty_bridge_a, test_cdr_single_twoparty_bridge_b, test_cdr_single_multiparty_bridge, test_cdr_dial_unanswered, test_cdr_dial_busy, test_cdr_dial_congestion, test_cdr_dial_unavailable, test_cdr_dial_caller_cancel, test_cdr_dial_parallel_failed, test_cdr_dial_answer_no_bridge, test_cdr_dial_answer_twoparty_bridge_a, test_cdr_dial_answer_twoparty_bridge_b, test_cdr_dial_answer_multiparty, test_cdr_park, test_cdr_fields, test_cdr_no_reset_cdr, test_cdr_fork_cdr |
| tests/test_cel.c | 26 | test_cel_channel_creation, test_cel_unanswered_inbound_call, test_cel_unanswered_outbound_call, test_cel_single_party, test_cel_single_bridge, test_cel_single_bridge_continue, test_cel_single_twoparty_bridge_a, test_cel_single_twoparty_bridge_b, test_cel_single_multiparty_bridge, test_cel_dial_unanswered, test_cel_dial_unanswered_filter, test_cel_dial_busy, test_cel_dial_congestion, test_cel_dial_unavailable, test_cel_dial_caller_cancel, test_cel_dial_parallel_failed, test_cel_dial_answer_no_bridge, test_cel_dial_answer_twoparty_bridge_a, test_cel_dial_answer_twoparty_bridge_b, test_cel_dial_answer_multiparty, test_cel_blind_transfer, test_cel_attended_transfer_bridges_swap, test_cel_attended_transfer_bridges_merge, test_cel_attended_transfer_bridges_link, test_cel_dial_pickup, test_cel_local_optimize |
| tests/test_channel.c | 2 | set_fd_grow, add_fd |
| tests/test_channel_feature_hooks.c | 2 | test_features_channel_dtmf, test_features_channel_interval |
| tests/test_codec_translations.c | 1 | codec_translate_roundtrip |
| tests/test_config.c | 12 | copy_config, config_basic_ops, config_filtered_ops, config_template_ops, config_save, config_hook, ast_parse_arg_test, config_options_test, config_dialplan_function, variable_lists_match, variable_list_join_replace, variable_list_from_string |
| tests/test_conversions.c | 6 | str_to_int, str_to_uint, str_to_long, str_to_ulong, str_to_imax, str_to_umax |
| tests/test_core_codec.c | 8 | codec_register, codec_register_twice, codec_register_unknown, codec_register_audio_no_sample_rate, codec_get, codec_get_unregistered, codec_get_unknown, codec_get_id |
| tests/test_core_format.c | 15 | format_create, format_create_attr, format_retrieve_attr, format_clone, format_cmp_same_codec, format_cmp_different_codec, format_attr_cmp_same_codec, format_joint_same_codec, format_attr_joint_same_codec, format_joint_different_codec, format_copy, format_attribute_set_without_interface, format_attribute_get_without_interface, format_parse_sdp_fmtp_without_interface, format_parse_and_generate_sdp_fmtp |
| tests/test_crypto.c | 6 | crypto_rsa_encrypt, crypto_rsa_decrypt, crypto_sign, crypto_verify, crypto_aes_encrypt, crypto_aes_decrypt |
| tests/test_data_buffer.c | 4 | buffer_create, buffer_put, buffer_resize, buffer_nominal |
| tests/test_db.c | 4 | put_get_del, gettree_deltree, perftest, put_get_long |
| tests/test_devicestate.c | 7 | device2extenstate_test, device_state_aggregation_test, devstate_prov_add, devstate_prov_del, devstate_changed, devstate_conversions, devstate_channels |
| tests/test_dlinklists.c | 0 | (no AST_TEST_DEFINE) |
| tests/test_dns.c | 13 | resolver_register_unregister, resolver_register_off_nominal, resolver_unregister_off_nominal, resolver_data, resolver_set_result, resolver_set_result_off_nominal, resolver_add_record, resolver_add_record_off_nominal, resolver_resolve_sync, resolver_resolve_sync_off_nominal, resolver_resolve_async, resolver_resolve_async_off_nominal, resolver_resolve_async_cancel |
| tests/test_dns_naptr.c | 6 | naptr_resolve_nominal, naptr_resolve_off_nominal_length, naptr_resolve_off_nominal_flags, naptr_resolve_off_nominal_services, naptr_resolve_off_nominal_regexp, naptr_resolve_off_nominal_interactions |
| tests/test_dns_query_set.c | 4 | query_set, query_set_empty, query_set_nominal_cancel, query_set_off_nominal_cancel |
| tests/test_dns_recurring.c | 4 | recurring_query, recurring_query_off_nominal, recurring_query_cancel_between, recurring_query_cancel_during |
| tests/test_dns_srv.c | 8 | srv_resolve_single_record, srv_resolve_sort_priority, srv_resolve_same_priority_zero_weight, srv_resolve_same_priority_different_weights, srv_resolve_different_priorities_different_weights, srv_resolve_record_missing_weight_port_host, srv_resolve_record_missing_port_host, srv_resolve_record_missing_host |
| tests/test_endpoints.c | 3 | create, defaults, setters |
| tests/test_event.c | 1 | event_new_test |
| tests/test_expr.c | 1 | expr_test |
| tests/test_file.c | 1 | read_dirs_test |
| tests/test_format_cache.c | 5 | format_cache_set, format_cache_set_duplicate, format_cache_set_null, format_cache_get, format_cache_get_nonexistent |
| tests/test_format_cap.c | 20 | format_cap_alloc, format_cap_append_single, format_cap_append_multiple, format_cap_append_all_unknown, format_cap_append_all_audio, format_cap_append_duplicate, format_cap_append_from_cap, format_cap_append_from_cap_duplicate, format_cap_set_framing, format_cap_remove_single, format_cap_remove_multiple, format_cap_remove_bytype, format_cap_remove_all, format_cap_get_compatible_format, format_cap_iscompatible_format, format_cap_get_compatible, format_cap_iscompatible, format_cap_get_names, format_cap_best_by_type, format_cap_replace_from_cap |
| tests/test_func_file.c | 1 | test_func_file |
| tests/test_gosub.c | 1 | test_gosub |
| tests/test_hashtab_thrash.c | 1 | hash_test |
| tests/test_heap.c | 3 | heap_test_1, heap_test_2, heap_test_3 |
| tests/test_http_media_cache.c | 9 | retrieve_content_type, retrieve_parsed_uri, retrieve_cache_control_directives, retrieve_cache_control_age, retrieve_etag_expired, retrieve_expires, retrieve_etag, retrieve_nominal, create_nominal |
| tests/test_jitterbuf.c | 12 | jitterbuffer_nominal_voice_frames, jitterbuffer_nominal_control_frames, jitterbuffer_out_of_order_voice, jitterbuffer_out_of_order_control, jitterbuffer_lost_voice, jitterbuffer_lost_control, jitterbuffer_late_voice, jitterbuffer_late_control, jitterbuffer_overflow_voice, jitterbuffer_overflow_control, jitterbuffer_resynch_control, jitterbuffer_resynch_voice |
| tests/test_json.c | 52 | json_test_false, json_test_true, json_test_bool0, json_test_bool1, json_test_null, json_test_null_val, json_test_string, json_test_string_null, json_test_stringf, json_test_int, json_test_non_int, json_test_array_create, json_test_array_append, json_test_array_inset, json_test_array_set, json_test_array_remove, json_test_array_clear, json_test_array_extend, json_test_array_null, json_test_object_alloc, json_test_object_set, json_test_object_set_overwrite, json_test_object_get, json_test_object_del, json_test_object_clear, json_test_object_merge_all, json_test_object_merge_existing, json_test_object_merge_missing, json_test_object_null, json_test_object_iter, json_test_object_iter_null, json_test_object_create_vars, json_test_dump_load_string, json_test_dump_load_str, json_test_dump_str_fail, json_test_load_buffer, json_test_dump_load_file, json_test_dump_load_new_file, json_test_dump_load_null, json_test_parse_errors, json_test_pack, json_test_pack_ownership, json_test_pack_errors, json_test_copy, json_test_deep_copy, json_test_copy_null, json_test_circular_object, json_test_circular_array, json_test_clever_circle, json_test_name_number, json_test_timeval, json_test_cep |
| tests/test_linkedlists.c | 2 | single_ll_tests, double_ll_tests |
| tests/test_locale.c | 0 | (no AST_TEST_DEFINE) |
| tests/test_logger.c | 0 | (no AST_TEST_DEFINE) |
| tests/test_media_cache.c | 5 | exists_nominal, exists_off_nominal, create_update_nominal, create_update_off_nominal, create_update_metadata |
| tests/test_message.c | 9 | test_message_msg_tech_registration, test_message_msg_handler_registration, test_message_manipulation, test_message_queue_dialplan_nominal, test_message_queue_handler_nominal, test_message_queue_both_nominal, test_message_has_destination_dialplan, test_message_has_destination_handler, test_message_msg_send |
| tests/test_mwi.c | 2 | implicit_publish, explicit_publish |
| tests/test_named_lock.c | 1 | named_lock_test |
| tests/test_netsock2.c | 2 | parsing, split_hostport |
| tests/test_optional_api.c | 2 | test_provide_first, test_provide_last |
| tests/test_pbx.c | 6 | pattern_match_test, segv, call_assert, call_backtrace, just_fail, just_pass |
| tests/test_poll.c | 1 | poll_test |
| tests/test_res_pjsip_scheduler.c | 5 | serialized_scheduler, unserialized_scheduler, scheduler_cleanup, scheduler_cancel, scheduler_policy |
| tests/test_res_pjsip_session_caps.c | 1 | low_level |
| tests/test_res_prometheus.c | 11 | metric_values, metric_callback_register, metric_register, counter_to_string, counter_create, gauge_to_string, gauge_create, config_general_basic_auth, config_general_enabled, config_general_core_metrics, bridge_to_string |
| tests/test_res_rtp.c | 8 | nack_no_packet_loss, nack_nominal, nack_overflow, lost_packet_stats_nominal, remb_nominal, sr_rr_nominal, fir_nominal, mes |
| tests/test_res_stasis.c | 3 | app_invoke_dne, app_invoke_one, app_replaced |
| tests/test_sched.c | 2 | sched_test_order, sched_test_freebird |
| tests/test_scope_trace.c | 1 | scope_test |
| tests/test_scoped_lock.c | 2 | lock_test, cleanup_order |
| tests/test_security_events.c | 0 | (no AST_TEST_DEFINE) |
| tests/test_skel.c | 1 | sample_test |
| tests/test_sorcery.c | 51 | wizard_registration, sorcery_open, apply_default, apply_config, object_register, object_register_without_mapping, object_field_register, object_fields_register, object_alloc_with_id, object_alloc_without_id, object_copy, object_copy_native, object_diff, object_diff_native, objectset_create, objectset_json_create, objectset_create_regex, objectset_apply, objectset_apply_handler, objectset_apply_invalid, objectset_transform, objectset_apply_fields, extended_fields, changeset_create, changeset_create_unchanged, object_create, object_retrieve_id, object_retrieve_field, object_retrieve_multiple_all, object_retrieve_multiple_field, object_retrieve_regex, object_update, object_update_uncreated, object_delete, object_delete_uncreated, object_is_stale, caching_wizard_behavior, object_type_observer, configuration_file_wizard, configuration_file_wizard_with_file_integrity, configuration_file_wizard_with_criteria, configuration_file_wizard_retrieve_field, configuration_file_wizard_retrieve_multiple, configuration_file_wizard_retrieve_multiple_all, dialplan_function, object_field_registered, global_observation, instance_observation, wizard_observation, wizard_apply_and_insert, wizard_read_only |
| tests/test_sorcery_astdb.c | 10 | object_create, object_retrieve_id, object_retrieve_field, object_retrieve_multiple_all, object_retrieve_multiple_field, object_retrieve_regex, object_update, object_update_uncreated, object_delete, object_delete_uncreated |
| tests/test_sorcery_memory_cache_thrash.c | 7 | low_unique_object_count_immediately_stale, low_unique_object_count_immediately_expire, low_unique_object_count_high_concurrent_updates, unique_objects_exceeding_maximum, unique_objects_exceeding_maximum_with_expire_and_stale, conflicting_expire_and_stale, high_object_count_without_expiration |
| tests/test_sorcery_realtime.c | 13 | object_create, object_retrieve_id, object_retrieve_field, object_retrieve_multiple_all, object_retrieve_multiple_all_nofetch, object_retrieve_multiple_field, object_retrieve_regex, object_retrieve_regex_nofetch, object_update, object_delete, object_delete_uncreated, object_allocate_on_retrieval, object_filter |
| tests/test_stasis.c | 27 | message_type, message, subscription_messages, subscription_pool_messages, publish, publish_sync, publish_pool, unsubscribe_stops_messages, forward, interleaving, subscription_interleaving, cache_filter, cache, cache_dump, cache_eid_aggregate, router, router_pool, router_cache_updates, no_to_json, to_json, no_to_ami, to_ami, dtor_order, caching_dtor_order, type_filters, formatter_filters, combo_filters |
| tests/test_stasis_channels.c | 6 | channel_blob_create, null_blob, multi_channel_blob_create, multi_channel_blob_snapshots, channel_snapshot_json, channel_redirect_snapshot_json |
| tests/test_stasis_endpoints.c | 3 | state_changes, cache_clear, channel_messages |
| tests/test_stasis_state.c | 2 | implicit_publish, explicit_publish |
| tests/test_stream.c | 25 | stream_create, stream_create_no_name, stream_set_type, stream_set_formats, stream_set_state, stream_metadata, stream_topology_create, stream_topology_clone, stream_topology_append_stream, stream_topology_set_stream, stream_topology_del_stream, stream_topology_create_from_format_cap, stream_topology_get_first_stream_by_type, stream_topology_create_from_channel_nativeformats, stream_topology_channel_set, stream_write_non_multistream, stream_write_multistream, stream_read_non_multistream, stream_read_multistream, stream_topology_change_request_from_application_non_multistream, stream_topology_change_request_from_channel_non_multistream, stream_topology_change_request_from_application, stream_topology_change_request_from_channel, format_cap_from_stream_topology, stream_topology_map_create |
| tests/test_stringfields.c | 2 | string_field_test, string_field_aggregate_test |
| tests/test_strings.c | 10 | str_test, begins_with_test, ends_with_test, strsep_test, strsep_quoted_test, escape_semicolons_test, escape_test, strings_match, temp_strings, in_delimited_string |
| tests/test_substitution.c | 1 | test_substitution |
| tests/test_taskpool.c | 10 | taskpool_push, taskpool_push_synchronous, taskpool_push_serializer, taskpool_push_serializer_synchronous, taskpool_push_serializer_synchronous_requeue, taskpool_push_grow, taskpool_push_shrink, taskpool_serializer_suspension, taskpool_serializer_multiple_suspension, taskpool_serializer_push_wait_while_suspended_from_other_serializer |
| tests/test_taskprocessor.c | 8 | default_taskprocessor, subsystem_alert, default_taskprocessor_load, taskprocessor_listener, taskprocessor_shutdown, taskprocessor_push_local, serializer_pool, taskprocessor_cli_show |
| tests/test_threadpool.c | 16 | threadpool_push, threadpool_initial_threads, threadpool_thread_creation, threadpool_thread_destruction, threadpool_thread_timeout, threadpool_thread_timeout_thrash, threadpool_one_task_one_thread, threadpool_one_thread_one_task, threadpool_one_thread_multiple_tasks, threadpool_auto_increment, threadpool_max_size, threadpool_reactivation, threadpool_task_distribution, threadpool_more_destruction, threadpool_serializer, threadpool_serializer_dupe |
| tests/test_time.c | 5 | test_timezone_watch, test_time_str_to_unit, test_time_create_by_unit, test_time_create_by_unit_str, test_time_tv_to_usec |
| tests/test_uri.c | 3 | uri_parse, uri_default_http, uri_default_http_secure |
| tests/test_utils.c | 12 | uri_encode_decode_test, quoted_escape_test, md5_test, sha1_test, base64_test, crypto_loaded_test, adsi_loaded_test, agi_loaded_test, safe_mkdir_test, crypt_test, quote_mutation, quote_unescaping |
| tests/test_uuid.c | 1 | uuid |
| tests/test_vector.c | 4 | basic_ops, basic_ops_integer, callbacks, locks |
| tests/test_voicemail_api.c | 10 | voicemail_api_nominal_snapshot, voicemail_api_off_nominal_snapshot, voicemail_api_nominal_move, voicemail_api_off_nominal_move, voicemail_api_nominal_remove, voicemail_api_off_nominal_remove, voicemail_api_nominal_forward, voicemail_api_off_nominal_forward, voicemail_api_nominal_msg_playback, voicemail_api_off_nominal_msg_playback |
| tests/test_websocket_client.c | 4 | websocket_client_create_and_connect, websocket_client_bad_url, websocket_client_unsupported_protocol, websocket_client_multiple_protocols |
| tests/test_xml_escape.c | 1 | xml_escape_test |

## 非 tests/ 目录的注册明细（74 个 / 25 个文件）

全树口径 707 = tests/*.c 633 + 下列 74。Asterisk 允许模块在自身 .c 里用
`AST_TEST_DEFINE` 注册自测用例（如 `res/res_sorcery_memory_cache.c`），故清点不能只看 tests/。

| file | cases |
|---|---:|
| res/res_sorcery_memory_cache.c | 10 |
| res/res_pjsip_pubsub.c | 7 |
| res/res_resolver_unbound.c | 7 |
| apps/app_voicemail.c | 6 |
| funcs/func_strings.c | 6 |
| res/parking/parking_tests.c | 6 |
| funcs/func_presencestate.c | 4 |
| main/utf8.c | 4 |
| main/manager.c | 3 |
| bridges/bridge_softmix.c | 2 |
| main/dsp.c | 2 |
| res/res_geolocation/geoloc_eprofile.c | 2 |
| res/res_pjproject.c | 2 |
| res/res_pjsip.c | 2 |
| funcs/func_curl.c | 1 |
| funcs/func_json.c | 1 |
| funcs/func_math.c | 1 |
| funcs/func_sayfiles.c | 1 |
| main/channelstorage.c | 1 |
| main/pbx_variables.c | 1 |
| main/presencestate.c | 1 |
| main/test.c | 1 |
| res/res_agi.c | 1 |
| res/res_pjsip_session.c | 1 |
| res/res_timing_kqueue.c | 1 |
| **合计** | **74**（25 个文件） |
