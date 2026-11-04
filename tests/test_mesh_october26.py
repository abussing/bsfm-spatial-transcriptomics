import unittest
import json
import os
from pathlib import Path
import subprocess
import tempfile
from unittest.mock import patch
import numpy as np
from scipy import sparse

from bsfm.mesh.october26 import (normalize_glia, historical_half_indices,
    fem_matrices, polynomial_fem, spectral_artifact, marginal_root, warp_cells, build)
from bsfm.mesh.projectors import project, validate, active
from bsfm.mesh.identities import REPO, file_record


class October26Regression(unittest.TestCase):
    def test_runtime_relocation_retains_identity_and_builder_arguments(self):
        # Mock only process execution; real file hashing guards launch.
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);exe=root/'relocated Rscript';exe.write_bytes(b'test runtime, never executed')
            lock=root/'runtime.json'
            lock.write_text(json.dumps({'R':dict(path=str(root/'old-machine-path'),**file_record(exe))}))
            args=[root/n for n in ('cells.csv','vertices.csv','triangles.csv','environment','config.json','output')]
            completed=subprocess.CompletedProcess([],0,stdout=b'fixture',stderr=b'')
            with patch('bsfm.mesh.october26.subprocess.run',return_value=completed) as run:
                receipt=build(*args,runtime_lock=lock,rscript=exe)
                command=run.call_args.args[0]
                self.assertEqual(command[0],str(exe.resolve()))
                self.assertEqual(command[3:],[str(args[i].resolve()) for i in (3,4,0,1,2,5)])
                self.assertEqual(receipt['runtime_lock']['sha256'],file_record(lock)['sha256'])
                self.assertEqual(receipt['runtime_executable']['sha256'],file_record(exe)['sha256'])
                self.assertEqual(run.call_args.kwargs['env']['OMP_NUM_THREADS'],'1')
            exe.write_bytes(b'changed runtime')
            with patch('bsfm.mesh.october26.subprocess.run') as run:
                with self.assertRaisesRegex(ValueError,'runtime executable identity'):
                    build(*args,runtime_lock=lock,rscript=exe)
                run.assert_not_called()

    def setUp(self):
        self.v = np.array([[0., 0.], [1., 0.], [0., 1.], [1., 1.]])
        self.t = np.array([[0, 1, 2], [1, 3, 2]])
        self.xy = np.array([[0., 0.], [.5, 0.], [.2, .3]])
        self.a = project(self.v, self.t, self.xy, 5e-12)

    def test_coordinate_transform_and_axis_order(self):
        raw = np.array([[20., -4.], [22., 0.], [21., -2.]])
        xy, origin, scale = normalize_glia(raw)
        np.testing.assert_array_equal(origin, [20., -4.])
        self.assertEqual(scale, 4.)
        np.testing.assert_array_equal(xy, [[0., 0.], [.5, 1.], [.25, .5]])
        np.testing.assert_array_equal(normalize_glia(raw.copy())[0], xy)
        with self.assertRaises(ValueError): normalize_glia(np.zeros((3, 2)))

    def test_vertex_edge_interior_projector_and_affine(self):
        audit = validate(self.a, self.v, self.xy, 5e-12)
        self.assertLess(audit['affine_error'], 5e-12)
        np.testing.assert_allclose(self.a.toarray(), [[1,0,0,0],[.5,.5,0,0],[.5,.2,.3,0]], atol=1e-15)
        with self.assertRaises(ValueError): project(self.v, self.t, np.array([[2., 2.]]))

    def test_zero_and_known_displacements(self):
        np.testing.assert_array_equal(warp_cells(self.a, np.zeros_like(self.v), coordinates=self.xy), self.xy)
        d = np.column_stack((.1+.2*self.v[:,0], -.3+.4*self.v[:,1]))
        expected = self.xy+np.column_stack((.1+.2*self.xy[:,0], -.3+.4*self.xy[:,1]))
        np.testing.assert_allclose(warp_cells(self.a,d,coordinates=self.xy), expected, atol=1e-15)
        # Direct-coordinate chart has no implicit addition of reference locations.
        np.testing.assert_array_equal(warp_cells(self.a,np.zeros_like(self.v)), np.zeros_like(self.xy))

    def test_active_partition_and_full_marginal(self):
        idx = active(self.a)
        np.testing.assert_array_equal(idx, [0,1,2])
        self.assertEqual(self.a[:,3].nnz, 0)
        m,g,_ = fem_matrices(self.v,self.t)
        terms = polynomial_fem(m,g)
        u,diags,_ = spectral_artifact(terms)
        l,sd = marginal_root(u,diags,idx,1.)
        full = (u*sd)@(u*sd).T
        np.testing.assert_allclose(l@l.T,full[np.ix_(idx,idx)],rtol=2e-12,atol=1e-12)
        np.testing.assert_allclose((self.a@u)*sd,(self.a[:,idx]@u[idx])*sd,atol=1e-15)
        # Independent dense Schur complement: marginal, not conditioned Q_AA^-1.
        q = np.linalg.inv(full)
        schur = q[:3,:3]-q[:3,3:]@np.linalg.solve(q[3:,3:],q[3:,:3])
        np.testing.assert_allclose(np.linalg.inv(schur),l@l.T,rtol=2e-10,atol=1e-10)
        self.assertGreater(np.linalg.norm(np.linalg.inv(q[:3,:3])-l@l.T),1e-4)

    def test_consistent_mass_natural_boundary_and_index_rejection(self):
        m,g,areas = fem_matrices(self.v,self.t)
        self.assertAlmostEqual(areas.sum(),1.)
        self.assertAlmostEqual(float(np.ones(4)@m@np.ones(4)),1.)
        np.testing.assert_allclose(g@np.ones(4),0,atol=1e-15)
        self.assertGreater(m[0,1],0)  # consistent, not lumped
        with self.assertRaises(ValueError): fem_matrices(self.v,self.t+1)

    def test_thinning_reuses_geometry_and_recomputes_support(self):
        xy = np.array([[0.,0.],[1.,0.],[0.,1.],[1.,1.],[.5,.5],[.25,.25]])
        types = np.array([0,0,1,1,2,2])
        keep = historical_half_indices(xy,types)
        self.assertEqual(len(keep),3)
        np.testing.assert_array_equal(keep,historical_half_indices(xy.copy(),types.copy()))
        a = project(self.v,self.t,xy)
        vertices = self.v.copy(); triangles = self.t.copy()
        half = a[keep]
        np.testing.assert_allclose(half@self.v,xy[keep],atol=1e-15)
        np.testing.assert_array_equal(self.v,vertices)
        np.testing.assert_array_equal(self.t,triangles)

    def test_corrupted_projector_and_membership_fail(self):
        bad = self.a.copy(); bad.data[0] += .001
        with self.assertRaises(ValueError): validate(bad,self.v,self.xy,5e-12)
        with self.assertRaises(ValueError): validate(self.a,self.v,self.xy[::-1],5e-12)
        wrong = sparse.csr_matrix(self.a.shape)
        with self.assertRaises(ValueError): validate(wrong,self.v,self.xy,5e-12)

    def test_actual_python_JSON_R_boundary_preserves_numeric_angle(self):
        """Use build()'s real command/JSON path; stop R before geometry work."""
        runtime = json.loads((REPO/'environment/mesh/runtime-lock.json').read_text())['R']['path']
        environment = json.loads((REPO/'environment/mesh/environment-spec.json').read_text())['external_root']
        if not Path(runtime).exists() or not Path(environment).exists():
            self.skipTest('Accepted local mesh R environment unavailable')
        script = r'''
arg <- commandArgs(TRUE)
stopifnot(length(arg)==7L)
commandArgs <- function(trailingOnly=FALSE) arg[1:6]
expressions <- parse(arg[7])
for (expr in expressions) {
  if (grepl("^cells <-", paste(deparse(expr),collapse=" "))) break
  eval(expr, envir=.GlobalEnv)
}
stopifnot(typeof(fromJSON(arg[2])$minimum_angle)=="integer")
stopifnot(typeof(cfg$minimum_angle)=="double", identical(cfg$minimum_angle,25))
options <- fmesher:::handle_rcdt_options_inla(extend=FALSE,
  refine=list(min.angle=cfg$minimum_angle,max.edge=.13,max.edge.extra=.13),
  .n=list(segm=0L,lattice=0L,loc=3L),.loc=rbind(c(0,0),c(1,0),c(0,1)))
stopifnot(identical(options$rcdt_min_angle,25),typeof(options$rcdt_min_angle)=="double")
cat("PASS: JSON integer converted to native numeric angle; no mesh constructed\n")
'''
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'argument_test.R'
            path.write_text(script,encoding='utf-8')
            real_run = subprocess.run
            config = REPO/'config/mesh/october26-warp-basis.json'
            self.assertEqual(json.loads(config.read_text())['minimum_angle'],25)
            commands = []

            def intercept(command, **kwargs):
                # Preserve the actual Python builder's argument order, paths,
                # environment and subprocess. Only stop R before mesh creation.
                commands.append(command)
                return real_run(command[:2]+[str(path)]+command[3:]+[command[2]], **kwargs)

            with patch('bsfm.mesh.october26.subprocess.run', side_effect=intercept):
                result = build(Path(tmp)/'unused-cells.csv',Path(tmp)/'unused-v.csv',
                    Path(tmp)/'unused-t.csv',environment,config,Path(tmp)/'unused-output')
            self.assertEqual(result['exit_code'],0)
            self.assertEqual(commands[0][4],str(config.resolve()))
            self.assertIn('PASS:',(Path(tmp)/'construction.log').read_text())
            self.assertFalse((Path(tmp)/'unused-output').exists())

            # A removed correction must fail rather than accidentally test the
            # historical double literal or accept the integer/default route.
            original = REPO/'src/bsfm/mesh/october26_builder.R'
            mutant = Path(tmp)/'without-correction.R'
            text = original.read_text()
            line = 'cfg$minimum_angle <- as.double(cfg$minimum_angle)'
            self.assertIn(line,text)
            mutant.write_text(text.replace(line,''),encoding='utf-8')
            command = commands[0]
            failed = real_run(command[:2]+[str(path)]+command[3:]+[str(mutant)],
                env=dict(os.environ,LANG='C',LC_ALL='C'),capture_output=True,text=True)
            self.assertNotEqual(failed.returncode,0)


if __name__ == '__main__':
    unittest.main()
