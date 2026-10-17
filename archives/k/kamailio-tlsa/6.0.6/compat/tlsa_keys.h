/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef KSR_TLSA_KEYS_H
#define KSR_TLSA_KEYS_H

/* Register fork callbacks for keys owned by the embedded OpenSSL copy. */
int tlsa_keys_atfork(void) __attribute__((visibility("hidden")));

#endif
