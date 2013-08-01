import nuke, nukescripts, nuke.rotopaint as rp, nuke.splinewarp as sw, math
import time, threading
import sys

def rptsw_walker(obj, list):
    for i in obj:
        x = i.getAttributes()  
        if isinstance(i, nuke.rotopaint.Shape):
            list.append([i, obj]) 
        if isinstance(i, nuke.rotopaint.Layer):
            list.append([i, obj])
            rptsw_walker(i, list)
    return list

    
def rptsw_TransformToMatrix(point, transf, f):
    
    extramatrix = transf.evaluate(f).getMatrix()
    vector = nuke.math.Vector4(point[0], point[1], 1, 1)
    x = (vector[0] * extramatrix[0]) + (vector[1] * extramatrix[1]) + extramatrix[2] + extramatrix[3]
    y = (vector[0] * extramatrix[4]) + (vector[1] * extramatrix[5]) + extramatrix[6] + extramatrix[7]
    z = (vector[0] * extramatrix[8]) + (vector[1] * extramatrix[9]) + extramatrix[10] + extramatrix[11]
    w = (vector[0] * extramatrix[12]) + (vector[1] * extramatrix[13]) + extramatrix[14] + extramatrix[15]
    vector = nuke.math.Vector4(x, y, z, w)
    vector = vector / w
    return vector
  
def rptsw_TransformLayers(point, Layer, f, rotoRoot, rptsw_shapeList):
    if Layer == rotoRoot:
 
        transf = Layer.getTransform()
        newpoint = rptsw_TransformToMatrix(point, transf, f)
       
    else:

        transf = Layer.getTransform()
        newpoint = rptsw_TransformToMatrix(point, transf, f)
        for x in rptsw_shapeList: #look the layer parent
            if x[0] == Layer:
                newpoint = rptsw_TransformLayers(newpoint, x[1], f, rotoRoot, rptsw_shapeList)
    return newpoint

def rptsw_Relative_transform(relPoint, centerPoint, centerPointBaked, transf, f, rotoRoot, rptsw_shapeList, shape):
    transfRelPoint = [0,0]
    count = 0
    for pos in relPoint:
        transfRelPoint[count] = centerPoint[count] + (relPoint[count] * -1)
        count +=1
    transfRelPoint = rptsw_TransformToMatrix(transfRelPoint, transf, f)                             
    transfRelPoint = rptsw_TransformLayers(transfRelPoint, shape[1], f, rotoRoot, rptsw_shapeList)
    count = 0
    for pos in relPoint:    
        relPoint[count] = (transfRelPoint[count] + (centerPointBaked[count] * -1)) *-1
        count+=1
    return relPoint

  
def breakshapesintoPin(rotoNode, fRange):
    global cancel
    task = nuke.ProgressTask( 'Break Roto into Pins' )
    rptsw_shapeList = []
    curveKnob = rotoNode['curves']
    rotoRoot = curveKnob.rootLayer
    rptsw_shapeList = rptsw_walker(rotoRoot, rptsw_shapeList)  
    removalList =[]
    for shape in rptsw_shapeList:
        if cancel:
            return
        if isinstance(shape[0], nuke.rotopaint.Shape):
            removalList.append(shape)
            pt = 0
            for points in shape[0]:
                if task.isCancelled():
                    cancel = True
                if cancel:
                    break
                task.setMessage( 'Creating Pin From ' + shape[0].name + ' point ' + str(pt+1) + " of " + str(len(shape[0])) )   
                newPointShape = rp.Shape(curveKnob, type="bspline")
                newPoint = rp.ShapeControlPoint(0,0)
                for f in fRange:
                    task.setProgress( int( float(f)/fRange.last() * 100 ) )
                    point = [points.center.getPositionAnimCurve(0).evaluate(f),points.center.getPositionAnimCurve(1).evaluate(f)]
                    newPoint.center.addPositionKey(f, (point[0],point[1]))
                    transf = shape[0].getTransform()
                    center_xy = rptsw_TransformToMatrix(point, transf, f)                    
                    center_xy = rptsw_TransformLayers(center_xy, shape[1], f, rotoRoot, rptsw_shapeList)
                    newPoint.center.addPositionKey(f, (center_xy[0],center_xy[1] ))
                newPointShape.name = "%s_PIN[%s]" % (shape[0].name, str(pt))
                newPointShape.append(newPoint)
                rotoRoot.append(newPointShape)
                pt +=1
    for shape in removalList:
        print "removal:" ,shape[0].name, shape[1].name
        for item in reversed(range(len(shape[1]))):
            if shape[0].name == shape[1][item].name:
                shape[1].remove(item)



