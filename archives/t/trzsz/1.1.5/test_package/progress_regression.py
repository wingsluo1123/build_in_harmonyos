"""Exercise trzsz's real file/protocol functions; stdout is the evidence record.

Run with the tested trzsz-libs/trzsz-svr on the interpreter's import path.
--baseline expects the original zero-progress acceptance and stops it with a
finite peer fail frame. The default expects the two file-data guards.
"""

import argparse
import contextlib
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from pathlib import Path

from trzsz.libs import transfer, utils
from trzsz.svr.__version__ import __version__


STOP = "bounded baseline peer stop"
CLI_TIMEOUT = 20


def require(condition, message):
    if not condition:
        raise AssertionError(message)


class Steps(utils.TrzszCallback):
    def __init__(self):
        self.steps = []
        self.done = 0

    def on_step(self, step):
        self.steps.append(step)

    def on_done(self):
        self.done += 1


def fresh():
    utils.CONFIG = utils.TransferConfig()
    utils.GLOBAL = utils.GlobalVariables()
    utils.CONFIG.timeout = 2
    utils.CONFIG.max_buf_size = 1024
    utils.CONFIG.newline = "!\n" if utils.IS_RUNNING_ON_WINDOWS else "\n"


def line(kind, value):
    return ("#%s:%s%s" % (kind, value, utils.CONFIG.newline)).encode("utf8")


def stop_frame():
    return line("fail", utils.encode_buffer(STOP.encode("utf8")))


def expect_error(action, remote, expected_message):
    try:
        action()
    except utils.TrzszError as error:
        require(error.is_remote_fail() == remote,
                "unexpected error origin: %s" % error)
        if remote:
            require(str(error) == STOP, "unexpected baseline stop error")
        else:
            require(error.typ is None and not error.trace_back(),
                    "file guard must use the local, trace=False error path")
            require(str(error) == expected_message, "unexpected file guard error: %s" % error)
        return {"message": str(error), "type": error.typ}
    raise AssertionError("expected TrzszError was not raised")


def sender_truncated(baseline):
    fresh()
    writer = io.StringIO()
    utils.GLOBAL.trzsz_writer = writer
    callback = Steps()
    with tempfile.TemporaryDirectory(prefix="trzsz-progress-send-") as directory:
        path = Path(directory) / "source.bin"
        path.write_bytes(b"x" * 128)
        utils.GLOBAL.next_read_buffer = line("SUCC", 128)
        size = transfer.send_file_size({"abs_path": str(path)}, callback)
        require(size == 128 and "#SIZE:128" in writer.getvalue(),
                "the real SIZE handshake did not establish 128 bytes")
        # Truncate the real source only after the SIZE handshake succeeded.
        with path.open("wb") as truncated:
            truncated.truncate(0)
        utils.GLOBAL.next_read_buffer = line("SUCC", 0) + stop_frame()
        with path.open("rb") as source:
            error = expect_error(
                lambda: transfer.send_file_data(source, size, callback), baseline,
                "Unexpected end of file")
        wire = writer.getvalue()
        data_lines = [item for item in wire.splitlines() if item.startswith("#DATA:")]
        require(len(data_lines) == (2 if baseline else 0),
                "unexpected number of emitted empty DATA frames")
        for item in data_lines:
            require(utils.decode_buffer(item.split(":", 1)[1].rstrip("!")) == b"",
                    "DATA was not a decoded empty block")
        require(callback.steps == ([0, 0] if baseline else [0]),
                "unexpected progress after EOF")
        require("#MD5:" not in wire and callback.done == 0,
                "truncated transfer reached MD5 completion")
        require(path.stat().st_size == 0, "the real source was not truncated")
        return {"advertised_size": size, "actual_size": 0, "steps": callback.steps,
                "error": error, "stdout_wire": wire}


