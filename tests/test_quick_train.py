"""End-to-end checks for training on the embedded engineering fixture."""
from argparse import Namespace
import json
from pathlib import Path
import sys

import pytest

torch = pytest.importorskip('torch')
pytest.importorskip('gymnasium')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from learning_demo import load_policy, model_class, run_rollout
from learning_smoke import load_engineering_train
from quick_train import CONSTRUCTOR, train


def test_quick_train_updates_weights_and_exports_loadable_policy(tmp_path):
    fixture = ROOT / 'examples/quick_train/families/demo_family_train_000'
    torch.manual_seed(1234)
    initial = model_class('AM-EVRPTW')(**CONSTRUCTOR)
    summary = train(Namespace(steps=3, threads=1, learning_rate=1e-4, seed=1234,
        family_dir=fixture, view_id='demo_train_000', output_dir=tmp_path / 'run'))
    assert summary['optimizer_steps'] == 3
    rows = [json.loads(line) for line in (tmp_path / 'run/loss.jsonl').read_text().splitlines()]
    assert [r['optimizer_step'] for r in rows] == [1, 2, 3]
    assert all(r['parameter_tensors_changed'] > 0 and r['parameter_update_l2'] > 0 for r in rows)
    policy, payload = load_policy(tmp_path / 'run/demo_checkpoint.pt')
    assert payload['epoch'] is None
    assert payload['training_regime'] == 'demo/train'
    assert payload['scope'] == 'quick_training_demo'
    assert payload['resumable'] is False
    initial_parameters = dict(initial.named_parameters())
    assert any(not torch.equal(value, initial_parameters[name]) for name, value in policy.named_parameters())
    instance = load_engineering_train(fixture, 'demo_train_000')
    info, _ = run_rollout(policy, payload, instance, candidates=4, seed=1234, max_steps=44)
    assert len(info['routes']) == 4
    assert any(info['success'])


def test_quick_train_rejects_benchmark_view_before_creating_outputs(tmp_path):
    with pytest.raises(ValueError, match='never benchmark test views'):
        train(Namespace(steps=3, threads=1, learning_rate=1e-4, seed=1234,
            family_dir=ROOT / 'examples/quick_train/families/demo_family_train_000',
            view_id='iv_4073f1928fa0c95f3de64257', output_dir=tmp_path / 'forbidden'))
    assert not (tmp_path / 'forbidden').exists()
