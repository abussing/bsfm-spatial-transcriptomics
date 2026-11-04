"""Streaming pointwise Gaussian-mixture scores; never uses sampler RNG."""
import numpy as np


class PredictiveSummary:
    def __init__(self, truth):
        self.truth=np.asarray(truth,np.float64)
        if not np.isfinite(self.truth).all():raise ValueError('Finite scoring truth required')
        self.count=0;self.mean=np.zeros_like(self.truth);self.second=np.zeros_like(self.truth)
        self.log_density_sum=np.full_like(self.truth,-np.inf)

    def update(self, mean, variance):
        mean,variance=np.asarray(mean),np.asarray(variance)
        if (mean.shape!=self.truth.shape or variance.shape!=self.truth.shape
                or not np.isfinite(mean).all() or not np.isfinite(variance).all() or np.any(variance<=0)):
            raise ValueError('Finite predictive means and positive marginal variances required')
        logp=-.5*(np.log(2*np.pi)+np.log(variance)+(self.truth-mean)**2/variance)
        self.log_density_sum=np.logaddexp(self.log_density_sum,logp)
        self.count+=1
        self.mean+=(mean-self.mean)/self.count
        self.second+=(variance+mean**2-self.second)/self.count

    def arrays(self):
        if not self.count:raise ValueError('No predictive draws')
        return dict(mean=self.mean.copy(),variance=np.maximum(0,self.second-self.mean**2),
                    pointwise_log_predictive_density=self.log_density_sum-np.log(self.count))