def receiver_empty(baseline, binary):
    fresh()
    utils.CONFIG.binary = binary
    writer = io.StringIO()
    utils.GLOBAL.trzsz_writer = writer
    callback = Steps()
    payload = b"#DATA:0\n" if binary else line("DATA", utils.encode_buffer(b""))
    # Both frames go through recv_data/recv_check and the original parser.
    utils.GLOBAL.next_read_buffer = payload + stop_frame()
    with tempfile.TemporaryFile(mode="w+b") as destination:
        error = expect_error(
            lambda: transfer.recv_file_data(destination, 1, callback), baseline,
            "Received empty file data")
        destination.seek(0, os.SEEK_END)
        require(destination.tell() == 0, "empty DATA wrote file bytes")
    wire = writer.getvalue()
    require(wire.count("#SUCC:0") == (1 if baseline else 0),
            "empty DATA received an unexpected success acknowledgement")
    require(callback.steps == ([0, 0] if baseline else [0]) and callback.done == 0,
            "empty DATA reached progress/completion")
    return {"mode": "binary" if binary else "text", "remaining": 1,
            "input_wire": payload.decode("ascii"), "steps": callback.steps,
            "error": error, "stdout_wire": wire}


def valid_file(data):
    fresh()
    sender = io.StringIO()
    utils.GLOBAL.trzsz_writer = sender
    send_steps = Steps()
    digest = hashlib.md5(data).digest()
    lengths = [min(1024, len(data) - start) for start in range(0, len(data), 1024)]
    utils.GLOBAL.next_read_buffer = (line("SUCC", len(data))
                                     + b"".join(line("SUCC", size) for size in lengths)
                                     + line("SUCC", utils.encode_buffer(digest)))
    with tempfile.TemporaryDirectory(prefix="trzsz-valid-file-") as directory:
        path = Path(directory) / "source.bin"
        path.write_bytes(data)
        size = transfer.send_file_size({"abs_path": str(path)}, send_steps)
        require(size == len(data), "valid file SIZE handshake differs from actual file")
        with path.open("rb") as source:
            actual_digest = transfer.send_file_data(source, size, send_steps)
    transfer.send_file_md5(actual_digest, send_steps)
    require(actual_digest == digest and send_steps.done == 1,
            "sender did not complete the actual file MD5 handshake")
    sent_wire = sender.getvalue()
    require(sent_wire.count("#DATA:") == len(lengths), "incorrect DATA block count")

    fresh()
    receiver = io.StringIO()
    utils.GLOBAL.trzsz_writer = receiver
    utils.GLOBAL.next_read_buffer = sent_wire.encode("utf8")
    recv_steps = Steps()
    with tempfile.TemporaryFile(mode="w+b") as destination:
        size = transfer.recv_file_size(recv_steps)
        require(size == len(data), "received file SIZE differs from actual file")
        received_digest = transfer.recv_file_data(destination, size, recv_steps)
        transfer.recv_file_md5(received_digest, recv_steps)
        destination.seek(0)
        require(destination.read() == data, "receiver bytes differ from the real source")
    expected_steps = [0]
    for size in lengths:
        expected_steps.append(expected_steps[-1] + size)
    require(send_steps.steps == recv_steps.steps == expected_steps,
            "file progress did not match actual byte lengths")
    require(received_digest == digest and recv_steps.done == 1,
            "receiver did not complete the actual file MD5 handshake")
    return {"size": len(data), "chunks": lengths, "steps": recv_steps.steps,
            "md5": digest.hex(), "sender_stdout_wire": sent_wire,
            "receiver_stdout_wire": receiver.getvalue()}


@contextlib.contextmanager
def peer_streams(process, observed):
    """Use real read_buffer; the wrapper records its actual OS-read bytes."""
    old_stdin, old_read = sys.stdin, utils.read_buffer
    writer = io.TextIOWrapper(process.stdin, encoding="utf8", write_through=True)

    def observed_read(size):
        buffered = bool(utils.GLOBAL.next_read_buffer)
        value = old_read(size)
        if not buffered:
            observed.extend(value)
        return value

    fresh()
    sys.stdin = process.stdout
    utils.GLOBAL.trzsz_writer = writer
    utils.read_buffer = observed_read
    try:
        yield
    finally:
        utils.read_buffer = old_read
        sys.stdin = old_stdin
        writer.detach()  # Popen retains ownership of the raw pipe.


