from pathlib import Path
from dataclasses import asdict
import json
from evrptw_core.objective import load_objective, select_objective_distance
from EVRPTW_Benchmark.MetaHeuristics.benchmark_common import Stage2ViewTask, load_stage2_instance
from EVRPTW_Benchmark.Exact.Gurobi_Solver.route_validator import validate_routes

REPO = Path(__file__).resolve().parents[2]

def inside(root, relative):
    root = Path(root).resolve()
    path = (root / relative).resolve()
    if Path(relative).is_absolute() or not path.is_relative_to(root):
        raise ValueError("Bundle reference must stay inside its root")
    return path

def selected_view(bundle, view_id=None):
    root = Path(bundle).resolve()
    manifest = json.loads((root / "sample_manifest.json").read_text())
    views = manifest["views"]
    view = views[0] if view_id is None else next((v for v in views if v["view_id"] == view_id), None)
    if view is None:
        raise ValueError(f"View not in frozen sample: {view_id}")
    return root, view

def task_for(bundle, view_id=None):
    root, v = selected_view(bundle, view_id)
    family = inside(root, v["family_dir"])
    vm = json.loads(inside(root, v["view_manifest"]).read_text())
    return Stage2ViewTask(index_path="sample_manifest.json", family_dir=str(family), view_id=v["view_id"], family_id=v["family_id"], consumer_cohort_id=vm.get("consumer_cohort_id", "review"), split_id=v["split_id"], track_id=v["track_id"], city_slug=v["city_slug"], scale_id=v["scale_id"], customer_count=v["customer_count"], charging_station_count=v["charging_station_count"], row_position=0, family_cohort_id=vm.get("family_cohort_id", ""), terminal_count=v["terminal_count"], view_seed=int(vm.get("view_seed", 0)))

def objective():
    return load_objective(REPO / "configs/paper/objective.json")

def load_review(bundle, view_id=None):
    return select_objective_distance(load_stage2_instance(task_for(bundle, view_id)), objective())

def replay(bundle, route_path, view_id=None):
    payload = json.loads(Path(route_path).read_text())
    if isinstance(payload, list):
        routes = payload
    else:
        route_id = payload.get("instance_id", payload.get("view_id"))
        if view_id and route_id and route_id != view_id:
            raise ValueError("Route instance ID does not match requested view")
        view_id = view_id or route_id
        routes = payload.get("routes", payload.get("solution", {}).get("routes"))
    if routes is None:
        raise ValueError("Route JSON must contain a routes list")
    # Reject lossy int coercion before invoking the unchanged production replay.
    if not isinstance(routes, list) or any(not isinstance(route, list) or any(type(n) is not int for n in route) for route in routes):
        raise ValueError("routes must be lists of integer terminal indices")
    inst = load_review(bundle, view_id)
    audit = validate_routes(inst, routes)
    return {"schema": "evrptw_review_result_v1", "scope": "recorded_route_replay_current_objective", "instance_id": inst.instance_id, "status": "VERIFIED" if audit["passed"] else "INVALID", "verified_feasible": audit["passed"], "vehicle_count": len(routes), "objective_distance_km": audit["objective_distance_km"] if audit["passed"] else None, **(objective().fields(audit["objective_distance_km"], len(routes)) if audit["passed"] else {"objective_cost_usd": None}), "audit": audit, "online_time_s": None, "timing_semantics": "replay_does_not_reconstruct_original_solver_runtime"}
