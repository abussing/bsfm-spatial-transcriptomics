"""Self-contained process-log evidence. External paths are provenance only."""
from __future__ import annotations

import base64
import binascii
import hashlib
import re

from .raw_preflight import require


def scan_log(content):
    """Preserve original bytes; decode only for a reproducible warning scan."""
    decoded = content.decode("utf-8", errors="replace")
    return {"text_encoding": "utf-8", "decode_errors": "replace",
            "stack_imbalance_detected": bool(re.search(r"stack[-\s]+imbalance", decoded, re.IGNORECASE)),
            "warning_lines": [line for line in decoded.splitlines() if "warning" in line.casefold()]}


def embed_log(content):
    return {"schema": "bsfm.embedded-process-log.v1", "encoding": "base64",
            "data": base64.b64encode(content).decode("ascii"), "bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(), "warning_scan": scan_log(content),
            "external_path_authority": "provenance_only"}


def authenticate_log(record):
    """Authenticate and scan embedded bytes without opening any path."""
    require(record.get("schema") == "bsfm.embedded-process-log.v1", "Missing embedded log schema")
    require(record.get("encoding") == "base64", "Unsupported embedded log encoding")
    require(record.get("external_path_authority") == "provenance_only", "External log path must be non-authoritative")
    require(isinstance(record.get("data"), str), "Missing embedded log bytes")
    try:
        content = base64.b64decode(record["data"], validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("Invalid embedded log base64") from exc
    require(type(record.get("bytes")) is int and len(content) == record["bytes"], "Embedded log byte count mismatch")
    require(hashlib.sha256(content).hexdigest() == record.get("sha256"), "Embedded log SHA-256 mismatch")
    measured = scan_log(content)
    require(record.get("warning_scan") == measured, "Embedded log warning scan mismatch")
    require(not measured["stack_imbalance_detected"], "Stack imbalance warning in embedded log")
    return content


def authenticate_process(process):
    require(process["exit_code"] == 0 and process["failure"] is None, "Process did not succeed")
    return authenticate_log(process["log"])
