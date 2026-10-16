#!/bin/sh
#--------------------------------------------------------------------
# Consumer test for userinfo 2.5 (installed `ui` program + modules).
#
# Env:
#   UI_BIN  path to the installed ui executable
# Exit: 0 = all checks passed, 1 = failure
#--------------------------------------------------------------------
set -u

UI="${UI_BIN:?UI_BIN must point to the installed ui executable}"

WORK="${TMPDIR:-.}/ui-test.$$"
mkdir -p "$WORK" || { echo "FAIL: cannot create workdir $WORK"; exit 1; }
trap 'rm -rf "$WORK"' EXIT

checks=0
fails=0

check_eq() { # check_eq <name> <actual> <expected>
	checks=$((checks + 1))
	if [ "$2" = "$3" ]; then
		echo "PASS: $1"
	else
		echo "FAIL: $1 (got '$2', want '$3')"
		fails=$((fails + 1))
	fi
}

contains() { # contains <name> <file> <needle>
	checks=$((checks + 1))
	if grep -q -F -- "$3" "$2" 2>/dev/null; then
		echo "PASS: $1"
	else
		echo "FAIL: $1 (missing '$3' in $2)"
		fails=$((fails + 1))
	fi
}

# 1. version
out="$WORK/v.out"; timeout 15 "$UI" -V > "$out" 2>&1; rc=$?
check_eq "ui -V exits 0" "$rc" 0
contains "ui -V prints the version" "$out" "userinfo 2.5"

# 2. help
out="$WORK/h.out"; timeout 15 "$UI" -h > "$out" 2>&1
contains "ui -h prints usage" "$out" "Usage:"
contains "ui -h lists the -O module option" "$out" "-O"

# 3. passwd module (default ':' separator); modules must load via RUNPATH
out="$WORK/pw.out"; timeout 15 "$UI" -O passwd.so root > "$out" 2>&1; rc=$?
check_eq "ui -O passwd.so root exits 0" "$rc" 0
contains "ui passwd output for root" "$out" "root:x:0:0"

# 4. custom field separator
out="$WORK/pwF.out"; timeout 15 "$UI" -F '|' -O passwd.so root > "$out" 2>&1; rc=$?
check_eq "ui -F exits 0" "$rc" 0
contains "ui -F uses the custom separator" "$out" "root|x|0|0"

# 5. default module set (-d)
out="$WORK/def.out"; timeout 15 "$UI" -d root > "$out" 2>&1; rc=$?
check_eq "ui -d root exits 0" "$rc" 0
contains "ui -d includes passwd fields" "$out" "root:x:0:0"

# 6. unknown user
out="$WORK/nou.out"; timeout 15 "$UI" -O passwd.so nosuchuser123 > "$out" 2>&1; rc=$?
check_eq "ui unknown user fails" "$([ "$rc" -ne 0 ] && echo yes || echo no)" yes
contains "ui unknown user diagnostic" "$out" "no such user"

# 7. unknown module -> dlopen failure
out="$WORK/nom.out"; timeout 15 "$UI" -O does_not_exist.so root > "$out" 2>&1; rc=$?
check_eq "ui unknown module fails" "$([ "$rc" -ne 0 ] && echo yes || echo no)" yes

# 8. mail module
out="$WORK/mail.out"; timeout 15 "$UI" -O mail.so root > "$out" 2>&1; rc=$?
check_eq "ui -O mail.so exits 0" "$rc" 0

# 9. login module
out="$WORK/login.out"; timeout 15 "$UI" -O login.so root > "$out" 2>&1; rc=$?
check_eq "ui -O login.so exits 0" "$rc" 0

# 10. configuration file
cat > "$WORK/uirc" <<'EOF'
passwd.so
EOF
out="$WORK/cfg.out"; timeout 15 "$UI" -c "$WORK/uirc" root > "$out" 2>&1; rc=$?
check_eq "ui -c config exits 0" "$rc" 0
contains "ui -c loads the configured module" "$out" "root:x:0:0"

# 11. deterministic output
timeout 15 "$UI" -O passwd.so root > "$WORK/d1.out" 2>&1
timeout 15 "$UI" -O passwd.so root > "$WORK/d2.out" 2>&1
check_eq "ui output is deterministic" \
	"$(cmp -s "$WORK/d1.out" "$WORK/d2.out" && echo same || echo diff)" same

# 12. multiple users
out="$WORK/multi.out"; timeout 15 "$UI" -O passwd.so root bin > "$out" 2>&1; rc=$?
check_eq "ui multiple users exits 0" "$rc" 0
contains "ui output for root among users" "$out" "root:x:0:0"
contains "ui output for bin among users" "$out" "bin:x:2:2"

# 13. verbose adds group names
out="$WORK/verb.out"; timeout 15 "$UI" -v -O passwd.so root > "$out" 2>&1; rc=$?
check_eq "ui -v exits 0" "$rc" 0
contains "ui -v shows group names" "$out" "(root)"

echo "USERINFO_CHECK_SUMMARY checks=$checks fails=$fails"
[ "$fails" -eq 0 ]
