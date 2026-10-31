"""Verify installed Windows packages against authenticated archive MD5 records.

Archive authenticity is anchored by the SHA-256 source lock; upstream MD5
records detect incomplete/changed unpacked files. Optional repair writes only
exact members of authenticated Windows binary archives, atomically per file.
"""
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import time
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("environment", type=Path)
    parser.add_argument("--output-prefix", required=True)
    parser.add_argument("--repair", action="store_true")
    args = parser.parse_args()
    root = args.environment.resolve()
    lock = json.loads((root / "source-lock.json").read_text())
    started = time.monotonic()
    checks = []
    complete = {p["package"]: True for p in lock["packages"]}
    for package in lock["packages"]:
        name = package["package"]
        binary = Path(package["binary"]["path"])
        if hashlib.sha256(binary.read_bytes()).hexdigest() != package["binary"]["sha256"]:
            raise ValueError(f"Archive identity mismatch: {name}")
        source = Path(package["source"]["path"])
        if hashlib.sha256(source.read_bytes()).hexdigest() != package["source"]["sha256"]:
            raise ValueError(f"Source archive identity mismatch: {name}")
        installed = root / "library" / name
        with zipfile.ZipFile(binary) as archive:
            lines = archive.read(name + "/MD5").decode().splitlines()
        for line in lines:
            expected, filename = line.split(maxsplit=1)
            path = installed / filename.lstrip("*")
            if not path.resolve().is_relative_to(installed.resolve()):
                raise ValueError("Unsafe archive MD5 path")
            checks.append((name, path, expected))

    def check(item):
        name, path, expected = item
        try:
            return name, hashlib.md5(path.read_bytes()).hexdigest() == expected
        except OSError:
            return name, False

    with concurrent.futures.ThreadPoolExecutor(max_workers=24) as executor:
        for name, success in executor.map(check, checks):
            complete[name] &= success
    damaged_before = sorted(k for k, v in complete.items() if not v)
    if args.repair:
        def repair(package):
            name = package["package"]
            with zipfile.ZipFile(package["binary"]["path"]) as archive:
                for member in archive.infolist():
                    if member.is_dir():
                        continue
                    path = (root / "library" / member.filename).resolve()
                    if not path.is_relative_to((root / "library" / name).resolve()):
                        raise ValueError("Unsafe binary member path")
                    content = archive.read(member)
                    if path.exists() and path.read_bytes() == content:
                        continue
                    path.parent.mkdir(parents=True, exist_ok=True)
                    temporary = path.with_name(path.name + ".bsfm-partial")
                    with temporary.open("wb") as stream:
                        stream.write(content)
                        stream.flush()
                        os.fsync(stream.fileno())
                    temporary.replace(path)
            return name
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            list(executor.map(repair, [p for p in lock["packages"] if p["package"] in damaged_before]))
        complete = {p["package"]: True for p in lock["packages"]}
        with concurrent.futures.ThreadPoolExecutor(max_workers=24) as executor:
            for name, success in executor.map(check, checks):
                complete[name] &= success
    report = {"schema": "bsfm.installed-package-audit.v1", "checked_files": len(checks),
              "repair_requested": args.repair, "damaged_before": damaged_before,
              "complete_packages": sorted(k for k, v in complete.items() if v),
              "incomplete_packages": sorted(k for k, v in complete.items() if not v),
              "elapsed_seconds": time.monotonic() - started}
    prefix = root / args.output_prefix
    if not prefix.resolve().is_relative_to(root):
        raise ValueError("Output prefix must stay inside environment")
    prefix.with_suffix(".json").write_text(json.dumps(report, indent=2) + "\n")
    prefix.with_suffix(".txt").write_text("\n".join(report["complete_packages"]) + "\n")
    print(json.dumps({"checked_files": len(checks), "complete": len(report["complete_packages"]),
                      "incomplete": report["incomplete_packages"]}))
    return bool(report["incomplete_packages"])


if __name__ == "__main__":
    raise SystemExit(main())
