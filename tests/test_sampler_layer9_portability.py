"""OS-process ownership and authenticated wheel corruption checks."""
import os
import importlib.util
import marshal
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

from bsfm.sampler.run_storage import writer, publish, file_record
from bsfm.sampler.run_linux_environment import verify_wheel


class PortabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_writer_excludes_fresh_process(self):
        code = '''import sys
from bsfm.sampler.run_storage import writer
try:
    with writer(sys.argv[1]): pass
except RuntimeError:
    sys.exit(17)
'''
        with writer(self.root):
            result = subprocess.run([sys.executable, '-B', '-c', code, str(self.root)], timeout=30)
            self.assertEqual(result.returncode, 17)
        result = subprocess.run([sys.executable, '-B', '-c', code, str(self.root)], timeout=30)
        self.assertEqual(result.returncode, 0)

    def test_writer_released_on_process_death(self):
        code = '''import sys,time
from bsfm.sampler.run_storage import writer
with writer(sys.argv[1]):
    print('LOCKED',flush=True)
    time.sleep(60)
'''
        child = subprocess.Popen([sys.executable, '-B', '-c', code, str(self.root)], stdout=subprocess.PIPE, text=True)
        try:
            self.assertEqual(child.stdout.readline().strip(), 'LOCKED')
            with self.assertRaises(RuntimeError):
                with writer(self.root): pass
            child.kill()
            child.wait(timeout=30)
            with writer(self.root): pass
        finally:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=30)
            child.stdout.close()

    def test_directory_publication_and_collision(self):
        source = self.root/'source'; source.mkdir()
        (source/'payload').write_bytes(b'complete')
        dest = self.root/'committed'
        publish(source, dest)
        self.assertEqual((dest/'payload').read_bytes(), b'complete')
        source.mkdir()
        (source/'payload').write_bytes(b'conflict')
        with self.assertRaises(FileExistsError): publish(source, dest)
        self.assertEqual((dest/'payload').read_bytes(), b'complete')
        self.assertTrue(source.exists())

    @unittest.skipUnless(sys.platform == 'linux', 'Linux syscall boundary')
    def test_linux_syscall_cannot_replace_empty_directory(self):
        from bsfm.sampler.run_linux_storage import rename_noreplace
        source = self.root/'source'; source.mkdir()
        dest = self.root/'dest'; dest.mkdir()
        with self.assertRaises(FileExistsError): rename_noreplace(source, dest)
        self.assertTrue(source.exists())
        self.assertTrue(dest.exists())

    def wheel(self, name='pkg/module.py', payload=b'original'):
        path = self.root/'package.whl'
        with zipfile.ZipFile(path, 'w') as archive: archive.writestr(name, payload)
        return path, file_record(path)

    def test_wheel_members_and_mutation(self):
        site = self.root/'site'; (site/'pkg').mkdir(parents=True)
        target = site/'pkg/module.py'; target.write_bytes(b'original')
        wheel, expected = self.wheel()
        self.assertEqual(verify_wheel(wheel, expected, site), 1)
        target.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'member changed'):
            verify_wheel(wheel, expected, site)

    def test_wheel_archive_mutation(self):
        wheel, expected = self.wheel()
        wheel.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'wheel changed'):
            verify_wheel(wheel, expected, self.root/'site')

    def test_wheel_escape_rejected(self):
        wheel, expected = self.wheel('../escape.py')
        with self.assertRaisesRegex(ValueError, 'escapes'):
            verify_wheel(wheel, expected, self.root/'site')

    def test_recompiled_wheel_bytecode_requires_exact_source_code(self):
        site = self.root/'site'; (site/'pkg/__pycache__').mkdir(parents=True)
        source = b'value = 42\n'
        name = 'pkg/__pycache__/module.'+sys.implementation.cache_tag+'.pyc'
        def bytecode(text, filename):
            return importlib.util.MAGIC_NUMBER+b'\0'*12+marshal.dumps(compile(text, filename, 'exec', dont_inherit=True))
        wheel = self.root/'compiled.whl'
        with zipfile.ZipFile(wheel, 'w') as archive:
            archive.writestr('pkg/module.py', source)
            archive.writestr(name, bytecode(source, '/build/pkg/module.py'))
        (site/'pkg/module.py').write_bytes(source)
        (site/name).write_bytes(bytecode(source, str(site/'pkg/module.py')))
        expected = file_record(wheel)
        regenerated = {}
        self.assertEqual(verify_wheel(wheel, expected, site, regenerated=regenerated), 2)
        self.assertEqual(set(regenerated), {(site/name).resolve()})
        self.assertEqual(regenerated[(site/name).resolve()][1], len(bytecode(source, '/build/pkg/module.py')))
        (site/name).write_bytes(bytecode(b'value = 43\n', str(site/'pkg/module.py')))
        with self.assertRaisesRegex(ValueError, 'bytecode differs'):
            verify_wheel(wheel, expected, site)


if __name__ == '__main__':
    unittest.main()
