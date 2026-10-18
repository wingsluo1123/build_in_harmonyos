#!/usr/bin/env python3
"""Minimal IRC server used as the peer in the sircbot consumer test.

Binds 127.0.0.1 on an ephemeral port and writes the chosen port to --portfile
so the caller can point sircbot at it.  It speaks just enough IRC for sircbot
(banner, JOIN echo, PONG), records every line exchanged to --log, and can
inject one inbound PRIVMSG after a delay to exercise the channel hooks.

This is test scaffolding: it is the peer the installed binaries talk to, not a
replacement for them.
"""
import argparse
import socket
import sys
import threading
import time


def send(conn, log, payload):
    conn.sendall(payload.encode())
    log.write("> %s" % payload)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--portfile", required=True)
    ap.add_argument("--log", required=True)
    ap.add_argument("--channel", default="#testchan")
    ap.add_argument("--inject-after", type=float, default=None)
    ap.add_argument("--inject-text", default=None)
    args = ap.parse_args()

    log = open(args.log, "a", buffering=1)
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    srv.listen(4)
    port = srv.getsockname()[1]
    with open(args.portfile, "w") as fh:
        fh.write("%d\n" % port)
    log.write("> LISTENING %d\n" % port)

    conn, addr = srv.accept()
    log.write("> ACCEPT %s\n" % (addr,))

    if args.inject_after is not None:
        # Bound to a distinct name: the receive loop below rebinds `text`
        # repeatedly, and a closure would otherwise send the most recent line
        # it received instead of the payload chosen here.
        inject_payload = args.inject_text or (
            ":alice!u@h PRIVMSG %s :hello-from-irc" % args.channel)

        def inject():
            time.sleep(args.inject_after)
            log.write("> INJECT %s\n" % inject_payload)
            try:
                conn.sendall((inject_payload + "\r\n").encode())
            except OSError as exc:
                log.write("> INJECT-FAILED %s\n" % exc)

        threading.Thread(target=inject, daemon=True).start()

    nick = "sircbot"
    buf = b""
    conn.settimeout(120)
    try:
        while True:
            try:
                chunk = conn.recv(4096)
            except socket.timeout:
                log.write("> RECV-TIMEOUT\n")
                break
            if not chunk:
                break
            buf += chunk
            while b"\n" in buf:
                raw, buf = buf.split(b"\n", 1)
                text = raw.decode("utf-8", "replace").rstrip("\r")
                log.write("< %s\n" % text)
                parts = text.split()
                verb = parts[0].upper() if parts else ""
                if verb == "NICK":
                    nick = parts[1] if len(parts) > 1 else nick
                    send(conn, log, ":fakeircd 001 %s :Welcome to the sircbot test server\r\n" % nick)
                elif verb == "JOIN":
                    chan = parts[1] if len(parts) > 1 else args.channel
                    send(conn, log, ":%s!u@h JOIN %s\r\n" % (nick, chan))
                    send(conn, log, ":fakeircd 353 %s = %s :@%s\r\n" % (nick, chan, nick))
                    send(conn, log, ":fakeircd 366 %s %s :End of /NAMES list\r\n" % (nick, chan))
                elif verb == "PING":
                    send(conn, log, "PONG %s\r\n" % (parts[1] if len(parts) > 1 else "x"))
                elif verb == "QUIT":
                    raise SystemExit(0)
    except (OSError, SystemExit) as exc:
        log.write("> END %s\n" % exc)
    finally:
        try:
            conn.close()
        except OSError:
            pass
        srv.close()
        log.write("> CLOSED\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
