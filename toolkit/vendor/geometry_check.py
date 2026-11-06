from dataclasses import asdict,dataclass
import math
from pathlib import Path
import randomize_table as phase1
from pxr import Gf,Usd,UsdGeom,UsdPhysics
TARGET=phase1.TARGET
FLOOR='/YAZHI_TWIN/ShellColliders/Floor'
EPS=1e-6

class Settings:
    # Every margin/region bound here is a Prototype Assumption, not a measurement.
    floor_margin_m: float = 0.02
    obstacle_margin_m: float = 0.01
    max_support_gap_m: float = 0.001
    max_support_penetration_m: float = 0.001
    study_xy_half_width_m: float = 0.15
    study_yaw_offset_max_degrees: float = 15.0

def dot(a, b):
    return sum(x * y for x, y in zip(a, b))

def length(a):
    return math.sqrt(dot(a, a))

def upright_rigid_pose(matrix):
    if not all(math.isfinite(matrix[i][j]) for i in range(4) for j in range(4)):
        return False
    rows = [[matrix[i][j] for j in range(3)] for i in range(3)]
    return (all(abs(dot(rows[i], rows[j]) - (1 if i == j else 0)) < 1e-8 for i in range(3) for j in range(3))
            and all(abs(matrix[i][3]) < 1e-8 for i in range(3)) and abs(matrix[3][3] - 1) < 1e-8
            and matrix.GetDeterminant() > 0 and abs(rows[2][2] - 1) < 1e-8)

def extract_primitive(stage, prim, world_override=None):
    """Read primitive parameters even for invisible guide instance proxies.

    The optional world matrix is math-only; no USD property is authored.
    """
    world = world_override if world_override is not None else UsdGeom.XformCache().GetLocalToWorldTransform(prim)
    rows = [[float(world[i][j]) for j in range(3)] for i in range(3)]
    scale = [length(row) for row in rows]
    axes = [[x / s for x in row] if s > 1e-12 else [0, 0, 0] for row, s in zip(rows, scale)]
    center = list(world.ExtractTranslation())
    out = {'path': str(prim.GetPath()), 'geometry_type': prim.GetTypeName(),
           'is_instance_proxy': prim.IsInstanceProxy(),
           'purpose': str(UsdGeom.Imageable(prim).ComputePurpose()),
           'visibility': str(UsdGeom.Imageable(prim).ComputeVisibility()),
           'local_transform': phase1.matrix_list(UsdGeom.Xformable(prim).GetLocalTransformation()),
           'world_transform': phase1.matrix_list(world), 'scale': scale,
           'center_xy': center[:2], 'kind': 'unsupported'}
    orthogonal = all(s > 1e-12 for s in scale) and all(abs(dot(axes[i], axes[j])) < 1e-8 for i in range(3) for j in range(i))
    if prim.IsA(UsdGeom.Cylinder):
        cylinder = UsdGeom.Cylinder(prim)
        radius, height = float(cylinder.GetRadiusAttr().Get()), float(cylinder.GetHeightAttr().Get())
        axis = ('X', 'Y', 'Z').index(cylinder.GetAxisAttr().Get())
        radial = [i for i in range(3) if i != axis]
        out['geometry_parameters'] = {'radius': radius, 'height': height, 'axis': ('X', 'Y', 'Z')[axis]}
        extent = [abs(rows[axis][j]) * height / 2 + radius * math.sqrt(sum(rows[i][j] ** 2 for i in radial)) for j in range(3)]
        if (orthogonal and abs(abs(axes[axis][2]) - 1) < 1e-8
                and all(abs(axes[i][2]) < 1e-8 for i in radial)
                and abs(scale[radial[0]] - scale[radial[1]]) < 1e-8):
            out.update(kind='circle', radius_m=radius * scale[radial[0]])
        else:
            out['unsupported_reason'] = 'Cylinder is tilted, sheared, singular or elliptically scaled'
    elif prim.IsA(UsdGeom.Cube):
        size = float(UsdGeom.Cube(prim).GetSizeAttr().Get())
        out['geometry_parameters'] = {'size': size}
        extent = [size / 2 * sum(abs(rows[i][j]) for i in range(3)) for j in range(3)]
        if orthogonal and abs(abs(axes[2][2]) - 1) < 1e-8 and all(abs(axes[i][2]) < 1e-8 for i in (0, 1)):
            out.update(kind='rectangle', axes_xy=[axes[0][:2], axes[1][:2]],
                       half_sizes_xy_m=[size * scale[0] / 2, size * scale[1] / 2])
        else:
            out['unsupported_reason'] = 'Cube is tilted, sheared or singular'
    else:
        # A USD bound can only be used for broad phase; never certify an
        # unimplemented narrow-phase case from this bound alone.
        cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ['default', 'render', 'proxy', 'guide'], False, True)
        bound = cache.ComputeUntransformedBound(prim)
        transformed = Gf.BBox3d(bound.GetRange(), bound.GetMatrix() * world).ComputeAlignedRange()
        out.update(world_aabb={'min': list(transformed.GetMin()), 'max': list(transformed.GetMax())},
                   unsupported_reason='No narrow phase for this USD geometry type')
        out.update(z_min=float(transformed.GetMin()[2]), z_max=float(transformed.GetMax()[2]))
        return out
    out['world_aabb'] = {'min': [center[i] - extent[i] for i in range(3)],
                         'max': [center[i] + extent[i] for i in range(3)]}
    out.update(z_min=center[2] - extent[2], z_max=center[2] + extent[2])
    return out

