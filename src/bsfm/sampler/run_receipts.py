"""Receipt bytes are closed before becoming a prepared-envelope member."""
from pathlib import Path
import tempfile
from bsfm.sampler.run_storage import safe,write_json,publish


def publish_json(path,value,*,staging_directory):
    path=safe(path);staging=safe(staging_directory)
    if path.exists():raise FileExistsError(path)
    # Stage outside the transaction/genesis directory. A killed write leaves
    # evidence under its attempt, never a misleading prepared-receipt name.
    candidate=Path(tempfile.mkdtemp(prefix='receipt-',dir=staging))/'candidate.json'
    write_json(candidate,value)
    publish(candidate,path)
