"""Meaningful entry-point checks without network acquisition or a city-scale build."""
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('review_generate_tests', ROOT / 'scripts/review_generate.py')
entry = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(entry)


def invoke(*arguments, env=None):
    environment = dict(os.environ)
    environment['PYTHON'] = sys.executable
    if env:
        environment.update(env)
    return subprocess.run(['bash', str(ROOT / 'generate.sh'), *map(str, arguments)],
                          cwd=ROOT, env=environment, text=True, capture_output=True)


def test_dry_run_does_not_need_credentials_or_write_directories(tmp_path):
    output, cache = tmp_path / 'not created output', tmp_path / 'not created cache'
    sentinel = 'TEST_CREDENTIAL_DO_NOT_PRINT'
    result = invoke('--dry-run', '--count', '3', '--seed', '0', '--output', output, '--cache-dir', cache,
                    env={'NLR_API_KEY': sentinel, 'NREL_API_KEY': ''})
    assert result.returncode == 0, result.stderr
    plan = json.loads(result.stdout)
    assert plan['network_requests'] == plan['files_written'] == 0
    assert plan['count'] == 3 and plan['seed'] == 0
    assert plan['stage1'] == 'production generate_us_city_cle.py'
    assert sentinel not in result.stdout + result.stderr
    assert not output.exists() and not cache.exists()
    assert all('api_key=' not in str(url) for url in plan['source_urls'].values())


@pytest.mark.parametrize('argument,value', [('--count', '0'), ('--scale', '0'), ('--workers', '0'),
                                           ('--seed', '-1'), ('--seed', '4294967296')])
def test_invalid_bounds_fail_before_generation(argument, value, tmp_path):
    result = invoke(argument, value, '--output', tmp_path / 'invalid')
    assert result.returncode != 0
    assert not (tmp_path / 'invalid').exists()


def test_exact_count_and_determinism_on_real_cached_roads(tmp_path):
    fixture = ROOT / 'examples/generation/fixture'
    assert fixture.is_dir(), 'Bundled real-road fixture is required for this entry check'
    indices = []
    for workers in (1, 2):
        output = tmp_path / f'generated with {workers} workers'
        result = invoke('--cached-fixture', fixture, '--scale', '8', '--count', '3',
                        '--workers', workers, '--output', output)
        assert result.returncode == 0, result.stderr
        rows = [json.loads(line) for line in (output / 'instances.jsonl').read_text().splitlines()]
        indices.append(rows)
        assert len(rows) == 3
        assert len(list(output.glob('families/*/views/*/view_manifest.json'))) == 3
        report = json.loads((output / 'generation_report.json').read_text())
        assert report['status'] == 'PASS' and report['completed_count'] == 3
        assert report['stage1'].startswith('NOT RUN') and report['stage2'] == 'PASS'
        assert report['source_cle_release_blockers']
        for row in rows:
            manifest = json.loads((output / row['view_manifest']).read_text())
            assert manifest['customer_count'] == 8
            assert manifest['scope'] == 'engineering_sample_not_benchmark_cohort'
            assert manifest['source_cle_release_blockers'] == report['source_cle_release_blockers']
    assert indices[0] == indices[1]


def test_smallest_scale_and_largest_seed_are_supported(tmp_path):
    result = invoke('--cached-fixture', ROOT / 'examples/generation/fixture', '--scale', '1',
                    '--count', '1', '--seed', '4294967295', '--output', tmp_path / 'one')
    assert result.returncode == 0, result.stderr
    rows = (tmp_path / 'one/instances.jsonl').read_text().splitlines()
    assert len(rows) == 1 and json.loads(rows[0])['customer_count'] == 1


def test_oversized_fixture_request_fails_without_hidden_fallback(tmp_path):
    output = tmp_path / 'too large'
    result = invoke('--cached-fixture', ROOT / 'examples/generation/fixture', '--scale', '100', '--output', output)
    assert result.returncode != 0
    report = json.loads((output / 'generation_report.json').read_text())
    assert report['status'] == 'FAIL' and report['stage2'] == 'NOT RUN'
    assert 'cannot supply' in report['error']
    assert not (output / 'instances.jsonl').exists()


def test_existing_output_is_not_overwritten(tmp_path):
    output = tmp_path / 'existing'
    output.mkdir()
    (output / 'sentinel').write_text('preserve me')
    result = invoke('--cached-fixture', ROOT / 'examples/generation/fixture', '--scale', '8', '--output', output)
    assert result.returncode != 0 and 'already exists' in result.stderr
    assert list(output.iterdir()) == [output / 'sentinel']


def test_public_download_is_atomic_checksummed_and_reusable(monkeypatch, tmp_path):
    body = b'{"small_public_fixture": true}'
    class Response(io.BytesIO):
        headers = {'Content-Length': str(len(body))}
    calls = []
    def fetch(request, timeout):
        calls.append(request.full_url)
        return Response(body)
    monkeypatch.setattr(entry.urllib.request, 'urlopen', fetch)
    destination = tmp_path / 'cache with spaces' / 'input.json'
    entry.download('https://example.invalid/public/input.json', destination)
    entry.download('https://example.invalid/public/input.json', destination)
    assert destination.read_bytes() == body and len(calls) == 1
    assert json.loads(destination.with_suffix('.json.download.json').read_text())['sha256'] == entry.digest(destination)
    destination.write_bytes(b'corrupt')
    with pytest.raises(ValueError, match='does not match'):
        entry.download('https://example.invalid/public/input.json', destination)


