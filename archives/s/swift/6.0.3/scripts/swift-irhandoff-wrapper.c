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

static char *dup_string(const char *value) {
  char *copy = (char *)malloc(strlen(value) + 1);
  if (!copy) return NULL;
  strcpy(copy, value);
  return copy;
}

static char *resolve_invocation_path(const char *argv0) {
  if (strchr(argv0, '/')) return dup_string(argv0);

  const char *path = getenv("PATH");
  if (!path || !path[0]) return dup_string(argv0);

  char *path_copy = dup_string(path);
  if (!path_copy) return dup_string(argv0);

  char *save = NULL;
  for (char *dir = strtok_r(path_copy, ":", &save); dir;
       dir = strtok_r(NULL, ":", &save)) {
    if (!dir[0]) dir = ".";
    char *candidate = join_path(dir, argv0);
    if (candidate && access(candidate, X_OK) == 0) {
      free(path_copy);
      return candidate;
    }
    free(candidate);
  }

  free(path_copy);
  return dup_string(argv0);
}

static int ends_with(const char *value, const char *suffix) {
  size_t vn = strlen(value);
  size_t sn = strlen(suffix);
  return vn >= sn && strcmp(value + vn - sn, suffix) == 0;
}

static char *strip_path_suffix(const char *path, const char *suffix) {
  size_t pn = strlen(path);
  size_t sn = strlen(suffix);
  if (pn < sn || strcmp(path + pn - sn, suffix) != 0) return NULL;
  char *p = (char *)malloc(pn - sn + 1);
  if (!p) return NULL;
  memcpy(p, path, pn - sn);
  p[pn - sn] = '\0';
  return p;
}

