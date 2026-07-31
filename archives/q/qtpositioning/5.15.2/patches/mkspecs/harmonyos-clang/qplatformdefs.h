/****************************************************************************
**
** qmake spec for HarmonyOS (OpenHarmony) aarch64 — clang toolchain.
** Self-contained qplatformdefs.h for the standalone harmonyos-clang mkspec.
** Modeled on Qt 5.15.2 mkspecs/linux-g++ + mkspecs/common/posix
** (LGPL-3.0, (C) The Qt Company Ltd), adapted for OHOS / musl libc:
**   - no glibc <features.h>; POSIX types come from the sys headers
**   - socklen_t on OHOS is unsigned int (ElaWidgetTools adaptation notes)
**
****************************************************************************/

#ifndef QPLATFORMDEFS_H
#define QPLATFORMDEFS_H

// Get Qt defines/settings
#include "qglobal.h"

#include <unistd.h>

#include <pthread.h>
#include <dirent.h>
#include <fcntl.h>
#include <grp.h>
#include <pwd.h>
#include <signal.h>

#include <sys/types.h>
#include <sys/ioctl.h>
#include <sys/ipc.h>
#include <sys/time.h>
#include <sys/shm.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <netinet/in.h>

// ── File / stat / I/O (POSIX, non-LFS branch — OHOS off_t is 64-bit) ──────
#define QT_STATBUF              struct stat
#define QT_FPOS_T               fpos_t
#define QT_OFF_T                off_t

#define QT_STAT                 ::stat
#define QT_LSTAT                ::lstat
#define QT_TRUNCATE             ::truncate

// File I/O
#define QT_OPEN                 ::open
#define QT_LSEEK                ::lseek
#define QT_FSTAT                ::fstat
#define QT_FTRUNCATE            ::ftruncate

// Standard C89
#define QT_FOPEN                ::fopen
#define QT_FSEEK                ::fseeko
#define QT_FTELL                ::ftello
#define QT_FGETPOS              ::fgetpos
#define QT_FSETPOS              ::fsetpos

#define QT_MMAP                 ::mmap

#define QT_STAT_MASK            S_IFMT
#define QT_STAT_REG             S_IFREG
#define QT_STAT_DIR             S_IFDIR
#define QT_STAT_LNK             S_IFLNK

#define QT_ACCESS               ::access
#define QT_GETCWD               ::getcwd
#define QT_CHDIR                ::chdir
#define QT_MKDIR                ::mkdir
#define QT_RMDIR                ::rmdir

// File I/O
#define QT_CLOSE                ::close
#define QT_READ                 ::read
#define QT_WRITE                ::write

#define QT_OPEN_LARGEFILE       O_LARGEFILE
#define QT_OPEN_RDONLY          O_RDONLY
#define QT_OPEN_WRONLY          O_WRONLY
#define QT_OPEN_RDWR            O_RDWR
#define QT_OPEN_CREAT           O_CREAT
#define QT_OPEN_TRUNC           O_TRUNC
#define QT_OPEN_APPEND          O_APPEND
#define QT_OPEN_EXCL            O_EXCL

// Posix extensions to C89
#define QT_FILENO               fileno

// Directory iteration
#define QT_DIR                  DIR
#define QT_OPENDIR              ::opendir
#define QT_CLOSEDIR             ::closedir
#define QT_DIRENT               struct dirent
#define QT_READDIR              ::readdir
#define QT_READDIR_R            ::readdir_r

// ── Sockets ───────────────────────────────────────────────────────────────
// OHOS (musl): socklen_t is unsigned int — do NOT force plain int
#define QT_SOCKLEN_T            socklen_t
#define QT_SOCKET_CONNECT       ::connect
#define QT_SOCKET_BIND          ::bind

// ── Signals ───────────────────────────────────────────────────────────────
#define QT_SIGNAL_RETTYPE       void
#define QT_SIGNAL_ARGS          int
#define QT_SIGNAL_IGNORE        SIG_IGN

// ── stdio ─────────────────────────────────────────────────────────────────
#define QT_SNPRINTF             ::snprintf
#define QT_VSNPRINTF            ::vsnprintf

#endif // QPLATFORMDEFS_H
