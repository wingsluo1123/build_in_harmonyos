#define _GNU_SOURCE
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

static const char *first_env(const char *a, const char *b, const char *c) {
  const char *value = a ? getenv(a) : NULL;
  if (value && value[0]) return value;
  value = b ? getenv(b) : NULL;
  if (value && value[0]) return value;
  value = c ? getenv(c) : NULL;
  if (value && value[0]) return value;
  return NULL;
}

static char *dup_dirname(const char *path) {
  const char *slash = strrchr(path, '/');
  if (!slash) return NULL;
  size_t len = (size_t)(slash - path);
  char *dir = (char *)malloc(len + 1);
  if (!dir) return NULL;
  memcpy(dir, path, len);
  dir[len] = '\0';
  return dir;
}

static char *join_path(const char *a, const char *b) {
  if (!a || !b) return NULL;
  size_t an = strlen(a);
  size_t bn = strlen(b);
  int slash = an > 0 && a[an - 1] == '/';
  char *p = (char *)malloc(an + bn + (slash ? 1 : 2));
  if (!p) return NULL;
  snprintf(p, an + bn + (slash ? 1 : 2), "%s%s%s", a, slash ? "" : "/", b);
  return p;
}

static char *sibling_path(const char *argv0, const char *name) {
  char *dir = dup_dirname(argv0);
  if (!dir) return NULL;
  char *path = join_path(dir, name);
  free(dir);
  return path;
}

static char *toolchain_relative_path(const char *argv0, const char *relative) {
  char *bin_dir = dup_dirname(argv0);
  if (!bin_dir) return NULL;
  char *root = dup_dirname(bin_dir);
  free(bin_dir);
  if (!root) return NULL;
  char *path = join_path(root, relative);
  free(root);
  return path;
}

static int has_arg(int argc, char **argv, const char *arg) {
  for (int i = 1; i < argc; ++i)
    if (strcmp(argv[i], arg) == 0) return 1;
  return 0;
}

static int has_optimization(int argc, char **argv) {
  for (int i = 1; i < argc; ++i) {
    if (strcmp(argv[i], "-O") == 0 ||
        strcmp(argv[i], "-Ounchecked") == 0 ||
        strcmp(argv[i], "-Osize") == 0) {
      return 1;
    }
  }
  return 0;
}

static int has_glibc_modulemap(int argc, char **argv) {
  for (int i = 1; i < argc; ++i) {
    if (strncmp(argv[i], "-fmodule-map-file=", 18) == 0 &&
        strstr(argv[i], "glibc.modulemap")) {
      return 1;
    }
    if (strcmp(argv[i], "-Xcc") == 0 && i + 1 < argc &&
        strncmp(argv[i + 1], "-fmodule-map-file=", 18) == 0 &&
        strstr(argv[i + 1], "glibc.modulemap")) {
      return 1;
    }
  }
  return 0;
}

static const char *find_output(int argc, char **argv) {
  for (int i = 1; i + 1 < argc; ++i)
    if (strcmp(argv[i], "-o") == 0) return argv[i + 1];
  return NULL;
}

static long file_size(const char *path) {
  struct stat st;
  if (!path || stat(path, &st) != 0) return -1;
  return (long)st.st_size;
}

static int run_wait(const char *exe, char **args) {
  pid_t pid = fork();
  if (pid < 0) {
    fprintf(stderr, "[ohos-irhandoff] fork failed: %s\n", strerror(errno));
    return 127;
  }
  if (pid == 0) {
    if (strchr(exe, '/')) execv(exe, args);
    else execvp(exe, args);
    fprintf(stderr, "[ohos-irhandoff] exec failed for %s: %s\n", exe, strerror(errno));
    _exit(127);
  }

  int status = 0;
  while (waitpid(pid, &status, 0) < 0) {
    if (errno == EINTR) continue;
    fprintf(stderr, "[ohos-irhandoff] waitpid failed: %s\n", strerror(errno));
    return 127;
  }
  if (WIFEXITED(status)) return WEXITSTATUS(status);
  if (WIFSIGNALED(status)) return 128 + WTERMSIG(status);
  return 127;
}

static char *make_temp_path(const char *out, const char *suffix) {
  size_t n = strlen(out) + strlen(suffix) + 64;
  char *p = (char *)malloc(n);
  if (!p) return NULL;
  snprintf(p, n, "%s.ohos-irhandoff.%ld.%s", out, (long)getpid(), suffix);
  return p;
}

static const char *select_real(char **argv, char **allocated) {
  const char *slash = strrchr(argv[0], '/');
  const char *name = slash ? slash + 1 : argv[0];
  if (strstr(name, "swift-frontend")) {
    const char *env = getenv("SWIFT_OHOS_REAL_FRONTEND");
    if (env && env[0]) return env;
    *allocated = sibling_path(argv[0], "swift-frontend.real-irhandoff");
    return *allocated ? *allocated : "swift-frontend.real-irhandoff";
  }

  const char *env = getenv("SWIFT_OHOS_REAL_SWIFTC");
  if (env && env[0]) return env;
  *allocated = sibling_path(argv[0], "swiftc.real-irhandoff");
  return *allocated ? *allocated : "swiftc.real-irhandoff";
}

static int should_intercept(int argc, char **argv, const char **out) {
  if (!has_arg(argc, argv, "-frontend")) return 0;
  if (!has_arg(argc, argv, "-c")) return 0;
  if (!has_optimization(argc, argv)) return 0;
  if (has_arg(argc, argv, "-emit-ir") || has_arg(argc, argv, "-emit-sil")) return 0;
  if (has_arg(argc, argv, "-modulewrap")) return 0;
  *out = find_output(argc, argv);
  return *out != NULL;
}

