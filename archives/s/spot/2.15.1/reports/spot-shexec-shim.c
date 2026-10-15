/* spot-shexec-shim.c — OHOS 无脚本 execve 的 LD_PRELOAD 垫片（2026-10-04, 任务 10869）
 *
 * 背景：OHOS 拒绝对任何 `#!` 脚本直接 execve（EACCES/Permission denied，
 * 且 busybox sh 的 `sh -c ./script` 同样 126，无 ENOEXEC 回退）。上游 spot 测试
 * （tests/core/ltlcross{6,ce,ce2,grind}.test）在运行期以 heredoc 生成 `fake`
 * 翻译器脚本并 chmod +x，再由 ltlcross/ltldo 经 posix_spawnp 直接执行 →
 * 在 OHOS 上必挂（`ltlcross: failed to run './fake': Permission denied`）。
 *
 * 处理：拦截 posix_spawnp/posix_spawn——目标文件是 `#!` 脚本时改写为
 * `/bin/sh <script> <args...>`（与 POSIX 正常平台的脚本执行语义等价：
 * 上游测试逻辑零改动）。ELF 目标原样透传。无斜杠名字按 PATH 解析后判定
 * （与 posix_spawnp 语义一致）。
 *
 * 构建（真机）：
 *   /data/service/hnp/bin/clang -shared -fPIC -O2 -o spot-shexec-shim.so spot-shexec-shim.c
 * 使用：
 *   LD_PRELOAD=<绝对路径>/spot-shexec-shim.so make -k check ...
 *
 * 边界：仅覆盖经 libc 符号调用的 posix_spawn(p)（spot 二进制即此路径）；
 *       静态链接/直接 syscall 的 exec 不经此垫片；execv(e|p)/execl* 未覆盖
 *       （本任务不需要，保持最小面）。
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <fcntl.h>
#include <spawn.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

typedef int (*spawn_t)(pid_t*, const char*, const posix_spawn_file_actions_t*,
                       const posix_spawnattr_t*, char* const[], char* const[]);

static int
is_shebang(const char* path)
{
  int fd = open(path, O_RDONLY);
  if (fd < 0)
    return 0;
  char b[2];
  ssize_t n = read(fd, b, 2);
  close(fd);
  return n == 2 && b[0] == '#' && b[1] == '!';
}

/* PATH 解析（等价 posix_spawnp 的查找；返回 malloc 路径或 NULL） */
static char*
find_in_path(const char* file)
{
  const char* p = getenv("PATH");
  if (!p)
    return NULL;
  size_t flen = strlen(file);
  for (;;)
    {
      const char* c = strchr(p, ':');
      size_t len = c ? (size_t)(c - p) : strlen(p);
      char* cand;
      if (len == 0)
        {
          cand = malloc(flen + 1);
          if (cand)
            memcpy(cand, file, flen + 1);
        }
      else
        {
          cand = malloc(len + 1 + flen + 1);
          if (cand)
            {
              memcpy(cand, p, len);
              cand[len] = '/';
              memcpy(cand + len + 1, file, flen + 1);
            }
        }
      if (cand && is_shebang(cand) && access(cand, X_OK) == 0)
        return cand;
      free(cand);
      if (!c)
        return NULL;
      p = c + 1;
    }
}

static char**
wrap_argv(const char* path, char* const argv[])
{
  size_t n = 0;
  while (argv && argv[n])
    ++n;
  char** na = malloc((n + 2) * sizeof(char*));
  if (!na)
    return NULL;
  na[0] = (char*)"/bin/sh";
  na[1] = (char*)path;
  for (size_t i = 1; i < n; ++i)
    na[i + 1] = argv[i];
  na[n + 1] = NULL;
  return na;
}

int
posix_spawnp(pid_t* pid, const char* file,
             const posix_spawn_file_actions_t* fa,
             const posix_spawnattr_t* at,
             char* const argv[], char* const envp[])
{
  static spawn_t real;
  if (!real)
    real = (spawn_t)dlsym(RTLD_NEXT, "posix_spawnp");
  const char* script = NULL;
  char* resolved = NULL;
  if (file)
    {
      if (strchr(file, '/'))
        {
          if (is_shebang(file))
            script = file;
        }
      else
        {
          resolved = find_in_path(file);
          script = resolved;
        }
    }
  if (script)
    {
      char** na = wrap_argv(script, argv);
      if (na)
        {
          int r = real(pid, "/bin/sh", fa, at, na, envp);
          free(na);
          free(resolved);
          if (!r)
            return 0;
        }
      else
        free(resolved);
    }
  return real(pid, file, fa, at, argv, envp);
}

int
posix_spawn(pid_t* pid, const char* file,
            const posix_spawn_file_actions_t* fa,
            const posix_spawnattr_t* at,
            char* const argv[], char* const envp[])
{
  static spawn_t real;
  if (!real)
    real = (spawn_t)dlsym(RTLD_NEXT, "posix_spawn");
  if (file && is_shebang(file))
    {
      char** na = wrap_argv(file, argv);
      if (na)
        {
          int r = real(pid, "/bin/sh", fa, at, na, envp);
          free(na);
          if (!r)
            return 0;
        }
    }
  return real(pid, file, fa, at, argv, envp);
}
