"""
Integration tests that validate the *actual* zenoh-python object shapes we rely on.

These are in-process (no external router needed for the local session in our environment).
"""

import time
import uuid

import pytest


zenoh = pytest.importorskip("zenoh")


def test_pubsub_payload_is_zbytes_and_has_to_bytes():
    z = zenoh.open(zenoh.Config())
    ke = f"test/payload_shape/{uuid.uuid4().hex}"

    seen = {"done": False}

    def cb(sample):
        assert hasattr(sample, "payload")
        payload = sample.payload
        # In this environment it is builtins.ZBytes
        assert payload is not None
        assert hasattr(payload, "to_bytes")
        b = payload.to_bytes()
        assert b == b"hello"
        seen["done"] = True

    sub = z.declare_subscriber(ke, cb)
    pub = z.declare_publisher(ke)
    pub.put(b"hello")

    for _ in range(50):
        if seen["done"]:
            break
        time.sleep(0.05)

    sub.undeclare()
    pub.undeclare()
    z.close()

    assert seen["done"], "did not receive pub/sub sample"


def test_service_reply_shapes_ok_is_sample_err_is_replyerror():
    z = zenoh.open(zenoh.Config())
    ke = f"test/service_shape/{uuid.uuid4().hex}"

    def qhandler(query):
        # Echo the same payload/attachment
        query.reply(ke, query.payload, attachment=query.attachment)

    qable = z.declare_queryable(ke, qhandler, complete=True)
    querier = z.declare_querier(
        ke,
        target=zenoh.QueryTarget.ALL_COMPLETE,
        timeout=2000,
        consolidation=zenoh.ConsolidationMode.NONE,
    )

    seen = {"done": False}

    def cb(reply):
        assert reply.err is None
        ok = reply.ok
        assert ok is not None
        # ok is a Sample, with ok.payload being ZBytes
        payload = ok.payload
        assert hasattr(payload, "to_bytes")
        assert payload.to_bytes() == b"ping"
        assert ok.attachment.to_bytes() == b"att"
        seen["done"] = True

    querier.get(cb, parameters="", payload=zenoh.ZBytes(b"ping"), attachment=zenoh.ZBytes(b"att"))

    for _ in range(50):
        if seen["done"]:
            break
        time.sleep(0.05)

    qable.undeclare()
    querier.undeclare()
    z.close()

    assert seen["done"], "did not receive service reply"

