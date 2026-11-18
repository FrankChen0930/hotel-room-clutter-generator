def matrix():
    return [[1.,0.,0.,0.],[0.,1.,0.,0.],[0.,0.,1.,0.],[0.,0.,0.,1.]]


def source():
    return dict(mount='room', path='room.usda', root_prim='/Room', sha256='a'*64,
                closure_ref='closure.json', closure_sha256='b'*64)


def profile():
    return dict(schema_version='1.0', profile_id='synthetic', profile_version='1', source=source(),
                coordinates=dict(meters_per_unit=1., up_axis='Z', to_common=matrix()),
                supports=[dict(support_id='desk', prim='/Room/Table', collider='/Room/Table/Mesh',
                               kind='mesh_top', local_frame=matrix(), allowed_region=[[-1,-1],[1,-1],[1,1],[-1,1]],
                               edge_margin_m=.01, tags=['desk'])], forbidden_regions=[],
                source_objects=[dict(object_id='table', prim='/Room/Table', mobility='FIXED', allowed_operations=[])],
                override_allowlist=[], test_freeze=dict(body_mode='kinematic'), cameras=[],
                provenance=dict(kind='synthetic_fixture'))


def catalog():
    state=dict(state_id='clean', version='1', usd_locator_or_native_prim=source(), sha256='c'*64,
               units=1., up_axis='Z', pivot=[0.,0.,0.], alignment=matrix(),
               visual_bounds=[[-.05,-.05,0.],[.05,.05,.1]], footprint=[[-.05,-.05],[.05,-.05],[.05,.05],[-.05,.05]],
               support_envelope=dict(clearance_m=.001), allowed_pose_tags=['upright'], acceptance_refs=[],
               physics_proxy=dict(kind='none', capability='STATIC_ONLY', shape_paths=[], geometry_hash='c'*64))
    return dict(schema_version='1.0', catalog_id='synthetic', version='1',
                entries=[dict(asset_id='cup',version='1',category='cup',origin='external', source_locator=source(),
                              dependency_hashes=[],root_prim='/Cup',dimensions=[.1,.1,.1],
                              provenance=dict(kind='synthetic_fixture'),license_scope='INTERNAL_EVALUATION_ONLY',
                              states=[state], qualification_refs=[])])


def policy():
    return dict(schema_version='1.0', policy_id='synthetic', version='1',
                assumptions=['SYNTHETIC_RESEARCH_ASSUMPTIONS'],
                scenarios={name:dict(roles=[], eligible_categories=['cup'], ownership='guest', action='retain',
                                    required_categories=['cup'], allowed_support_tags=['desk'])
                           for name in ['STAYOVER','CHECKOUT']},
                levels={level:dict(count_ranges={'STAYOVER':stay,'CHECKOUT':check},
                                   coverage=dict(hard=False,target=0.), spread=dict(hard=False,target=0.),
                                   state_proportions={}, allowed_pose_tags=['upright'])
                        for level,stay,check in [('low',[5,6],[7,8]),('medium',[8,9],[11,12]),('high',[12,13],[16,18])]},
                budgets=dict(max_supports=3,samples_per_support=800,repair_passes=1,max_samples_per_request=4800,native_retries=1))


def manifest():
    effective=dict(world_matrix=matrix(),state_id='clean',support_id='desk',semantic_state='guest',body_mode='kinematic')
    return dict(schema_version='3.0',generator_version='1.0',run_id='test',attempt_id='a000',parent_attempt_id=None,
                inputs=dict(seed=705,scenario='STAYOVER',level='low',code_hash='a'*64,profile_hash='a'*64,
                            catalog_hash='a'*64,policy_hash='a'*64,source_closure_hash='b'*64),
                environment={},requests=[],targets={},achieved={},
                objects=[dict(instance_id='guest/cup/0',request_id='guest/cup/0',asset_id='cup',state_sha256='c'*64,
                              origin='external',source_object_id=None,native_prim=None,before=dict(exists=False),
                              after=effective.copy(),effective=effective.copy())],
                scene=dict(locator=dict(mount='run',path='scene.usda'),sha256='d'*64,state_digest='e'*64,dependencies=[]),
                evidence_refs=[],failure_refs=[],attempt_lineage=[],limits=['Synthetic fixture only'])
