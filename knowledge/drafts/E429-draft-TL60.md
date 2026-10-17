# E429-draft-TL60 — Embedded OpenSSL symbol and thread-key ownership

Contributor draft, 2026-10-05. E429 is a provisional draft identifier, not an
assigned official knowledge number. Source package: `kamailio-tlsa/6.0.6`.

## Trigger and diagnostic sequence

A plugin statically embeds PIC OpenSSL and sets a private allocator before SSL
initialization. Another globally visible OpenSSL user initializes first. The
plugin then fails to create an SSL_CTX or its allocator receives a pointer from
the other heap. Function binding alone (`-Bsymbolic-functions`) is insufficient:
default-visible data symbols remain subject to ELF lookup/interposition.

After archive symbols are hidden, a second independent failure can remain:
a fork callback clears a numeric range of pthread keys. Keys allocated earlier
by another module are inside the range even though they are not owned by this
plugin. A fixed scan of the first 32 keys also misses later private keys.
Treat key values as opaque identifiers and track ownership, not order.

Inspect the two boundaries separately:

1. Build the ordinary PIC shared object without symbol hiding. A PIC failure
   must be solved in the dependency; symbol hiding is not its substitute.
2. Inspect dynamic OBJECT relocations and definitions. Keep the plugin's ABI
   exports visible, then localize just the embedded SSL archives.
3. Test a preinitialized, globally visible second OpenSSL, checking its allocator
   callbacks before and after module initialization. Actually exchange TLS data.
4. Add unrelated pthread keys before module initialization, fork workers, and
   verify both their values and independent SSL use in every observed child.
5. Allocate more than 32 preceding keys; successful default-order tests alone
   do not establish ownership correctness.

## Implementation and semantic preservation

The TLSA Makefile keeps `libssl.a`/`libcrypto.a` local with
`-Wl,--exclude-libs,libssl.a:libcrypto.a`; module entry points and references to
the real core stay visible. Linker wrapping of `pthread_key_create` and
`pthread_key_delete` records only references linked into TLSA. The registry
stores opaque key values in bounded slots, removes successfully deleted keys,
and propagates allocation/deletion errors. No external DSO key is registered.

Atfork prepare takes the registry mutex. Parent releases it; child detaches
only still-owned values and then releases it. Detachment does not run
destructors against inherited parent shared-memory state. Core's existing
per-process OpenSSL initialization remains responsible for fresh child state.
The original `tls` module retains its prior path through a TLSA-only feature
guard. See generated patches 0002–0003 and `compat/tlsa_keys.{c,h}` in the package.

The supported lifecycle is Kamailio's registered, resident module with its
normal fork model. Dynamically loaded external providers are outside the
linker-wrapper domain. Unloading a DSO with registered atfork callbacks, FIPS,
PKCS#11, arbitrary multithreaded fork/reinitialization and shared external
OpenSSL objects require a separate lifecycle design and tests.

## Native evidence and negative controls

Environment: OHOS AArch64, HNP SDK 26.0.0.18 / Clang 15, OpenSSL 3.5.8.1
from the published Conan package. Exact upstream tag 6.0.6 commit
`9b4746db7278eece2f693f54a238106449b8cff6`.

| Experiment | Observed result |
|---|---|
| Independent plugin, normal linking | private allocator hook rejected: probe result 10; negative-control harness exit 0 |
| Independent plugin, function binding only | SSL_CTX creation failed: probe result 11, harness exit 6 |
| Independent plugin, SSL archives hidden | private allocation and SSL_CTX succeeded; host allocator unchanged, exit 0 |
| Original real TLSA + static peer | shared allocator reports bad pointer |
| Hidden TLSA + numeric key cleanup | foreign child sentinels report preserved=0 |
| Owned-key TLSA + real matching core | development suite 26/26 assertions, including 64 earlier keys and foreign child SSL |

Raw experiment logs are delivered separately under
`output/kamailio-tlsa-6.0.6/evidence/native/`. The package's Conan consumer
adds ELF/install checks to the same real-core test design. Final package
verification results belong in its reports; the development count above is
not a claim that CI or a full Kamailio suite passed.

An OHOS runtime integration issue was isolated separately with plain TCP:
core daemonization closes C-runtime-owned descriptors, which are subsequently
reused and invalidated around fork. The foreground-only descriptor patch and
`-DD` invocation are documented in `integration.md`. Descriptor repair does
not substitute for either OpenSSL boundary fix.

## Reuse example outside Kamailio

The following two-file dlopen probe isolates symbol/allocator behavior without
any Kamailio API, shared memory or worker machinery. Build against PIC static
OpenSSL. `SSL_PREFIX` must identify that dependency, not the system DSO path.

