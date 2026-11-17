"""Conservative visual-footprint and AABB operations, adapted from Hotel geometry."""
import math


def rotated_bounds(bounds,yaw,x=0.,y=0.,z=0.):
    lo,hi=bounds;c=math.cos(yaw);s=math.sin(yaw)
    points=[(c*a-s*b+x,s*a+c*b+y) for a,b in [(lo[0],lo[1]),(hi[0],lo[1]),(hi[0],hi[1]),(lo[0],hi[1])]]
    box=[[min(p[0] for p in points),min(p[1] for p in points),lo[2]+z],
         [max(p[0] for p in points),max(p[1] for p in points),hi[2]+z]]
    return points,box


def intersects(a,b,margin=0.):
    return all(a[0][i]<b[1][i]+margin and a[1][i]>b[0][i]-margin for i in range(3))


def obstacle_hit(box,obstacle):
    return any(intersects(box,piece) for piece in obstacle['triangle_bounds']) if 'triangle_bounds' in obstacle else intersects(box,obstacle['bounds'])


def forbidden_hit(box,regions):
    from .adapters import area,intersection,convex_hull
    footprint=[[box[0][0],box[0][1]],[box[1][0],box[0][1]],[box[1][0],box[1][1]],[box[0][0],box[1][1]]]
    for region in regions:
        if 'bounds' in region:
            if intersects(box,region['bounds']):return True
        elif 'polygon' in region and 'z_range' in region:
            if box[0][2]<region['z_range'][1] and box[1][2]>region['z_range'][0] and area(intersection(footprint,convex_hull(region['polygon'])))>1e-10:return True
        else:raise ValueError('UNKNOWN_FORBIDDEN_REGION')
    return False