def bakeShapes(shape, warpNode, fRange, rotoRoot, rptsw_shapeList,task):
    global cancel
    count = 0
    warpCurve = warpNode['curves']
    warpRoot = warpCurve.rootLayer  
    shapeattr = shape[0].getAttributes()
    transf = shape[0].getTransform()
    shapeattr.add("ab",1)
    for points in shape[0]:
        task.setMessage( 'baking ' + shape[0].name + ' point ' + str(count+1) + " of " + str(len(shape[0])) )#
        if cancel:
            return
        newpoint = points
        newtypes = [newpoint.center,newpoint.leftTangent, newpoint.rightTangent, newpoint.featherLeftTangent, newpoint.featherRightTangent]
        #===============================================================
        # bake all the keyframes before starting processing points
        #===============================================================
        for f in fRange:
            task.setProgress(int( float(f)/fRange.last() * 100 ))
            if task.isCancelled():
                cancel = True
                break                
            if cancel:
                break
            
            transf.addTransformKey(f)
            point = [points.center.getPositionAnimCurve(0).evaluate(f),points.center.getPositionAnimCurve(1).evaluate(f)]
            newtypes[0].addPositionKey(f, (point[0],point[1]))
        #===============================================================
        # end of baking process
        #===============================================================
        for f in fRange:
            if task.isCancelled():
                cancel = True
                break                
            if cancel:
                break
            
            transf.addTransformKey(f)
            point = [points.center.getPositionAnimCurve(0).evaluate(f),points.center.getPositionAnimCurve(1).evaluate(f)]
            newtypes[0].addPositionKey(f, (point[0],point[1]))
                
            point_lt =[points.leftTangent.getPositionAnimCurve(0).evaluate(f),points.leftTangent.getPositionAnimCurve(1).evaluate(f)]
            point_rt =[points.rightTangent.getPositionAnimCurve(0).evaluate(f),points.rightTangent.getPositionAnimCurve(1).evaluate(f)]
            transf = shape[0].getTransform()
            center_xy = rptsw_TransformToMatrix(point, transf, f)                    
            center_xy = rptsw_TransformLayers(center_xy, shape[1], f, rotoRoot, rptsw_shapeList)
            newtypes[0].addPositionKey(f, (center_xy[0],center_xy[1] ))
        #===============================================================
        # lock feather into the main-point, tangents ignored 
        # disabled for the moment
        #===============================================================
        # list = ['main.x','main.y']#,'left.x','left.y','right.x','right.y']
        # types = [points.featherCenter]#, points.featherLeftTangent, points.featherRightTangent]
        # y = 0
        # for n in range(0,len(types)*2,2):
        #     newcurve = nuke.rotopaint.AnimCurve()
        #     newcurve.useExpression = True
        #     newcurve.expressionString = "%s.curves.%s.curve.%s.%s" % (rotoNode.name(), shape[0].name, count, list[n])
        #     types[y].setPositionAnimCurve(0, newcurve)
        #     newcurve = nuke.rotopaint.AnimCurve()
        #     newcurve.useExpression = True
        #     newcurve.expressionString = "%s.curves.%s.curve.%s.%s" % (rotoNode.name(), shape[0].name, count, list[n+1])
        #     types[y].setPositionAnimCurve(1, newcurve)
        #     y+=1
        count+=1
        #===============================================================
        
    transf = shape[0].getTransform()                    
    for f in fRange:            
        transf.removeTransformKey(f) 
    transf.reset()
    #===========================================================================
    # move shapes to new home
    #===========================================================================
    warpRoot.insert(0,shape[0])