static char *argv0_for_exe(const char *exe) {
  if (ends_with(exe, ".real-irhandoff.real")) {
    char *tool_argv0 = strip_path_suffix(exe, ".real-irhandoff.real");
    if (tool_argv0) return tool_argv0;
  }
  return dup_string(exe);
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

static int has_arg_or_joined(int argc, char **argv, const char *arg) {
  size_t len = strlen(arg);
  for (int i = 1; i < argc; ++i) {
    if (strcmp(argv[i], arg) == 0) return 1;
    if (strncmp(argv[i], arg, len) == 0 && argv[i][len] == '=') return 1;
  }
  return 0;
}

static int has_arg_prefix(int argc, char **argv, const char *prefix) {
  size_t len = strlen(prefix);
  for (int i = 1; i < argc; ++i)
    if (strncmp(argv[i], prefix, len) == 0) return 1;
  return 0;
}

static int has_swift_input(int argc, char **argv) {
  for (int i = 1; i < argc; ++i) {
    size_t len = strlen(argv[i]);
    if (len > 6 && strcmp(argv[i] + len - 6, ".swift") == 0) return 1;
  }
  return 0;
}

static int is_compile_only_driver_job(int argc, char **argv) {
  return has_arg(argc, argv, "-c") ||
         has_arg(argc, argv, "-emit-object") ||
         has_arg(argc, argv, "-emit-module");
}

static int has_linker_code_sign(int argc, char **argv) {
  for (int i = 1; i < argc; ++i) {
    if (strcmp(argv[i], "-Xlinker=--code-sign") == 0) return 1;
    if (strcmp(argv[i], "-Xlinker") == 0 && i + 1 < argc &&
        strcmp(argv[i + 1], "--code-sign") == 0) {
      return 1;
    }
  }
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

static int exec_with_real_argv0(const char *exe, int argc, char **argv) {
  char **args = (char **)calloc((size_t)argc + 1, sizeof(char *));
  char *forward_argv0 = argv0_for_exe(exe);
  if (!args) {
    fprintf(stderr, "[ohos-irhandoff] calloc failed while forwarding to %s\n", exe);
    free(forward_argv0);
    return 127;
  }
  if (!forward_argv0) {
    fprintf(stderr, "[ohos-irhandoff] malloc failed while forwarding to %s\n", exe);
    free(args);
    return 127;
  }
  args[0] = forward_argv0;
  for (int i = 1; i < argc; ++i) args[i] = argv[i];
  args[argc] = NULL;
  if (strchr(exe, '/')) execv(exe, args);
  else execvp(exe, args);
  fprintf(stderr, "[ohos-irhandoff] exec pass-through failed for %s: %s\n", exe, strerror(errno));
  free(forward_argv0);
  free(args);
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
    if (strcmp(name, "swift-frontend.real-irhandoff") == 0) {
      *allocated = sibling_path(argv[0], "swift-frontend.real-irhandoff.real");
      return *allocated ? *allocated : "swift-frontend.real-irhandoff.real";
    }
    *allocated = sibling_path(argv[0], "swift-frontend.real-irhandoff");
    return *allocated ? *allocated : "swift-frontend.real-irhandoff";
  }

  const char *env = getenv("SWIFT_OHOS_REAL_SWIFTC");
  if (env && env[0]) return env;
  if (strcmp(name, "swiftc.real-irhandoff") == 0) {
    *allocated = sibling_path(argv[0], "swiftc.real-irhandoff.real");
    return *allocated ? *allocated : "swiftc.real-irhandoff.real";
  }
  *allocated = sibling_path(argv[0], "swiftc.real-irhandoff");
  return *allocated ? *allocated : "swiftc.real-irhandoff";
}

static int has_arg_value(int argc, char **argv, const char *arg,
                         const char *value) {
  for (int i = 1; i + 1 < argc; ++i)
    if (strcmp(argv[i], arg) == 0 && strcmp(argv[i + 1], value) == 0) return 1;
  size_t arg_len = strlen(arg);
  size_t value_len = strlen(value);
  for (int i = 1; i < argc; ++i) {
    if (strncmp(argv[i], arg, arg_len) == 0 && argv[i][arg_len] == '=' &&
        strlen(argv[i] + arg_len + 1) == value_len &&
        strcmp(argv[i] + arg_len + 1, value) == 0) {
      return 1;
    }
  }
  return 0;
}

static int should_inject_driver_defaults(int argc, char **argv) {
  const char *slash = strrchr(argv[0], '/');
  const char *name = slash ? slash + 1 : argv[0];
  if (strstr(name, "swift-frontend")) return 0;
  if (has_arg(argc, argv, "-frontend")) return 0;
  if (has_arg(argc, argv, "-help") || has_arg(argc, argv, "--help") ||
      has_arg(argc, argv, "-help-hidden") || has_arg(argc, argv, "--version")) {
    return 0;
  }
  if (has_arg_value(argc, argv, "-target", "aarch64-unknown-linux-ohos")) return 1;
  return has_swift_input(argc, argv);
}

static int should_intercept(int argc, char **argv, const char **out) {
  if (!has_arg(argc, argv, "-frontend")) return 0;
  if (!has_arg(argc, argv, "-c")) return 0;
  if (!has_arg_value(argc, argv, "-target", "aarch64-unknown-linux-ohos")) return 0;
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

static char *with_appended_suffix(const char *path, const char *suffix) {
  size_t pn = strlen(path);
  size_t sn = strlen(suffix);
  char *p = (char *)malloc(pn + sn + 1);
  if (!p) return NULL;
  memcpy(p, path, pn);
  memcpy(p + pn, suffix, sn);
  p[pn + sn] = '\0';
  return p;
}

static char *driver_real_path(const char *real) {
  if (ends_with(real, ".real-irhandoff")) {
    char *candidate = with_appended_suffix(real, ".real");
    if (candidate && file_size(candidate) > 0) return candidate;
    free(candidate);
  }
  return dup_string(real);
}

static int exec_driver_with_defaults(const char *real, int argc, char **argv) {
  char *bin_dir = dup_dirname(argv[0]);
  char *resource_dir = toolchain_relative_path(argv[0], "lib/swift");
  char *frontend_path = bin_dir ? join_path(bin_dir, "swift-frontend") : NULL;
  char *final_real = driver_real_path(real);
  char *driver_argv0 = final_real ? argv0_for_exe(final_real) : NULL;
  const char *sysroot = first_env("OHOS_SDKROOT", "OHOS_SYSROOT", "SDKROOT");
  int will_link = !is_compile_only_driver_job(argc, argv);

  if (!bin_dir || !resource_dir || !frontend_path || !final_real || !driver_argv0) {
    fprintf(stderr, "[ohos-irhandoff] failed to derive Swift OHOS driver defaults\n");
    free(bin_dir);
    free(resource_dir);
    free(frontend_path);
    free(final_real);
    free(driver_argv0);
    return 127;
  }
  if (!has_arg_or_joined(argc, argv, "-sdk") && !sysroot) {
    fprintf(stderr, "[ohos-irhandoff] OHOS_SDKROOT/OHOS_SYSROOT/SDKROOT is required for Swift OHOS driver defaults\n");
    free(bin_dir);
    free(resource_dir);
    free(frontend_path);
    free(final_real);
    free(driver_argv0);
    return 127;
  }

  int extra = 0;
  if (!has_arg_or_joined(argc, argv, "-sdk")) extra += 2;
  if (!has_arg_or_joined(argc, argv, "-resource-dir")) extra += 2;
  if (!has_arg_or_joined(argc, argv, "-tools-directory")) extra += 2;
  if (!has_arg_or_joined(argc, argv, "-driver-use-frontend-path")) extra += 2;
  if (will_link && !has_arg_prefix(argc, argv, "-use-ld")) extra += 1;
  if (will_link && !has_linker_code_sign(argc, argv)) extra += 2;

  char **args = (char **)calloc((size_t)argc + (size_t)extra + 1, sizeof(char *));
  if (!args) {
    fprintf(stderr, "[ohos-irhandoff] calloc failed while injecting Swift OHOS driver defaults\n");
    free(bin_dir);
    free(resource_dir);
    free(frontend_path);
    free(final_real);
    free(driver_argv0);
    return 127;
  }

  int j = 0;
  args[j++] = driver_argv0;
  for (int i = 1; i < argc; ++i) args[j++] = argv[i];
  if (!has_arg_or_joined(argc, argv, "-sdk")) {
    args[j++] = "-sdk";
    args[j++] = (char *)sysroot;
  }
  if (!has_arg_or_joined(argc, argv, "-resource-dir")) {
    args[j++] = "-resource-dir";
    args[j++] = resource_dir;
  }
  if (!has_arg_or_joined(argc, argv, "-tools-directory")) {
    args[j++] = "-tools-directory";
    args[j++] = bin_dir;
  }
  if (!has_arg_or_joined(argc, argv, "-driver-use-frontend-path")) {
    args[j++] = "-driver-use-frontend-path";
    args[j++] = frontend_path;
  }
  if (will_link && !has_arg_prefix(argc, argv, "-use-ld")) {
    args[j++] = "-use-ld=lld";
  }
  if (will_link && !has_linker_code_sign(argc, argv)) {
    args[j++] = "-Xlinker";
    args[j++] = "--code-sign";
  }
  args[j] = NULL;

  if (strchr(final_real, '/')) execv(final_real, args);
  else execvp(final_real, args);
  fprintf(stderr, "[ohos-irhandoff] exec driver failed for %s: %s\n", final_real, strerror(errno));
  free(args);
  free(bin_dir);
  free(resource_dir);
  free(frontend_path);
  free(final_real);
  free(driver_argv0);
  return 127;
}

static void cleanup_owned(char *resolved_argv0, char *allocated_real, char *real_argv0,
                          char *derived_llc, char *derived_opt, char *resource_dir,
                          char *arch_dir, char *modulemap_path,
                          char *modulemap_arg, char *ir, char *stripped,
                          char **irargs) {
  if (!getenv("SWIFT_OHOS_KEEP_IRHANDOFF_TEMPS")) {
    if (ir) unlink(ir);
    if (stripped) unlink(stripped);
  }
  free(resolved_argv0);
  free(allocated_real);
  free(real_argv0);
  free(derived_llc);
  free(derived_opt);
  free(resource_dir);
  free(arch_dir);
  free(modulemap_path);
  free(modulemap_arg);
  free(ir);
  free(stripped);
  free(irargs);
}

int main(int argc, char **argv) {
  char *resolved_argv0 = resolve_invocation_path(argv[0]);
  if (resolved_argv0) argv[0] = resolved_argv0;

  char *allocated_real = NULL;
  const char *real = select_real(argv, &allocated_real);
  if (should_inject_driver_defaults(argc, argv)) {
    int driver_rc = exec_driver_with_defaults(real, argc, argv);
    free(resolved_argv0);
    free(allocated_real);
    return driver_rc;
  }

  const char *out = NULL;
  if (!should_intercept(argc, argv, &out)) {
    int exec_rc = exec_with_real_argv0(real, argc, argv);
    free(resolved_argv0);
    free(allocated_real);
    return exec_rc;
  }

  char *derived_llc = sibling_path(argv[0], "llc");
  char *derived_opt = sibling_path(argv[0], "opt");
  const char *llc = first_env("SWIFT_OHOS_LLC", "OHOS_LLC", NULL);
  if (!llc && derived_llc && file_size(derived_llc) > 0) llc = derived_llc;
  if (!llc) llc = "llc";
  const char *opt = first_env("SWIFT_OHOS_OPT", "OHOS_OPT", NULL);
  if (!opt && derived_opt && file_size(derived_opt) > 0) opt = derived_opt;
  if (!opt) opt = "opt";

  const char *sysroot = first_env("OHOS_SDKROOT", "OHOS_SYSROOT", "SDKROOT");
  if (!sysroot) {
    fprintf(stderr, "[ohos-irhandoff] OHOS_SDKROOT/OHOS_SYSROOT/SDKROOT is required for IR handoff\n");
    free(resolved_argv0);
    free(allocated_real);
    free(derived_llc);
    free(derived_opt);
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
  char *real_argv0 = argv0_for_exe(real);
  int rc = 127;
  char **irargs = NULL;
  if (!ir || !stripped || !resource_dir || !arch_dir || !real_argv0) goto cleanup;

  int extra = 2; /* -I arch_dir */
  int need_sdk = !has_arg(argc, argv, "-sdk");
  int need_resource = !has_arg(argc, argv, "-resource-dir");
  int need_modulemap = modulemap_arg && !has_glibc_modulemap(argc, argv);
  if (need_sdk) extra += 2;
  if (need_resource) extra += 2;
  if (need_modulemap) extra += 2;

  irargs = (char **)calloc((size_t)argc + (size_t)extra + 1, sizeof(char *));
  if (!irargs) goto cleanup;
  int j = 0;
  irargs[j++] = real_argv0;
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

  fprintf(stderr, "[ohos-irhandoff] intercept OHOS frontend object: %s\n", out);
  int ir_rc = run_wait(real, irargs);
  long ir_size = file_size(ir);
  fprintf(stderr, "[ohos-irhandoff] emit-ir rc=%d size=%ld\n", ir_rc, ir_size);
  if (ir_rc != 0) {
    rc = ir_rc;
    goto cleanup;
  }
  if (ir_size <= 0) {
    rc = 1;
    goto cleanup;
  }

  char *optargs[] = {(char *)opt, "-S", "-strip-debug", ir, "-o", stripped, NULL};
  int opt_rc = run_wait(opt, optargs);
  const char *llc_input = ir;
  if (opt_rc == 0 && file_size(stripped) > 0) llc_input = stripped;
  fprintf(stderr, "[ohos-irhandoff] opt rc=%d input=%s\n", opt_rc, llc_input);

  char *llcargs[] = {
      (char *)llc, "-filetype=obj", "-relocation-model=pic",
      "-mtriple=aarch64-unknown-linux-ohos",
      (char *)llc_input, "-o", (char *)out, NULL};
  int llc_rc = run_wait(llc, llcargs);
  long out_size = file_size(out);
  fprintf(stderr, "[ohos-irhandoff] llc rc=%d object-size=%ld\n", llc_rc, out_size);
  rc = llc_rc;

cleanup:
  cleanup_owned(resolved_argv0, allocated_real, real_argv0, derived_llc, derived_opt,
                derived_resource_dir, derived_arch_dir, modulemap_path,
                modulemap_arg, ir, stripped, irargs);
  return rc;
}
