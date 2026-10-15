"""Persist a sensor batch, then consume it in a fresh installed-package process."""
import json
import os
from pathlib import Path
import sys

import plyvel


def consume(phase, path):
    root = Path(os.environ["PLYVEL_PACKAGE_ROOT"]).resolve()
    origin = Path(plyvel.__file__).resolve()
    if not origin.is_relative_to(root):
        raise RuntimeError(f"Consumer loaded an unexpected module: {origin}")
    with plyvel.DB(path, create_if_missing=(phase == "write")) as db:
        readings = db.prefixed_db(b"sensor:")
        if phase == "write":
            with readings.write_batch(transaction=True, sync=True) as batch:
                batch.put(b"001", b"20")
                batch.put(b"002", b"19")
                batch.put(b"obsolete", b"0")
            with readings.snapshot() as snapshot:
                readings.put(b"001", b"21", sync=True)
                if snapshot.get(b"001") != b"20":
                    raise RuntimeError("Snapshot changed during the producer update")
            try:
                with readings.write_batch(transaction=True) as batch:
                    batch.put(b"uncommitted", b"999")
                    raise ValueError("Abort the incomplete sensor batch")
            except ValueError:
                pass
            readings.delete(b"obsolete", sync=True)
        elif phase != "read":
            raise ValueError(f"Unknown consumer phase: {phase}")
        records = list(readings.iterator())
        if records != [(b"001", b"21"), (b"002", b"19")]:
            raise RuntimeError(f"Committed sensor records differ: {records!r}")
        return {"phase": phase, "pid": os.getpid(), "origin": str(origin),
                "records": [[k.decode("ascii"), v.decode("ascii")] for k, v in records],
                "total": sum(int(value) for _, value in records)}


if __name__ == "__main__":
    print(json.dumps(consume(sys.argv[1], sys.argv[2])))