def aabb_gap(a, b):
    gaps = [max(a['min'][i] - b['max'][i], b['min'][i] - a['max'][i], 0.0) for i in range(3)]
    return length(gaps)

def planar_signed_clearance(circle, other):
    offset = [circle['center_xy'][i] - other['center_xy'][i] for i in range(2)]
    if other['kind'] == 'circle':
        return length(offset) - circle['radius_m'] - other['radius_m']
    distances = [abs(dot(offset, axis)) - half for axis, half in zip(other['axes_xy'], other['half_sizes_xy_m'])]
    return length([max(v, 0) for v in distances]) + min(max(distances), 0) - circle['radius_m']

def pair_check(a, b, margin):
    """Cylinder/cylinder or cylinder/yaw-OBB extrusions; never infer hit from AABB."""
    gap = aabb_gap(a['world_aabb'], b['world_aabb'])
    result = {'aabb_distance_lower_bound_m': gap,
              'aabb_raw_overlap': all(a['world_aabb']['max'][i] >= b['world_aabb']['min'][i] and
                                      b['world_aabb']['max'][i] >= a['world_aabb']['min'][i] for i in range(3))}
    if gap > margin + EPS:
        return dict(result, status='PASS', broad_phase='AABB_CLEARLY_SEPARATED', narrow_phase='NOT_REQUIRED',
                    reason='bounding_volume_separation_proves_primitive_separation')
    result['broad_phase'] = 'AABB_OVERLAP_OR_NEAR'
    if a['kind'] != 'circle' or b['kind'] not in ('circle', 'rectangle'):
        return dict(result, status='UNKNOWN', narrow_phase='UNSUPPORTED', reason='overlapping_or_near_unsupported_geometry')
    horizontal = planar_signed_clearance(a, b)
    vertical_overlap = min(a['z_max'], b['z_max']) - max(a['z_min'], b['z_min'])
    separation = max(horizontal, -vertical_overlap)
    result.update(planar_signed_clearance_m=horizontal, vertical_interval_overlap_m=vertical_overlap,
                  signed_separating_axis_clearance_m=separation)
    if horizontal < -EPS and vertical_overlap > EPS:
        return dict(result, status='REJECT', narrow_phase='PRIMITIVE_PENETRATION', reason='definite_primitive_volume_intersection',
                    conservative_axis_penetration_m=min(-horizontal, vertical_overlap))
    if separation > margin + EPS:
        return dict(result, status='PASS', narrow_phase='PRIMITIVES_SEPARATED', reason='primitive_separation_meets_margin')
    if separation > EPS:
        return dict(result, status='REJECT', narrow_phase='PRIMITIVES_SEPARATED_BUT_MARGIN_SMALL',
                    reason='prototype_obstacle_margin_not_met')
    return dict(result, status='UNKNOWN', narrow_phase='TANGENT_OR_NUMERIC_BOUNDARY', reason='contact_or_separation_within_numerical_tolerance')

def floor_clearance(circle, floor):
    offset = [circle['center_xy'][i] - floor['center_xy'][i] for i in range(2)]
    return min(half - abs(dot(offset, axis)) - circle['radius_m']
               for axis, half in zip(floor['axes_xy'], floor['half_sizes_xy_m']))

