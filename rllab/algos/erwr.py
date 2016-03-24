from rllab.algos.vpg import VPG
from rllab.misc.tensor_utils import flatten_tensors
from rllab.misc.ext import merge_dict, compile_function, extract, new_tensor, \
    flatten_tensor_variables, unflatten_tensor_variables
from rllab.misc import autoargs, ext
from rllab.misc.overrides import overrides
from rllab.algos.batch_polopt import BatchPolopt
import rllab.misc.logger as logger
import theano
import theano.tensor as TT
from pydoc import locate
import numpy as np

from rllab.optimizers.lbfgs_optimizer import LbfgsOptimizer


class ERWR(VPG):
    """
    Episodic Reward Weighted Regression [1]_

    Notes
    -----
    This does not implement the original RwR [2]_ that deals with "immediate reward problems" since
    it doesn't find solutions that optimize for temporally delayed rewards.

    .. [1] Kober, Jens, and Jan R. Peters. "Policy search for motor primitives in robotics." Advances in neural information processing systems. 2009.
    .. [2] Peters, Jan, and Stefan Schaal. "Using reward-weighted regression for reinforcement learning of task space control." Approximate Dynamic Programming and Reinforcement Learning, 2007. ADPRL 2007. IEEE International Symposium on. IEEE, 2007.
    """

    def __init__(
            self,
            optimizer=None,
            optimizer_args=None,
            **kwargs):
        if optimizer is None:
            if optimizer_args is None:
                optimizer_args = dict()
            optimizer = LbfgsOptimizer(**optimizer_args)
        super(ERWR, self).__init__(optimizer=optimizer, **kwargs)