def cli_exchange(module, arguments, peer):
    environment = os.environ.copy()
    environment.pop("TMUX", None)  # This scoped child tests the normal pipe protocol.
    command = [sys.executable, "-m", module] + arguments
    # Match the parent's tested modules even if the caller's cwd contains the
    # upstream metapackage, whose plain __init__.py would shadow libs/svr.
    module_root = Path(transfer.__file__).resolve().parents[2]
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, bufsize=0, env=environment, cwd=module_root)
    expired = []

    def stop_own_child():
        if process.poll() is None:
            expired.append(True)
            try:
                process.kill()
            except ProcessLookupError:
                pass

    watchdog = threading.Timer(CLI_TIMEOUT, stop_own_child)
    watchdog.daemon = True
    observed = bytearray()
    started = time.monotonic()
    failure = None
    result = None
    watchdog.start()
    try:
        try:
            with peer_streams(process, observed):
                result = peer()
        except Exception as error:
            failure = error
        tail, stderr = process.communicate()
        wire = (bytes(observed) + tail).decode("utf8", errors="backslashreplace")
        evidence = {"command": command, "cwd": str(module_root),
                    "parent_transfer_module": transfer.__file__, "returncode": process.returncode,
                    "elapsed_seconds": round(time.monotonic() - started, 3),
                    "watchdog_killed": bool(expired), "peer": result,
                    "stdout_wire": wire,
                    "stderr": stderr.decode("utf8", errors="backslashreplace")}
        print(json.dumps({"cli_evidence": evidence}, ensure_ascii=False), flush=True)
        require(not expired, "the 20-second safety timeout killed this script's CLI child")
        if failure:
            raise failure
        require(process.returncode == 0,
                "the original CLI return-code behavior changed or an unrelated failure occurred")
        require("#MD5:" not in wire, "failed CLI transfer continued to MD5")
        return evidence
    finally:
        watchdog.cancel()
        if process.poll() is None:
            process.kill()
            process.communicate()


def cli_sender(baseline):
    with tempfile.TemporaryDirectory(prefix="trzsz-cli-send-") as directory:
        source = Path(directory) / "source.bin"
        source.write_bytes(b"x" * 128)
        destination = Path(directory) / "received"
        destination.mkdir()

        def peer():
            transfer.send_action(True, __version__, False)
            transfer.recv_config()
            require(transfer.recv_file_num(None) == 1, "unexpected CLI file count")
            output, _name = transfer.recv_file_name(str(destination), None)
            with output:
                size = utils.recv_integer("SIZE")
                require(size == 128, "unexpected CLI advertised size")
                # Deterministic: truncate BEFORE acknowledging SIZE to release the sender.
                with source.open("wb") as truncated:
                    truncated.truncate(0)
                utils.send_integer("SUCC", size)
                if baseline:
                    require(utils.recv_data() == b"", "baseline sender did not emit empty DATA")
                    utils.send_integer("SUCC", 0)
                    require(utils.recv_data() == b"", "baseline sender did not repeat empty DATA")
                    utils.send_string("fail", STOP)
                    return {"advertised_size": size, "actual_size": 0,
                            "decoded_empty_blocks": 2, "zero_acknowledgements": 1,
                            "finite_peer_stop_sent": True}
                try:
                    utils.recv_data()
                except utils.TrzszError as error:
                    require(error.is_remote_fail(), "sender CLI did not propagate fail")
                    require(str(error) == "Unexpected end of file", "unexpected sender CLI error")
                    return {"advertised_size": size, "actual_size": 0,
                            "remote_error": str(error), "remote_error_type": error.typ}
                raise AssertionError("patched sender CLI emitted DATA instead of fail")

        evidence = cli_exchange("trzsz.svr.send", ["-q", "-t", "2", str(source)], peer)
        require(source.stat().st_size == 0, "CLI source was not actually truncated")
        require(evidence["stdout_wire"].count("#DATA:") == (2 if baseline else 0),
                "unexpected CLI empty DATA count")
        if not baseline:
            require("#fail:" in evidence["stdout_wire"], "sender CLI fail frame is missing")
        return evidence


