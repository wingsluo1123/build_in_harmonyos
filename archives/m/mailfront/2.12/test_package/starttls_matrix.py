#!/usr/bin/env python3
"""Exercise mailfront's real UCSPI STARTTLS production path.

The bridge implements only the external UCSPI descriptor contract.  SMTP
state, authentication, authorization, framing, and module dispatch remain in
the installed mailfront executable and its installed modules.
"""

import argparse
import os
import select
import shutil
import socket
import ssl
import subprocess
import tempfile
import threading
import time


AUTH_PLAIN = b"AUTH PLAIN dGVzdHVzZXIAdGVzdHVzZXIAdGVzdHBhc3M=\r\n"


class StarttlsSession:
    def __init__(self, args, plugins, backend="echo", extra_env=None):
        self.args = args
        self.plugins = plugins
        self.backend = backend
        self.extra_env = extra_env or {}
        self.process = None
        self.client = None
        self.buffer = bytearray()
        self.bridge_thread = None
        self.bridge_error = []
        self.stop_bridge = threading.Event()

    def start(self):
        client, server = socket.socketpair()
        bridge_socket = server.dup()
        control_read, control_write = os.pipe()
        app_read, bridge_write = os.pipe()
        bridge_read, app_write = os.pipe()
        env = os.environ.copy()
        env.update(
            {
                "PROTO": "TEST",
                "TESTLOCALIP": "127.0.0.1",
                "TESTREMOTEIP": "127.0.0.2",
                "TESTLOCALHOST": "local.test",
                "TESTREMOTEHOST": "remote.test",
                "MODULE_PATH": self.args.modules,
                "UCSPITLS": "1",
                "SSLCTLFD": str(control_write),
                "SSLREADFD": str(app_read),
                "SSLWRITEFD": str(app_write),
                "CVM_SASL_PLAIN": self.args.auth_module,
            }
        )
        env.update(self.extra_env)
        command = [self.args.mailfront, "smtp", self.backend] + self.plugins.split(":")
        self.process = subprocess.Popen(
            command,
            stdin=server,
            stdout=server,
            stderr=subprocess.DEVNULL,
            env=env,
            close_fds=True,
            pass_fds=(control_write, app_read, app_write),
        )
        self.pid = self.process.pid
        server.close()
        os.close(control_write)
        os.close(app_read)
        os.close(app_write)
        self.client = client
        self.control_read = control_read
        self.bridge_socket = bridge_socket
        self.bridge_write = bridge_write
        self.bridge_read = bridge_read
        greeting = self.reply()
        check(greeting[-1].startswith(b"220 "), "SMTP greeting")
        return self

    def _readline(self, timeout=5.0):
        deadline = time.monotonic() + timeout
        while b"\n" not in self.buffer:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise AssertionError("timed out waiting for SMTP reply")
            readable, _, _ = select.select([self.client], [], [], remaining)
            if not readable:
                raise AssertionError("timed out waiting for SMTP reply")
            data = self.client.recv(4096)
            if not data:
                raise AssertionError("mailfront closed the connection")
            self.buffer.extend(data)
        line, _, rest = self.buffer.partition(b"\n")
        self.buffer = bytearray(rest)
        return bytes(line + b"\n")

    def reply(self, timeout=5.0):
        first = self._readline(timeout)
        lines = [first]
        if len(first) < 4 or first[3:4] != b"-":
            return lines
        code = first[:3]
        while True:
            line = self._readline(timeout)
            lines.append(line)
            if line.startswith(code + b" "):
                return lines

    def command(self, command, expected=None):
        self.client.sendall(command)
        lines = self.reply()
        if expected is not None:
            check(lines[-1].startswith(expected), command.strip().decode("ascii"))
        return lines

    def upgrade(self):
        self.command(b"STARTTLS\r\n", b"220 ")
        readable, _, _ = select.select([self.control_read], [], [], 5.0)
        check(bool(readable), "UCSPI control notification")
        check(os.read(self.control_read, 1) == b"y", "UCSPI start-TLS request")

        self._activate_tls()

    def _activate_tls(self):

        server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        server_context.load_cert_chain(self.args.certificate, self.args.private_key)

        def bridge():
            tls_server = None
            try:
                tls_server = server_context.wrap_socket(
                    self.bridge_socket, server_side=True
                )
                tls_server.setblocking(False)
                while not self.stop_bridge.is_set():
                    readable, _, _ = select.select(
                        [tls_server, self.bridge_read], [], [], 0.1
                    )
                    if tls_server in readable:
                        try:
                            data = tls_server.recv(4096)
                        except ssl.SSLWantReadError:
                            data = None
                        if data == b"":
                            break
                        if data:
                            os.write(self.bridge_write, data)
                    if self.bridge_read in readable:
                        data = os.read(self.bridge_read, 4096)
                        if not data:
                            break
                        view = memoryview(data)
                        while view:
                            try:
                                sent = tls_server.send(view)
                                view = view[sent:]
                            except (ssl.SSLWantReadError, ssl.SSLWantWriteError):
                                time.sleep(0.01)
            except Exception as exc:
                self.bridge_error.append(exc)
            finally:
                if tls_server is not None:
                    try:
                        tls_server.close()
                    except OSError:
                        pass

        self.bridge_thread = threading.Thread(target=bridge, daemon=True)
        self.bridge_thread.start()
        client_context = ssl.create_default_context()
        client_context.check_hostname = False
        client_context.verify_mode = ssl.CERT_NONE
        self.client = client_context.wrap_socket(
            self.client, server_hostname="localhost"
        )
        check(self.process.poll() is None, "same mailfront process remains alive")
        check(self.process.pid == self.pid, "mailfront PID is unchanged by STARTTLS")

    def close(self):
        if self.client is not None and self.process is not None:
            try:
                if self.process.poll() is None:
                    self.command(b"QUIT\r\n", b"221 ")
            except (AssertionError, OSError, ssl.SSLError):
                pass
        if self.process is not None:
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                self.process.wait(timeout=3)
        self.stop_bridge.set()
        for fd_name in ("control_read", "bridge_write", "bridge_read"):
            fd = getattr(self, fd_name, None)
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
        if self.client is not None:
            try:
                self.client.close()
            except OSError:
                pass
        if self.bridge_thread is not None:
            self.bridge_thread.join(timeout=2)
        check(not self.bridge_error, "TLS bridge completed without error")