static char *prefixed(const char *prefix, const char *value) {
  size_t pn = strlen(prefix);
  size_t vn = strlen(value);
  char *p = (char *)malloc(pn + vn + 1);
  if (!p) return NULL;
  memcpy(p, prefix, pn);
  memcpy(p + pn, value, vn);
  p[pn + vn] = '\0';
  return p;
}

static void cleanup_owned(char *allocated_real, char *resource_dir,
                          char *arch_dir, char *modulemap_path,
                          char *modulemap_arg, char *ir, char *stripped,
                          char **irargs) {
  free(allocated_real);
  free(resource_dir);
  free(arch_dir);
  free(modulemap_path);
  free(modulemap_arg);
  free(ir);
  free(stripped);
  free(irargs);
}

int main(int argc, char **argv) {
  char *allocated_real = NULL;
  const char *real = select_real(argv, &allocated_real);
  const char *out = NULL;
  if (!should_intercept(argc, argv, &out)) {
    execv(real, argv);
    fprintf(stderr, "[ohos-irhandoff] exec pass-through failed for %s: %s\n", real, strerror(errno));
    free(allocated_real);
    return 127;
  }

  const char *clang = first_env("SWIFT_OHOS_CLANG", "OHOS_CLANG", NULL);
  if (!clang) clang = "clang-15";
  const char *opt = first_env("SWIFT_OHOS_OPT", "OHOS_OPT", NULL);
  if (!opt) opt = "opt";

  const char *sysroot = first_env("OHOS_SDKROOT", "OHOS_SYSROOT", "SDKROOT");
  if (!sysroot) {
    fprintf(stderr, "[ohos-irhandoff] OHOS_SDKROOT/OHOS_SYSROOT/SDKROOT is required for IR handoff\n");
    free(allocated_real);
    return 127;
  }

  char *derived_resource_dir = toolchain_relative_path(argv[0], "lib/swift");
  const char *resource_dir = first_env("SWIFT_OHOS_RESOURCE_DIR", NULL, NULL);
  if (!resource_dir) resource_dir = derived_resource_dir;

  char *derived_arch_dir = resource_dir ? join_path(resource_dir, "ohos/aarch64") : NULL;
  const char *arch_dir = first_env("SWIFT_OHOS_ARCH_DIR", NULL, NULL);
  if (!arch_dir) arch_dir = derived_arch_dir;

  char *modulemap_path = arch_dir ? join_path(arch_dir, "glibc.modulemap") : NULL;
  char *modulemap_arg = NULL;
  if (modulemap_path && file_size(modulemap_path) > 0) {
    modulemap_arg = prefixed("-fmodule-map-file=", modulemap_path);
  }

  char *ir = make_temp_path(out, "ll");
  char *stripped = make_temp_path(out, "strip.ll");
  int rc = 127;
  if (!ir || !stripped || !resource_dir || !arch_dir) goto cleanup;

  int extra = 2; /* -I arch_dir */
  int need_sdk = !has_arg(argc, argv, "-sdk");
  int need_resource = !has_arg(argc, argv, "-resource-dir");
  int need_modulemap = modulemap_arg && !has_glibc_modulemap(argc, argv);
  if (need_sdk) extra += 2;
  if (need_resource) extra += 2;
  if (need_modulemap) extra += 2;

  char **irargs = (char **)calloc((size_t)argc + (size_t)extra + 1, sizeof(char *));
  if (!irargs) goto cleanup;
  int j = 0;
  irargs[j++] = argv[0];
  for (int i = 1; i < argc; ++i) {
    if (strcmp(argv[i], "-c") == 0) irargs[j++] = "-emit-ir";
    else if (i > 1 && strcmp(argv[i - 1], "-o") == 0) irargs[j++] = ir;
    else irargs[j++] = argv[i];
  }
  if (need_sdk) {
    irargs[j++] = "-sdk";
    irargs[j++] = (char *)sysroot;
  }
  if (need_resource) {
    irargs[j++] = "-resource-dir";
    irargs[j++] = (char *)resource_dir;
  }
  irargs[j++] = "-I";
  irargs[j++] = (char *)arch_dir;
  if (need_modulemap) {
    irargs[j++] = "-Xcc";
    irargs[j++] = modulemap_arg;
  }
  irargs[j] = NULL;

  fprintf(stderr, "[ohos-irhandoff] intercept optimized frontend object: %s\n", out);
  int ir_rc = run_wait(real, irargs);
  long ir_size = file_size(ir);
  fprintf(stderr, "[ohos-irhandoff] emit-ir rc=%d size=%ld\n", ir_rc, ir_size);
  if (ir_size <= 0) {
    rc = ir_rc ? ir_rc : 1;
    goto cleanup;
  }

  char *optargs[] = {(char *)opt, "-S", "-strip-debug", ir, "-o", stripped, NULL};
  int opt_rc = run_wait(opt, optargs);
  const char *clang_input = ir;
  if (opt_rc == 0 && file_size(stripped) > 0) clang_input = stripped;
  fprintf(stderr, "[ohos-irhandoff] opt rc=%d input=%s\n", opt_rc, clang_input);

  char *clangargs[] = {
      (char *)clang, "-target", "aarch64-unknown-linux-ohos",
      "--sysroot", (char *)sysroot, "-fPIC", "-c",
      (char *)clang_input, "-o", (char *)out, NULL};
  int clang_rc = run_wait(clang, clangargs);
  long out_size = file_size(out);
  fprintf(stderr, "[ohos-irhandoff] clang rc=%d object-size=%ld\n", clang_rc, out_size);
  rc = clang_rc;

cleanup:
  cleanup_owned(allocated_real, derived_resource_dir, derived_arch_dir,
                modulemap_path, modulemap_arg, ir, stripped, irargs);
  return rc;
}
