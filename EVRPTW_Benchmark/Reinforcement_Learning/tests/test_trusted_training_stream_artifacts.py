from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
import yaml

from EVRPTW_Benchmark.Reinforcement_Learning.common.training_stream import (
    STREAM_CONTENT_DIGEST_SCHEME,
    STREAM_SCHEMA,
    training_stream_contract_digest,
    training_stream_manifest_digest,
)
from EVRPTW_Benchmark.Reinforcement_Learning.scripts import build_training_stream
from EVRPTW_Benchmark.Reinforcement_Learning.scripts.refresh_preverified_training_streams import (
    PREVERIFIED_INTEGRITY_MODE,
    _canonical_digest,
    refresh_preverified_streams,
)


def test_build_stream_can_reuse_declared_source_index_digest(
    tmp_path, monkeypatch, capsys
) -> None:
    declared = "a" * 64
    output = tmp_path / "stream.parquet"
    args = SimpleNamespace(
        index=tmp_path / "index.parquet",
        scale="Cus500",
        seed=1234,
        customer_exposures=500,
        allowed_family_ids=None,
        reuse_source_index_sha256=declared.upper(),
        output=output,
    )
    monkeypatch.setattr(build_training_stream, "parse_args", lambda: args)
    monkeypatch.setattr(build_training_stream.pd, "read_parquet", lambda _path: object())
    monkeypatch.setattr(
        build_training_stream,
        "build_training_stream",
        lambda *_args, **_kwargs: (pd.DataFrame(), {}),
    )
    captured = {}
    monkeypatch.setattr(
        build_training_stream,
        "atomic_write_stream",
        lambda path, stream, manifest: captured.update(
            path=path, stream=stream, manifest=dict(manifest)
        ),
    )
    monkeypatch.setattr(
        build_training_stream,
        "file_sha256",
        lambda _path: pytest.fail("declared source digest must avoid file_sha256"),
    )

    build_training_stream.main()

    assert captured["path"] == output
    assert captured["manifest"]["source_index_sha256"] == declared
    assert json.loads(capsys.readouterr().out)["source_index_sha256"] == declared


def test_selective_refresh_uses_sidecar_without_reading_parquet(tmp_path) -> None:
    repo = tmp_path / "repo"
    stream = repo / "artifacts/terran/Cus500/seed_1234.parquet"
    stream.parent.mkdir(parents=True)
    stream.write_bytes(b"must-not-be-read")
    sidecar = stream.with_suffix(".parquet.manifest.json")
    manifest = {
        "schema": STREAM_SCHEMA,
        "content_digest_scheme": STREAM_CONTENT_DIGEST_SCHEME,
        "stream_content_sha256": "b" * 64,
        "source_index_sha256": "c" * 64,
        "allowed_family_ids_sha256": None,
        "sample_count": 740000,
        "scale": "Cus500",
        "seed": 1234,
        "file_hash_validation_performed": True,
    }
    manifest["manifest_sha256"] = training_stream_manifest_digest(manifest)
    sidecar.write_text(json.dumps(manifest), encoding="utf-8")
    relative = stream.relative_to(repo).as_posix()

    marker = {
        "schema": "drl_rq_artifact_preparation_v2",
        "runtime_budget_id": "budget",
        "dataset_root": "/dataset",
        "file_hash_validation_performed": True,
        "training_stream_contracts": [
            {"relative_path": relative, "sha256": "old", "snapshot": {}}
        ],
    }
    marker["marker_sha256"] = _canonical_digest(
        marker, omitted={"marker_sha256", "dataset_root"}
    )
    registry = {
        "schema": "drl_training_stream_registry_v1",
        "runtime_budget_id": "budget",
        "source_scope": "training_split_and_track_only",
        "artifact_preparation_marker_sha256": marker["marker_sha256"],
        "streams": {"G/Full-support/terran/Cus500/seed_1234": {
            "path": relative,
            "snapshot": {},
        }},
    }
    registry["sha256"] = _canonical_digest(registry, omitted={"sha256"})
    marker_path = repo / "marker.json"
    registry_path = repo / "registry.json"
    marker_path.write_text(json.dumps(marker), encoding="utf-8")
    registry_path.write_text(json.dumps(registry), encoding="utf-8")

    result = refresh_preverified_streams(
        repo_root=repo,
        registry_path=registry_path,
        marker_path=marker_path,
        stream_paths=[stream],
    )

    refreshed_marker = json.loads(marker_path.read_text(encoding="utf-8"))
    refreshed_registry = json.loads(registry_path.read_text(encoding="utf-8"))
    snapshot = refreshed_marker["training_stream_contracts"][0]["snapshot"]
    assert snapshot["sample_count"] == 740000
    assert refreshed_registry["streams"][
        "G/Full-support/terran/Cus500/seed_1234"
    ]["snapshot"] == snapshot
    assert refreshed_marker["file_hash_validation_performed"] is False
    assert refreshed_marker["stream_integrity_mode"] == PREVERIFIED_INTEGRITY_MODE
    assert result["stream_integrity_mode"] == PREVERIFIED_INTEGRITY_MODE
