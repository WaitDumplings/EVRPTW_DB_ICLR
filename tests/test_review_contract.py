from dataclasses import replace
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from evrptw_core.schema import EVRPTWInstance
from evrptw_core.objective import select_objective_distance
from EVRPTW_Benchmark.Exact.Gurobi_Solver.route_validator import validate_routes
from evrptw_db.review import objective
from evrptw_db.reporting import aggregate


def instance():
    fast=np.array([[0,2,7,1],[3,0,4,2],[5,8,0,2],[1,2,3,0]],dtype=float)
    raw=dict(instance_id='unit_contract',working_start_s=0,working_end_s=10000,depot=[0,0],customers=[[1,0],[2,0]],charging_stations=[[0,1]],distance_matrix_km=fast/2,demands_cm3=[1,1],package_counts=[1,1],service_time_s=[1,1],tw_s=[[0,9000],[0,9000]],cs_time_to_depot_s=[10],vehicle={'battery_capacity_kwh':10,'cargo_capacity_cm3':2},charging_power_kw=[10],charging_policy={'charging_power_derating_factor':0.9},running_time_path_distance_km=fast,running_time_shortest_matrix_s=fast*10,running_time_path_energy_kwh=fast/2)
    return select_objective_distance(EVRPTWInstance.from_dict(raw),objective())


def test_asymmetric_fast_path_cost_and_charge():
    inst=instance(); a=validate_routes(inst,[[0,1,2,0]])
    assert a['passed'] and a['objective_distance_km']==11
    assert not np.array_equal(inst.distance_matrix_km,inst.distance_matrix_km.T)
    assert objective().fields(11,1)['objective_cost_usd']==pytest.approx(413.6331536717643+0.39*0.38910505836575876*11)
    charged=validate_routes(inst,[[0,1,3,2,0]])
    assert charged['passed'] and charged['total_charging_time_s']==pytest.approx(800)
    assert not validate_routes(replace(inst,working_end_s=500),[[0,1,3,2,0]])['passed']


@pytest.mark.parametrize('routes', [[[0,1,0]],[[0,1,2,1,0]],[[0,1,0,2,0]],[[0,1,2]],[[0,1,99,0]],[[0,3,0],[0,1,2,0]]])
def test_bad_coverage_and_structure(routes):
    assert not validate_routes(instance(),routes)['passed']


def test_resources_rejected():
    inst=instance();routes=[[0,1,2,0]]
    assert not validate_routes(replace(inst,demands_cm3=np.array([2,2])),routes)['passed']
    assert not validate_routes(replace(inst,vehicle={**inst.vehicle,'battery_capacity_kwh':1}),routes)['passed']
    assert not validate_routes(replace(inst,tw_s=np.array([[0,1],[0,9000]])),routes)['passed']
    assert not validate_routes(replace(inst,working_end_s=30),routes)['passed']
    bad=inst.raw['running_time_shortest_matrix_s'].copy();bad[0,1]=np.inf
    assert not validate_routes(replace(inst,raw={**inst.raw,'running_time_shortest_matrix_s':bad}),routes)['passed']


def test_missing_objective_path_refused():
    inst=instance();raw=dict(inst.raw);raw.pop('running_time_path_distance_km')
    with pytest.raises(ValueError,match='refusing'):
        select_objective_distance(replace(inst,raw=raw),objective())


def test_paper_profile_selects_same_cost_distance_in_core_and_learning():
    from evrptw_core.objective import load_objective as load_core_objective
    from EVRPTW_Benchmark.Reinforcement_Learning.common.objective import (
        load_objective as load_learning_objective,
        resolve_objective,
        select_objective_instance,
    )

    path = Path(__file__).resolve().parents[1] / 'configs/paper/objective.json'
    core = load_core_objective(path)
    learning = load_learning_objective(path)
    original = instance()
    core_instance = select_objective_distance(original, core)
    learning_instance = select_objective_instance(original, learning)
    assert learning.objective_distance_source == 'running_time_path_distance_km'
    for selected, profile in ((core_instance, core), (learning_instance, learning)):
        replay = validate_routes(selected, [[0, 1, 2, 0]])
        assert replay['passed']
        assert replay['objective_distance_km'] == 11
        assert replay['objective_distance_source'] == 'running_time_path_distance_km'
        assert profile.value(11, 1) == core.value(11, 1)
        assert selected.raw['running_time_shortest_matrix_s'] is original.raw['running_time_shortest_matrix_s']
        assert selected.raw['running_time_path_energy_kwh'] is original.raw['running_time_path_energy_kwh']

    # Old learning checkpoints still resolve their omitted field as D_dist.
    legacy = dict(json.loads(path.read_text())['objective'])
    legacy.pop('objective_distance_source')
    restored = select_objective_instance(original, resolve_objective(legacy))
    assert validate_routes(restored, [[0, 1, 2, 0]])['objective_distance_km'] == 5.5


def test_core_profile_rejects_conflicting_explicit_cost_distance(tmp_path):
    from evrptw_core.objective import load_objective

    payload = objective().to_dict()
    payload['objective_distance_source'] = 'distance_matrix_km'
    path = tmp_path / 'conflicting_objective.json'
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match='requires running_time_path_distance_km'):
        load_objective(path)


def test_missing_failures_and_unfrozen_bks_not_hidden():
    cohort=pd.DataFrame({'cohort_id':['T1']*3,'instance_id':['a','b','c']})
    rows=pd.DataFrame({'cohort_id':['T1']*2,'instance_id':['a','b'],'config_id':['method']*2,'verified_feasible':[True,False],'cost_usd':[4,None],'online_time_s':[1,None]})
    bks=cohort.assign(bks_cost_usd=2,freeze_status='not_frozen')
    summary=aggregate(rows,cohort,bks).iloc[0]
    assert summary['instances']==3 and summary.verified==1
    assert summary.feasibility_rate==pytest.approx(1/3)
    assert pd.isna(summary.mean_cost_usd) and pd.isna(summary.mean_online_time_s)
    assert pd.isna(summary.mean_gap_percent)
    with pytest.raises(ValueError,match='Duplicate'):
        aggregate(pd.concat([rows,rows]),cohort)


def test_wholly_missing_pairs_and_nonfinite_metrics():
    cohort=pd.DataFrame({'cohort_id':['T1','T2'],'instance_id':['a','b']})
    rows=pd.DataFrame({'cohort_id':['T1'],'instance_id':['a'],'config_id':['known'],'verified_feasible':[True],'cost_usd':[4],'online_time_s':[1]})
    result=aggregate(rows,cohort,configurations=['known','absent'])
    assert len(result)==4 and result.instances.sum()==4 and result.verified.sum()==1
    with pytest.raises(ValueError,match='Nonfinite'):
        aggregate(rows.assign(online_time_s=float('inf')),cohort)
    bks=cohort.assign(bks_cost_usd=float('inf'),freeze_status='frozen')
    summary=aggregate(rows,cohort,bks)
    assert not summary.bks_complete_frozen.any()
    assert summary.mean_gap_percent.isna().all()
