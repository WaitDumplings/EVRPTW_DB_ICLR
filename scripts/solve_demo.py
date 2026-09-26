"""Bounded real ALNS runner, followed by the independent exact-module replay."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
import time
from evrptw_db.review import REPO, task_for, objective, load_review

sys.path.insert(0, str(REPO / "EVRPTW_Benchmark/MetaHeuristics/ALNS_Solver"))
from run_alns import solve_one
from EVRPTW_Benchmark.Exact.Gurobi_Solver.route_validator import validate_routes

def main():
    p=argparse.ArgumentParser();p.add_argument("--bundle",required=True);p.add_argument("--view-id");p.add_argument("--seconds",type=float,default=10);p.add_argument("--seed",type=int,default=2026);p.add_argument("--output",required=True);a=p.parse_args()
    if not 0 < a.seconds <= 30: p.error("smoke budget must be (0,30]")
    task={"input_kind":"stage2", "stage2_task":asdict(task_for(a.bundle,a.view_id)), "seed":a.seed, "checkpoints_s":(a.seconds,), "time_limit_s":a.seconds, "objective_config":objective().to_dict(), "max_iters":None, "delta_iters":None, "verbose":False, "save_traceback":False}
    started=time.perf_counter();result=solve_one(task);wall=time.perf_counter()-started
    row=result["summary_row"]; routes=json.loads(row.get("routes_json") or "[]")
    audit=validate_routes(load_review(a.bundle,a.view_id),routes)
    public={"schema":"evrptw_review_result_v1", "scope":"10s_or_user_selected_smoke_not_paper_result", "instance_id":task["stage2_task"]["view_id"], "config_id":"alns_review_smoke", "status":row["status"], "verified_feasible":audit["passed"], "routes":routes, "vehicle_count":len(routes), "objective_distance_km":audit["objective_distance_km"] if audit["passed"] else None, **(objective().fields(audit["objective_distance_km"],len(routes)) if audit["passed"] else {"objective_cost_usd":None}), "time_limit_s":a.seconds, "online_time_s":row.get("runtime_s") or None, "adapter_load_solve_and_final_replay_wall_s":wall, "timing_semantics":row.get("timing_scope"), "seed":a.seed, "audit":audit, "errors":row.get("errors", "")}
    path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(public,indent=2,allow_nan=False)+"\n");print(json.dumps({k:v for k,v in public.items() if k not in {"routes","audit"}},indent=2))
    return 0 if audit["passed"] else 2
if __name__ == "__main__": raise SystemExit(main())
