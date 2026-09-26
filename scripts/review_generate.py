#!/usr/bin/env python3
"""Download public inputs, build a CLE, and generate a requested road-instance sample.

This is an independent engineering sample, not the frozen 11-city paper cohort.
The official Stage-2 plan, C3, Git provenance and approval rules remain unchanged.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import multiprocessing as mp
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / 'EVRPTW_Dataset_Generator'
AMAZON_ROOT = 'https://amazon-last-mile-challenges.s3.us-west-2.amazonaws.com/almrrc2021'
AMAZON_INPUTS = 'almrrc2021-data-training/model_build_inputs'
AMAZON_FILES = ('route_data.json', 'package_data.json', 'travel_times.json')
SKIPPED = ['official cohort plan and fixed split counts', 'whole-city CBG splits',
           'Amazon spatial structure matching and C3 joint-support gates',
           'region-first family selection', 'official Phase-1 statistical acceptance']


def positive(value):
    value = int(value)
    if value <= 0:
        raise argparse.ArgumentTypeError('must be a positive integer')
    return value


def seed_value(value):
    value = int(value)
    if not 0 <= value <= 2**32 - 1:
        raise argparse.ArgumentTypeError('seed must satisfy 0 <= seed <= 4294967295')
    return value


def parser():
    result = argparse.ArgumentParser(description=__doc__, epilog=(
        'A new online city build can download state-scale data and take substantial time. '
        'Use --dry-run to inspect the exact scope. --cached-fixture is an explicit '
        'offline Stage-2 test and never claims to run Stage 1.'))
    result.add_argument('--city', default='Fort Worth', help='U.S. Census Place name')
    result.add_argument('--state', default='TX', help='State abbreviation, name, or FIPS')
    result.add_argument('--count', type=positive, default=2, help='Exact number of output instances (default: 2)')
    result.add_argument('--scale', type=positive, default=100, help='Customers per instance, 1..2000 (default: 100)')
    result.add_argument('--seed', type=seed_value, default=1234)
    result.add_argument('--output', type=Path, default=Path('outputs/generated'), help='New output directory')
    result.add_argument('--cache-dir', type=Path, default=ROOT.parent / 'generation-cache', help='Reusable source/CLE cache')
    result.add_argument('--workers', type=positive, default=1, help='Family workers; also NSI download workers')
    result.add_argument('--stations', type=positive, help='Override station count; defaults: 20 at scale 100, 50 above 100')
    result.add_argument('--cached-fixture', type=Path, help='Explicit offline cached-CLE fixture; e.g. examples/generation/fixture with --scale 8')
    result.add_argument('--dry-run', action='store_true', help='Print stages and source URLs; no network, files or key required')
    return result


def digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + '\n')


def download(url, path):
    """Stream public S3 objects atomically; reuse only intact recorded downloads."""
    path = Path(path)
    manifest_path = path.with_suffix(path.suffix + '.download.json')
    if path.is_file() and manifest_path.is_file():
        old = json.loads(manifest_path.read_text())
        if old.get('url') != url or old.get('sha256') != digest(path):
            raise ValueError(f'Cached source does not match its download manifest: {path}')
        print(f'REUSE {path}', flush=True)
        return
    if path.exists():
        raise FileExistsError(f'Untracked cached file cannot be assumed complete: {path}')
    print(f'DOWNLOAD {url}', flush=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'evrptw-db-source-acquisition/1.0'})
        with urllib.request.urlopen(request, timeout=600) as response:
            expected_bytes = response.headers.get('Content-Length')
            with tempfile.NamedTemporaryFile('wb', dir=path.parent, prefix='.'+path.name, delete=False) as stream:
                temporary = Path(stream.name)
                shutil.copyfileobj(response, stream, length=1024*1024)
        if not temporary.stat().st_size:
            raise ValueError(f'Empty source response: {url}')
        if expected_bytes is not None and temporary.stat().st_size != int(expected_bytes):
            raise ValueError(f'Truncated source response: {url}')
        temporary.replace(path)
        write_json(manifest_path, {'url': url, 'sha256': digest(path), 'bytes': path.stat().st_size,
                                  'downloaded_utc': datetime.now(timezone.utc).isoformat()})
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def source_plan(args):
    states = json.loads((GENERATOR / 'configs/us_states_v1.json').read_text())['states']
    value = args.state.strip().casefold()
    state = [r for r in states if value in {str(r['name']).casefold(), str(r['abbr']).casefold(), str(r['fips'])}]
    if len(state) != 1:
        raise ValueError(f'Unrecognized U.S. state: {args.state}')
    state = state[0]
    slug = re.sub('[^a-z0-9]+', '-', args.city.casefold()).strip('-')
    if not slug:
        raise ValueError('city must contain letters or numbers')
    urls = {
        'census_places': f"https://www2.census.gov/geo/tiger/TIGER2025/PLACE/tl_2025_{state['fips']}_place.zip",
        'census_counties': 'https://www2.census.gov/geo/tiger/TIGER2025/COUNTY/tl_2025_us_county.zip',
        'census_areawater': 'https://www2.census.gov/geo/tiger/TIGER2025/AREAWATER/ (intersecting counties resolved during Stage 1)',
        'osm': f"https://download.geofabrik.de/north-america/us/{state['geofabrik_slug']}-latest.osm.pbf",
        'microsoft_buildings': f"https://minedbuildings.z5.web.core.windows.net/legacy/usbuildings-v2/{state['microsoft_file']}.zip",
        'hpms': f"https://geo.dot.gov/server/rest/services/Hosted/{state['hpms_service_token']}_2018_PR/FeatureServer",
        'afdc': 'https://developer.nlr.gov/api/alt-fuel-stations/v1.csv',
        'nsi': 'https://nsi.sec.usace.army.mil/nsiapi/structures',
        'census_geocoder': 'https://geocoding.geo.census.gov/geocoder/locations/addressbatch',
        'amazon': [f'{AMAZON_ROOT}/{AMAZON_INPUTS}/{name}' for name in AMAZON_FILES]
                  + [f'{AMAZON_ROOT}/License.txt', f'{AMAZON_ROOT}/Readme.txt'],
        'moves': 'bundled configs/us_moves5_speed_profile_v1.json (no simulator download)',
    }
    return slug, state, urls


def run(command):
    # API credentials are inherited only through the environment, never argv.
    print('RUN ' + shlex.join([str(v) for v in command]), flush=True)
    env = dict(os.environ)
    env['PYTHONPATH'] = os.pathsep.join([str(GENERATOR / 'src'), str(ROOT / 'EVRPTW_Core'), env.get('PYTHONPATH', '')])
    subprocess.run([str(v) for v in command], check=True, cwd=ROOT, env=env)


def prepare_online_inputs(args, slug, report):
    needed = ['geopandas', 'osmnx', 'shapely', 'folium', 'matplotlib', 'pyogrio', 'requests']
    missing = [name for name in needed if importlib.util.find_spec(name) is None]
    if missing:
        raise RuntimeError('Install generator dependencies first: python -m pip install -e ".[geographic]"; missing ' + ', '.join(missing))
    if shutil.which('osmium') is None:
        raise RuntimeError('Stage 1 needs osmium-tool on PATH: conda install -c conda-forge osmium-tool')
    cache = args.cache_dir.resolve()
    state_code = source_plan(args)[1]['abbr'].lower()
    city_cache = cache / 'cities' / state_code / slug
    source_cache = cache / 'sources' / state_code
    afdc = source_cache / 'afdc/afdc_us_public_available_electric.csv'
    if not afdc.is_file() and not (os.environ.get('NLR_API_KEY') or os.environ.get('NREL_API_KEY')):
        raise RuntimeError('Export NLR_API_KEY before downloading AFDC (legacy NREL_API_KEY accepted). --dry-run needs no key.')
    cle_root = cache / 'CLE_v2' / state_code / slug
    report['active_stage'] = 'stage1'
    write_json(args.output / 'generation_report.json', report)
    run([sys.executable, GENERATOR / 'scripts/generate_us_city_cle.py',
         '--city', args.city, '--state', args.state, '--city-slug', slug,
         '--custom-root', city_cache, '--source-root', source_cache,
         '--release-root', cle_root, '--nsi-workers', args.workers])
    report['stage1'] = 'PASS'
    report['active_stage'] = 'amazon_sources'
    write_json(args.output / 'generation_report.json', report)
    amazon_root = cache / 'sources/amazon-last-mile-2021'
    for name in AMAZON_FILES:
        download(f'{AMAZON_ROOT}/{AMAZON_INPUTS}/{name}', amazon_root / 'model_build_inputs' / name)
    for name in ('License.txt', 'Readme.txt'):
        download(f'{AMAZON_ROOT}/{name}', amazon_root / name)
    artifact_root = cache / 'amazon-stage2-artifacts'
    if not (artifact_root / 'manifest.json').is_file():
        run([sys.executable, GENERATOR / 'scripts/build_amazon_stage2_artifacts.py',
             '--model-build-inputs', amazon_root / 'model_build_inputs', '--output-dir', artifact_root])
    report['amazon_artifacts'] = 'PASS'
    return cle_root, artifact_root


def prepare_engineering_fixture(cle_root, artifact_root, args, slug, profile, output):
    """Use the strict Stage-1 reader; select a bounded eligible terminal pool."""
    import numpy as np
    import pandas as pd
    from evrptw_stage2.amazon import load_amazon_stage2_artifacts
    from evrptw_stage2.reader import load_portable_cle
    from evrptw_stage2.selection import _common_terminal_record, _resolve_charging_power
    cle = load_portable_cle(cle_root, slug, mode='non_release_pilot',
                            minimum_customers=args.scale, minimum_chargers=args.stations)
    depots = cle.read_depots().sort_values('candidate_id')
    depot = depots.iloc[0]
    def nearest(frame, longitude, latitude, count, source_id):
        frame = frame.copy()
        frame['_distance'] = ((frame[longitude] - depot.longitude)**2 * np.cos(np.deg2rad(depot.latitude))**2
                              + (frame[latitude] - depot.latitude)**2)
        return frame.sort_values(['_distance', source_id], kind='stable').head(count).drop(columns='_distance')
    customers = nearest(cle.read_service_locations(), 'location_lon', 'location_lat',
                        max(args.scale*4, 48), 'latent_service_location_id')
    chargers = nearest(cle.read_chargers(), 'resolved_longitude', 'resolved_latitude',
                       max(args.stations*2, args.stations), 'charger_id')
    chargers, _ = _resolve_charging_power(chargers, profile=profile, generation_mode='non_release_pilot')
    records = [_common_terminal_record(depot, terminal_index=0, terminal_kind='depot',
               source_id=str(depot.candidate_id), longitude=depot.longitude, latitude=depot.latitude)]
    for _, row in customers.iterrows():
        records.append(_common_terminal_record(row, terminal_index=len(records), terminal_kind='customer',
                       source_id=str(row.latent_service_location_id), longitude=row.location_lon, latitude=row.location_lat))
    for _, row in chargers.iterrows():
        record = _common_terminal_record(row, terminal_index=len(records), terminal_kind='charging_station',
                                         source_id=str(row.charger_id), longitude=row.resolved_longitude, latitude=row.resolved_latitude)
        record['effective_charging_power_kw'] = float(row.effective_charging_power_kw)
        records.append(record)
    output.mkdir(parents=True)
    pd.DataFrame(records).to_parquet(output / 'terminal_pool.parquet', index=False)
    for source, name in ((cle.graph_path, 'road.graphml'), (cle.speeds_path, 'directed_speeds.parquet')):
        # Family artifacts remain portable; these provenance inputs reuse the explicit cache.
        (output / name).symlink_to(source.resolve())
    amazon = load_amazon_stage2_artifacts(artifact_root,
              cohort_split_path=GENERATOR / 'configs/amazon_cohort_split_v1.json')
    train_days = amazon.station_day_ids_for_track('train')
    templates = amazon.templates.loc[amazon.templates.station_day_id.isin(train_days)
                                     & amazon.templates.day_type.eq('weekday')]
    counts = templates.groupby('station_day_id').size()
    eligible_days = sorted(counts.loc[counts >= args.scale].index.tolist())
    if not eligible_days:
        raise ValueError('No training-pool Amazon weekday has enough templates for this scale')
    # The seed selects a real source day; no evaluation/metric-holdout day is consumed.
    day = eligible_days[args.seed % len(eligible_days)]
    templates.loc[templates.station_day_id.eq(day)].sort_values('template_id').to_parquet(output / 'order_templates.parquet', index=False)
    files = {name: digest(output / name) for name in ('terminal_pool.parquet', 'road.graphml', 'directed_speeds.parquet', 'order_templates.parquet')}
    manifest = {'schema': 'evrptw_demo_cached_cle_v1', 'artifact_id': 'generated_engineering_inputs_' + slug,
                'city_slug': slug, 'scope': 'engineering_sample_not_benchmark_cohort',
                'terminal_pool': {'depot': 1, 'customer': len(customers), 'charging_station': len(chargers)},
                'source_day': day, 'day_type': 'weekday', 'files': files,
                'road': {'clipping': 'none; complete Stage-1 operational road graph'},
                'source_cle_release_blockers': list(cle.release_blockers),
                'manual_cle_release_claimed': False, 'source_cle_eligibility': cle.eligibility_summary(),
                'source_cle_manifest_sha256': digest(cle.root / 'manifest.json'),
                'selection': 'first eligible depot by source ID; nearest eligible pools then seeded family sampling'}
    write_json(output / 'fixture_manifest.json', manifest)
    return output


def validate_fixture(path, scale, stations):
    import pandas as pd
    path = Path(path).resolve()
    manifest = json.loads((path / 'fixture_manifest.json').read_text())
    if manifest.get('schema') != 'evrptw_demo_cached_cle_v1':
        raise ValueError('Unsupported cached fixture schema')
    for filename in ('terminal_pool.parquet', 'road.graphml', 'directed_speeds.parquet', 'order_templates.parquet'):
        if manifest.get('files', {}).get(filename) != digest(path / filename):
            raise ValueError(f'Fixture checksum mismatch: {filename}')
    pool = pd.read_parquet(path / 'terminal_pool.parquet')
    counts = pool.terminal_kind.value_counts()
    if int(counts.get('depot', 0)) != 1 or int(counts.get('customer', 0)) < scale or int(counts.get('charging_station', 0)) < stations:
        raise ValueError(f'Cached fixture cannot supply scale={scale}, stations={stations}; pools={counts.to_dict()}')
    if len(pd.read_parquet(path / 'order_templates.parquet')) < scale:
        raise ValueError('Cached fixture has fewer order templates than requested customers')
    return manifest


def generate(args, slug, urls):
    args.output = args.output.resolve()
    if args.output.exists():
        raise FileExistsError('Output directory already exists; choose a new --output')
    args.output.mkdir(parents=True)
    report = {'schema': 'review_generation_entry_v1', 'status': 'RUNNING', 'active_stage': 'input_validation',
              'scope': 'engineering_sample_not_benchmark_cohort', 'requested_count': args.count,
              'customer_count': args.scale, 'charging_station_count': args.stations, 'seed': args.seed,
              'workers': args.workers, 'stage1': 'NOT RUN', 'stage2': 'NOT RUN',
              'official_cohort_generation': 'NOT RUN', 'skipped_official_operations': SKIPPED,
              'source_urls': urls if args.cached_fixture is None else {},
              'code_sha256': {str(p.relative_to(ROOT)): digest(p) for p in [Path(__file__), ROOT / 'scripts/generate_demo.py',
                  GENERATOR / 'scripts/generate_us_city_cle.py', GENERATOR / 'scripts/prepare_us_city.py',
                  *[GENERATOR / 'src/evrptw_stage2' / (name + '.py') for name in
                    ('road_state', 'routing', 'orders', 'materialize', 'selection', 'artifacts')]]}}
    started = time.perf_counter()
    try:
        for directory in (GENERATOR / 'src', ROOT / 'EVRPTW_Core'):
            sys.path.insert(0, str(directory))
        profile = json.loads((ROOT / 'configs/demo/generation_profile.json').read_text())
        profile.update(profile_status='engineering_unapproved', official_generation_eligible=False)
        profile.pop('acceptance_promotion', None)
        profile_path = args.output / 'generation_profile.json'
        write_json(profile_path, profile)
        report['reference_profile_sha256'] = digest(profile_path)
        if args.cached_fixture is not None:
            fixture = args.cached_fixture.resolve()
            report['stage1'] = 'NOT RUN (explicit --cached-fixture)'
        else:
            cle_root, artifact_root = prepare_online_inputs(args, slug, report)
            report['active_stage'] = 'engineering_selection'
            fixture = prepare_engineering_fixture(cle_root, artifact_root, args, slug, profile, args.output / '_inputs')
        fixture_manifest = validate_fixture(fixture, args.scale, args.stations)
        actual_city = fixture_manifest['city_slug']
        run_key = hashlib.sha256(json.dumps({'city': actual_city, 'scale': args.scale, 'stations': args.stations,
                                             'seed': args.seed, 'sources': fixture_manifest['files']}, sort_keys=True).encode()).hexdigest()[:12]
        config = {'master_seed': args.seed, 'customers': args.scale, 'stations': args.stations,
                  'families': args.count, 'profile': 'generation_profile.json', 'city_slug': actual_city,
                  'emit_nested': False, 'id_prefix': 'generated_' + run_key, 'day_type': 'weekday',
                  'scope': 'engineering_sample_not_benchmark_cohort'}
        write_json(args.output / 'generation_config.json', config)
        report.update(active_stage='stage2', city_slug=actual_city,
                      source_cle_release_blockers=fixture_manifest.get('source_cle_release_blockers', []),
                      manual_cle_release_claimed=False, fixture_manifest_sha256=digest(fixture / 'fixture_manifest.json'))
        write_json(args.output / 'generation_report.json', report)
        from generate_demo import generate_family
        tasks = [(str(fixture), str(profile_path), str(args.output), config, 'sample', ordinal) for ordinal in range(args.count)]
        if args.workers == 1:
            families = [generate_family(task) for task in tasks]
        else:
            with ProcessPoolExecutor(max_workers=args.workers, mp_context=mp.get_context('spawn')) as executor:
                families = list(executor.map(generate_family, tasks))
        index = []
        for row in families:
            family = args.output / 'families' / row['family_id']
            metadata_files = [family / 'family_manifest.json'] + [
                family / 'views' / view_id / 'view_manifest.json' for view_id in row['scientific_sha256']]
            for metadata_path in metadata_files:
                metadata = json.loads(metadata_path.read_text())
                metadata.update(scope='engineering_sample_not_benchmark_cohort',
                                source_cle_release_blockers=report['source_cle_release_blockers'],
                                manual_cle_release_claimed=False,
                                fixture_manifest_sha256=report['fixture_manifest_sha256'])
                write_json(metadata_path, metadata)
            for view_id in row['scientific_sha256']:
                index.append({'instance_id': view_id, 'family_id': row['family_id'], 'city_slug': actual_city,
                              'customer_count': args.scale, 'charging_station_count': args.stations,
                              'view_manifest': str((family / 'views' / view_id / 'view_manifest.json').relative_to(args.output)),
                              'scientific_sha256': row['scientific_sha256'][view_id],
                              'scope': 'engineering_sample_not_benchmark_cohort'})
        if len(index) != args.count:
            raise RuntimeError(f'Expected exactly {args.count} instances, got {len(index)}')
        (args.output / 'instances.jsonl').write_text(''.join(json.dumps(row, sort_keys=True) + '\n' for row in index))
        report.update(status='PASS', active_stage='complete', stage2='PASS', completed_count=len(index),
                      instances_index='instances.jsonl', families=families, elapsed_s=time.perf_counter()-started)
        write_json(args.output / 'generation_report.json', report)
        print(json.dumps({key: report[key] for key in ('status', 'stage1', 'stage2', 'completed_count', 'city_slug', 'customer_count', 'scope')}, indent=2))
        print(f'Instances: {args.output / "instances.jsonl"}')
    except Exception as error:
        detail = str(error)
        for name in ('NLR_API_KEY', 'NREL_API_KEY'):
            key = os.environ.get(name)
            if key:
                detail = detail.replace(key, '[REDACTED]')
        report.update(status='FAIL', error_type=type(error).__name__, error=detail, elapsed_s=time.perf_counter()-started)
        write_json(args.output / 'generation_report.json', report)
        raise RuntimeError(f'Generation failed during {report["active_stage"]}: {detail}') from None


def main():
    command = parser()
    args = command.parse_args()
    if not 1 <= args.scale <= 2000:
        command.error('--scale must be between 1 and 2000')
    args.stations = args.stations or (50 if args.scale > 100 else 20 if args.scale == 100 else max(1, min(10, args.scale//4)))
    try:
        slug, state, urls = source_plan(args)
        if args.dry_run:
            print(json.dumps({'status': 'DRY RUN', 'network_requests': 0, 'files_written': 0,
                 'scope': 'engineering_sample_not_benchmark_cohort', 'city': args.city, 'state': state['abbr'],
                 'count': args.count, 'scale': args.scale, 'stations': args.stations, 'seed': args.seed,
                 'output': str(args.output.resolve()), 'cache': str(args.cache_dir.resolve()),
                 'stage1': 'NOT RUN (explicit cached fixture)' if args.cached_fixture else 'production generate_us_city_cle.py',
                 'stage2': 'production road-state/routing/order matching/attributes/independent certificates',
                 'cached_fixture': str(args.cached_fixture.resolve()) if args.cached_fixture else None,
                 'authentication': 'No key needed for this dry run; live AFDC download requires NLR_API_KEY',
                 'source_urls': {} if args.cached_fixture else urls, 'skipped_official_operations': SKIPPED}, indent=2))
            return
        generate(args, slug, urls)
    except (ValueError, RuntimeError, FileNotFoundError, FileExistsError) as error:
        command.exit(2, f'ERROR: {error}\n')


if __name__ == '__main__':
    main()
