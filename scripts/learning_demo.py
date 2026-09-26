#!/usr/bin/env python3
"""CPU inference with real, strict-loaded, metadata-minimized checkpoint weights."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import platform
import sys
import time
ROOT = Path(__file__).resolve().parents[1]
for sub in ('', 'EVRPTW_Core', 'EVRPTW_Dataset_Generator/src'):
    sys.path.insert(0, str(ROOT / sub))
import numpy as np
import torch
from EVRPTW_Benchmark.Reinforcement_Learning.common.stage2_data import make_envs
from EVRPTW_Benchmark.Reinforcement_Learning.common.evaluation import select_min_verified_objective
from EVRPTW_Benchmark.Reinforcement_Learning.common.objective import select_objective_instance
from EVRPTW_Benchmark.MetaHeuristics.benchmark_common import Stage2ViewTask, load_stage2_instance


def jsonable(value):
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [jsonable(v) for v in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, torch.Tensor):
        return value.detach().cpu().tolist()
    return value


def model_class(method):
    if method == 'AM-EVRPTW':
        from EVRPTW_Benchmark.Reinforcement_Learning.AM_EVRPTW.model import AMEVRPTWPolicy
        return AMEVRPTWPolicy
    if method == 'EVRPTW-RL':
        from EVRPTW_Benchmark.Reinforcement_Learning.EVRPTW_RL.model import EVRPTWRLPolicy
        return EVRPTWRLPolicy
    if method == 'DRL-TS':
        from EVRPTW_Benchmark.Reinforcement_Learning.DRL_TS.model import DRLTSPolicy
        return DRLTSPolicy
    if method == 'RRNCO':
        from EVRPTW_Benchmark.Reinforcement_Learning.RRNCO_EVRPTW.model import RRNCOEVPolicy
        return RRNCOEVPolicy
    if method == 'TERRAN':
        from EVRPTW_Benchmark.Reinforcement_Learning.TERRAN.models import Agent
        return Agent
    raise ValueError(f'Unsupported method: {method}')


def load_policy(path):
    payload = torch.load(path, map_location='cpu', weights_only=True)
    if payload.get('format') != 'evrptw_inference_weights_v1':
        raise ValueError('Use the cleaned inference checkpoint format; original training pickles are not accepted.')
    policy = model_class(payload['method'])(**payload['constructor'])
    policy.load_state_dict(payload['state_dict'], strict=True)
    policy.to('cpu').eval()
    return policy, payload


def load_review_instance(bundle, view_id=None):
    bundle = Path(bundle)
    manifest = json.loads((bundle / 'sample_manifest.json').read_text())
    matches = [r for r in manifest['views'] if r['view_id'] == view_id] if view_id else [
        r for r in manifest['views'] if r['customer_count'] == 100]
    if not matches:
        raise ValueError('Requested review view is absent')
    row = matches[0]
    family_dir = bundle / row['family_dir']
    vm = json.loads((family_dir / 'views' / row['view_id'] / 'view_manifest.json').read_text())
    task = Stage2ViewTask(index_path='sample_manifest.json', family_dir=str(family_dir),
        view_id=row['view_id'], family_id=row['family_id'], consumer_cohort_id=vm.get('consumer_cohort_id','review'),
        family_cohort_id=vm.get('family_cohort_id',''), split_id=row['split_id'], track_id=row['track_id'],
        city_slug=row['city_slug'], scale_id=row['scale_id'], customer_count=row['customer_count'],
        charging_station_count=row['charging_station_count'], terminal_count=row['terminal_count'],
        view_seed=int(vm.get('view_seed', 0)), row_position=0)
    return load_stage2_instance(task), row


def run_rollout(policy, payload, instance, *, candidates=30, seed=1234, max_steps=360):
    torch.manual_seed(seed)
    np.random.seed(seed)
    method = payload['method']
    norm = dict(payload.get('normalization', {}))
    if 'reward_distance_scale_mode' in norm:
        # Dataset-calibrated scale is explicit; the environment accepts the base statistic.
        norm['reward_distance_scale_mode'] = norm['reward_distance_scale_mode'].removeprefix('dataset_')
    instance = select_objective_instance(instance, payload['objective'])
    if method == 'TERRAN':
        from EVRPTW_Benchmark.Reinforcement_Learning.TERRAN.env_factory import make_terran_env
        from EVRPTW_Benchmark.Reinforcement_Learning.TERRAN.rollout import rollout_eval_batch
        stable = payload['constructor'].get('critic_mode') == 'stable_cost_v1'
        kwargs = {'training_mode': 'stable_cost_v1', 'rollout_horizon_steps': max_steps} if stable else {}
        env = make_terran_env(instance=instance, n_traj=candidates, reward_mode='distance',
            charging_mode='station_power_full', matrix_mode='canonical', info_level='full',
            use_jit_mask=False, objective_config=payload['objective'], **norm, **kwargs)
        try:
            row = rollout_eval_batch(policy, [env], decode_mode='sample', max_steps=max_steps,
                device='cpu', seed=seed, include_routes=True, return_final_info=True)[0]
            info = row.pop('_final_info')
            measured = row.get('runtime_s', row.get('runtime_seconds'))
            return info, None if measured is None else float(measured)
        finally:
            env.close()
    envs = make_envs([instance], n_traj=candidates, info_level='full', use_jit_mask=False,
        objective_config=payload['objective'], **norm)
    kwargs = dict(decode_type='sampling', max_steps=max_steps, seed=seed, compute_log_likelihood=False)
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
        with torch.no_grad():
            result = rollout(policy, envs, **kwargs)
        return result.infos[0], result.runtime_s
    finally:
        for env in envs:
            env.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, default=ROOT.parent / 'review-core')
    parser.add_argument('--checkpoint', type=Path, default=ROOT.parent / 'review-checkpoints/am_evrptw_road_100.pt')
    parser.add_argument('--view-id')
    parser.add_argument('--candidates', type=int, default=30)
    parser.add_argument('--seed', type=int, default=1234)
    parser.add_argument('--max-steps', type=int, default=360)
    parser.add_argument('--threads', type=int, default=1)
    parser.add_argument('--output', type=Path, default=Path('outputs/learning_demo.json'))
    args = parser.parse_args()
    if min(args.candidates, args.max_steps, args.threads) <= 0:
        parser.error('Candidates, max-steps and threads must be positive')
    torch.set_num_threads(args.threads)
    started = time.perf_counter()
    policy, payload = load_policy(args.checkpoint)
    instance, row = load_review_instance(args.bundle, args.view_id)
    info, decode_seconds = run_rollout(policy, payload, instance, candidates=args.candidates,
        seed=args.seed, max_steps=args.max_steps)
    selection_started = time.perf_counter()
    idx, routes, verification = select_min_verified_objective(instance, info, payload['objective'])
    selection_seconds = time.perf_counter() - selection_started
    success = bool(info['success'][idx]) and bool(verification['passed'])
    result = dict(schema='learning_review_result_v1', method=payload['method'], artifact_id=payload['artifact_id'],
        checkpoint_sha256=hashlib.sha256(args.checkpoint.read_bytes()).hexdigest(), checkpoint_epoch=payload['epoch'],
        strict_load='PASS', inference_only=True, instance_id=row['view_id'], customer_count=row['customer_count'],
        candidates=args.candidates, environment_success_count=int(np.count_nonzero(info['success'])),
        decode_type='sampling', seed=args.seed, max_steps=args.max_steps, selected_trajectory=idx,
        objective=payload['objective'], complete_and_feasible=success, routes=routes, verification=verification,
        timing=dict(model_setup_and_decode_s=decode_seconds, selection_and_verification_s=selection_seconds,
            end_to_end_s=time.perf_counter()-started),
        environment=dict(device='cpu', torch=str(torch.__version__), python=platform.python_version(), threads=args.threads),
        scope='Small review sample; not a full benchmark or a paper-result reproduction.')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(jsonable(result), indent=2, allow_nan=False)+'\n')
    print(json.dumps({k: result[k] for k in ('method','instance_id','candidates','complete_and_feasible','timing')}, indent=2))
    if not success:
        raise SystemExit(2)

if __name__ == '__main__':
    main()
