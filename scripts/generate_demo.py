#!/usr/bin/env python3
"""Generate new engineering views with production Stage-2 numerical modules."""
from __future__ import annotations
import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import multiprocessing as mp
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
for sub in ('EVRPTW_Dataset_Generator/src', 'EVRPTW_Core'):
    sys.path.insert(0, str(ROOT / sub))
import numpy as np
import pandas as pd
from evrptw_stage2.artifacts import load_materialized_view, verify_materialized_family
from evrptw_stage2.materialize import view_parent_terminal_indices
from evrptw_stage2.orders import (FULL_CS_TO_DEPOT_CACHE_CONTRACT,
    match_amazon_order_templates, build_view_attributes_from_amazon)
from evrptw_stage2.planning import derive_seed
from evrptw_stage2.road_state import build_family_road_state
from evrptw_stage2.routing import PhysicalRoadNetwork

MATRIX_NAMES = ('distance_matrix_km', 'distance_path_travel_time_s',
                'running_time_shortest_matrix_s', 'running_time_path_distance_km')


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')


def scientific_digest(payload):
    """Hash stable IDs, resources and exact array bytes; exclude measured timings."""
    h = hashlib.sha256()
    def update(value):
        if isinstance(value, np.ndarray):
            h.update(str(value.dtype).encode()); h.update(str(value.shape).encode())
            h.update(json.dumps(value.tolist(), sort_keys=True).encode() if value.dtype.kind in 'OUS'
                     else np.ascontiguousarray(value).tobytes())
        elif isinstance(value, dict):
            for key in sorted(value):
                h.update(key.encode()); update(value[key])
        else:
            h.update(json.dumps(value, sort_keys=True).encode())
    update(payload)
    return h.hexdigest()