def support_check(shapes, floor, settings):
    if floor['kind'] != 'rectangle' or not shapes or any(s['kind'] != 'circle' for s in shapes):
        return {'status': 'UNKNOWN', 'reasons': ['unsupported_floor_or_target_support_geometry']}
    bottom = min(s['z_min'] for s in shapes)
    bases = [s for s in shapes if s['z_min'] <= bottom + EPS]
    gap = bottom - floor['z_max']
    base_clearance = min(floor_clearance(s, floor) for s in bases)
    whole_clearance = min(floor_clearance(s, floor) for s in shapes)
    reasons = []
    if whole_clearance < -EPS:
        reasons.append('whole_object_footprint_outside_floor')
    elif whole_clearance < settings.floor_margin_m - EPS:
        reasons.append('prototype_floor_edge_margin_not_met')
    if gap > settings.max_support_gap_m + EPS:
        reasons.append('unsupported_vertical_gap')
    if gap < -settings.max_support_penetration_m - EPS:
        reasons.append('excessive_initial_floor_penetration')
    return {'status': 'REJECT' if reasons else 'PASS', 'reasons': reasons,
            'bottom_collider_paths': [s.get('path', 'synthetic') for s in bases],
            'object_bottom_z_m': bottom, 'floor_support_plane_z_m': floor['z_max'],
            'signed_bottom_floor_gap_m': gap, 'floor_penetration_m': max(-gap, 0),
            'base_footprint_edge_clearance_m': base_clearance,
            'whole_object_footprint_edge_clearance_m': whole_clearance,
            'clearance_after_prototype_margin_m': whole_clearance - settings.floor_margin_m,
            'scope': 'Geometric coverage/gap only; no physical stability claim'}

