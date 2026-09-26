#!/usr/bin/env python3
"""Bounded forward/backward/optimizer checks on separate generated demo/train views.

This is an engineering gradient check, not paper training or a saved model.
The generic diagnostic loss below is not a replacement for native training losses.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import time
from learning_demo import ROOT, model_class, jsonable
import numpy as np
import torch
from evrptw_core.schema import EVRPTWInstance
from evrptw_stage2.artifacts import load_materialized_view
from EVRPTW_Benchmark.Reinforcement_Learning.common.stage2_data import make_envs
from EVRPTW_Benchmark.Reinforcement_Learning.common.objective import select_objective_instance


def load_engineering_train(family_dir, view_id):
    if not view_id.startswith('demo_train_'):
        raise ValueError('Smoke gradients accept only generated demo_train_* views, never benchmark test views')
    fm = json.loads((Path(family_dir) / 'family_manifest.json').read_text())
    if fm.get('family_cohort_id') != 'demo/train':
        raise ValueError('Training requires a separate demo/train family')
    return load_engineering_instance(family_dir, view_id)


def load_engineering_instance(family_dir, view_id):
    """Load a declared engineering view, retaining its actual demo split."""
    family_dir = Path(family_dir)
    fm = json.loads((family_dir / 'family_manifest.json').read_text())
    if fm.get('stage2_generation_contract') != 'review_engineering_subset_v1':
        raise ValueError('Expected separate review engineering fixture')
    p = load_materialized_view(family_dir, view_id)
    vehicle = {**p['vehicle'], 'charging_power_derating_factor': p['charging_policy']['charging_power_derating_factor']}
    # Same physical field mapping as the formal native loader. The formal cohort
    # validator is intentionally unchanged: these small fixtures have their own contract.
    data = {key: p[key] for key in ('instance_id','day_type','working_start_s','working_end_s',
        'depot','customers','charging_stations','distance_matrix_km','demands_cm3','package_counts',
        'service_time_s','tw_s','charging_power_kw','charging_policy','running_time_shortest_matrix_s',
        'running_time_path_energy_kwh','running_time_path_distance_km','distance_path_travel_time_s',
        'full_cs_to_depot_time_s','terminal_parent_indices')}
    data.update(region_id=p.get('city_slug','demo'), mother_board_id=p['family_id'], operating_day_id=p['family_id'],
        vehicle=vehicle, cs_time_to_depot_s=p['full_cs_to_depot_time_s'],
        raw_travel_time_matrix_s=p['running_time_shortest_matrix_s'], shortest_time_matrix_s=p['running_time_shortest_matrix_s'],
        energy_matrix_kwh=p['running_time_path_energy_kwh'], cs_activation={'charging_power_kw':p['charging_power_kw']},
        metadata={**p['metadata'], 'split_id':fm.get('family_cohort_id', 'demo'),'stage2_generation_contract':'review_engineering_subset_v1'},
        feasibility_certificate=p.get('feasibility_certificate'))
    return EVRPTWInstance.from_dict(data)


def check_method(item, instance, seed):
    torch.manual_seed(seed); np.random.seed(seed)
    policy = model_class(item['method'])(**item['constructor']).train()
    optimizer = torch.optim.Adam(policy.parameters(), lr=1e-5)
    before = {name: value.detach().clone() for name, value in policy.named_parameters()}
    instance = select_objective_instance(instance, item['objective'])
    method = item['method']; started = time.perf_counter()
    if method == 'TERRAN':
        from EVRPTW_Benchmark.Reinforcement_Learning.TERRAN.env_factory import make_terran_env
        from EVRPTW_Benchmark.Reinforcement_Learning.TERRAN.rollout import stack_observations
        env = make_terran_env(instance=instance, n_traj=2, use_jit_mask=False,
            charging_mode='station_power_full', matrix_mode='canonical', info_level='full', objective_config=item['objective'])
        try:
            obs, _ = env.reset(seed=seed)
            actions, log_prob, entropy, value = policy.get_action_and_value(stack_observations([obs]))
            _, reward, _, _, _ = env.step(actions.detach().cpu().numpy()[0])
            target = torch.as_tensor(reward, dtype=value.dtype).reshape_as(value)
            loss = -log_prob.mean() + 0.01 * (value - target).square().mean() - 0.001 * entropy.mean()
            transitions = 2
        finally:
            env.close()
    else:
        envs = make_envs([instance], n_traj=2, info_level='full', use_jit_mask=False, objective_config=item['objective'])
        kwargs = dict(decode_type='sampling', max_steps=48, seed=seed, compute_log_likelihood=True)
        if method == 'AM-EVRPTW':
            from EVRPTW_Benchmark.Reinforcement_Learning.AM_EVRPTW.rollout import rollout
            kwargs['incomplete_penalty_km'] = 10000.0
        elif method == 'EVRPTW-RL':
            from EVRPTW_Benchmark.Reinforcement_Learning.EVRPTW_RL.rollout import rollout
        elif method == 'DRL-TS':
            from EVRPTW_Benchmark.Reinforcement_Learning.DRL_TS.rollout import rollout
            kwargs['soft_constraints'] = False
        else:
            from EVRPTW_Benchmark.Reinforcement_Learning.RRNCO_EVRPTW.rollout import rollout
        try:
            result = rollout(policy, envs, **kwargs)
            # Diagnostic policy-gradient loss exercises the native differentiable
            # rollout. Native baselines, staged shaping and PPO updates are not reproduced.
            weights = 1.0 + result.objective_value.detach() / 1000.0
            loss = (weights * result.log_likelihood).mean()
            transitions = result.environment_transitions
        finally:
            for env in envs: env.close()
    if not torch.isfinite(loss):
        raise AssertionError('Non-finite loss')
    optimizer.zero_grad(set_to_none=True); loss.backward()
    gradients = [p.grad for p in policy.parameters() if p.grad is not None]
    if not gradients or not all(bool(torch.isfinite(g).all()) for g in gradients):
        raise AssertionError('Missing/non-finite gradients')
    grad_norm = torch.nn.utils.clip_grad_norm_(policy.parameters(), 1.0)
    if not torch.isfinite(grad_norm) or grad_norm <= 0:
        raise AssertionError('Zero or non-finite gradient norm')
    optimizer.step()
    changed = sum(not torch.equal(before[n], p.detach()) for n, p in policy.named_parameters())
    if not changed: raise AssertionError('Optimizer changed no parameters')
    return dict(method=method, status='PASS', initialization='random_for_gradient_check_only',
        architecture=item['constructor'], transitions=transitions, loss=float(loss.detach()),
        gradient_norm=float(grad_norm), parameters_with_gradients=len(gradients),
        parameter_tensors_changed=changed, seconds=time.perf_counter()-started)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--family-dir', type=Path, default=ROOT.parent/'review-core/generation/generated_train/families/demo_family_train_000')
    p.add_argument('--view-id', default='demo_train_000')
    p.add_argument('--seed', type=int, default=1234)
    p.add_argument('--output', type=Path, default=Path('outputs/learning_smoke.json'))
    args = p.parse_args(); torch.set_num_threads(1)
    instance = load_engineering_train(args.family_dir, args.view_id)
    inventory = json.loads((ROOT/'configs/training/learning_inventory.json').read_text())
    rows = []
    for item in inventory['artifacts']:
        if item['training_regime'] != 'Road-100': continue
        try: row = check_method(item, instance, args.seed)
        except Exception as exc: row = dict(method=item['method'], status='FAIL', error_type=type(exc).__name__, error=str(exc))
        rows.append(row); print(json.dumps(row), flush=True)
    result = dict(schema='learning_gradient_smoke_v1', view_id=args.view_id, split='demo/train', device='cpu',
        seed=args.seed, customer_count=len(instance.customers), full_training='NOT RUN',
        scope='One bounded diagnostic optimizer step per original architecture; no benchmark test training; no inference checkpoint produced.', checks=rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(jsonable(result), indent=2, allow_nan=False)+'\n')
    if len(rows)!=5 or any(r['status']!='PASS' for r in rows): raise SystemExit(2)

if __name__ == '__main__': main()