def check(condition, label):
    if not condition:
        raise AssertionError(label)
    check.count += 1


check.count = 0


def ehlo(session, name=b"client.test"):
    lines = session.command(b"EHLO " + name + b"\r\n")
    check(lines[-1].startswith(b"250 "), "EHLO succeeds")
    return b"".join(lines)


def auth(session):
    session.command(AUTH_PLAIN, b"235 ")


def expected_code(mode, fixed, vulnerable):
    return fixed if mode == "fixed" else vulnerable


def transaction_scenario(args):
    session = StarttlsSession(args, "starttls-ucspi:accept").start()
    try:
        ehlo(session)
        session.command(b"MAIL FROM:<from@test>\r\n", b"250 ")
        session.command(b"RCPT TO:<to@test>\r\n", b"250 ")
        session.upgrade()
        session.command(
            b"DATA\r\n", expected_code(args.expect, b"503 ", b"354 ")
        )
    finally:
        session.close()


def authentication_scenario(args):
    session = StarttlsSession(
        args, "starttls-ucspi:cvm-authenticate:relayclient:accept-sender"
    ).start()
    try:
        ehlo(session)
        auth(session)
        session.upgrade()
        ehlo(session, b"post-tls.test")
        session.command(
            AUTH_PLAIN, expected_code(args.expect, b"235 ", b"503 ")
        )
    finally:
        session.close()


def authorization_scenario(args):
    session = StarttlsSession(
        args, "starttls-ucspi:cvm-authenticate:relayclient:accept-sender"
    ).start()
    try:
        ehlo(session)
        auth(session)
        session.upgrade()
        ehlo(session, b"post-tls.test")
        session.command(b"MAIL FROM:<from@test>\r\n", b"250 ")
        session.command(
            b"RCPT TO:<external@test>\r\n",
            expected_code(args.expect, b"550 ", b"250 "),
        )
    finally:
        session.close()


def protocol_identity_scenario(args, root):
    queue = os.path.join(root, "queue")
    os.makedirs(os.path.join(queue, "tmp"))
    os.makedirs(os.path.join(queue, "new"))
    session = StarttlsSession(
        args,
        "starttls-ucspi:add-received:accept",
        backend="queuedir",
        extra_env={"QUEUEDIR": queue},
    ).start()
    try:
        ehlo(session, b"pre-tls.example")
        session.upgrade()
        session.command(b"MAIL FROM:<from@test>\r\n", b"250 ")
        session.command(b"RCPT TO:<to@test>\r\n", b"250 ")
        session.command(b"DATA\r\n", b"354 ")
        session.client.sendall(b"Subject: state boundary\r\n\r\nbody\r\n.\r\n")
        check(session.reply()[-1].startswith(b"250 "), "message accepted")
        queued = [os.path.join(queue, "new", name) for name in os.listdir(os.path.join(queue, "new"))]
        check(len(queued) == 1, "one queued message")
        with open(queued[0], "rb") as stream:
            message = stream.read()
        if args.expect == "fixed":
            check(b"pre-tls.example" not in message, "pre-TLS EHLO identity discarded")
            check(b"with SMTP via" in message, "protocol identity reset to SMTP")
            check(b"with ESMTP via" not in message, "pre-TLS ESMTP identity discarded")
        else:
            check(b"pre-tls.example" in message, "vulnerable arm retains EHLO identity")
            check(b"with ESMTP via" in message, "vulnerable arm retains ESMTP identity")
    finally:
        session.close()


