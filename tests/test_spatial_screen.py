import json
from pathlib import Path
import unittest
import warnings
from unittest.mock import patch

import numpy as np
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel
from threadpoolctl import threadpool_limits
from bsfm.preprocessing.spatial_screen import (screen_sample, aggregate_animals,
    expression_summary, fixed_screen_mean, review_screen)

ROOT=Path(__file__).resolve().parents[1]


def fixture():
    n=32
    x=np.linspace(0,3,n)
    d=dict(expression=np.array([2+np.sin(x*3),3+np.cos(x*2)]),
        coordinates=np.column_stack([x,np.sin(x)]),
        gene_names=np.array(['g1','g2']),cell_names=np.array(['c'+str(i) for i in range(n)]),
        group_names=np.array(['type']*n),sample_names=np.array(['section']*n),
        animal_names=np.array(['animal']*n),source_row_indices=np.arange(n))
    m=dict(schema='bsfm.dataset.v1',dataset_id='synthetic',animal_identity_known=True,
        coordinate_units='synthetic',normalization=dict(response='uncentered_normalized',
        method='synthetic',units='log1p SCT corrected counts',population='synthetic',evidence='fixture'))
    config=json.loads((ROOT/'config/preprocessing/recovered-gp-screen.json').read_text())
    config['cap']=16
    spec=dict(sample='section',groups=['type'],training_cells=d['cell_names'][:28].tolist(),
        genes=['g1','g2'],config=config)
    return d,m,spec



class SpatialScreenTests(unittest.TestCase):
    def test_review_recovers_original_mean_and_response_units(self):
        d,m,spec=fixture();screen=screen_sample(d,m,**spec)
        train=np.array(screen['training_dataset_indices']['type'])
        X=(d['coordinates']-d['coordinates'].min(0))/np.ptp(d['coordinates'],axis=0).max()
        kernel=ConstantKernel(1.,(.01,100.))*Matern(.3,(.02,3.),nu=2.5)+WhiteKernel(.5,(.001,100.))
        with threadpool_limits(limits=1),warnings.catch_warnings():
            warnings.simplefilter('ignore')
            gp=GaussianProcessRegressor(kernel=kernel,**spec['config']['regressor']).fit(X[train],d['expression'][0,train])
            expected=gp.predict(X)
        with patch.object(GaussianProcessRegressor,'_constrained_optimization',side_effect=AssertionError('Unexpected reoptimization')):
            actual=fixed_screen_mean(X,d['expression'][0],train,screen['rows'][0],spec['config'])
        np.testing.assert_allclose(actual,expected,rtol=1e-12,atol=1e-12)
        scaled=fixed_screen_mean(X,7*d['expression'][0]+3,train,screen['rows'][0],spec['config'])
        np.testing.assert_allclose(scaled,7*actual+3,rtol=1e-12,atol=1e-12)
        result=review_screen(d,m,screen,spec,minimum_spatial_fraction=0)
        self.assertAlmostEqual(result['rows'][0]['spatial_amplitude'],float(np.diff(np.quantile(expected[:28],[.1,.9]))[0]))
        # Held-out responses must not affect the summaries or reconstructed mean.
        d['expression'][:,28:]+=100
        self.assertEqual(result,review_screen(d,m,screen,spec,minimum_spatial_fraction=0))
        screen['training_dataset_indices']['type'].reverse()
        with self.assertRaises(ValueError):review_screen(d,m,screen,spec,minimum_spatial_fraction=0)

    def test_expression_review_zeros_and_strength_are_distinct(self):
        low=expression_summary([0,0,1,1]);high=expression_summary([0,0,8,8])
        self.assertEqual(low['detection_fraction'],high['detection_fraction'])
        self.assertEqual(high['positive_median'],8)
        self.assertEqual(high['mean_expression'],4)
        self.assertIsNone(expression_summary([0,0])['positive_median'])
        for invalid in ([-1,2],[np.nan,1],[],[[1,2]]):
            with self.assertRaises(ValueError):expression_summary(invalid)

    def test_historical_gp_same_runtime_and_heldout_independence(self):
        d,m,spec=fixture()
        result=screen_sample(d,m,**spec)
        train=np.random.RandomState(0).choice(np.arange(28),16,replace=False)
        self.assertEqual(result['training_dataset_indices']['type'],train.tolist())
        xy=d['coordinates'];X=(xy-xy.min(0))/np.ptp(xy,axis=0).max()
        kernel=ConstantKernel(1.,(.01,100.))*Matern(.3,(.02,3.),nu=2.5)+WhiteKernel(.5,(.001,100.))
        with threadpool_limits(limits=1),warnings.catch_warnings():
            warnings.simplefilter('ignore')
            gp=GaussianProcessRegressor(kernel=kernel,normalize_y=True,n_restarts_optimizer=0,alpha=1e-6)
            gp.fit(X[train],d['expression'][0,train])
        signal=float(gp.kernel_.k1.k1.constant_value);noise=float(gp.kernel_.k2.noise_level)
        self.assertEqual(result['rows'][0]['spatial_fraction'],signal/(signal+noise))
        self.assertEqual(result['rows'][0]['length_scale'],float(gp.kernel_.k1.k2.length_scale))
        d['expression'][:,28:]+=100
        self.assertEqual(result,screen_sample(d,m,**spec))
        m['normalization']['units']='log2 library normalized'
        with self.assertRaises(ValueError):screen_sample(d,m,**spec)

    def test_technical_sections_are_not_independent_animals(self):
        rows=[dict(sample=s,gene='g',celltype='t',animal='a',status='FIT',spatial_fraction=v)
              for s,v in [('s1',.2),('s2',.8)]]
        self.assertEqual(aggregate_animals(rows),[dict(gene='g',celltype='t',animal='a',spatial_fraction=.5)])
        with self.assertRaises(ValueError):aggregate_animals(rows+[rows[0]])
        rows[1].update(sample='s1',gene='g2',animal='b')
        with self.assertRaises(ValueError):aggregate_animals(rows)
        rows[0]['animal']=None
        with self.assertRaises(ValueError):aggregate_animals(rows[:1])


if __name__=='__main__':unittest.main()
