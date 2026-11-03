import sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'src'))
from bsfm.sampler import run_receipts as proposal
from bsfm.sampler.run_storage import read_json,writer

class Interrupted(BaseException):pass
class ReceiptTests(unittest.TestCase):
    def test_torn_write_is_preserved_outside_authoritative_envelope(self):
        with tempfile.TemporaryDirectory() as tmp:
            attempt=Path(tmp);envelope=attempt/'transaction';envelope.mkdir()
            dest=envelope/'prepared.json'
            def torn(path,value):
                path.write_bytes(b'{"schema":');raise Interrupted()
            with patch.object(proposal,'write_json',side_effect=torn):
                with self.assertRaises(Interrupted):proposal.publish_json(dest,{'schema':'test'},staging_directory=attempt)
            self.assertEqual(list(envelope.iterdir()),[])
            partial=list(attempt.glob('receipt-*/candidate.json'))
            self.assertEqual(len(partial),1)
            with writer(attempt):proposal.publish_json(dest,{'schema':'test'},staging_directory=attempt)
            self.assertEqual(read_json(dest),{'schema':'test'})
            self.assertEqual(partial[0].read_bytes(),b'{"schema":')
    def test_existing_receipt_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);dest=p/'receipt.json';dest.write_bytes(b'original')
            with self.assertRaises(FileExistsError):proposal.publish_json(dest,{},staging_directory=p)
            self.assertEqual(dest.read_bytes(),b'original')

if __name__=='__main__':
    result=unittest.TextTestRunner(stream=sys.stdout,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ReceiptTests))
    sys.exit(not result.wasSuccessful())
