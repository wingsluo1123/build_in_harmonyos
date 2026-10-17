#!/data/service/hnp/bin/bash
# Consumer smoke test for the installed Erlang/OTP 28 package.
#
# Runs inside the conanrun environment, so PATH already contains the packaged
# bin/ directory.  Every assertion drives the shipped BEAM; the compiler checks
# exercise Erlang's self-hosted compiler (written in Erlang, running on the VM
# that this very package builds).
set -eu

ASSERTIONS=0
FAILURES=0
check() {  # check <description> <expected> <actual>
    ASSERTIONS=$((ASSERTIONS + 1))
    if [ "$2" = "$3" ]; then
        echo "  ok   $1"
    else
        echo "  FAIL $1: expected [$2] got [$3]"
        FAILURES=$((FAILURES + 1))
    fi
}

work="$PWD/test-work"
echo "workdir=$work"
mkdir -p "$work"
cd "$work"

echo "[1] erl reports the OTP release"
check "otp_release is 28" "28" \
    "$(erl -noshell -eval 'io:format("~s",[erlang:system_info(otp_release)]),halt().')"

echo "[2] the BEAM flavour is the just-in-time compiler"
check "emu_flavor is jit" "jit" \
    "$(erl -noshell -eval 'io:format("~s",[erlang:system_info(emu_flavor)]),halt().')"

echo "[3] the scheduler uses more than one logical processor"
check "schedulers_online > 1" "yes" \
    "$(erl -noshell -eval 'case erlang:system_info(schedulers_online) > 1 of true -> io:format("yes"); false -> io:format("no") end,halt().')"

echo "[4] the runtime identifies the platform as HarmonyOS"
check "os:type/0 is {unix,harmonyos}" "{unix,harmonyos}" \
    "$(erl -noshell -eval 'io:format("~p",[os:type()]),halt().')"

echo "[5] processes, mailboxes and arithmetic"
check "spawn/receive square of 21" "441" \
    "$(erl -noshell -eval 'P=spawn(fun()->receive {F,N}->F!{ok,N*N} end end),P!{self(),21},receive {ok,V}->io:format("~p",[V]) end,halt().')"

echo "[6] binaries, maps and the BIF dispatch path"
check "map/binaries evaluation" "{2,\"ohos\",4}" \
    "$(erl -noshell -eval 'M = #{a=>1,b=>2}, B = <<"ohos">>,io:format("~p",[{maps:size(M),binary_to_list(B),byte_size(B)}]),halt().')"

echo "[7] the Erlang compiler builds a module"
cat > hello.erl <<'EOF'
-module(hello).
-export([sum/1, name/0]).
sum(N) -> lists:sum(lists:seq(1, N)).
name() -> erlang:system_info(otp_release).
EOF
erlc hello.erl
check "erlc produced hello.beam" "yes" \
    "$([ -f hello.beam ] && echo yes || echo no)"

echo "[8] the freshly compiled module runs on the VM"
check "hello:sum(100)" "5050" \
    "$(erl -noshell -pa . -eval 'io:format("~p",[hello:sum(100)]),halt().')"

echo "[9] code loading resolves the standard libraries"
check "code:which(lists) points at a .beam file" "yes" \
    "$(erl -noshell -eval 'case code:which(lists) of P when is_list(P) -> io:format("yes"); _ -> io:format("no") end,halt().')"

echo "[10] escript runs a standalone script"
cat > probe.escript <<'EOF'
#!/usr/bin/env escript
main(_) -> io:format("~s", [erlang:system_info(otp_release)]).
EOF
check "escript output" "28" "$(escript probe.escript)"

echo "[11] the zlib NIF compresses and uncompresses"
check "zlib round-trip" "harmonyos" \
    "$(erl -noshell -eval 'io:format("~s",[zlib:uncompress(zlib:compress(<<"harmonyos">>))]),halt().')"

echo "[12] the crypto NIF is linked against OpenSSL"
check "sha256 digest length" "32" \
    "$(erl -noshell -eval 'io:format("~p",[byte_size(crypto:hash(sha256,<<"ohos">>))]),halt().')"

echo "[13] the inet driver opens and closes a UDP socket"
check "gen_udp open/close" "ok" \
    "$(erl -noshell -eval '{ok,S}=gen_udp:open(0),ok=gen_udp:close(S),io:format("ok"),halt().')"

echo "[14] file IO round-trips through the local filesystem"
check "file read back" "harmonyos-pc" \
    "$(erl -noshell -eval 'F="probe.txt",ok=file:write_file(F,<<"harmonyos-pc">>),{ok,B}=file:read_file(F),io:format("~s",[B]),halt().')"

echo "[15] timers and message ordering survive a scheduler round trip"
check "timer:sleep + monotonic time" "yes" \
    "$(erl -noshell -eval 'T0=erlang:monotonic_time(),timer:sleep(20),case erlang:monotonic_time() > T0 of true -> io:format("yes"); false -> io:format("no") end,halt().')"

echo
echo "assertions=$ASSERTIONS failures=$FAILURES"
if [ "$FAILURES" -ne 0 ]; then
    echo "consumer test FAILED"
    exit 1
fi
echo "consumer test PASSED"
