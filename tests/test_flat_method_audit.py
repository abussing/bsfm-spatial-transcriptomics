"""Independent distribution checks for the diagnostic scalar slice update."""
import unittest
import numpy as np
from bsfm.sampler.flat_method_audit import slice_one, provisional_ess, saved_tuning

class FlatMethodAuditTests(unittest.TestCase):
    def test_narrow_and_broad_gaussian_invariant_moments(self):
        for sd in [.025,3.]:
            rng=np.random.default_rng(20261116)
            x=.8
            draws=[]
            for i in range(10000):
                x,info=slice_one(lambda v:-.5*((v-.8)/sd)**2,x,rng,
                    width=.4,max_steps=32,max_shrink=128)
                self.assertGreaterEqual(info['evaluations'],2)
                if i>=1000:draws.append(x)
            a=(np.array(draws)-.8)/sd
            self.assertLess(abs(a.mean()),.09)
            self.assertLess(abs(a.var()-1),.12)

    def test_truncated_density_and_no_out_of_support_samples(self):
        rng=np.random.default_rng(60);x=.5;values=[]
        for _ in range(4000):
            x,_=slice_one(lambda v:0. if 0<v<1 else -np.inf,x,rng,
                width=2.,max_steps=8,max_shrink=128)
            values.append(x)
        self.assertTrue(all(0<v<1 for v in values))
        self.assertLess(abs(np.mean(values)-.5),.025)
        self.assertLess(abs(np.var(values)-1/12),.01)

    def test_correlated_gaussian_component_updates(self):
        rng=np.random.default_rng(21);x=np.zeros(2);values=[]
        rho=.8;sd=np.sqrt(1-rho*rho)
        for i in range(12000):
            for j in range(2):
                mean=rho*x[1-j]
                x[j],_=slice_one(lambda v:-.5*((v-mean)/sd)**2,x[j],rng,
                    width=1.,max_steps=16,max_shrink=128)
            if i>=2000:values.append(x.copy())
        np.testing.assert_allclose(np.cov(np.array(values).T),[[1,rho],[rho,1]],atol=.10)
        np.testing.assert_allclose(np.mean(values,axis=0),0,atol=.10)

    def test_invalid_density_fails_explicitly(self):
        with self.assertRaises(FloatingPointError):
            slice_one(lambda v:np.nan,0,np.random.default_rng(0),
                      width=1,max_steps=8,max_shrink=128)
        with self.assertRaises(ValueError):
            slice_one(lambda v:-v*v,0,np.random.default_rng(0),
                      width=0,max_steps=8,max_shrink=128)

    def test_ess_detects_slow_autocorrelation(self):
        rng=np.random.default_rng(4);white=rng.normal(size=5000)
        slow=np.zeros(5000)
        for i in range(1,5000):slow[i]=.95*slow[i-1]+white[i]
        self.assertGreater(provisional_ess(white),3000)
        self.assertLess(provisional_ess(slow),400)
        self.assertEqual(provisional_ess(np.ones(100)),0.)


class SavedTuningTests(unittest.TestCase):
    def test_selection_and_rejections(self):
        row=dict(case=0,method="nugget_slice",start=1,status="complete",
                 step=.2,inverse_mass=[1.,2.],endpoint=[99,99,99])
        step,mass=saved_tuning(dict(chains=[row]),0,"nugget_slice",1)
        self.assertEqual(step,.2)
        np.testing.assert_array_equal(mass,[1,2])
        for rows,case in [([row,row],0),([row],1)]:
            with self.assertRaises(ValueError):
                saved_tuning(dict(chains=rows),case,"nugget_slice",1)
        for update in [dict(step=0),dict(step=float("nan")),
                       dict(inverse_mass=[1.,1.,1.]),dict(inverse_mass=[1.,-1.]),
                       dict(status="warmup_budget_exhausted")]:
            with self.assertRaises(ValueError):
                saved_tuning(dict(chains=[dict(row,**update)]),0,"nugget_slice",1)