def generate_family(task):
    fixture, profile_path, output, config, split, ordinal = task
    fixture, output = Path(fixture), Path(output)
    profile = json.loads(Path(profile_path).read_text())
    prefix = config.get('id_prefix', 'demo')
    city_slug = config.get('city_slug', 'fort-worth')
    day_type = config.get('day_type', 'weekday')
    family_id = f'{prefix}_family_{split}_{ordinal:03d}'
    seed = derive_seed(config['master_seed'], 'anonymous_review_generation', split, ordinal)
    family_dir = output / 'families' / family_id
    if family_dir.exists():
        raise FileExistsError(f'Refusing to overwrite {family_id}')
    pool = pd.read_parquet(fixture / 'terminal_pool.parquet')
    customers = pool.loc[pool.terminal_kind.eq('customer')].copy()
    customers['_rank'] = customers.source_id.map(
        lambda value: derive_seed(seed, 'customer', str(value)))
    customers = customers.sort_values(['_rank', 'source_id']).head(config['customers']).drop(columns='_rank')
    chargers = pool.loc[pool.terminal_kind.eq('charging_station')].copy()
    chargers['_rank'] = chargers.source_id.map(lambda value: derive_seed(seed, 'charger', str(value)))
    chargers = chargers.sort_values(['_rank', 'source_id']).head(config['stations']).drop(columns='_rank')
    terminals = pd.concat([pool.loc[pool.terminal_kind.eq('depot')], customers, chargers], ignore_index=True)
    terminals['terminal_index'] = np.arange(len(terminals), dtype=np.int32)
    state, state_report = build_family_road_state(
        pd.read_parquet(fixture / 'directed_speeds.parquet'), day_type=day_type,
        road_state_seed=derive_seed(seed, 'road_state'), profile=profile)
    network = PhysicalRoadNetwork.from_files(fixture / 'road.graphml', state, profile)
    matrices = network.route_terminals(terminals)
    source_templates = pd.read_parquet(fixture / 'order_templates.parquet')
    source = {'order_source_mode': 'SINGLE_ORDER_DAY',
              'station_code': str(source_templates.station_code.iloc[0]),
              'station_day_ids': source_templates.station_day_id.unique().tolist()}
    parent_power = chargers.effective_charging_power_kw.to_numpy(dtype=np.float32)
    matched, order_report = match_amazon_order_templates(
        customer_count=len(customers), order_sources=[(source, source_templates)], matching_seed=seed,
        operating_start_s=28800, operating_end_s=86400,
        running_time_matrix_s=matrices.running_time_shortest_matrix_s,
        running_time_path_distance_matrix_km=matrices.running_time_path_distance_km,
        charging_power_kw=parent_power, profile=profile)
    for key, col in [('order_template_id', 'template_id'), ('order_station_day_id', 'station_day_id')]:
        terminals[key] = ''
        terminals.loc[1:len(customers), key] = matched[col].astype(str).to_numpy()
    terminals['order_source_mode'] = ''
    terminals.loc[1:len(customers), 'order_source_mode'] = 'SINGLE_ORDER_DAY'
    family_dir.mkdir(parents=True)
    terminals.to_parquet(family_dir / 'terminal_index.parquet', index=False)
    (family_dir / 'matrices').mkdir()
    matrix_files = {}
    for name in MATRIX_NAMES:
        rel = f'matrices/{name}.npy'
        np.save(family_dir / rel, getattr(matrices, name).astype(np.float32), allow_pickle=False)
        matrix_files[name] = rel
    vehicle = dict(profile['vehicle'])
    vehicle.update(battery_capacity_kwh=profile['energy']['battery_capacity_kwh'],
                   specific_energy_consumption_kwh_per_km=profile['energy']['specific_energy_consumption_kwh_per_km'])
    view_ids = []
    for child in ((False, True) if config.get('emit_nested', True) else (False,)):
        count = len(customers) // 2 if child else len(customers)
        station_count = 1 if child else len(chargers)
        view_id = f'{prefix}_{split}_{ordinal:03d}' + ('_nested' if child else '')
        view_ids.append(view_id)
        indices = view_parent_terminal_indices(
            {'customer_count': count, 'charging_station_count': station_count, 'branch_index': 0,
             'scale_id': f'demo_cus{count}', 'view_seed': derive_seed(seed, 'view', child)},
            parent_customer_count=len(customers), parent_charging_station_count=len(chargers),
            running_time_matrix_s=matrices.running_time_shortest_matrix_s)
        view_terms = terminals.iloc[indices].reset_index(drop=True)
        power = view_terms.iloc[1 + count:].effective_charging_power_kw.to_numpy(dtype=np.float32)
        attributes = build_view_attributes_from_amazon(
            view_terms.iloc[1:1 + count], matched.iloc[indices[1:1 + count] - 1].reset_index(drop=True),
            day_type=day_type, operating_start_s=28800, operating_end_s=86400,
            running_time_matrix_s=matrices.running_time_shortest_matrix_s[np.ix_(indices, indices)],
            running_time_path_distance_matrix_km=matrices.running_time_path_distance_km[np.ix_(indices, indices)],
            charging_power_kw=power, profile=profile, order_source_report=order_report)
        dest = family_dir / 'views' / view_id; dest.mkdir(parents=True)
        np.save(dest / 'terminal_parent_indices.npy', indices, allow_pickle=False)
        np.savez_compressed(dest / 'customer_attributes.npz', **{
            k: v for k, v in vars(attributes).items() if k not in ('report', 'full_cs_to_depot_time_s')})
        np.savez_compressed(dest / 'charging_attributes.npz', charging_power_kw=power,
                            full_cs_to_depot_time_s=attributes.full_cs_to_depot_time_s)
        write_json(dest / 'view_manifest.json', {
            'schema': 'cle_evrptw_materialized_view_v4', 'view_id': view_id, 'family_id': family_id,
            'consumer_cohort_id': f'demo/{split}', 'split_id': f'demo/{split}', 'track_id': 'demo',
            'city_slug': city_slug, 'scale_id': f'demo_cus{count}', 'day_type': day_type,
            'customer_count': count, 'charging_station_count': station_count,
            'operating_horizon_s': [28800, 86400], 'matrix_storage': 'parent_index_view',
            'parent_matrix_files': matrix_files, 'terminal_parent_indices': 'terminal_parent_indices.npy',
            'customer_attributes': 'customer_attributes.npz', 'charging_attributes': 'charging_attributes.npz',
            'full_cs_to_depot_cache': FULL_CS_TO_DEPOT_CACHE_CONTRACT,
            'vehicle': vehicle, 'energy_model': profile['energy'], 'charging_policy': profile['charging'],
            'attribute_report': attributes.report, 'generation_mode': 'non_release_pilot',
            'non_release_pilot': True, 'scope': 'engineering_demo_not_benchmark_cohort',
            'charger_selection': {'parent_terminal_indices': indices[1 + count:].tolist(),
                                  'policy': 'production_road_time_child_roster_reselection'},
            'order_template_ids_inherited_from_parent': True})
    write_json(family_dir / 'family_manifest.json', {
        'schema': 'cle_evrptw_materialized_matrix_family_v3',
        'stage2_generation_contract': 'review_engineering_subset_v1',
        'family_id': family_id, 'family_cohort_id': f'demo/{split}', 'city_slug': city_slug,
        'parent_customer_count': len(customers), 'parent_charging_station_count': len(chargers),
        'terminal_count': len(terminals), 'terminal_index': 'terminal_index.parquet',
        'matrix_files': matrix_files, 'matrix_total_bytes': sum((family_dir / p).stat().st_size for p in matrix_files.values()),
        'view_ids': view_ids, 'view_count': len(view_ids), 'reference_profile_id': profile['profile_id'],
        'reference_profile_status': profile['profile_status'], 'energy_model': profile['energy'],
        'vehicle': vehicle, 'charging_policy': profile['charging'], 'non_release_pilot': True,
        'materialization_status': 'complete', 'family_seed': seed, 'road_state_report': state_report,
        'routing_report': matrices.report, 'scope': 'engineering_demo_not_benchmark_cohort',
        'skipped_full_pipeline_operations': ['whole-city CBG split construction',
            'Amazon spatial structure matching and joint support gates', 'region-first family selection',
            'official cohort plan and Phase-1 statistical acceptance'],
        'demo_selection': 'stable seeded hash of a fixed nearby eligible CLE terminal pool'})
    verification = verify_materialized_family(family_dir)
    if not verification['passed']:
        raise ValueError(json.dumps(verification))
    write_json(family_dir / 'verification.json', verification)
    return {'family_id': family_id, 'verification': verification,
            'scientific_sha256': {v: scientific_digest(load_materialized_view(family_dir, v)) for v in view_ids}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', type=Path, default=ROOT.parent / 'review-core/generation/fixture')
    parser.add_argument('--config', type=Path, default=ROOT / 'configs/demo/generation.json')
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--workers', type=int, choices=(1, 2), default=1)
    parser.add_argument('--split', choices=('train', 'demo'), default='demo')
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    fixture_manifest = json.loads((args.fixture / 'fixture_manifest.json').read_text())
    for filename, expected in fixture_manifest['files'].items():
        if hashlib.sha256((args.fixture / filename).read_bytes()).hexdigest() != expected:
            raise ValueError(f'Fixture checksum mismatch: {filename}')
    profile_path = args.config.parent / config['profile']
    tasks = [(str(args.fixture.resolve()), str(profile_path.resolve()), str(args.output_dir.resolve()),
              config, args.split, i) for i in range(config['families'])]
    started = time.perf_counter()
    if args.workers == 1:
        rows = [generate_family(t) for t in tasks]
    else:
        with ProcessPoolExecutor(max_workers=args.workers, mp_context=mp.get_context('spawn')) as executor:
            rows = list(executor.map(generate_family, tasks))
    report = {'schema': 'evrptw_generation_demo_report_v1', 'status': 'PASS',
              'scope': f'demo/{args.split}', 'workers': args.workers,
              'wall_time_s': time.perf_counter() - started, 'families': rows,
              'stage1_mini': 'NOT RUN', 'full_cohort_generation': 'NOT RUN',
              'fixture_artifact_id': fixture_manifest['artifact_id']}
    write_json(args.output_dir / 'generation_report.json', report)
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
