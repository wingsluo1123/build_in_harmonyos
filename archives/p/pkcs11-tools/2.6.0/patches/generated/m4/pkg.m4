# pkg.m4 - Macros to locate and utilise pkg-config.   -*- Autoconf -*-
# serial 12 (pkg-config-0.29)

dnl PKG_PREREQ([MIN-VERSION])
AC_DEFUN([PKG_PREREQ],
[m4_define([pkg_mm_version], [0.29])
m4_if(m4_version_compare(m4_default(m4_defn([pkg_mm_version]), [0.29]), [$1]), -1,
    [m4_fatal([pkg ]m4_default(m4_defn([pkg_mm_version]), [0.29])[ is too old.  Version $1 or newer is required.])])
])dnl PKG_PREREQ

dnl PKG_PROG_PKG_CONFIG([MIN-VERSION])
AC_DEFUN([PKG_PROG_PKG_CONFIG],
[m4_pattern_forbid([^pkg_check_])
m4_pattern_allow([^pkg_config_])
m4_pattern_forbid([^PKG_CONFIG_(PATH|LIBDIR|SYSROOT_DIR)$])
PKG_PREREQ([$1])dnl
AC_ARG_VAR([PKG_CONFIG], [path to pkg-config utility])
AC_ARG_VAR([PKG_CONFIG_PATH], [directories to add to pkg-config's search path])
AC_ARG_VAR([PKG_CONFIG_LIBDIR], [path overriding pkg-config's built-in search path])

if test -n "$PKG_CONFIG"; then
    _PKG_CONFIG
elif test -n "$ac_cv_env_PKG_CONFIG_set"; then
    PKG_CONFIG=$ac_cv_env_PKG_CONFIG_value
fi

if test -z "$PKG_CONFIG"; then
    AC_PATH_PROG([PKG_CONFIG], [pkg-config])
fi
if test -n "$PKG_CONFIG"; then
    pkg_cv_PKG_CONFIG=$PKG_CONFIG
    AC_MSG_CHECKING([for $PKG_CONFIG])
    AC_MSG_RESULT([$pkg_cv_PKG_CONFIG])
fi
[]dnl
])dnl PKG_PROG_PKG_CONFIG

dnl _PKG_CONFIG_VERSION_CHECK
AC_DEFUN([_PKG_CONFIG_VERSION_CHECK],
[
    if test -n "$PKG_CONFIG"; then
        if ! $PKG_CONFIG --atleast-pkgconfig-version 0.20; then
            _pkg_short_errors_supported=no
        else
            _pkg_short_errors_supported=yes
        fi
    fi
])dnl _PKG_CONFIG_VERSION_CHECK

dnl _PKG_CONFIG([VARIABLE], [COMMAND], [MODULES])
AC_DEFUN([_PKG_CONFIG],
[AC_MSG_CHECKING([for $3 $2])
if test -n "$$1"; then
    pkg_cv_[]$1="$$1"
 elif test -n "$PKG_CONFIG"; then
    pkg_cv_[]$1=`$PKG_CONFIG --$2 "$3" 2>/dev/null`
    test "x$?" != "x0" && pkg_failed=yes
 else
    pkg_failed=untried
fi
AC_MSG_RESULT([$pkg_cv_[]$1])
])

dnl PKG_CHECK_MODULES(VARIABLE-PREFIX, MODULES, [ACTION-IF-FOUND],
dnl   [ACTION-IF-NOT-FOUND])
AC_DEFUN([PKG_CHECK_MODULES],
[AC_REQUIRE([PKG_PROG_PKG_CONFIG])dnl
AC_ARG_VAR([$1][_CFLAGS], [C compiler flags for $1, overriding pkg-config])
AC_ARG_VAR([$1][_LIBS], [linker flags for $1, overriding pkg-config])

pkg_failed=no
_PKG_CONFIG_VERSION_CHECK

AC_MSG_CHECKING([for $2])

_PKG_CONFIG([$1][_CFLAGS], [cflags], [$2])
_PKG_CONFIG([$1][_LIBS], [libs], [$2])

m4_define([_PKG_TEXT], [Alternatively, you may set the environment variables $1[]_CFLAGS
and $1[]_LIBS to avoid the need to call pkg-config.
See the pkg-config man page for more details.])

if test $pkg_failed = yes; then
    AC_MSG_RESULT([no])
    if $PKG_CONFIG --exists "$2" 2>/dev/null; then
        $1[]_PKG_ERRORS=`$PKG_CONFIG --print-errors "$2" 2>&1`
        AC_MSG_ERROR([$$1[]_PKG_ERRORS])
    else
        AC_MSG_RESULT([no])
        $4
    fi
elif test $pkg_failed = untried; then
    AC_MSG_RESULT([no])
    $4
else
    $1[]_CFLAGS=$pkg_cv_[]$1[]_CFLAGS
    $1[]_LIBS=$pkg_cv_[]$1[]_LIBS
    AC_MSG_RESULT([yes])
    $3
fi[]dnl
])dnl PKG_CHECK_MODULES

dnl PKG_CHECK_EXISTS(MODULES, [ACTION-IF-FOUND], [ACTION-IF-NOT-FOUND])
AC_DEFUN([PKG_CHECK_EXISTS],
[AC_REQUIRE([PKG_PROG_PKG_CONFIG])dnl
if test -n "$PKG_CONFIG" && \
    AC_RUN_LOG([$PKG_CONFIG --exists --print-errors "$1"]); then
    m4_default([$2], [:])
else
    m4_default([$3], [:])
fi
])
