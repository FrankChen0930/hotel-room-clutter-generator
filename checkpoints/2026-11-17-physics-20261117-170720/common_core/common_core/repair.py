"""Bounded repair decisions; never reclassify runtime/identity failures as geometry."""


def classify_native(report,process,static=None):
    if not report or process.get('termination_reason') or report.get('outcome')=='UNKNOWN':return 'RUNTIME_INCOMPLETE'
    if report.get('execution')!='EXECUTED':return 'RECORDED_OR_UNVERIFIED_RESULT'
    checks=report.get('checks',{})
    if not checks.get('native_steps') or not checks.get('native_120hz'):return 'RUNTIME_INCOMPLETE'
    if report.get('callback_errors') or report.get('physx_errors') or not checks.get('callbacks_clean') or not checks.get('physx_errors_clean'):
        return 'RUNTIME_ERROR'
    if report.get('outcome')=='PASS' and process.get('native_exit_code')==0:return 'PASS'
    targets=list(report.get('target_checks',{}).values())
    if not targets:return 'IDENTITY_OR_SCOPE_ERROR'
    if any(not t.get('initial_position_matches') or not t.get('initial_angle_matches') for t in targets):
        bad_gap=static and any(abs(c.get('gap_m',.001)-.001)>.0001 for c in static.get('checks',[]))
        return 'INITIAL_GEOMETRY_INVALID' if bad_gap else 'INITIAL_POSE_MISMATCH'
    if any(not t.get('expected_support_contact') or not t.get('footprint_retained') or not t.get('penetration_under_3mm') for t in targets):return 'SUPPORT_OR_PENETRATION'
    if any(not t.get('no_unexpected_contacts') for t in targets):return 'COLLISION'
    if any(not t.get('displacement_under_3cm') or not t.get('settled_last_30') for t in targets):return 'UNSTABLE'
    return 'UNCLASSIFIED_FAILURE'


def repair(plan,result,assessment,budget):
    retries=budget.get('native_retries_used',0)
    if type(retries) is not int or retries<0:raise ValueError('REPAIR_BUDGET')
    maximum=plan['budgets'].get('native_retries',0)
    if type(maximum) is not int or maximum not in (0,1):raise ValueError('REPAIR_NATIVE_RETRY_LIMIT')
    kind=assessment['failure_kind']
    if kind=='PASS':return dict(action='KEEP',reason='ALREADY_PASS',native_retries_used=retries)
    if kind not in ['INITIAL_GEOMETRY_INVALID','SUPPORT_OR_PENETRATION','COLLISION','UNSTABLE']:
        return dict(action='TERMINAL',reason=kind,native_retries_used=retries)
    if plan['budgets'].get('repair_passes',1)==0:return dict(action='TERMINAL',reason='GEOMETRY_REPAIR_DISABLED',native_retries_used=retries)
    if retries>=maximum:return dict(action='TERMINAL',reason='NATIVE_BUDGET_EXHAUSTED',native_retries_used=retries)
    used={r['request_id']:r['samples'] for r in result.get('sampling',[])}
    remaining={r['request_id']:plan['budgets'].get('max_samples_per_request',4800)-used.get(r['request_id'],0) for r in plan.get('requests',[])}
    if any(value<=0 for value in remaining.values()):return dict(action='TERMINAL',reason='GEOMETRY_BUDGET_EXHAUSTED',native_retries_used=retries)
    parent=assessment['attempt_id'];ordinal=retries+1
    return dict(action='NEW_ATTEMPT',reason=kind,parent_attempt_id=parent,attempt_id=f'a{ordinal:03d}',
        native_retries_used=ordinal,attempt_ordinal=ordinal,rng_stream='repair',
        preferred_supports={o['request_id']:o['effective']['support_id'] for o in result['objects']},
        remaining_samples=remaining,
        request_count=plan['targets']['count'],required_requests_preserved=True)
