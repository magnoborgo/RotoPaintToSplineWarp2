import nuke
nuke.tprint('Loading freezeSplineWarp_v3.py')
try:
    from freezeSplineWarp_v3 import *
    from RotopaintToSplineWarp_v3 import *
except:
    pass

# #===============================================================================
# # BVFX ToolBar Menu definitions
# #===============================================================================
toolbar = nuke.menu("Nodes")
bvfxt = toolbar.addMenu("BoundaryVFX Tools", "BoundaryVFX.png")
bvfxt.addCommand('Rotopaint > FreezeWarp', 'combo()','F8', icon='bvfx_SplineF.png')

def combo():
    Roto_to_WarpSpline_v3()
    freezeWarp_v3()