def cli_receiver(baseline):
    with tempfile.TemporaryDirectory(prefix="trzsz-cli-recv-") as directory:
        source = Path(directory) / "peer.bin"
        source.write_bytes(b"x")
        destination = Path(directory) / "received"
        destination.mkdir()
        metadata = {"abs_path": str(source), "path_name": ["peer.bin"],
                    "path_id": 0, "is_dir": False}

        def peer():
            transfer.send_action(True, __version__, False)
            transfer.recv_config()
            transfer.send_file_num(1, None)
            transfer.send_file_name(metadata, None)
            require(transfer.send_file_size(metadata, None) == 1, "unexpected CLI SIZE")
            utils.send_data(b"")
            if baseline:
                require(utils.recv_integer("SUCC") == 0, "baseline receiver did not ACK empty DATA")
                utils.send_string("fail", STOP)
                return {"remaining": 1, "decoded_empty_block_sent": True,
                        "zero_acknowledgements": 1, "finite_peer_stop_sent": True}
            try:
                utils.recv_integer("SUCC")
            except utils.TrzszError as error:
                require(error.is_remote_fail(), "receiver CLI did not propagate fail")
                require(str(error) == "Received empty file data", "unexpected receiver CLI error")
                return {"remaining": 1, "remote_error": str(error),
                        "remote_error_type": error.typ}
            raise AssertionError("patched receiver CLI acknowledged empty DATA")

        evidence = cli_exchange("trzsz.svr.recv", ["-q", "-t", "2", str(destination)], peer)
        wire = evidence["stdout_wire"]
        require(wire.count("#SUCC:0") == (1 if baseline else 0), "unexpected CLI SUCC0")
        require("Saved " not in wire, "failed receiver CLI reported success")
        require((destination / "peer.bin").stat().st_size == 0,
                "empty DATA unexpectedly wrote destination bytes")
        if not baseline:
            require("#fail:" in wire, "receiver CLI fail frame is missing")
        return evidence


def main():
    arguments = argparse.ArgumentParser(description=__doc__)
    arguments.add_argument("--baseline", action="store_true")
    args = arguments.parse_args()
    print(json.dumps({"version": __version__, "mode": "baseline" if args.baseline else "patched",
                      "platform": sys.platform, "python": sys.version,
                      "transfer_module": transfer.__file__, "utils_module": utils.__file__,
                      "cli_timeout_seconds": CLI_TIMEOUT}, ensure_ascii=False), flush=True)
    cases = [("sender_SIZE_then_real_truncation", lambda: sender_truncated(args.baseline)),
             ("receiver_text_decoded_empty", lambda: receiver_empty(args.baseline, False)),
             ("receiver_binary_decoded_empty", lambda: receiver_empty(args.baseline, True)),
             ("legal_SIZE_zero_MD5", lambda: valid_file(b"")),
             ("nonempty_multiblock_MD5", lambda: valid_file((b"0123456789" * 205)[:2049])),
             ("CLI_sender_real_truncation_fail", lambda: cli_sender(args.baseline)),
             ("CLI_receiver_empty_fail", lambda: cli_receiver(args.baseline))]
    failed, skipped = 0, 0
    for name, action in cases:
        if utils.IS_RUNNING_ON_WINDOWS and (name.startswith("CLI_") or "binary" in name):
            skipped += 1
            print(json.dumps({"case": name, "status": "SKIP",
                              "reason": "native Windows CLI/binary paths differ; POSIX/OHOS result NOT_RUN"}),
                  flush=True)
            continue
        try:
            evidence = action()
            print(json.dumps({"case": name, "status": "PASS", "evidence": evidence},
                             ensure_ascii=False), flush=True)
        except Exception:
            failed += 1
            print(json.dumps({"case": name, "status": "FAIL", "traceback": traceback.format_exc()},
                             ensure_ascii=False), flush=True)
        finally:
            fresh()
    print(json.dumps({"summary": {"total": len(cases), "passed": len(cases) - failed - skipped,
                                 "failed": failed, "skipped": skipped}}), flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