def queuedir_collision_scenario(args, root):
    """Exercise the installed queuedir backend's publish-collision path."""
    queue = os.path.join(root, "queue-collision")
    tmp_dir = os.path.join(queue, "tmp")
    new_dir = os.path.join(queue, "new")
    os.makedirs(tmp_dir)
    os.makedirs(new_dir)
    session = StarttlsSession(
        args,
        "accept",
        backend="queuedir",
        extra_env={"QUEUEDIR": queue},
    ).start()
    try:
        ehlo(session, b"queue-collision.test")
        session.command(b"MAIL FROM:<from@test>\r\n", b"250 ")
        temporary = os.listdir(tmp_dir)
        check(len(temporary) == 1, "queuedir created one private temporary file")
        target = os.path.join(new_dir, temporary[0])
        sentinel = b"existing-queue-entry-must-survive\n"
        with open(target, "wb") as stream:
            stream.write(sentinel)

        session.command(b"RCPT TO:<to@test>\r\n", b"250 ")
        session.command(b"DATA\r\n", b"354 ")
        session.client.sendall(b"Subject: collision\r\n\r\nbody\r\n.\r\n")
        check(
            session.reply()[-1].startswith(b"451 "),
            "queuedir reports an atomic publication collision",
        )
        with open(target, "rb") as stream:
            check(stream.read() == sentinel, "existing queue entry is unchanged")
        check(not os.listdir(tmp_dir), "failed writer removes only its temporary file")
    finally:
        session.close()


def ordinary_reset_scenario(args):
    session = StarttlsSession(
        args, "starttls-ucspi:cvm-authenticate:relayclient:accept-sender"
    ).start()
    try:
        ehlo(session)
        auth(session)
        session.command(b"MAIL FROM:<one@test>\r\n", b"250 ")
        session.command(b"RCPT TO:<one@external>\r\n", b"250 ")
        session.command(b"DATA\r\n", b"354 ")
        session.client.sendall(b"Subject: one\r\n\r\none\r\n.\r\n")
        check(session.reply()[-1].startswith(b"250 "), "first message accepted")
        session.command(b"MAIL FROM:<two@test>\r\n", b"250 ")
        session.command(b"RCPT TO:<two@external>\r\n", b"250 ")
    finally:
        session.close()


def malformed_pipeline_scenario(args):
    session = StarttlsSession(args, "starttls-ucspi:accept").start()
    try:
        ehlo(session)
        session.client.sendall(b"STARTTLS\r\nMAIL FROM:<smuggled@test>\r\n")
        check(session.reply()[-1].startswith(b"220 "), "STARTTLS accepted")
        readable, _, _ = select.select([session.control_read], [], [], 5.0)
        check(bool(readable), "pipelined STARTTLS reaches UCSPI control")
        check(os.read(session.control_read, 1) == b"y", "pipelined transition requested")
        session._activate_tls()
        check(
            session.reply()[-1].startswith(b"500 "),
            "pipelined plaintext is rejected after TLS establishment",
        )
        ehlo(session, b"recovered-after-reject.test")
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mailfront", required=True)
    parser.add_argument("--modules", required=True)
    parser.add_argument("--auth-module", required=True)
    parser.add_argument("--openssl", required=True)
    parser.add_argument(
        "--expect", choices=("original", "transaction-only", "fixed"), required=True
    )
    parser.add_argument(
        "--starttls-only",
        action="store_true",
        help="run only the six scenarios shared by all three STARTTLS arms",
    )
    args = parser.parse_args()

    root = tempfile.mkdtemp(prefix="mailfront-starttls-")
    try:
        args.certificate = os.path.join(root, "certificate.pem")
        args.private_key = os.path.join(root, "private-key.pem")
        subprocess.run(
            [
                args.openssl,
                "req",
                "-config",
                "/dev/null",
                "-x509",
                "-newkey",
                "rsa:2048",
                "-nodes",
                "-keyout",
                args.private_key,
                "-out",
                args.certificate,
                "-subj",
                "/CN=localhost",
                "-days",
                "1",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        transaction_scenario(args)
        authentication_scenario(args)
        authorization_scenario(args)
        protocol_identity_scenario(args, root)
        ordinary_reset_scenario(args)
        malformed_pipeline_scenario(args)
        scenario_count = 6
        if args.expect == "fixed" and not args.starttls_only:
            queuedir_collision_scenario(args, root)
            scenario_count += 1
        print(
            "STARTTLS matrix: {} scenarios, {} assertions PASS ({})".format(
                scenario_count, check.count, args.expect
            )
        )
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    main()
