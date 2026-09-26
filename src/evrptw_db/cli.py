import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

def emit(data, output=None):
    text = json.dumps(data, indent=2, allow_nan=False)
    if output:
        path = Path(output); path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text + "\n")
    print(text)

def main():
    p = argparse.ArgumentParser(description="Offline EVRP-TW review tools")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    q = sub.add_parser("integrity"); q.add_argument("bundle")
    q = sub.add_parser("inspect"); q.add_argument("--bundle", required=True); q.add_argument("--view-id")
    q = sub.add_parser("verify"); q.add_argument("--bundle", required=True); q.add_argument("--routes", required=True); q.add_argument("--view-id"); q.add_argument("--output")
    q = sub.add_parser("solve"); q.add_argument("--bundle", required=True); q.add_argument("--view-id"); q.add_argument("--seconds", type=float, default=10); q.add_argument("--seed", type=int, default=2026); q.add_argument("--output", required=True)
    q = sub.add_parser("report"); q.add_argument("--records", required=True); q.add_argument("--cohort", required=True); q.add_argument("--bks"); q.add_argument("--configurations"); q.add_argument("--output", required=True); q.add_argument("--scope", required=True)
    a = p.parse_args()
    if a.command == "doctor":
        names = ["numpy", "pandas", "pyarrow", "scipy", "networkx", "torch", "gurobipy", "geopandas", "pytest"]
        versions = {}
        for name in names:
            try: versions[name] = importlib.metadata.version(name)
            except importlib.metadata.PackageNotFoundError: versions[name] = None
        emit({"python": sys.version.split()[0], "packages": versions, "core_available": all(versions[x] for x in names[:5]), "note": "Learning/Gurobi/geographic packages are optional; no device initialization or network requests."})
    elif a.command == "integrity":
        from .review import inside
        root = Path(a.bundle)
        entries = json.loads((root / "FILE_MANIFEST.json").read_text())["files"]
        failed = []
        for entry in entries:
            path = inside(root, entry["path"])
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]: failed.append(entry["path"])
        listed = {e["path"] for e in entries} | {"FILE_MANIFEST.json"}
        extra = sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p.relative_to(root).as_posix() not in listed and "__pycache__" not in p.parts)
        emit({"status": "PASS" if not failed and not extra else "FAIL", "checked": len(entries), "failed": failed, "unexpected": extra})
        return int(bool(failed or extra))
    elif a.command == "inspect":
        from .review import load_review
        import numpy as np
        inst = load_review(a.bundle, a.view_id)
        distance = inst.distance_matrix_km
        emit({"instance_id": inst.instance_id, "customers": inst.num_customers, "stations": inst.num_charging_stations, "city": inst.region_id, "split": inst.metadata["track_id"], "matrix_shape": list(distance.shape), "directed_asymmetric": not np.array_equal(distance, distance.T), "objective_distance_source": inst.metadata["objective_distance_source"], "units": {"distance": "km", "time": "seconds", "energy": "kWh", "power": "kW", "demand_capacity": "cm3"}})
    elif a.command == "verify":
        from .review import replay
        result = replay(a.bundle, a.routes, a.view_id)
        emit(result, a.output)
        return 0 if result["verified_feasible"] else 2
    elif a.command == "solve":
        from .review import REPO
        if not 0 < a.seconds <= 30: p.error("review smoke budget must be in (0, 30]; use production runner for formal experiments")
        cmd = [sys.executable, str(REPO / "scripts/solve_demo.py"), "--bundle", a.bundle, "--seconds", str(a.seconds), "--seed", str(a.seed), "--output", a.output]
        if a.view_id: cmd += ["--view-id", a.view_id]
        return subprocess.call(cmd, env={**os.environ, "CUDA_VISIBLE_DEVICES": "", "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1"})
    elif a.command == "report":
        from .reporting import build_report
        emit(build_report(a.records, a.cohort, a.bks, a.output, a.scope, a.configurations))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
