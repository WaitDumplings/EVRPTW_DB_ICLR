#!/usr/bin/env python3
"""Evaluate one explicit checkpoint/instance and save verified routes plus an SVG."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import time

from learning_demo import (
    ROOT, Stage2ViewTask, jsonable, load_policy, load_review_instance,
    load_stage2_instance, np, run_rollout, select_min_verified_objective, torch,
)
from evrptw_core.schema import EVRPTWInstance
from evrptw_db.route_plot import write_route_svg


def load_instance(reference: str, bundle: Path):
    """Accept a frozen sample ID, materialized view path, or canonical JSON payload."""
    path = Path(reference)
    if not path.exists():
        if path.name == reference and reference.startswith('iv_'):
            instance, _ = load_review_instance(bundle, reference)
            return instance, 'review_bundle_view_id'
        raise FileNotFoundError(f'Instance path does not exist: {reference}')
    if path.is_dir():
        path = path / 'view_manifest.json'
    payload = json.loads(path.read_text())
    if path.name != 'view_manifest.json':
        if not isinstance(payload, dict) or 'instance_id' not in payload or 'depot' not in payload:
            raise ValueError('Expected a materialized view_manifest.json or canonical instance JSON')
        return EVRPTWInstance.from_dict(payload), 'canonical_instance_json'
    path = path.resolve()
    if path.parent.parent.name != 'views':
        raise ValueError('Keep a materialized view under <family>/views/<view_id>/')
    family = path.parents[2]
    fm = json.loads((family / 'family_manifest.json').read_text())
    view_id = str(payload['view_id'])
    if view_id != path.parent.name or payload['family_id'] != fm['family_id']:
        raise ValueError('View path, family manifest and view identifiers disagree')
    if fm.get('stage2_generation_contract') == 'review_engineering_subset_v1':
        # The bundled demo/train input is intentionally separate from benchmark
        # evaluation views. This loader keeps the production cohort gate intact.
        from learning_smoke import load_engineering_instance
        return load_engineering_instance(family, view_id), 'engineering_demo_view'
    task = Stage2ViewTask(
        index_path='explicit_view_manifest', family_dir=str(family), view_id=view_id,
        family_id=str(payload['family_id']),
        consumer_cohort_id=str(payload.get('consumer_cohort_id', 'review')),
        family_cohort_id=str(payload.get('family_cohort_id', fm.get('family_cohort_id', ''))),
        split_id=str(payload.get('split_id', '')), track_id=str(payload.get('track_id', '')),
        city_slug=str(payload.get('city_slug', fm.get('city_slug', ''))),
        scale_id=str(payload.get('scale_id', f"cus{payload['customer_count']}")),
        customer_count=int(payload['customer_count']),
        charging_station_count=int(payload['charging_station_count']),
        terminal_count=int(payload.get('terminal_count', 1 + int(payload['customer_count']) + int(payload['charging_station_count']))), view_seed=int(payload.get('view_seed', 0)),
        row_position=0,
    )
    return load_stage2_instance(task), 'materialized_view_path'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ckpt', '--checkpoint', dest='checkpoint', type=Path, required=True,
                        help='Clean inference weights or a quick_train demo_checkpoint.pt')
    parser.add_argument('--inst_path', '--instance', '--inst-path', dest='instance', required=True,
                        help='Review view ID, view directory/view_manifest.json, or canonical JSON')
    parser.add_argument('--bundle', type=Path, default=ROOT.parent / 'review-core',
                        help='Only needed when --instance is a review view ID')
    parser.add_argument('--candidates', type=int, default=30)
    parser.add_argument('--max-steps', type=int, default=None,
                        help='Default: 4 times the actual terminal count (native environment limit)')
    parser.add_argument('--seed', type=int, default=1234)
    parser.add_argument('--threads', type=int, default=1)
    parser.add_argument('--output-dir', '--output', type=Path, default=None,
                        help='Default: a fresh directory under outputs/')
    parser.add_argument('--annotate', action='store_true', help='Show terminal numbers on the SVG')
    args = parser.parse_args(argv)
    if min(args.candidates, args.threads) <= 0 or (args.max_steps is not None and args.max_steps <= 0):
        parser.error('candidates, max-steps and threads must be positive')
    # A fresh directory prevents a previous successful plot from surviving a
    # failed evaluation and being mistaken for the new result.
    if args.output_dir is not None and args.output_dir.exists():
        parser.error('Output directory already exists; choose a new --output-dir')
    torch.set_num_threads(args.threads)
    started = time.perf_counter()
    policy, checkpoint = load_policy(args.checkpoint)
    instance, input_kind = load_instance(args.instance, args.bundle)
    if args.max_steps is None:
        args.max_steps = 4 * instance.num_terminals
    if args.output_dir is None:
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
        args.output_dir = Path('outputs') / f'eval_road{instance.num_customers}_{stamp}'
    args.output_dir.mkdir(parents=True, exist_ok=False)
    info, native_decode_s = run_rollout(
        policy, checkpoint, instance, candidates=args.candidates, seed=args.seed,
        max_steps=args.max_steps,
    )
    selection_started = time.perf_counter()
    selected, routes, verification = select_min_verified_objective(instance, info, checkpoint['objective'])
    selection_s = time.perf_counter() - selection_started
    success = bool(info['success'][selected]) and bool(verification['passed'])
    inference_s = time.perf_counter() - started
    result = {
        'schema': 'quick_evaluation_v1',
        'status': 'VERIFIED' if success else 'NO_VERIFIED_SOLUTION',
        'method': checkpoint['method'], 'artifact_id': checkpoint['artifact_id'],
        'checkpoint_sha256': hashlib.sha256(args.checkpoint.read_bytes()).hexdigest(),
        'checkpoint_epoch': checkpoint.get('epoch'),
        'checkpoint_optimizer_steps': checkpoint.get('optimizer_steps'),
        'checkpoint_scope': checkpoint.get('scope', checkpoint.get('training_scope', 'released_inference_weights')),
        'strict_load': 'PASS', 'instance_id': instance.instance_id,
        'input_kind': input_kind, 'customer_count': instance.num_customers,
        'candidates': args.candidates, 'decode_type': 'sampling', 'seed': args.seed,
        'max_steps': args.max_steps, 'selected_trajectory': selected,
        'environment_success_count': int(np.count_nonzero(info['success'])),
        'complete_and_feasible': success, 'routes': routes, 'verification': verification,
        'objective': checkpoint['objective'],
        'vehicle_count': len(routes) if success else None,
        'objective_cost_usd': verification.get('objective_cost_usd') if success else None,
        'objective_distance_km': verification.get('objective_distance_km') if success else None,
        'timing': {'native_setup_and_decode_s': native_decode_s,
                   'selection_and_verification_s': selection_s,
                   'inference_end_to_end_s': inference_s},
        'environment': {'device': 'cpu', 'threads': args.threads,
                        'python': platform.python_version(), 'torch': str(torch.__version__)},
        'plot': None,
        'scope': 'One-instance review demo. A demo/train replay is not held-out policy evaluation.',
    }
    output = args.output_dir / 'result.json'
    # Persist an invalid result without drawing a successful route. Missing
    # measurements stay null; incurred failure accounting remains in verification.
    output.write_text(json.dumps(jsonable(result), indent=2, allow_nan=False) + '\n')
    if success:
        plot_started = time.perf_counter()
        write_route_svg(instance, routes, args.output_dir / 'routes.svg',
                        title=f"{checkpoint['method']} | {instance.instance_id}",
                        verified=True, cost_usd=result['objective_cost_usd'], annotate=args.annotate)
        result['plot'] = 'routes.svg'
        result['timing']['plot_s'] = time.perf_counter() - plot_started
        result['timing']['total_with_plot_s'] = time.perf_counter() - started
        output.write_text(json.dumps(jsonable(result), indent=2, allow_nan=False) + '\n')
    print(json.dumps({key: result[key] for key in (
        'status', 'method', 'instance_id', 'candidates', 'vehicle_count',
        'objective_cost_usd', 'objective_distance_km', 'plot',
    )}, indent=2), flush=True)
    print(f'Result: {output}', flush=True)
    return 0 if success else 2


if __name__ == '__main__':
    raise SystemExit(main())
