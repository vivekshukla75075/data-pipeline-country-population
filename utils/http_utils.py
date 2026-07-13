"""Utility helpers for handling HTTP response bodies safely."""

import gzip
import zlib
from typing import Mapping


def decode_response_body(payload: bytes, headers: Mapping[str, str] | None = None) -> str:
    """Decode an HTTP response body, handling gzip/deflate content as needed."""
    if not payload:
        return ""

    headers = headers or {}
    content_encoding = str(headers.get("Content-Encoding", "") or headers.get("content-encoding", "") or "").lower()

    if "gzip" in content_encoding:
        return gzip.decompress(payload).decode("utf-8")

    if "deflate" in content_encoding:
        try:
            return zlib.decompress(payload).decode("utf-8")
        except zlib.error:
            return zlib.decompress(payload, -zlib.MAX_WBITS).decode("utf-8")

    if payload.startswith(b"\x1f\x8b"):
        return gzip.decompress(payload).decode("utf-8")

    if payload.startswith(b"x\x9c"):
        return zlib.decompress(payload).decode("utf-8")

    return payload.decode("utf-8")
