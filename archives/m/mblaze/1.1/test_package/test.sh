#!/bin/sh
set -eu

: "${MBLAZE_BIN:?MBLAZE_BIN must name the installed mblaze bin directory}"
bin=$MBLAZE_BIN

for command in maddr magrep mdate mdeliver mdirs mexport mflag mflow mgenmid mhdr \
    minc mlist mmime mpick mscan msed mseq mshow msort mthread \
    mcolor mcom mless mmkdir mquote museragent mbnc mfwd mrep mrefile; do
    if [ ! -x "$bin/$command" ]; then
        printf 'missing installed command: %s\n' "$command" >&2
        exit 1
    fi
done
printf 'PASS installed command inventory\n'

tmp_root=${TMPDIR:-${HOME:?HOME or TMPDIR is required}/tmp}
mkdir -p "$tmp_root"
work=$(mktemp -d "$tmp_root/mblaze-consumer.XXXXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM
mkdir -p "$work/maildir/cur"
message="$work/maildir/cur/1:2,"
cat >"$message" <<'MAIL'
From: Ada Lovelace <ada@example.org>
Subject: Progress update
Date: Thu, 30 Mar 2017 15:42:05 +0200
Message-Id: <mblaze-test@example.org>

Hello from mblaze.
MAIL

actual=$("$bin/maddr" -a "$message")
[ "$actual" = 'ada@example.org' ] || {
    printf 'maddr: expected ada@example.org, got <%s>\n' "$actual" >&2
    exit 1
}
printf 'PASS address extraction\n'

actual=$("$bin/mhdr" -h subject "$message")
[ "$actual" = 'Progress update' ] || {
    printf 'mhdr: expected Progress update, got <%s>\n' "$actual" >&2
    exit 1
}
printf 'PASS header extraction\n'

actual=$("$bin/magrep" subject:Progress "$message")
[ "$actual" = "$message" ] || {
    printf 'magrep: expected message path, got <%s>\n' "$actual" >&2
    exit 1
}
printf 'PASS subject search\n'

actual=$("$bin/msort" -F "$message")
[ "$actual" = "$message" ] || {
    printf 'msort: expected message path, got <%s>\n' "$actual" >&2
    exit 1
}
printf 'PASS explicit message sorting\n'

"$bin/mmime" -c <"$message"
printf 'PASS MIME validation\n'

printf '%s\n' "$message" >"$work/seq"
actual=$(MAILSEQ="$work/seq" "$bin/mseq" 1)
[ "$actual" = "$message" ] || {
    printf 'mseq: expected message path, got <%s>\n' "$actual" >&2
    exit 1
}
printf 'PASS message sequence lookup\n'

MAILSEQ="$work/seq" "$bin/mflag" -S 1
[ -f "$work/maildir/cur/1:2,S" ] || {
    printf 'mflag: seen flag was not applied to the Maildir message\n' >&2
    exit 1
}
printf 'PASS Maildir seen flag\n'
