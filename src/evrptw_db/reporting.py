"""Rebuild metrics without dropping missing/failed cohort positions or replacing BKS."""
from pathlib import Path
import html
import json
import math
import pandas as pd


def aggregate(records, cohort, bks=None, configurations=None):
    keys = ['cohort_id', 'instance_id']
    if cohort.duplicated(keys).any():
        raise ValueError('Duplicate cohort instance IDs')
    if records.duplicated(['config_id'] + keys).any():
        raise ValueError('Duplicate config/cohort/instance results; select an explicit snapshot')
    if records.merge(cohort[keys], on=keys, how='left', indicator=True)['_merge'].eq('left_only').any():
        raise ValueError('Result refers to an instance outside the declared cohort')
    if bks is not None and bks.duplicated(keys).any():
        raise ValueError('Duplicate BKS instance IDs')
    output = []
    configs = sorted(set(records.config_id) if configurations is None else set(configurations))
    if not set(records.config_id).issubset(configs):
        raise ValueError('Result configuration is outside the expected configuration list')
    from itertools import product
    for config, group_id in product(configs, sorted(set(cohort.cohort_id))):
        rows = records[records.config_id.eq(config) & records.cohort_id.eq(group_id)]
        expected = cohort[cohort.cohort_id.eq(group_id)][keys]
        joined = expected.merge(rows, on=keys, how='left', validate='one_to_one')
        good = joined.verified_feasible.astype(str).str.lower().isin(['true', '1'])
        costs = pd.to_numeric(joined.cost_usd, errors='coerce')
        if (good & (~costs.map(lambda x: pd.notna(x) and math.isfinite(x) and x >= 0))).any():
            raise ValueError('Verified row has missing/nonfinite/negative cost')
        duration = pd.to_numeric(joined.online_time_s, errors='coerce')
        if any(not math.isfinite(v) or v < 0 for v in duration.dropna()):
            raise ValueError('Nonfinite or negative measured runtime')
        full = bool(good.all())
        item = {'config_id':config, 'cohort_id':group_id, 'instances':len(joined), 'verified':int(good.sum()), 'failed_or_missing':int((~good).sum()), 'feasibility_rate':float(good.mean()), 'mean_cost_usd':float(costs.mean()) if full else None, 'mean_online_time_s':float(duration.mean()) if duration.notna().all() else None, 'timing_observations':int(duration.notna().sum()), 'mean_gap_percent':None, 'bks_complete_frozen':False}
        if bks is not None:
            reference = joined.merge(bks[keys+['bks_cost_usd','freeze_status']],on=keys,how='left',validate='one_to_one')
            bc = pd.to_numeric(reference.bks_cost_usd,errors='coerce')
            frozen = reference.freeze_status.astype(str).str.lower().isin(['frozen', 'frozen_verified', 'frozen_reference'])
            ready = bool(frozen.all() and bc.notna().all() and bc.map(lambda x: pd.notna(x) and math.isfinite(x) and x > 0).all())
            item['bks_complete_frozen'] = ready
            if full and ready: item['mean_gap_percent'] = float(((costs.to_numpy()-bc.to_numpy())/bc.to_numpy()*100).mean())
        output.append(item)
    return pd.DataFrame(output)


def build_report(records_path, cohort_path, bks_path, output, scope, configurations_path=None):
    records=pd.read_csv(records_path,keep_default_na=False, dtype=str)
    cohort=pd.read_csv(cohort_path,keep_default_na=False, dtype=str)
    bks=pd.read_csv(bks_path,keep_default_na=False, dtype=str) if bks_path else None
    configs=pd.read_csv(configurations_path,dtype=str)['config_id'].tolist() if configurations_path else None
    summary=aggregate(records,cohort,bks,configs)
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    summary.to_csv(out/'summary.csv',index=False)
    # An exportable standalone SVG has no plotting dependency or remote assets.
    width=1100;height=65+len(summary)*23
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">', '<rect width="100%" height="100%" fill="white"/>',f'<text x="15" y="24" font-family="sans-serif" font-size="16">Feasibility rate — {html.escape(scope)}</text>']
    for i,row in summary.iterrows():
        y=55+i*23
        label=html.escape(str(row['config_id'])+' | '+str(row['cohort_id']))
        parts += [f'<text x="15" y="{y}" font-family="monospace" font-size="11">{label}</text>',f'<rect x="650" y="{y-12}" width="{350*row.feasibility_rate}" height="14" fill="#25778e"/>',f'<text x="1010" y="{y}" font-family="sans-serif" font-size="11">{row.feasibility_rate:.1%}</text>']
    parts.append('</svg>');(out/'feasibility.svg').write_text('\n'.join(parts))
    result={'scope':scope,'recorded_rows':len(records),'declared_instances':len(cohort),'config_cohort_pairs':len(summary), 'configuration_source':'explicit_expected_list' if configurations_path else 'distinct_configurations_in_records','quality_rule':'mean cost only when entire cohort FR=1','timing_rule':'mean only when every expected position has measured runtime; missing remains missing','bks_rule':'no reference construction; gaps require complete frozen reference','limitations':'Metric reconstruction does not independently replay every route or reproduce training. Scope label is user supplied; it does not certify paper alignment.'}
    (out/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