def test_truncated_download_never_publishes_partial_source(monkeypatch, tmp_path):
    class Response(io.BytesIO):
        headers = {'Content-Length': '1000'}
    monkeypatch.setattr(entry.urllib.request, 'urlopen', lambda *args, **kwargs: Response(b'short'))
    destination = tmp_path / 'input.json'
    with pytest.raises(ValueError, match='Truncated'):
        entry.download('https://example.invalid/public/input.json', destination)
    assert list(tmp_path.iterdir()) == []


def test_stage1_afdc_key_is_environment_only(monkeypatch, tmp_path, capsys):
    # Isolate acquisition orchestration from optional geographic imports/network;
    # exercise the actual production _download_sources implementation.
    for name, function in [('download_hpms_city', 'download_hpms_city'),
                           ('download_microsoft_state_buildings', 'download_state_buildings'),
                           ('prepare_us_city', 'prepare_us_city')]:
        monkeypatch.setitem(sys.modules, name, SimpleNamespace(**{function: lambda **kwargs: None}))
    spec = importlib.util.spec_from_file_location('stage1_acquisition_tests', ROOT / 'EVRPTW_Dataset_Generator/scripts/generate_us_city_cle.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    existing = tmp_path / 'existing_evidence.csv'
    existing.write_text('preexisting evidence')
    contract = {'sources': {
        'microsoft_buildings': {'state_file': 'State.geojson', 'path': str(tmp_path / 'State.geojson'), 'url': 'https://example.invalid/buildings'},
        'pbf': {'path': str(tmp_path / 'roads.pbf')},
        'hpms': {'service_url': 'https://example.invalid/hpms', 'path': str(tmp_path / 'hpms.geojson')},
        'afdc': {'path': str(tmp_path / 'missing_afdc.csv'), 'osm_charging_pois_path': str(existing),
                 'census_address_anchors_path': str(existing), 'resolved_path': str(existing)}},
        'configs': {'preset': str(tmp_path / 'preset.json')}, 'custom_root': str(tmp_path),
        'boundaries': {'land': str(tmp_path / 'land.geojson')},
        'city': {'slug': 'test-city', 'state': {'abbr': 'TX'}}}
    calls = []
    monkeypatch.setattr(module.subprocess, 'run', lambda command, **kwargs: calls.append((command, kwargs)))
    credential = 'TEST_SECRET_NEVER_IN_ARGV'
    module._download_sources(contract=contract, generator_root=ROOT, api_key=credential, force=False)
    afdc = [(argv, kwargs) for argv, kwargs in calls if 'scripts/download_afdc_snapshot.py' in argv]
    assert len(afdc) == 1
    assert afdc[0][1]['env']['NLR_API_KEY'] == credential
    assert all(credential not in str(argv) for argv, _ in calls)
    assert credential not in capsys.readouterr().out


def test_same_city_in_different_states_uses_separate_stage1_caches(monkeypatch, tmp_path):
    monkeypatch.setattr(entry.importlib.util, 'find_spec', lambda name: object())
    monkeypatch.setattr(entry.shutil, 'which', lambda name: '/installed/osmium')
    monkeypatch.setenv('NLR_API_KEY', 'TEST_KEY_ENV_ONLY')
    monkeypatch.setattr(entry, 'download', lambda *args: None)
    commands = []
    monkeypatch.setattr(entry, 'run', lambda command: commands.append(list(map(str, command))))
    for state in ('OR', 'ME'):
        args = entry.parser().parse_args(['--city', 'Portland', '--state', state,
                  '--cache-dir', str(tmp_path / 'shared cache'), '--output', str(tmp_path / state)])
        entry.prepare_online_inputs(args, 'portland', {})
    stage1 = [command for command in commands if any(v.endswith('generate_us_city_cle.py') for v in command)]
    assert len(stage1) == 2
    for flag in ('--source-root', '--custom-root', '--release-root'):
        values = [command[command.index(flag)+1] for command in stage1]
        assert values[0] != values[1]
        assert '/or' in values[0] and '/me' in values[1]
    assert 'TEST_KEY_ENV_ONLY' not in str(commands)


def test_online_failure_stays_failure_without_cached_fallback(monkeypatch, tmp_path):
    args = entry.parser().parse_args(['--output', str(tmp_path / 'failed')])
    args.stations = 20
    monkeypatch.setenv('NLR_API_KEY', 'PRIVATE_TEST_KEY')
    def fail(*unused):
        raise RuntimeError('Provider unavailable: PRIVATE_TEST_KEY')
    monkeypatch.setattr(entry, 'prepare_online_inputs', fail)
    with pytest.raises(RuntimeError, match=r'Provider unavailable: \[REDACTED\]'):
        entry.generate(args, 'fort-worth', {})
    report = json.loads((args.output / 'generation_report.json').read_text())
    assert report['status'] == 'FAIL'
    assert report['stage1'] == report['stage2'] == 'NOT RUN'
    assert 'PRIVATE_TEST_KEY' not in (args.output / 'generation_report.json').read_text()
    assert not (args.output / 'instances.jsonl').exists()
