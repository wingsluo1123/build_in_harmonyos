# ===========================================================================
#   https://www.gnu.org/software/autoconf-archive/ax_prog_bison.html
# ===========================================================================
#
# SYNOPSIS
#
#   AX_PROG_BISON([ACTION-IF-TRUE], [ACTION-IF-FALSE])
#   AX_PROG_BISON_VERSION(VERSION, [ACTION-IF-TRUE], [ACTION-IF-FALSE])
#
# DESCRIPTION
#
#   Check for bison and set YACC to it.
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

AC_DEFUN([AX_PROG_BISON], [
    AC_REQUIRE([AC_PROG_YACC])
    AC_CACHE_CHECK([whether yacc is GNU bison], [ax_cv_bison],
      [ax_cv_bison=no
       if test -n "$YACC"; then
         echo "%%" >conftest.y
         if $YACC conftest.y >/dev/null 2>&1; then
           if $YACC --version 2>&1 | grep -qi "bison"; then
             ax_cv_bison=yes
           fi
         fi
         rm -f conftest.y y.tab.c
       fi])
    AS_IF([test "x$ax_cv_bison" = "xyes"], [$1], [$2])
])

AC_DEFUN([AX_PROG_BISON_VERSION], [
    AC_REQUIRE([AX_PROG_BISON])
    AC_CACHE_CHECK([for bison version >= $1], [ax_cv_bison_version],
      [ax_cv_bison_version=no
       if test "x$ax_cv_bison" = "xyes"; then
         bison_version=$($YACC --version 2>/dev/null | sed 's/.* //' | sed 's/[^0-9.]//g')
         ax_cv_bison_version=$(awk -v a="$bison_version" -v b="$1" 'BEGIN {if (a >= b) print "yes"; else print "no"}')
       fi])
    AS_IF([test "x$ax_cv_bison_version" = "xyes"], [$2], [$3])
])
