/*
 * lttng-ust 2.12.10 consumer probe — tracepoint provider definition.
 *
 * 与 doc/examples/easy-ust 同款两段式：本头文件只声明事件，
 * tp.c 用 TRACEPOINT_CREATE_PROBES 展开探针代码对象。
 */
#undef TRACEPOINT_PROVIDER
#define TRACEPOINT_PROVIDER lttng_ust_probe

#undef TRACEPOINT_INCLUDE
#define TRACEPOINT_INCLUDE "./probe_tp.h"

#if !defined(_LTTNG_UST_PROBE_TP_H) || defined(TRACEPOINT_HEADER_MULTI_READ)
#define _LTTNG_UST_PROBE_TP_H

#include <lttng/tracepoint.h>

TRACEPOINT_EVENT(
	lttng_ust_probe,
	message,
	TP_ARGS(char *, text),
	TP_FIELDS(
		ctf_string(message, text)
	)
)

TRACEPOINT_LOGLEVEL(lttng_ust_probe, message, TRACE_WARNING)

#endif /* _LTTNG_UST_PROBE_TP_H */

#include <lttng/tracepoint-event.h>
