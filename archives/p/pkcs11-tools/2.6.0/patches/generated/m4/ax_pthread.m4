# ===========================================================================
#   https://www.gnu.org/software/autoconf-archive/ax_pthread.html
# ===========================================================================
#
# SYNOPSIS
#
#   AX_PTHREAD([ACTION-IF-FOUND[, ACTION-IF-NOT-FOUND]])
#
# DESCRIPTION
#
#   Figure out how to build C programs using POSIX threads.
#
# LICENSE
#
#   Copyright (c) 2008 Steven G. Johnson <stevenj@alum.mit.edu>
#   Copyright (c) 2011 John Zavrel <john@archlinux.us>
#
#   Copying and distribution of this file, with or without modification, are
#   permitted in any medium without royalty provided the copyright notice
#   and this notice are preserved. This file is offered as-is, without any
#   warranty.

#serial 27

AU_ALIAS([ACX_PTHREAD], [AX_PTHREAD])

AC_DEFUN([AX_PTHREAD], [
AC_REQUIRE([AC_CANONICAL_HOST])
AC_REQUIRE([AC_PROG_CC])
AC_LANG_PUSH([C])
ax_pthread_ok=no

# Check for pthread support
AC_MSG_CHECKING([for pthread])

# Try without extra flags first
AC_LINK_IFELSE([AC_LANG_CALL([], [pthread_join])],
    [ax_pthread_ok=yes], [ax_pthread_ok=no])

if test "x$ax_pthread_ok" = "xno"; then
    # Try with -lpthread
    ax_pthread_flags="-lpthread"
    for flag in $ax_pthread_flags; do
        ax_pthread_save_LIBS=$LIBS
        LIBS="$LIBS $flag"
        AC_LINK_IFELSE([AC_LANG_CALL([], [pthread_join])],
            [ax_pthread_ok=yes; PTHREAD_LIBS="$flag"], [ax_pthread_ok=no])
        LIBS=$ax_pthread_save_LIBS
        if test "x$ax_pthread_ok" = "xyes"; then
            break
        fi
    done
fi

if test "x$ax_pthread_ok" = "xno"; then
    # Try with -pthread
    ax_pthread_save_CFLAGS=$CFLAGS
    CFLAGS="$CFLAGS -pthread"
    AC_LINK_IFELSE([AC_LANG_CALL([], [pthread_join])],
        [ax_pthread_ok=yes; PTHREAD_CFLAGS="-pthread"; PTHREAD_LIBS="-pthread"],
        [ax_pthread_ok=no])
    CFLAGS=$ax_pthread_save_CFLAGS
fi

AC_MSG_RESULT([$ax_pthread_ok])

if test "x$ax_pthread_ok" = "xyes"; then
    AC_DEFINE([HAVE_PTHREAD], [1], [Define if you have POSIX threads libraries and header files.])
    AC_SUBST([PTHREAD_CFLAGS])
    AC_SUBST([PTHREAD_LIBS])
    m4_ifval([$1], [$1], [])
else
    PTHREAD_CFLAGS=""
    PTHREAD_LIBS=""
    m4_ifval([$2], [$2], [])
fi
AC_LANG_POP([C])
])dnl AX_PTHREAD
