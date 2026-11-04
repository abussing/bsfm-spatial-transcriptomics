"""Fresh process death at an explicit local publication boundary; synthetic only."""
import os
import sys
from sampler_layer9_support import controller
from unittest.mock import patch

if __name__=='__main__':
    ctl=controller(sys.argv[1])
    def die(stage):
        if stage==sys.argv[2]:os._exit(91)
    with patch('bsfm.sampler.run_controller.initialize',side_effect=AssertionError('Committed genesis replay')):
        ctl.run(stop_after=1,fault=die)
