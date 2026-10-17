#define _GNU_SOURCE
#include <dlfcn.h>
#include <openssl/ssl.h>
#include <openssl/crypto.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

static pthread_key_t foreign_keys[64];
static unsigned foreign_count;
static int sentinel;
static CRYPTO_malloc_fn saved_malloc;
static CRYPTO_realloc_fn saved_realloc;
static CRYPTO_free_fn saved_free;
static void foreign_destroy(void);

__attribute__((constructor)) static void foreign_init(void)
{
    foreign_count = getenv("TLSA_HIGH_KEYS") ? 64 : 1;
    for (unsigned i = 0; i < foreign_count; ++i) {
        if (pthread_key_create(&foreign_keys[i], NULL) != 0 ||
                pthread_setspecific(foreign_keys[i], &sentinel) != 0) _exit(90);
    }
    CRYPTO_get_mem_functions(&saved_malloc, &saved_realloc, &saved_free);
    SSL_CTX *ctx = SSL_CTX_new(TLS_method());
    if (!ctx) _exit(91);
    SSL_CTX_free(ctx);
    fprintf(stderr, "[FOREIGN_SSL] initialized key=%u pid=%ld\n",
            (unsigned)foreign_keys[foreign_count - 1], (long)getpid());
}

pid_t fork(void)
{
    pid_t (*next_fork)(void) = dlsym(RTLD_NEXT, "fork");
    if (!next_fork) _exit(92);
    pid_t pid = next_fork();
    if (pid >= 0) foreign_destroy();
    if (pid == 0) {
        int preserved = 1;
        for (unsigned i = 0; i < foreign_count; ++i)
            preserved &= pthread_getspecific(foreign_keys[i]) == &sentinel;
        fprintf(stderr, "[FOREIGN_STATE] child=%ld preserved=%d\n",
                (long)getpid(), preserved);
        if (preserved) {
            SSL_CTX *ctx = SSL_CTX_new(TLS_method());
            fprintf(stderr, "[FOREIGN_STATE] child=%ld ssl_context=%d\n",
                    (long)getpid(), ctx != NULL);
            SSL_CTX_free(ctx);
        }
    }
    return pid;
}

__attribute__((destructor)) static void foreign_destroy(void)
{
    CRYPTO_malloc_fn mf; CRYPTO_realloc_fn rf; CRYPTO_free_fn ff;
    CRYPTO_get_mem_functions(&mf, &rf, &ff);
    fprintf(stderr, "[FOREIGN_SSL] allocator_unchanged=%d pid=%ld\n",
            mf == saved_malloc && rf == saved_realloc && ff == saved_free,
            (long)getpid());
}
