# ===========================================================================
#   https://www.gnu.org/software/autoconf-archive/ax_prog_flex.html
# ===========================================================================
#
# SYNOPSIS
#
#   AX_PROG_FLEX([ACTION-IF-TRUE], [ACTION-IF-FALSE])
#   AX_PROG_FLEX_VERSION(VERSION, [ACTION-IF-TRUE], [ACTION-IF-FALSE])
#
# DESCRIPTION
#
#   Check for flex and set LEX to it.
#
# LICENSE
#
#   Copyright (c) 2024 Autoconf Archive
#
#   Copying and distribution of this file, with or without modification, are
#   permitted in any medium without royalty provided the copyright notice
#   and this notice are preserved. This file is offered as-is, without any
#   warranty.

#serial 2

AC_DEFUN([AX_PROG_FLEX], [
    AC_REQUIRE([AM_PROG_LEX])
    AC_CACHE_CHECK([whether lex is GNU flex], [ax_cv_flex],
      [ax_cv_flex=no
       if test -n "$LEX"; then
         echo "int main(){return 0;}" >conftest.l
         if $LEX conftest.l >/dev/null 2>&1; then
           if $LEX --version 2>&1 | grep -qi "flex"; then
             ax_cv_flex=yes
           fi
         fi
         rm -f conftest.l lex.yy.c
       fi])
    AS_IF([test "x$ax_cv_flex" = "xyes"], [$1], [$2])
])

AC_DEFUN([AX_PROG_FLEX_VERSION], [
    AC_REQUIRE([AX_PROG_FLEX])
    AC_CACHE_CHECK([for flex version >= $1], [ax_cv_flex_version],
      [ax_cv_flex_version=no
       if test "x$ax_cv_flex" = "xyes"; then
         flex_version=$($LEX --version 2>/dev/null | sed 's/flex //' | sed 's/[^0-9.]//g')
         ax_cv_flex_version=$(awk -v a="$flex_version" -v b="$1" 'BEGIN {if (a >= b) print "yes"; else print "no"}')
       fi])
    AS_IF([test "x$ax_cv_flex_version" = "xyes"], [$2], [$3])
])
