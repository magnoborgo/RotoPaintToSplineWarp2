import nuke
nuke.tprint('Loading RotopaintToSplineWarp_v2.py')
try:
    from RotopaintToSplineWarp_v2 import *
except:
    pass

#===============================================================================
# BVFX ToolBar Menu definitions
#===============================================================================
toolbar = nuke.menu("Nodes")
bvfxt = toolbar.addMenu("BoundaryVFX Tools", "BoundaryVFX.png")
bvfxt.addCommand('Rotopaint to SplineWarp Nukev7', 'Roto_to_WarpSpline_v2()', 'F8', icon='bvfx_SplineW.png')
