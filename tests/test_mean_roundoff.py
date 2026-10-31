"""Forward-error regression tests; stored scientific means are never rewritten."""
import copy
import math
import unittest
from fractions import Fraction

import numpy as np

from bsfm.preprocessing.mean_roundoff import MEAN_POLICY, check_means, mean_allowance, gamma_upper
from bsfm.preprocessing.raw_preflight import ContractError


class MeanRoundoffTests(unittest.TestCase):
    def test_observed_sox10_ogc_scalar_regression(self):
        stored=1.4270851667900744; reference=1.4270851667900435; n=4720
        bound=mean_allowance(n,reference,MEAN_POLICY)
        self.assertGreater(abs(stored-reference),1e-14+1e-14*abs(reference))
        self.assertLess(abs(stored-reference),bound)
        self.assertGreater(abs(stored+1e-10-reference),bound)
        self.assertLess(bound,4e-12)
        self.assertEqual(MEAN_POLICY['reference_operation_bound'],'n')
        u=Fraction(1,2**53);gamma=n*u/(1-n*u)
        exact_policy=2*(gamma+gamma)*Fraction.from_float(reference)/(1-gamma)
        self.assertGreaterEqual(Fraction.from_float(bound),exact_policy)

    def test_gamma_is_upper_bound_for_exact_rational_formula(self):
        u=Fraction(1,2**53)
        for n in [1,3,2252,3157,4042,4720,30000]:
            self.assertGreaterEqual(Fraction.from_float(gamma_upper(n,float(u))),n*u/(1-n*u))

    def test_layout_and_reduction_orders(self):
        rng=np.random.default_rng(1234)
        x=np.log1p(rng.integers(0,100,size=(7,12000))).astype(np.float64)
        types=np.repeat(np.arange(3),4000)
        references=np.array([[math.fsum(x[g,types==t])/4000 for t in range(3)] for g in range(7)])
        for order in ['C','F']:
            laid=np.array(x,order=order)
            for reduction in ['axis','reverse','sequential','reference']:
                if reduction=='reference':means=references.copy()
                else:
                    cols=[]
                    for t in range(3):
                        block=np.array(laid[:,types==t],order=order)
                        if reduction=='axis':v=block.mean(axis=1)
                        elif reduction=='reverse':v=block[:,::-1].mean(axis=1)
                        else:v=np.array([np.add.accumulate(row)[-1]/4000 for row in block])
                        cols.append(v)
                    means=np.column_stack(cols)
                before=means.copy();report=check_means(laid,types,means,MEAN_POLICY)
                self.assertTrue(report['all_passed']);self.assertTrue(np.array_equal(before,means))
                self.assertEqual(report['reference_means'],references.tolist())
                np.testing.assert_array_equal(
                    report['discrepancy_to_bound_ratios'],
                    np.asarray(report['absolute_discrepancies'])/np.asarray(report['allowed_bounds']))

    def test_materially_changed_mean_fails(self):
        x=np.tile(np.log1p(np.arange(1,3001,dtype=np.float64)),(2,1));types=np.repeat(np.arange(3),1000)
        means=np.column_stack([x[:,types==t].mean(axis=1) for t in range(3)])
        check_means(x,types,means,MEAN_POLICY)
        means[0,2]+=1e-10
        with self.assertRaisesRegex(ContractError,'forward-error'):check_means(x,types,means,MEAN_POLICY)

    def test_zero_group_requires_exact_zero_mean(self):
        x=np.zeros((2,9));types=np.repeat(np.arange(3),3);means=np.zeros((2,3))
        result=check_means(x,types,means,MEAN_POLICY)
        self.assertEqual(result['allowed_bounds'],means.tolist())
        means[0,0]=np.nextafter(0.,1.)
        with self.assertRaises(ContractError):check_means(x,types,means,MEAN_POLICY)

    def test_policy_and_domain_rejected(self):
        with self.assertRaises(ContractError):mean_allowance(0,1.,MEAN_POLICY)
        with self.assertRaises(ContractError):mean_allowance(2,float('inf'),MEAN_POLICY)
        changed=copy.deepcopy(MEAN_POLICY);changed['safety_factor']=4.
        with self.assertRaises(ContractError):mean_allowance(2,1.,changed)
        changed=copy.deepcopy(MEAN_POLICY);changed['reference_operation_bound']=3
        with self.assertRaises(ContractError):mean_allowance(2,1.,changed)
        with self.assertRaises(ContractError):check_means(np.full((2,3),np.nextafter(0.,1.)),np.arange(3),np.zeros((2,3)),MEAN_POLICY)


if __name__=='__main__':unittest.main()
