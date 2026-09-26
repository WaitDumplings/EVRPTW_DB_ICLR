#!/usr/bin/env python3
"""Small, actual CPU training runs on EVRPTW-D road training instances.

One epoch is one complete pass over the selected training manifest. The bundled
Road-100 manifest has two genuine core/train instances, separate from review
evaluation data. This entry point demonstrates native learning updates; use the
method training modules and registered configurations for full experiments.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib
import json
import math
from pathlib import Path
import random
import re
import sys
import time

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
from learning_demo import load_policy, model_class
import numpy as np
import torch
from evrptw_core.schema import EVRPTWInstance
from EVRPTW_Benchmark.Reinforcement_Learning.common.objective import select_objective_instance
from EVRPTW_Benchmark.Reinforcement_Learning.common.stage2_data import make_envs


ALIASES = {
    'am': 'AM-EVRPTW', 'am_evrptw': 'AM-EVRPTW',
    'evrptw_rl': 'EVRPTW-RL', 'evrptw': 'EVRPTW-RL',
    'terran': 'TERRAN', 'rrnco': 'RRNCO', 'rrnco_ev': 'RRNCO',
    'rrnco_evrptw': 'RRNCO', 'drl_ts': 'DRL-TS', 'drlts': 'DRL-TS',
}
MODULES = {'AM-EVRPTW': 'AM_EVRPTW', 'EVRPTW-RL': 'EVRPTW_RL',
           'RRNCO': 'RRNCO_EVRPTW', 'DRL-TS': 'DRL_TS'}
PREFIX = 'EVRPTW_Benchmark.Reinforcement_Learning.'


def model_name(value):
    key = value.strip().lower().replace('-', '_')
    if key not in ALIASES:
        raise argparse.ArgumentTypeError('Choose AM, EVRPTW_RL, TERRAN, RRNCO, or DRL_TS')
    return ALIASES[key]


def load_training_data(data_dir, scale):
    """Require declared road/train provenance and exact customer count."""
    manifest_path = Path(data_dir) / 'sample_manifest.json'
    if not manifest_path.is_file():
        raise ValueError(f'No Road-{scale} training manifest at {manifest_path}. '
                         'Only Road-100 is bundled; supply --data-dir for another scale.')
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    if manifest.get('representation') != 'road' or manifest.get('source_cohort') != 'core/train':
        raise ValueError('Training requires a road manifest with source_cohort=core/train')
    if manifest.get('customer_count') != scale:
        raise ValueError('Manifest customer_count must equal --scale; no scale substitution is allowed')
    rows = manifest.get('views', [])
    if manifest.get('view_count') != len(rows):
        raise ValueError('Manifest view_count disagrees with its actual view rows')
    if not rows or len({r['view_id'] for r in rows}) != len(rows):
        raise ValueError('Training manifest must contain distinct, nonempty training views')
    instances, verified_inputs = [], []
    for row in rows:
        required = {'customer_count': scale, 'representation': 'road',
                    'source_cohort': 'core/train', 'family_cohort_id': 'core/train',
                    'split_id': 'train', 'instance_id': row['view_id']}
        if any(row.get(k) != v for k, v in required.items()):
            raise ValueError('Training view row has inconsistent identity, scale, representation, or cohort')
        digest = row.get('sha256', '')
        if not isinstance(digest, str) or re.fullmatch(r'[0-9a-f]{64}', digest) is None:
            raise ValueError('Every training instance requires a valid lowercase SHA256 digest')
        path = (Path(data_dir) / row['instance_path']).resolve()
        if not path.is_relative_to(Path(data_dir).resolve()):
            raise ValueError('Instance path must stay inside --data-dir')
        instance_bytes = path.read_bytes()
        if hashlib.sha256(instance_bytes).hexdigest() != digest:
            raise ValueError('Training instance SHA256 disagrees with its manifest')
        payload = json.loads(instance_bytes)
        metadata = payload.get('metadata', {})
        if metadata.get('split_id') != 'train' or metadata.get('family_cohort_id') != 'core/train':
            raise ValueError('Only original core/train instances may be used, never evaluation views')
        if payload.get('instance_id') != row['view_id']:
            raise ValueError('Canonical instance_id disagrees with its training manifest')
        if not row.get('family_id') or metadata.get('family_id') != row['family_id']:
            raise ValueError('Canonical family_id disagrees with its training manifest')
        terminal_count = 1 + len(payload.get('customers', [])) + len(payload.get('charging_stations', []))
        if row.get('terminal_count') != terminal_count or row.get('charging_station_count') != len(payload.get('charging_stations', [])):
            raise ValueError('Canonical terminal counts disagree with their training manifest')
        for key in ('distance_matrix_km', 'distance_path_travel_time_s',
                    'running_time_shortest_matrix_s', 'running_time_path_distance_km',
                    'running_time_path_energy_kwh'):
            matrix = np.asarray(payload.get(key), dtype=np.float64)
            if matrix.shape != (terminal_count, terminal_count) or not np.isfinite(matrix).all() or (matrix < 0).any():
                raise ValueError(f'Missing or invalid canonical road matrix: {key}')
        instance = EVRPTWInstance.from_dict(payload)
        if len(instance.customers) != scale:
            raise ValueError(f"{row['view_id']}: expected exactly {scale} customers")
        # Road matrices and original train provenance are mandatory. Coordinates
        # are never converted into Euclidean edges by this training entry point.
        if metadata.get('representation') != 'road':
            raise ValueError('Every instance must explicitly declare road representation')
        if metadata.get('view_id') != row['view_id']:
            raise ValueError('Instance view_id disagrees with its training manifest')
        instances.append(instance)
        verified_inputs.append({'view_id': row['view_id'], 'family_id': row['family_id'],
                                'sha256': digest, 'size_bytes': len(instance_bytes)})
    manifest = {**manifest, 'verified_inputs': verified_inputs,
                'verified_manifest_sha256': hashlib.sha256(manifest_bytes).hexdigest()}
    return manifest, rows, instances


def native_configuration(method):
    inventory = json.loads((ROOT / 'configs/training/learning_inventory.json').read_text())
    record = next(r for r in inventory['artifacts']
                  if r['method'] == method and r['training_regime'] == 'Road-100')
    objective = next(r['objective'] for r in inventory['artifacts']
                     if r['method'] == 'AM-EVRPTW' and r['training_regime'] == 'Road-100')
    return dict(record['constructor']), dict(objective)


def gradient_step(policy, optimizer, loss):
    if not bool(torch.isfinite(loss)):
        raise FloatingPointError('Non-finite native training loss')
    optimizer.zero_grad(set_to_none=True)
    loss.backward()
    gradients = [p.grad for p in policy.parameters() if p.grad is not None]
    if not gradients or not all(bool(torch.isfinite(g).all()) for g in gradients):
        raise FloatingPointError('Missing or non-finite native training gradients')
    norm = torch.nn.utils.clip_grad_norm_(policy.parameters(), 1.0)
    if not bool(torch.isfinite(norm)):
        raise FloatingPointError('Non-finite native training gradient norm')
    optimizer.step()
    if not all(bool(torch.isfinite(p).all()) for p in policy.parameters()):
        raise FloatingPointError('Non-finite updated parameters')
    return float(norm)


def parameter_change(policy, before):
    deltas = [p.detach() - before[n] for n, p in policy.named_parameters()]
    return (sum(bool(torch.count_nonzero(d)) for d in deltas),
            math.sqrt(sum(float(d.double().square().sum()) for d in deltas)))


def reinforce_update(policy, baseline, optimizer, instance, method, objective,
                     normalization, args, epoch, step, state):
    soft = method == 'DRL-TS' and epoch <= round(args.epochs * 0.5)
    kwargs = dict(decode_type='sampling', seed=args.seed + step,
                  compute_log_likelihood=True)
    if method == 'AM-EVRPTW':
        kwargs['incomplete_penalty_km'] = 10000.0
    elif method == 'DRL-TS':
        kwargs.update(soft_constraints=soft, incomplete_penalty=100.0)
    rollout = importlib.import_module(PREFIX + MODULES[method] + '.rollout').rollout

    def environments(trajectories):
        if method == 'DRL-TS':
            name = '.soft_env' if soft else '.env'
            module = importlib.import_module(PREFIX + 'DRL_TS' + name)
            cls = getattr(module, 'DRLTSSoftConstraintEnv' if soft else 'DRLTSHardConstraintEnv')
            return [cls(instance=instance, n_traj=trajectories, reward_mode='distance',
                        charging_mode='station_power_full', matrix_mode='canonical',
                        info_level='full', use_jit_mask=False, objective_config=objective,
                        **normalization)]
        return make_envs([instance], n_traj=trajectories, info_level='full',
                         use_jit_mask=False, objective_config=objective, **normalization)

    actor_envs = environments(args.trajectories)
    baseline_envs = []
    try:
        kwargs['max_steps'] = actor_envs[0].unwrapped.max_steps
        policy.train()
        actor = rollout(policy, actor_envs, **kwargs)
        if method == 'RRNCO':
            from EVRPTW_Benchmark.Reinforcement_Learning.common.protocol_trainers import same_instance_leave_one_out
            baseline_cost = same_instance_leave_one_out(actor.training_cost)
            baseline_kind = 'native_same_instance_leave_one_out'
        elif method == 'EVRPTW-RL' and epoch == 1:
            observed = float(actor.training_cost.detach().mean())
            state['ema'] = observed if 'ema' not in state else 0.9 * state['ema'] + 0.1 * observed
            baseline_cost = torch.full_like(actor.training_cost, state['ema'])
            baseline_kind = 'native_ema_warmup'
        else:
            baseline_envs = environments(1)
            with torch.no_grad():
                greedy = rollout(baseline, baseline_envs,
                                 **{**kwargs, 'decode_type': 'greedy', 'compute_log_likelihood': False})
            baseline_cost = greedy.training_cost
            baseline_kind = 'frozen_greedy_rollout'
        advantage = (actor.training_cost - baseline_cost).detach()
        loss = (advantage * actor.log_likelihood).mean()
        grad_norm = gradient_step(policy, optimizer, loss)
        return {'loss': float(loss.detach()), 'grad_norm_before_clip': grad_norm,
                'mean_training_cost_normalized': float(actor.training_cost.detach().mean()),
                'mean_objective_usd': float(actor.objective_value.detach().mean()),
                'environment_success_rate': float(actor.feasible.float().mean()),
                'environment_transitions': int(actor.environment_transitions),
                'baseline_kind': baseline_kind, 'stage': 'soft' if soft else 'hard'}
    finally:
        for env in actor_envs + baseline_envs:
            env.close()


def terran_update(policy, optimizer, instance, objective, normalization, args, step):
    from EVRPTW_Benchmark.Reinforcement_Learning.TERRAN.env_factory import make_terran_env
    from EVRPTW_Benchmark.Reinforcement_Learning.TERRAN.rollout import collect_rollout, compute_returns
    from EVRPTW_Benchmark.Reinforcement_Learning.TERRAN.trainer import evaluate_policy_loss
    env = make_terran_env(instance=instance, n_traj=args.trajectories, reward_mode='distance',
                         charging_mode='station_power_full', matrix_mode='canonical',
                         info_level='full', use_jit_mask=False, objective_config=objective,
                         **normalization)
    cfg = {'training': {'clip_coef': 0.2, 'vf_coef': 0.5, 'ent_coef': 0.01,
                        'value_loss_type': 'mse'}}
    try:
        policy.eval()
        with torch.no_grad():
            batch = collect_rollout(policy, [env], rollout_steps=env.unwrapped.max_steps,
                                    decode_mode='sample', device='cpu', seed=args.seed + step,
                                    reward_discount_factor=1.0, collect_reward_diagnostics=False)
        returns = compute_returns(batch.rewards, batch.dones, gamma=1.0)
        advantages = returns - batch.values
        valid = advantages[batch.valid]
        if valid.numel() > 1:
            advantages = (advantages - valid.mean()) / (valid.std(unbiased=False) + 1e-8)
        policy.train()
        loss, actor_loss, critic_loss, entropy = evaluate_policy_loss(
            policy, batch, returns, advantages, cfg, device='cpu')
        grad_norm = gradient_step(policy, optimizer, loss)
        info = batch.final_infos[0]
        return {'loss': float(loss.detach()), 'policy_loss': float(actor_loss),
                'value_loss': float(critic_loss), 'entropy': float(entropy),
                'grad_norm_before_clip': grad_norm,
                'mean_objective_usd': float(np.asarray(info['objective_value']).mean()),
                'environment_success_rate': float(np.asarray(info['success']).mean()),
                'environment_transitions': int(batch.valid.sum()),
                'baseline_kind': 'native_critic_monte_carlo_returns', 'stage': 'legacy_ppo',
                'ppo_update_epochs': 1}
    finally:
        env.close()


def train(args):
    if min(args.epochs, args.scale, args.threads) < 1 or args.trajectories < 2:
        raise ValueError('Epochs, scale and threads must be positive; trajectories must be at least two')
    if not math.isfinite(args.learning_rate) or args.learning_rate <= 0:
        raise ValueError('Learning rate must be finite and positive')
    torch.set_num_threads(args.threads)
    random.seed(args.seed)
    np.random.seed(args.seed % (2**32))
    torch.manual_seed(args.seed)
    data_dir = args.data_dir or ROOT / f'examples/training/road_{args.scale}'
    manifest, rows, instances = load_training_data(data_dir, args.scale)
    constructor, objective = native_configuration(args.model)
    instances = [select_objective_instance(i, objective) for i in instances]
    # One shared normalization is fitted only to the selected training views.
    calibration = make_envs(instances, n_traj=1, info_level='light', use_jit_mask=False,
                            objective_config=objective)
    normalization = {
        'reward_distance_scale_mode': 'single_customer_repair_median',
        'reward_distance_scale_km': float(np.median([e.unwrapped.reward_distance_scale_km for e in calibration])),
        'reward_objective_scale': float(np.median([e.unwrapped.reward_objective_scale for e in calibration])),
    }
    for env in calibration:
        env.close()
    output = args.output_dir or Path('outputs') / (
        f"train_{args.model.lower().replace('-', '_')}_road{args.scale}_"
        + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ'))
    if output.exists():
        raise FileExistsError('Output directory already exists; choose a new --output, '
                              'or omit --output to create a directory automatically')
    output.mkdir(parents=True, exist_ok=False)
    policy = model_class(args.model)(**constructor).to('cpu')
    baseline = deepcopy(policy).eval() if args.model != 'TERRAN' else None
    if baseline is not None:
        for p in baseline.parameters():
            p.requires_grad_(False)
    optimizer = torch.optim.AdamW(policy.parameters(), lr=args.learning_rate, weight_decay=0.01)
    initial = {n: p.detach().clone() for n, p in policy.named_parameters()}
    state, history, epoch_history = {}, [], []
    started = time.perf_counter()
    print(f'{args.model} training demo | {len(instances)} Road-{args.scale} instances | '
          f'{args.epochs} epochs | CPU', flush=True)
    with (output / 'loss.jsonl').open('x') as log:
        for epoch in range(1, args.epochs + 1):
            epoch_start = time.perf_counter()
            updates = []
            for row, instance in zip(rows, instances):
                step = len(history) + 1
                before = {n: p.detach().clone() for n, p in policy.named_parameters()}
                t0 = time.perf_counter()
                if args.model == 'TERRAN':
                    metrics = terran_update(policy, optimizer, instance, objective, normalization, args, step)
                else:
                    metrics = reinforce_update(policy, baseline, optimizer, instance, args.model,
                                               objective, normalization, args, epoch, step, state)
                changed, update_l2 = parameter_change(policy, before)
                metrics.update(epoch=epoch, optimizer_step=step, view_id=row['view_id'],
                               parameter_tensors_changed=changed, parameter_update_l2=update_l2,
                               seconds=time.perf_counter() - t0)
                log.write(json.dumps(metrics, allow_nan=False) + '\n')
                log.flush()
                updates.append(metrics)
                history.append(metrics)
            if args.model == 'EVRPTW-RL' and epoch == 1:
                baseline.load_state_dict(policy.state_dict())
            epoch_row = {'epoch': epoch, 'instances': len(updates), 'optimizer_steps': len(history),
                         'mean_loss': float(np.mean([u['loss'] for u in updates])),
                         'mean_grad_norm': float(np.mean([u['grad_norm_before_clip'] for u in updates])),
                         'parameter_update_l2_sum': sum(u['parameter_update_l2'] for u in updates),
                         'stage': updates[-1]['stage'], 'seconds': time.perf_counter() - epoch_start}
            epoch_history.append(epoch_row)
            print(f"epoch={epoch}/{args.epochs} loss={epoch_row['mean_loss']:.6f}", flush=True)
    checkpoint = output / 'demo_checkpoint.pt'
    payload = {'format': 'evrptw_inference_weights_v1',
               'artifact_id': f"{args.model.lower().replace('-', '_')}_road{args.scale}_demo_seed{args.seed}",
               'method': args.model, 'training_regime': f'Road-{args.scale}',
               'scope': 'small_road_training_demo', 'epoch': args.epochs,
               'optimizer_steps': len(history), 'constructor': constructor,
               'objective': objective, 'normalization': normalization,
               'state_dict': {k: v.detach().cpu().clone() for k, v in policy.state_dict().items()},
               'resumable': False, 'seed': args.seed,
               'training_view_ids': [r['view_id'] for r in rows],
               'training_input_sha256': manifest['verified_inputs'],
               'training_manifest_sha256': manifest['verified_manifest_sha256'],
               'training_scope': 'Few original core/train road instances; not a full paper training run.'}
    torch.save(payload, checkpoint)
    reloaded, _ = load_policy(checkpoint)
    if not all(torch.equal(v, reloaded.state_dict()[k]) for k, v in policy.state_dict().items()):
        raise AssertionError('Strict reloaded checkpoint differs from trained model')
    changed_initial, total_l2 = parameter_change(policy, initial)
    summary = {'schema': 'road_training_demo_v1', 'status': 'PASS',
               'method': args.model, 'scale': args.scale, 'representation': 'road',
               'source_cohort': 'core/train', 'training_view_ids': payload['training_view_ids'],
               'training_input_sha256': manifest['verified_inputs'],
               'training_manifest_sha256': manifest['verified_manifest_sha256'],
               'epochs': args.epochs, 'epoch_definition': 'One pass over every manifest instance, once each',
               'optimizer_steps': len(history), 'instances_per_epoch': len(instances),
               'trajectories_per_instance': args.trajectories, 'device': 'cpu',
               'threads': args.threads, 'seed': args.seed, 'constructor': constructor,
               'optimizer': 'AdamW', 'learning_rate': args.learning_rate, 'weight_decay': 0.01,
               'max_grad_norm': 1.0, 'objective': objective, 'normalization': normalization,
               'strict_load': 'PASS', 'saved_tensor_identity': 'PASS',
               'updates_with_parameter_changes': sum(h['parameter_tensors_changed'] > 0 for h in history),
               'parameter_tensors_changed_from_initialization': changed_initial,
               'parameter_change_from_initialization_l2': total_l2,
               'checkpoint': checkpoint.name, 'checkpoint_sha256': hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
               'epoch_history': epoch_history, 'seconds': time.perf_counter() - started,
               'protocol_differences': [
                   'Only selected core/train road views, no large training pool or validation selection.',
                   'Training-only shared scales; legacy native terminal/auxiliary penalties, no full registered reward contract.',
                   'AM frozen initial greedy baseline; EVRPTW-RL one-epoch EMA warmup then frozen greedy baseline.',
                   'RRNCO native leave-one-out baseline; DRL-TS native soft then hard stages with frozen greedy baseline.',
                   'TERRAN native legacy PPO with Monte Carlo returns, critic MSE, entropy, one PPO update per instance.',
                   'No paired-test baseline refresh, curriculum between scales, early stopping, or best-checkpoint selection.',
                   'Loss is stochastic; route feasibility and solution quality are not guaranteed after a short demo.']}
    (output / 'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
    print(f'Saved checkpoint: {checkpoint.resolve()}', flush=True)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=model_name, default='EVRPTW-RL')
    parser.add_argument('--scale', type=int, default=100)
    parser.add_argument('--epochs', type=int, default=5)
    parser.add_argument('--data-dir', type=Path, help='Directory containing a core/train road sample_manifest.json')
    parser.add_argument('--output-dir', '--output', dest='output_dir', type=Path,
                        help='New output directory; omitted: unique timestamped directory under outputs/')
    parser.add_argument('--seed', type=int, default=1234)
    parser.add_argument('--threads', type=int, default=1)
    parser.add_argument('--learning-rate', type=float, default=1e-4)
    parser.add_argument('--trajectories', type=int, default=4)
    args = parser.parse_args()
    try:
        train(args)
    except (ValueError, FileExistsError) as exc:
        parser.error(str(exc))


if __name__ == '__main__':
    main()