```sh
cc -I"$SSL_PREFIX/include" -fPIE -pie -Wl,--export-dynamic host.c \
  "$SSL_PREFIX/lib/libssl.a" "$SSL_PREFIX/lib/libcrypto.a" -ldl -pthread -o host
cc -I"$SSL_PREFIX/include" -shared -fPIC plugin.c \
  "$SSL_PREFIX/lib/libssl.a" "$SSL_PREFIX/lib/libcrypto.a" -ldl -pthread -o plain.so
cc -I"$SSL_PREFIX/include" -shared -fPIC -Wl,-Bsymbolic-functions plugin.c \
  "$SSL_PREFIX/lib/libssl.a" "$SSL_PREFIX/lib/libcrypto.a" -ldl -pthread -o bound.so
cc -I"$SSL_PREFIX/include" -shared -fPIC \
  -Wl,--exclude-libs,libssl.a:libcrypto.a plugin.c \
  "$SSL_PREFIX/lib/libssl.a" "$SSL_PREFIX/lib/libcrypto.a" -ldl -pthread -o hidden.so
./host ./plain.so 10
./host ./bound.so 0
./host ./hidden.so 0
```

The middle command is intentionally expected to fail for the recorded
OpenSSL/platform combinations. The first command is a negative control,
not a successful isolation result. Exact outcomes can differ with OpenSSL
version and exported data; diagnose the actual binary before generalizing.

### host.c

```c
#define _GNU_SOURCE
#include <openssl/ssl.h>
#include <openssl/crypto.h>
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv)
{
    CRYPTO_malloc_fn m0,m1;
    CRYPTO_realloc_fn r0,r1;
    CRYPTO_free_fn f0,f1;
    if (argc != 3) return 2;
    CRYPTO_get_mem_functions(&m0,&r0,&f0);
    SSL_CTX *ctx = SSL_CTX_new(TLS_method());
    if (!ctx) return 3;
    SSL_CTX_free(ctx);
    void *handle = dlopen(argv[1],RTLD_NOW|RTLD_LOCAL);
    if (!handle) { fprintf(stderr,"[FAIL] dlopen: %s\n",dlerror()); return 4; }
    int (*probe)(void) = (int (*)(void))dlsym(handle,"probe_private_ssl");
    if (!probe) { fprintf(stderr,"[FAIL] dlsym: %s\n",dlerror()); return 5; }
    int result = probe();
    CRYPTO_get_mem_functions(&m1,&r1,&f1);
    int unchanged = m0==m1 && r0==r1 && f0==f1;
    int expected = atoi(argv[2]);
    printf("[RESULT] private_ssl=%d expected=%d host_allocator_unchanged=%d version=%s\n",result,expected,unchanged,OpenSSL_version(OPENSSL_VERSION));
    /* Keep DSO resident: OpenSSL cleanup handlers retain function pointers. */
    return result==expected && unchanged ? 0 : 6;
}
```

### plugin.c

```c
#include <openssl/ssl.h>
#include <openssl/crypto.h>
#include <stdlib.h>

static unsigned allocations;
static void *own_malloc(size_t n, const char *file, int line)
{ (void)file; (void)line; ++allocations; return malloc(n); }
static void *own_realloc(void *p, size_t n, const char *file, int line)
{ (void)file; (void)line; return realloc(p,n); }
static void own_free(void *p, const char *file, int line)
{ (void)file; (void)line; free(p); }

int probe_private_ssl(void)
{
    if (!CRYPTO_set_mem_functions(own_malloc,own_realloc,own_free)) return 10;
    SSL_CTX *ctx = SSL_CTX_new(TLS_method());
    if (!ctx) return 11;
    SSL_CTX_free(ctx);
    return allocations > 0 ? 0 : 12;
}
```

## Prior-knowledge comparison

Search baseline: official main `1262b4ac24a3244f254c3e8163fa35d04b48f7fb`;
`knowledge/graph`, `knowledge/doc`, `knowledge/drafts`, and Kamailio archives.
Terms: `tlsa`, `Bsymbolic`, `CRYPTO_set_mem`, `pthread`, `fork`, `STATIC_SRCLIB`.

| Existing material | Covered already | Addition here |
|---|---|---|
| kamailio-extras platform-definitions draft | OHOS macros and module-only builds | no duplicate macro contribution; real forked SSL state ownership |
| DRAFT-11941 module dependency pinning | static dependency path selection | complete symbol/allocator domain, including data relocations |
| DRAFT-11942 core plugin consumer | ABI/dlopen and core stubs | real shared-memory allocator, fork workers and network traffic |
| E2188-draft-B94A PIC check | PIC before hiding symbols | independent failed function-binding control, then ownership fix |
| OpenGL dispatcher symbol draft | function symbol selection | OpenSSL data plus TLS key lifecycle across fork |

This is a candidate B2 contribution. Structural validation and local tests do
not assign knowledge credit or C difficulty; those remain review decisions.
