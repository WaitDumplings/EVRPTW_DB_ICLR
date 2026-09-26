#!/usr/bin/env python3
"""Train AM-EVRPTW for a few CPU optimizer steps on separate demo/train data.

This command uses the native AM rollout and its REINFORCE loss with a frozen
initial greedy-rollout baseline. It is a small training demonstration, not a
paper training run. Sampled loss and route cost need not decrease each step.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import random
import time

from learning_demo import ROOT, load_policy, model_class
from learning_smoke import load_engineering_train
import numpy as np
import torch

from EVRPTW_Benchmark.Reinforcement_Learning.AM_EVRPTW.rollout import rollout
from EVRPTW_Benchmark.Reinforcement_Learning.common.objective import (
    load_objective, select_objective_instance,
)
from EVRPTW_Benchmark.Reinforcement_Learning.common.stage2_data import make_envs


CONSTRUCTOR = {
    'embedding_dim': 128,
    'hidden_dim': 128,
    'n_encode_layers': 3,
    'n_heads': 8,
    'tanh_clipping': 10.0,
    'normalization': 'batch',
}
TRAJECTORIES_PER_STEP = 8
INCOMPLETE_PENALTY_KM = 10000.0
MAX_GRAD_NORM = 1.0


def train(args):
    if args.steps <= 0 or args.threads <= 0:
        raise ValueError('--steps and --threads must be positive integers')
    if not math.isfinite(args.learning_rate) or args.learning_rate <= 0:
        raise ValueError('--learning-rate must be finite and positive')
    torch.set_num_threads(args.threads)
    random.seed(args.seed)
    np.random.seed(args.seed % (2**32))
    torch.manual_seed(args.seed)
    instance = load_engineering_train(args.family_dir, args.view_id)
    # Frozen monetary coefficients; demo distances follow the physical
    # fastest-time path. Scaling is derived solely from this demo/train view.
    profile_path = ROOT / 'EVRPTW_Benchmark/Reinforcement_Learning/configs/rivian_energy_vehicle_cost_v2.json'
    objective = load_objective(profile_path).to_dict()
    objective['objective_distance_source'] = 'running_time_path_distance_km'
    instance = select_objective_instance(instance, objective)

    if args.output_dir.exists():
        raise FileExistsError('Output directory already exists; choose a new --output-dir.')
    args.output_dir.mkdir(parents=True, exist_ok=False)

    policy = model_class('AM-EVRPTW')(**CONSTRUCTOR).to('cpu')
    baseline = deepcopy(policy).eval()
    for parameter in baseline.parameters():
        parameter.requires_grad_(False)
    optimizer = torch.optim.Adam(policy.parameters(), lr=args.learning_rate)
    initial_parameters = {name: p.detach().clone() for name, p in policy.named_parameters()}
    actor_envs = make_envs([instance], n_traj=TRAJECTORIES_PER_STEP,
        info_level='full', use_jit_mask=False, objective_config=objective)
    baseline_envs = make_envs([instance], n_traj=1,
        info_level='full', use_jit_mask=False, objective_config=objective)
    max_steps = max(env.unwrapped.max_steps for env in actor_envs)
    base = actor_envs[0].unwrapped
    normalization = {
        'reward_distance_scale_mode': base.reward_distance_scale_mode,
        'reward_distance_scale_km': float(base.reward_distance_scale_km),
        'reward_objective_scale': float(base.reward_objective_scale),
    }
    history = []
    started = time.perf_counter()
    print('AM-EVRPTW quick training: demo/train only; '
          f'{args.steps} optimizer steps, {TRAJECTORIES_PER_STEP} sampled trajectories per step, CPU. '
          'Loss is stochastic and is not guaranteed to decrease.', flush=True)
    try:
        with (args.output_dir / 'loss.jsonl').open('x', encoding='utf-8') as stream:
            for step in range(1, args.steps + 1):
                step_started = time.perf_counter()
                before = {name: p.detach().clone() for name, p in policy.named_parameters()}
                policy.train()
                actor = rollout(policy, actor_envs, decode_type='sampling',
                    max_steps=max_steps, seed=args.seed + step,
                    incomplete_penalty_km=INCOMPLETE_PENALTY_KM)
                with torch.no_grad():
                    greedy = rollout(baseline, baseline_envs, decode_type='greedy',
                        max_steps=max_steps, seed=args.seed + step,
                        incomplete_penalty_km=INCOMPLETE_PENALTY_KM,
                        compute_log_likelihood=False)
                # Native AM cost-objective REINFORCE loss. A single deterministic
                # greedy baseline cost broadcasts over the sampled trajectories.
                advantage = (actor.training_cost - greedy.training_cost).detach()
                loss = (advantage * actor.log_likelihood).mean()
                if not bool(torch.isfinite(loss)):
                    raise FloatingPointError('Non-finite training loss')
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                gradients = [p.grad for p in policy.parameters() if p.grad is not None]
                if not gradients or not all(bool(torch.isfinite(g).all()) for g in gradients):
                    raise FloatingPointError('Missing or non-finite training gradients')
                grad_norm = torch.nn.utils.clip_grad_norm_(policy.parameters(), MAX_GRAD_NORM)
                if not bool(torch.isfinite(grad_norm)):
                    raise FloatingPointError('Non-finite gradient norm')
                optimizer.step()
                if not all(bool(torch.isfinite(p).all()) for p in policy.parameters()):
                    raise FloatingPointError('Non-finite parameters after update')
                changes = [p.detach() - before[name] for name, p in policy.named_parameters()]
                changed_count = sum(bool(torch.count_nonzero(delta)) for delta in changes)
                update_l2 = math.sqrt(sum(float(delta.double().square().sum()) for delta in changes))
                row = {
                    'optimizer_step': step,
                    'loss': float(loss.detach()),
                    'mean_training_cost_normalized': float(actor.training_cost.mean()),
                    'baseline_training_cost_normalized': float(greedy.training_cost.mean()),
                    'mean_objective_usd': float(actor.objective_value.mean()),
                    'environment_success_rate': float(actor.feasible.float().mean()),
                    'mean_advantage': float(advantage.mean()),
                    'grad_norm_before_clip': float(grad_norm),
                    'max_grad_norm': MAX_GRAD_NORM,
                    'parameter_update_l2': update_l2,
                    'parameter_tensors_changed': changed_count,
                    'environment_transitions': int(actor.environment_transitions),
                    'seconds': time.perf_counter() - step_started,
                }
                stream.write(json.dumps(row, allow_nan=False) + '\n')
                stream.flush()
                history.append(row)
                print(f"step={step:03d}/{args.steps:03d} loss={row['loss']:.6f} "
                      f"cost_norm={row['mean_training_cost_normalized']:.6f} "
                      f"grad_norm={row['grad_norm_before_clip']:.6f} "
                      f"update_l2={update_l2:.6g} changed={changed_count} "
                      f"success={row['environment_success_rate']:.1%}", flush=True)
    finally:
        for env in actor_envs + baseline_envs:
            env.close()

    policy.eval()
    checkpoint_path = args.output_dir / 'demo_checkpoint.pt'
    payload = {
        'format': 'evrptw_inference_weights_v1',
        'artifact_id': f'am_evrptw_demo_train_seed{args.seed}_steps{args.steps}',
        'method': 'AM-EVRPTW',
        'training_regime': 'demo/train',
        'scope': 'quick_training_demo',
        'epoch': None,
        'optimizer_steps': args.steps,
        'constructor': dict(CONSTRUCTOR),
        'objective': objective,
        'normalization': normalization,
        'state_dict': {k: v.detach().cpu().clone() for k, v in policy.state_dict().items()},
        'resumable': False,
        'training_scope': 'Quick training on a separate generated engineering fixture; not paper weights.',
        'training_view_id': args.view_id,
        'seed': args.seed,
    }
    torch.save(payload, checkpoint_path)
    reloaded, _ = load_policy(checkpoint_path)
    strict_identity = all(torch.equal(value, reloaded.state_dict()[key])
                          for key, value in policy.state_dict().items())
    if not strict_identity:
        raise AssertionError('Saved checkpoint differs from trained model')
    changed_from_start = sum(not torch.equal(initial_parameters[name], p.detach())
                             for name, p in policy.named_parameters())
    summary = {
        'schema': 'am_quick_training_v1',
        'status': 'PASS',
        'method': 'AM-EVRPTW',
        'split': 'demo/train',
        'view_id': args.view_id,
        'customer_count': len(instance.customers),
        'constructor': dict(CONSTRUCTOR),
        'device': 'cpu',
        'threads': args.threads,
        'seed': args.seed,
        'optimizer': 'Adam',
        'learning_rate': args.learning_rate,
        'optimizer_steps': args.steps,
        'epochs': None,
        'trajectories_per_step': TRAJECTORIES_PER_STEP,
        'rollout_step_limit': max_steps,
        'baseline': 'Frozen initial policy, greedy rollout on the same demo/train instance',
        'loss': 'mean(detach(sampled_normalized_cost - greedy_normalized_cost) * sampled_log_likelihood)',
        'loss_monotonicity': 'Not guaranteed',
        'initial_loss': history[0]['loss'],
        'final_loss': history[-1]['loss'],
        'steps_with_parameter_changes': sum(r['parameter_tensors_changed'] > 0 for r in history),
        'parameter_tensors_changed_from_initialization': changed_from_start,
        'checkpoint': 'demo_checkpoint.pt',
        'checkpoint_sha256': hashlib.sha256(checkpoint_path.read_bytes()).hexdigest(),
        'strict_load': 'PASS',
        'saved_tensor_identity': 'PASS',
        'inference_only_checkpoint': True,
        'objective': objective,
        'normalization': normalization,
        'seconds': time.perf_counter() - started,
        'scope': 'Actual short REINFORCE training for demonstration; no benchmark test training, no paper reproduction or quality guarantee.',
    }
    (args.output_dir / 'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
    print(f"Saved demo_checkpoint.pt; strict_load=PASS; "
          f"steps_with_parameter_changes={summary['steps_with_parameter_changes']}/{args.steps}", flush=True)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--steps', type=int, default=8)
    parser.add_argument('--output-dir', type=Path, default=Path('outputs/quick_train'))
    parser.add_argument('--seed', type=int, default=1234)
    parser.add_argument('--threads', type=int, default=1)
    parser.add_argument('--learning-rate', type=float, default=1e-4)
    parser.add_argument('--family-dir', type=Path,
        default=ROOT / 'examples/quick_train/families/demo_family_train_000')
    parser.add_argument('--view-id', default='demo_train_000')
    args = parser.parse_args()
    train(args)


if __name__ == '__main__':
    main()
