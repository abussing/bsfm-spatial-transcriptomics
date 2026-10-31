"""Acquire a frozen Windows package closure; never install or resolve silently.

Run with the external environment root containing R-4.5.3. Keeps archives,
indexes and the acquired manifest there. Existing downloads are rehashed.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import tarfile
import urllib.error
import urllib.request
import zipfile

CRAN = "https://cran.r-project.org"
BIOC = "https://bioconductor.posit.co/packages/3.22/bioc"
SNAPSHOT = "https://packagemanager.posit.co/cran/2026-03-12"
PINS = {"Seurat": "5.4.0", "SeuratObject": "5.4.0",
        "sctransform": "0.4.3", "Matrix": "1.7-4", "glmGamPoi": "1.22.0"}


def dcf(text):
    records = []
    for block in re.split(r"\n\s*\n", text.strip()):
        record = {}
        key = None
        for line in block.splitlines():
            if line.startswith((" ", "\t")) and key:
                record[key] += " " + line.strip()
            elif ":" in line:
                key, value = line.split(":", 1)
                record[key] = value.strip()
        if record:
            records.append(record)
    return records


def download(url, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        partial = path.with_name(path.name + ".partial")
        with urllib.request.urlopen(url, timeout=90) as response, partial.open("wb") as out:
            while chunk := response.read(1024 * 1024):
                out.write(chunk)
        partial.replace(path)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return {"url": url, "path": str(path.resolve()), "bytes": path.stat().st_size,
            "sha256": digest.hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("environment", type=Path)
    parser.add_argument("--lock", type=Path,
                        help="Restore the recorded archive set without resolving new dependencies")
    parser.add_argument("--verify-only", action="store_true",
                        help="With --lock, verify existing archives without downloads or writes")
    args = parser.parse_args()
    root = args.environment.resolve()
    if args.lock:
        lock = json.loads(args.lock.read_text(encoding="utf-8"))
        records = [(lock["R_source"], "source")]
        records += [(p[k], k) for p in lock["packages"] for k in ("source", "binary")]
        for record, kind in records:
            name = record["url"].rsplit("/", 1)[-1]
            destination = root / "downloads" / kind / name
            if args.verify_only and not destination.exists():
                raise RuntimeError(f"Missing locked archive: {name}")
            downloaded = download(record["url"], destination)
            if downloaded["sha256"] != record["sha256"]:
                raise RuntimeError(f"Locked archive hash mismatch: {name}")
            record["path"] = downloaded["path"]
        if not args.verify_only:
            (root / "source-lock.json").write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
        print("Verified exact locked archive set; no dependency resolution")
        return
    if args.verify_only:
        parser.error("--verify-only requires --lock")
    rscript = root / "R-4.5.3/bin/Rscript.exe"
    # Use only this isolated R's bundled library when resolving base packages.
    query = 'stopifnot(getRversion()=="4.5.3"); write.table(installed.packages(lib.loc=.Library)[,c("Package","Version")],stdout(),sep="\\t",row.names=FALSE,quote=FALSE)'
    result = subprocess.run([str(rscript), "--vanilla", "-e", query],
                            check=True, capture_output=True, text=True)
    base = {r["Package"]: r["Version"] for r in csv.DictReader(io.StringIO(result.stdout), delimiter="\t")}
    assert base["Matrix"] == PINS["Matrix"]
    indexes = []
    available = {}
    for name, repo in [("cran", CRAN), ("bioc", BIOC)]:
        suffix = "bin/windows/contrib/4.5"
        path = root / "downloads" / f"{name}-win-PACKAGES.gz"
        indexes.append(download(repo + "/" + suffix + "/PACKAGES.gz", path))
        for record in dcf(gzip.decompress(path.read_bytes()).decode()):
            record["repository"] = repo
            available[record["Package"]] = record
    # Exact older Seurat binary from a dated CRAN mirror snapshot.
    seurat = root / "downloads/binary/Seurat_5.4.0.zip"
    download(SNAPSHOT + "/bin/windows/contrib/4.5/Seurat_5.4.0.zip", seurat)
    with zipfile.ZipFile(seurat) as archive:
        record = dcf(archive.read("Seurat/DESCRIPTION").decode())[0]
    record["repository"] = SNAPSHOT
    available["Seurat"] = record
    selected = {}
    pending = list(PINS) + ["renv", "BiocManager", "BiocVersion", "digest"]
    while pending:
        name = pending.pop()
        if name in base or name in selected or name == "R":
            continue
        if name not in available:
            raise RuntimeError(f"No binary metadata for required dependency {name}")
        rec = available[name]
        if name in PINS and rec["Version"] != PINS[name]:
            raise RuntimeError(f"Frozen version mismatch: {name} {rec['Version']}")
        selected[name] = rec
        for field in ["Depends", "Imports", "LinkingTo"]:
            pending.extend(re.sub(r"\s*\(.*?\)", "", d).strip()
                           for d in rec.get(field, "").split(",") if d.strip())
    plan = {"schema": "bsfm.environment-acquisition.v1", "indexes": indexes,
            "bundled_packages": base, "selected": selected}
    (root / "package-plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    print(f"Resolved {len(selected)} external packages and {len(base)} bundled packages", flush=True)

    def acquire(item):
        name, rec = item
        version, repo = rec["Version"], rec["repository"]
        binary_name = f"{name}_{version}.zip"
        binary = download(repo + "/bin/windows/contrib/4.5/" + binary_name,
                          root / "downloads/binary" / binary_name)
        with zipfile.ZipFile(binary["path"]) as archive:
            desc = archive.read(name + "/DESCRIPTION")
        got = dcf(desc.decode())[0]
        if (got["Package"], got["Version"]) != (name, version):
            raise RuntimeError(f"Binary identity mismatch {name}")
        binary["DESCRIPTION_sha256"] = hashlib.sha256(desc).hexdigest()
        binary["Built"] = got.get("Built")
        source_name = f"{name}_{version}.tar.gz"
        # Match the binary version exactly, even when the current source is newer.
        source_repo = BIOC if repo == BIOC else CRAN
        source_url = source_repo + "/src/contrib/" + source_name
        try:
            source = download(source_url, root / "downloads/source" / source_name)
        except urllib.error.HTTPError as exc:
            if exc.code != 404 or source_repo == BIOC:
                raise
            source_url = CRAN + f"/src/contrib/Archive/{name}/" + source_name
            source = download(source_url, root / "downloads/source" / source_name)
        with tarfile.open(source["path"], "r:gz") as archive:
            desc = archive.extractfile(name + "/DESCRIPTION").read()
        got = dcf(desc.decode())[0]
        if (got["Package"], got["Version"]) != (name, version):
            raise RuntimeError(f"Source identity mismatch {name}")
        source["DESCRIPTION_sha256"] = hashlib.sha256(desc).hexdigest()
        print(f"Acquired {name} {version}", flush=True)
        return {"package": name, "version": version, "repository": repo,
                "binary": binary, "source": source}

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        packages = list(executor.map(acquire, sorted(selected.items())))
    # Preserve the source for the R distribution, which also identifies its
    # bundled recommended packages, including the frozen Matrix 1.7-4.
    r_source = download(CRAN + "/src/base/R-4/R-4.5.3.tar.gz",
                        root / "downloads/source/R-4.5.3.tar.gz")
    plan = {"schema": "bsfm.package-source-lock.v1", "R_source": r_source,
            "bundled_packages": base, "packages": packages, "indexes": indexes,
            "binary_source_equivalence": "Matching name/version; no reproducible-build byte-equivalence claim."}
    (root / "source-lock.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    print("Acquisition complete", flush=True)


if __name__ == "__main__":
    main()
