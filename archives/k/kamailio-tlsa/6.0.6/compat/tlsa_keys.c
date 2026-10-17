/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifdef KSR_TLSA_OWNED_KEYS
#include <errno.h>
#include <limits.h>
#include <pthread.h>
#include <stddef.h>
#include "tlsa_keys.h"

#ifndef PTHREAD_KEYS_MAX
#define PTHREAD_KEYS_MAX _POSIX_THREAD_KEYS_MAX
#endif

/* These are slots, not numeric pthread key indices. Key identifiers need
 * not be contiguous, and a deleted key may be reused by another library. */
static struct {
	pthread_key_t key;
	int used;
} tlsa_keys[PTHREAD_KEYS_MAX];
static pthread_mutex_t tlsa_keys_lock = PTHREAD_MUTEX_INITIALIZER;

int __real_pthread_key_create(pthread_key_t *, void (*)(void *));
int __real_pthread_key_delete(pthread_key_t);
int __wrap_pthread_key_create(pthread_key_t *, void (*)(void *))
		__attribute__((visibility("hidden")));
int __wrap_pthread_key_delete(pthread_key_t)
		__attribute__((visibility("hidden")));

int __wrap_pthread_key_create(pthread_key_t *key, void (*destructor)(void *))
{
	size_t i;
	int ret;
	pthread_mutex_lock(&tlsa_keys_lock);
	for(i = 0; i < PTHREAD_KEYS_MAX; i++) {
		if(!tlsa_keys[i].used)
			break;
	}
	if(i == PTHREAD_KEYS_MAX) {
		pthread_mutex_unlock(&tlsa_keys_lock);
		return EAGAIN;
	}
	ret = __real_pthread_key_create(key, destructor);
	if(ret == 0) {
		tlsa_keys[i].key = *key;
		tlsa_keys[i].used = 1;
	}
	pthread_mutex_unlock(&tlsa_keys_lock);
	return ret;
}

int __wrap_pthread_key_delete(pthread_key_t key)
{
	size_t i;
	int ret;
	pthread_mutex_lock(&tlsa_keys_lock);
	ret = __real_pthread_key_delete(key);
	if(ret == 0) {
		for(i = 0; i < PTHREAD_KEYS_MAX; i++) {
			if(tlsa_keys[i].used && tlsa_keys[i].key == key) {
				tlsa_keys[i].used = 0;
				break;
			}
		}
	}
	pthread_mutex_unlock(&tlsa_keys_lock);
	return ret;
}

static void tlsa_keys_prepare(void)
{
	pthread_mutex_lock(&tlsa_keys_lock);
}

static void tlsa_keys_parent(void)
{
	pthread_mutex_unlock(&tlsa_keys_lock);
}

static void tlsa_keys_child(void)
{
	size_t i;
	/* The inherited OpenSSL values refer to the parent's shared-memory
	 * state. Detach them without destructors, preserving unrelated keys. */
	for(i = 0; i < PTHREAD_KEYS_MAX; i++) {
		if(tlsa_keys[i].used)
			pthread_setspecific(tlsa_keys[i].key, NULL);
	}
	pthread_mutex_unlock(&tlsa_keys_lock);
}

int tlsa_keys_atfork(void)
{
	return pthread_atfork(tlsa_keys_prepare, tlsa_keys_parent, tlsa_keys_child);
}
#endif
