"""Acquire mesh-environment records and archives, without installing packages."""
import argparse
import concurrent.futures
import csv
import gzip
import hashlib
import io
import json
import re
import subprocess
import tarfile
import urllib.request
import urllib.error
import zipfile
from pathlib import Path


def identity(path):
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"path": str(path.resolve()), "bytes": path.stat().st_size, "sha256": digest}


def fetch(url, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    receipt = path.with_suffix(path.suffix + '.acquisition.json')
    cached = json.loads(receipt.read_text(encoding='utf-8')) if receipt.exists() else None
    if not (path.exists() and cached and cached['url'] == url and
            cached['sha256'] == identity(path)['sha256']):
        tmp = path.with_suffix(path.suffix + ".partial")
        with urllib.request.urlopen(url, timeout=90) as src, tmp.open("wb") as dst:
            while data := src.read(1024 * 1024):
                dst.write(data)
        if path.exists() and identity(path)['sha256'] != identity(tmp)['sha256']:
            raise ValueError(f'Acquisition would change existing archive: {path}')
        tmp.replace(path)
        receipt.write_text(json.dumps(dict(url=url, **identity(path)), indent=2)+'\n', encoding='utf-8')
    return dict(url=url, **identity(path))


def dcf(text):
    records = []
    for block in text.strip().split("\n\n"):
        row, key = {}, None
        for line in block.splitlines():
            if line.startswith((" ", "\t")) and key:
                row[key] += " " + line.strip()
            elif ":" in line:
                key, val = line.split(":", 1)
                row[key] = val.strip()
        if row:
            records.append(row)
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--resolve-r", type=Path, help="Explicit immutable Rscript runtime")
    args = parser.parse_args()
    root = args.root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    url = "https://cran.r-project.org/src/contrib/Archive/fmesher/fmesher_0.7.0.tar.gz"
    path = root / "downloads/source/fmesher_0.7.0.tar.gz"
    record = fetch(url, path)
    with tarfile.open(path) as archive:
        desc = archive.extractfile("fmesher/DESCRIPTION").read()
    record["description"] = dcf(desc.decode())[0]
    assert record["description"]["Version"] == "0.7.0"
    (root / "fmesher-source.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))
    if args.resolve_r:
        resolve_r(root, args.resolve_r)


def resolve_r(root, rscript):
    snapshot = "https://packagemanager.posit.co/cran/2026-03-12"
    idxpath = root / "downloads/snapshot-win-PACKAGES.gz"
    index = fetch(snapshot + "/bin/windows/contrib/4.5/PACKAGES.gz", idxpath)
    available = {r["Package"]: r for r in dcf(gzip.decompress(idxpath.read_bytes()).decode())}
    assert available["fmesher"]["Version"] == "0.7.0", available["fmesher"]
    command = [str(rscript), "--vanilla", "-e", 'stopifnot(getRversion()=="4.5.3"); write.table(installed.packages(lib.loc=.Library)[,c("Package","Version","Priority")],stdout(),sep="\\t",row.names=FALSE,quote=FALSE)']
    query = subprocess.run(command, check=True, capture_output=True, text=True)
    bundled = {x["Package"]: x for x in csv.DictReader(io.StringIO(query.stdout), delimiter="\t")}
    # Install non-base dependencies into the new library, including Matrix.
    base = {k:v for k,v in bundled.items() if v['Priority'] == 'base'}
    needed = ["fmesher", "sf", "Matrix", "jsonlite"]
    selected = {}
    while needed:
        name = needed.pop()
        if name in base or name == "R" or name in selected:
            continue
        row = available[name]
        selected[name] = row
        for key in ["Depends", "Imports", "LinkingTo"]:
            needed.extend(re.findall(r"(?:^|,)\s*([A-Za-z][A-Za-z0-9.]*)", row.get(key, "")))
    def acquire(name):
        row = selected[name]; ver = row['Version']; filename = f"{name}_{ver}"
        binary = fetch(snapshot + f"/bin/windows/contrib/4.5/{filename}.zip", root / f"downloads/binary/{filename}.zip")
        with zipfile.ZipFile(binary['path']) as z:
            desc = dcf(z.read(name + '/DESCRIPTION').decode())[0]
        assert desc['Version'] == ver
        source_path = root / f"downloads/source/{filename}.tar.gz"
        errors = []
        for url in [f"https://cran.r-project.org/src/contrib/{filename}.tar.gz", f"https://cran.r-project.org/src/contrib/Archive/{name}/{filename}.tar.gz"]:
            try:
                source = fetch(url, source_path); break
            except urllib.error.HTTPError as exc:
                errors.append(str(exc))
        else:
            raise RuntimeError((name, errors))
        with tarfile.open(source['path']) as t:
            sd = dcf(t.extractfile(name+'/DESCRIPTION').read().decode())[0]
        assert sd['Version']==ver
        return dict(package=name,version=ver,binary=binary,source=source,description=desc,source_description=sd)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        packages = list(pool.map(acquire, sorted(selected)))
    lock = dict(schema_version=1,kind='resolved mesh R environment',snapshot=snapshot,index=index,runtime=identity(rscript),runtime_query=command,base_packages=base,packages=packages)
    (root/'r-source-lock.json').write_text(json.dumps(lock,indent=2)+'\n')
    print('RESOLVED',[(x['package'],x['version']) for x in packages])


if __name__ == "__main__":
    main()