class GeometryChecker:
    """Reusable evaluator accepting a world-space Gf.Matrix4d, without stage edits."""
    def __init__(self, stage, settings=None, target=TARGET, support=FLOOR):
        self.stage, self.settings, self.target, self.support = stage, settings or Settings(), target, support
        if any(not math.isfinite(value) or value < 0 for value in asdict(self.settings).values()):
            raise ValueError('Settings must be finite nonnegative Prototype Assumptions')
        if UsdGeom.GetStageMetersPerUnit(stage) != 1 or UsdGeom.GetStageUpAxis(stage) != 'Z':
            raise ValueError('This prototype requires meter / Z-up stage coordinates')
        self.root = stage.GetPrimAtPath(target)
        if not self.root or not self.root.IsInstance():
            raise ValueError('Expected existing target instance root')
        cache = UsdGeom.XformCache()
        self.original_world = cache.GetLocalToWorldTransform(self.root)
        self.target_prims = [q for q in Usd.PrimRange(self.root, Usd.TraverseInstanceProxies())
                             if q.HasAPI(UsdPhysics.CollisionAPI) and UsdPhysics.CollisionAPI(q).GetCollisionEnabledAttr().Get()]
        if len(self.target_prims) != 3:
            raise ValueError('Expected three existing table collision proxies')
        self.relative = {str(q.GetPath()): cache.GetLocalToWorldTransform(q) * self.original_world.GetInverse()
                         for q in self.target_prims}
        floor = stage.GetPrimAtPath(support)
        if not floor or not floor.HasAPI(UsdPhysics.CollisionAPI) or not UsdPhysics.CollisionAPI(floor).GetCollisionEnabledAttr().Get():
            raise ValueError('Support collider missing/disabled')
        ancestor = floor
        while ancestor and not ancestor.IsPseudoRoot():
            if ancestor.HasAPI(UsdPhysics.RigidBodyAPI):
                raise ValueError('Support is not a static collider')
            ancestor = ancestor.GetParent()
        self.floor = extract_primitive(stage, floor)
        self.obstacles = []
        for prim in Usd.PrimRange.Stage(stage, Usd.TraverseInstanceProxies()):
            path = str(prim.GetPath())
            if path == support or path == target or path.startswith(target + '/'):
                continue
            if prim.HasAPI(UsdPhysics.CollisionAPI) and UsdPhysics.CollisionAPI(prim).GetCollisionEnabledAttr().Get():
                shape = extract_primitive(stage, prim)
                owner = prim
                while owner and not owner.IsPseudoRoot() and not owner.HasAPI(UsdPhysics.RigidBodyAPI):
                    owner = owner.GetParent()
                shape['rigid_body_owner'] = str(owner.GetPath()) if owner and not owner.IsPseudoRoot() else None
                shape['obstacle_scope'] = 'authored default-time snapshot, including joint-linked parts; no future-motion guarantee'
                self.obstacles.append(shape)

    def virtual_shapes(self, world):
        return [extract_primitive(self.stage, prim, self.relative[str(prim.GetPath())] * world) for prim in self.target_prims]

    def evaluate(self, world):
        world = Gf.Matrix4d(world)
        result = {'target_prim_path': self.target, 'support_collider_path': self.support,
                  'candidate_pose': {'world_matrix': phase1.matrix_list(world), 'position_m': list(world.ExtractTranslation())},
                  'units': {'length': 'meter', 'angle': 'degrees', 'numerical_tolerance_m': EPS,
                            'transform_orthogonality_tolerance': 1e-8},
                  'legal_region_parameters': {'status': 'Prototype Assumption: pointwise predicate, not a certified free-space map',
                        'study_center_m': list(self.original_world.ExtractTranslation()), **asdict(self.settings)},
                  'geometry_assumptions': ['USD collision primitives, default-time snapshot; invisible guide proxies included.',
                     'Exact analytic upright circular cylinder / upright yaw-OBB extrusion tests for supported shapes.',
                     'All margins and study limits are Prototype Assumptions; touching/unsupported overlap yields UNKNOWN.',
                     'Signed separating-axis clearance is a conservative clearance, not a universal 3D distance.',
                     'No physics contact offsets, friction, mass or COM stability certification.']}
        if not upright_rigid_pose(world):
            return dict(result, final_status='UNKNOWN', rejection_reasons=[], unknown_reasons=['candidate_is_not_upright_unit_scale_rigid_world_pose'],
                        broad_phase={'status': 'NOT_RUN'}, narrow_phase={'status': 'NOT_RUN'}, support_result={'status': 'UNKNOWN'},
                        measured_clearance_or_penetration=None)
        shapes = self.virtual_shapes(world)
        support = support_check(shapes, self.floor, self.settings)
        center = world.ExtractTranslation()
        origin = self.original_world.ExtractTranslation()
        yaw = math.degrees(math.atan2(world[0][1], world[0][0]))
        original_yaw = math.degrees(math.atan2(self.original_world[0][1], self.original_world[0][0]))
        yaw_delta = (yaw - original_yaw + 180) % 360 - 180
        scope_reasons = []
        if any(abs(center[i] - origin[i]) > self.settings.study_xy_half_width_m + EPS for i in (0, 1)):
            scope_reasons.append('outside_prototype_local_study_region')
        if abs(yaw_delta) > self.settings.study_yaw_offset_max_degrees + 1e-6:
            scope_reasons.append('outside_prototype_yaw_study_range')
        nearby, broad_count, lower_bound = [], 0, math.inf
        for shape in shapes:
            for obstacle in self.obstacles:
                pair = pair_check(shape, obstacle, self.settings.obstacle_margin_m)
                lower_bound = min(lower_bound, pair['aabb_distance_lower_bound_m'])
                if pair['broad_phase'] == 'AABB_CLEARLY_SEPARATED':
                    broad_count += 1
                else:
                    nearby.append(dict(pair, target_collider=shape['path'], obstacle_collider=obstacle['path']))
        rejects = scope_reasons + (support.get('reasons', []) if support['status'] == 'REJECT' else [])
        rejects += [q['reason'] + ': ' + q['target_collider'] + ' vs ' + q['obstacle_collider'] for q in nearby if q['status'] == 'REJECT']
        unknowns = ([] if support['status'] != 'UNKNOWN' else list(support['reasons']))
        unknowns += [q['reason'] + ': ' + q['obstacle_collider'] for q in nearby if q['status'] == 'UNKNOWN']
        result.update(virtual_collision_proxies=shapes, support_result=support,
            broad_phase={'pair_count': len(shapes) * len(self.obstacles), 'clearly_separated_count': broad_count,
                         'overlap_or_near_count': len(nearby), 'minimum_aabb_distance_lower_bound_m': lower_bound,
                         'self_pairs_excluded': True, 'floor_pairs_routed_to_support_check': True},
            narrow_phase={'status': 'NOT_REQUIRED' if not nearby else 'EVALUATED', 'pairs': nearby},
            measured_clearance_or_penetration={'support': support,
                'pair_measurements': [{k: v for k, v in q.items() if k.endswith('_m') or k.endswith('_collider')} for q in nearby]},
            final_status='REJECT' if rejects else 'UNKNOWN' if unknowns else 'PASS',
            rejection_reasons=rejects, unknown_reasons=unknowns,
            local_study_result={'status': 'REJECT' if scope_reasons else 'PASS', 'yaw_offset_degrees': yaw_delta})
        return result