def Roto_to_WarpSpline_v2():
    try:
        rotoNode = nuke.selectedNode()
        if rotoNode.Class() not in ('Roto', 'RotoPaint'):
            if nuke.GUI:
                nuke.message( 'Unsupported node type. Selected Node must be Roto or RotoPaint' )
            return
    except:
        if nuke.GUI:
            nuke.message('Select a Roto or RotoPaint Node')
            return
    #===========================================================================
    # panel setup
    #===========================================================================
    p = nukescripts.panels.PythonPanel("RotoPaint to Splinewarp")
    k = nuke.String_Knob("framerange","FrameRange")
    k.setFlag(nuke.STARTLINE)    
    k.setTooltip("Set the framerange to bake the shapes, by default its the project start-end. Example: 10-20")
    p.addKnob(k)
    k.setValue("%s-%s" % (nuke.root().firstFrame(), nuke.root().lastFrame()))    
    k = nuke.Boolean_Knob("pin", "Break into Pin Points")
    k.setFlag(nuke.STARTLINE)
    k.setTooltip("This will break all the shapes into single points")
    p.addKnob(k)
    k = nuke.Boolean_Knob("mt", "MultiThread")
    k.setFlag(nuke.STARTLINE)
    k.setTooltip("This will speed up the script but without an accurate progress bar")
    p.addKnob(k)
    k.setValue(True)
    result = p.showModalDialog()    
    
    if result == 0:
        return # Canceled
    try:
        fRange = nuke.FrameRange(p.knobs()["framerange"].getText())
    except:
        if nuke.GUI:
            nuke.message( 'Framerange format is not correct, use startframe-endframe i.e.: 0-200' )
        return
    breakintopin = p.knobs()["pin"].value()
    multi = p.knobs()["mt"].value()
    #===========================================================================
    # end of panel
    #===========================================================================
    start_time = time.time()
#     task = nuke.ProgressTask('Roto to SplineWarp')
    rptsw_shapeList = []
    global cancel
    cancel = False
    if nuke.NUKE_VERSION_MAJOR > 6:
#         global cancel
        rptsw_shapeList = []
        nukescripts.node_copypaste()
        rotoNode = nuke.selectedNode()
        warpNode = nuke.createNode('SplineWarp3')
        warpNode.setName(rotoNode.name()+ "_" +  warpNode.name())
        warpCurve = warpNode['curves']
        warpRoot = warpCurve.rootLayer   
        rotoCurve = rotoNode['curves']
        rotoRoot = rotoCurve.rootLayer
        rptsw_shapeList = rptsw_walker(rotoRoot, rptsw_shapeList)  
        if breakintopin:
            breakshapesintoPin(rotoNode,fRange)  
            rptsw_shapeList = []
            rptsw_shapeList = rptsw_walker(rotoRoot, rptsw_shapeList)
        if cancel:
            return
        threadlist =[]
        n=0
        task = nuke.ProgressTask( 'Roto to SplineWarp' )
        bar = len(rptsw_shapeList) + 1
        for shape in rptsw_shapeList:
            if isinstance(shape[0], nuke.rotopaint.Shape):
                if multi:
                    task.setMessage( 'Processing' + shape[0].name )
                    task.setProgress((int(n/bar*100)))
                    threading.Thread(None, bakeShapes, args=(shape, warpNode, fRange, rotoRoot, rptsw_shapeList, task)).start() 
                else:
                    bakeShapes(shape, warpNode,fRange, rotoRoot, rptsw_shapeList,task)
            n+=1
        #===========================================================================
        #  join existing threads (to wait completion before continue)
        #===========================================================================
        main_thread = threading.currentThread()
        for t in threading.enumerate():
            if t is main_thread:
                continue
            t.join()
        
        warpCurve.changed()
        warpNode.knob('toolbar_output_ab').setValue(1)
        nuke.selectedNode().knob('selected').setValue(False)
        nuke.delete(rotoNode)
        rptsw_shapeList = []
    else:
        nuke.message( 'This version is for Nuke v7, use v1.1 with Nuke v6.3 from Nukepedia' )
    rptsw_shapeList = []
    if cancel:
        nuke.undo()
    print "Time elapsed:",time.time() - start_time, "seconds"
#runs the script on script editor
if __name__ == '__main__':
    Roto_to_WarpSpline_v2()