"""Bounded local data controls; never executes commands or makes network requests."""
def decision(settings, control, *, acquired_count, local_ready, elapsed_s, original_bytes):
    if control.get('stop') is True:return 'STOP_REQUESTED'
    if local_ready>=settings['target_local_ready']:return 'LOCAL_TARGET_REACHED'
    if acquired_count>=settings['max_total_sources']:return 'SOURCE_POOL_LIMIT_REACHED'
    if elapsed_s>=settings['max_elapsed_s']:return 'SESSION_TIME_LIMIT_REACHED'
    if original_bytes>=settings['max_original_bytes']:return 'SOURCE_BYTES_LIMIT_REACHED'
    if control.get('pause') is True:return 'PAUSED'
    return 'CONTINUE'

def validate_queries(queries):
    from batch_selection import TOKENS
    if not isinstance(queries,list) or len(queries)>400:raise ValueError('BOUNDED_QUERY_LIST_REQUIRED')
    for job in queries:
        if not isinstance(job,dict) or job.get('category') not in TOKENS:raise ValueError('KNOWN_HOTEL_CATEGORY_REQUIRED')
        if not isinstance(job.get('query'),str) or not 1<=len(job['query'])<=80:raise ValueError('BOUNDED_QUERY_REQUIRED')
        if not isinstance(job.get('scenario'),str) or not isinstance(job.get('regions'),list):raise ValueError('HOTEL_SCENARIO_REGIONS_REQUIRED')
    return queries
