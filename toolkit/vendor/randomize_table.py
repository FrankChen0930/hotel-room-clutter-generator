from pxr import Gf,Sdf,Usd,UsdGeom,UsdPhysics,UsdUtils
TARGET='/YAZHI_TWIN/Furniture/ROUND_BLACK_TABLE'

def matrix_list(matrix):
    return [[float(matrix[i][j]) for j in range(4)] for i in range(4)]
