"""Exercise shell handoff and fail-closed deployment checks; no scheduler/GPU."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASH = ('C:/Program Files/Git/bin/bash.exe' if os.name == 'nt' else shutil.which('bash'))

def shell_path(p):
    p = Path(p).resolve().as_posix()
    return '/'+p[0].lower()+p[2:] if os.name == 'nt' else p

@unittest.skipUnless(BASH and Path(BASH).is_file(), 'Bash required')
class HPCLauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.checkout = self.root/'source tree'
        self.checkout.mkdir(); (self.checkout/'src').mkdir()
        self.env = os.environ.copy()
        for key in list(self.env):
            if key.startswith('BSFM_'): self.env.pop(key)
        self.env.update(GIT_CONFIG_COUNT='1', GIT_CONFIG_KEY_0='safe.directory',
                        GIT_CONFIG_VALUE_0=self.checkout.as_posix())
        def git(*args):
            return subprocess.check_output(['git',*args],cwd=self.checkout,env=self.env,
                                           stderr=subprocess.STDOUT,text=True).strip()
        git('init','-q'); (self.checkout/'tracked').write_text('source\n')
        shutil.copytree(ROOT/'environment/hpc', self.checkout/'environment/hpc')
        git('add','tracked','environment')
        git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','fixture')
        self.commit=git('rev-parse','HEAD')
        self.capture=self.root/'capture'; python=self.root/'python shim'
        python.write_bytes(b'#!/usr/bin/env bash\nprintf "%s\\n" "$@" > "$CAPTURE"\n'
            b'printf "backend=%s\\nx64=%s\\nthreads=%s\\ncwd=%s\\n" '
            b'"$JAX_PLATFORMS" "$JAX_ENABLE_X64" "$OPENBLAS_NUM_THREADS" "$PWD" >> "$CAPTURE"\n')
        python.chmod(0o755)
        cuda=self.root/'cuda'; (cuda/'nvvm/libdevice').mkdir(parents=True)
        (cuda/'nvvm/libdevice/libdevice.10.bc').write_bytes(b'fixture')
        self.env.update(BSFM_CHECKOUT=shell_path(self.checkout),BSFM_PYTHON=shell_path(python),
            BSFM_MODULES='',BSFM_CUDA_HOME=shell_path(cuda),CAPTURE=shell_path(self.capture),
            MSYS_NO_PATHCONV='1')

    def launch(self,name='sample',commit=None):
        # Slurm executes a spooled copy without sibling files.
        spooled = self.root/'slurm_script'
        shutil.copyfile(self.checkout/f'environment/hpc/{name}.sbatch', spooled)
        return subprocess.run([BASH,shell_path(spooled),
            commit or self.commit,'/external/recipe with spaces.json','/external/output with spaces'],
            env=self.env,capture_output=True,text=True)

    def test_explicit_deployment_and_quoted_paths(self):
        r=self.launch(); self.assertEqual(r.returncode,0,r.stderr)
        text=self.capture.read_text()
        self.assertIn('/external/recipe with spaces.json\n',text)
        self.assertIn('/external/output with spaces\n',text)
        self.assertIn('backend=cuda,cpu\nx64=true\nthreads=1',text)
        self.assertIn(self.commit,text)
        r=self.launch('initialize'); self.assertEqual(r.returncode,0,r.stderr)
        self.assertIn('threads=4',self.capture.read_text())

    def test_wrong_commit_dirty_source_and_missing_deployment_do_not_launch(self):
        r=self.launch(commit='0'*40); self.assertNotEqual(r.returncode,0)
        self.assertFalse(self.capture.exists())
        (self.checkout/'tracked').write_text('changed\n')
        r=self.launch(); self.assertNotEqual(r.returncode,0)
        self.assertFalse(self.capture.exists())
        self.env.pop('BSFM_PYTHON')
        r=self.launch(); self.assertNotEqual(r.returncode,0)
        self.assertIn('BSFM_PYTHON',r.stderr)

    def test_missing_cuda_and_relative_deployment_do_not_launch(self):
        self.env['BSFM_CUDA_HOME']='/does-not-exist'
        r=self.launch(); self.assertNotEqual(r.returncode,0)
        self.assertIn('libdevice',r.stderr); self.assertFalse(self.capture.exists())
        self.env['BSFM_CHECKOUT']='relative'
        r=self.launch(); self.assertNotEqual(r.returncode,0)
        self.assertIn('absolute',r.stderr)

if __name__ == '__main__': unittest.main()
