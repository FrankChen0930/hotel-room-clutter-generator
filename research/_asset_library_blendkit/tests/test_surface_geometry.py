import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from surface_geometry import HeightMesh,fit_horizontal,footprint_grid

class SurfaceTests(unittest.TestCase):
    def test_actual_triangle_height_and_no_hole_fill(self):
        mesh=HeightMesh([[0,0,0],[1,0,1],[0,1,0]],[[0,1,2]])
        self.assertAlmostEqual(mesh.height(.2,.3),.2)
        self.assertIsNone(mesh.height(.8,.8))
    def test_relief_and_missing_support_rejected(self):
        mesh=HeightMesh([[0,0,0],[1,0,1],[0,1,0]],[[0,1,2]])
        self.assertIsNone(fit_horizontal(mesh,[[.1,.1],[.2,.1]],.008))
        self.assertIsNone(fit_horizontal(mesh,[[.1,.1],[.8,.8]],1))
    def test_flat_contact_measured_not_aabb_top(self):
        mesh=HeightMesh([[0,0,.3],[1,0,.3],[0,1,.3]],[[0,1,2]])
        fit=fit_horizontal(mesh,[[.1,.1],[.2,.1]])
        self.assertAlmostEqual(fit['z'],.3)
        self.assertAlmostEqual(fit['max_clearance_m'],.001)
    def test_footprint_sampling_includes_rotated_corners(self):
        points=footprint_grid([[-.1,-.2,0],[.1,.2,.1]],1,2,0)
        self.assertEqual(len(points),81);self.assertEqual(points[0],[.9,1.8])
    def test_peak_is_clipped_not_whole_mesh_aabb(self):
        mesh=HeightMesh([[0,0,0],[1,0,1],[0,1,0]],[[0,1,2]])
        self.assertAlmostEqual(mesh.peak_over_polygon([[.1,.1],[.3,.1],[.3,.3],[.1,.3]]),.3)
    def test_peak_catches_unsampled_interior_spike(self):
        mesh=HeightMesh([[0,0,0],[1,0,0],[1,1,0],[0,1,0],[.37,.41,.1]],[[0,1,4],[1,2,4],[2,3,4],[3,0,4]])
        self.assertAlmostEqual(mesh.peak_over_polygon([[0,0],[1,0],[1,1],[0,1]]),.1)

if __name__=='__main__':unittest.main()
