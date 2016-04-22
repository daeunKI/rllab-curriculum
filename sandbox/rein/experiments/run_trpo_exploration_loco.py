import os
from rllab.envs.mujoco.walker2d_env import Walker2DEnv
os.environ["THEANO_FLAGS"] = "device=cpu"

from rllab.policies.gaussian_mlp_policy import GaussianMLPPolicy
from rllab.envs.normalized_env import NormalizedEnv
from rllab.baselines.gaussian_mlp_baseline import GaussianMLPBaseline
from sandbox.rein.algos.trpo_unn import TRPO
from rllab.misc.instrument import stub, run_experiment_lite
import itertools

stub(globals())

# Param ranges
seeds = range(10)
etas = [0.00001, 0.0001, 0.001, 0.01, 0.1]
normalize_rewards = [False, True]
mdp_classes = [Walker2DEnv]
mdps = [NormalizedEnv(env=mdp_class())
        for mdp_class in mdp_classes]
param_cart_product = itertools.product(
    normalize_rewards, mdps, etas, seeds
)

for normalize_reward, mdp, eta, seed in param_cart_product:

    policy = GaussianMLPPolicy(
        env_spec=mdp.spec,
        hidden_sizes=(64, 32),
    )

    baseline = GaussianMLPBaseline(
        mdp.spec,
        regressor_args=dict(hidden_sizes=(64, 32)),
    )

    batch_size = 50000
    algo = TRPO(
        env=mdp,
        policy=policy,
        baseline=baseline,
        batch_size=batch_size,
        whole_paths=True,
        max_path_length=500,
        n_itr=500,
        step_size=0.01,
        eta=eta,
        eta_discount=1.0,
        snn_n_samples=10,
        subsample_factor=0.1,
        use_reverse_kl_reg=True,
        use_replay_pool=True,
        use_kl_ratio=False,
        use_kl_ratio_q=False,
        n_itr_update=5,
        kl_batch_size=5,
        normalize_reward=normalize_reward,
        stochastic_output=False,
        replay_pool_size=2500000,
        n_updates_per_sample=50000,
        #         second_order_update=True,
        unn_n_hidden=[64, 32],
        unn_layers_type=[1, 1, 1],
        unn_learning_rate=0.001
    )

    run_experiment_lite(
        algo.train(),
        exp_prefix="trpo-expl-loco-v1x",
        n_parallel=15,
        snapshot_mode="last",
        seed=seed,
        mode="lab_kube",
        dry=False,
        script="sandbox/rein/run_experiment_lite.py",
    )
