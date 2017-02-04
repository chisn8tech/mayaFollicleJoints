'''
API of the Chisholm pipeline
'''

import pymel.core as pm

def filterSelectionForShapeType(objs=None, typ='nurbsSurface', ni=1):
    # Look for object type in objs, then in selection, then in components' objects
    outShapes = []
    
    # Filter input values, use selection if not objects supplied
    nicerError = ''
    if not type(typ) is list: typ = [typ]
    if objs:
        if type(objs) is not list: objs = [objs]
    else:
        objs = pm.ls(sl=1, typ=typ+['transform'])
        if not objs:
            objs = pm.ls(sl=1)
        nicerError = ' in selection'
    
    if objs:
        # Find all transforms and relevant shapes in the object list
        xforms = pm.ls(objs, typ='transform')
        shapes = pm.ls(objs, typ=typ)
        if not shapes: shapes = []
        # Get all non-intermediate children, of the shape type, under the transform nodes
        if xforms:
            for xform in xforms:
                testShapes = xform.getChildren(typ=typ, ni=ni)  
                if testShapes: shapes.extend(testShapes)
        
        # If no shape is found in objects or shapes, look for any in components
        if not shapes:
            for obj in objs:
                if '.' in str(obj):
                    node = obj.node()
                    if pm.ls(node, typ=typ, ni=ni):
                        shapes.append(pm.PyNode(node))
        
        # Remove duplicates
        allSet = set()
        
        for shape in shapes:
            if not shape in allSet:
                outShapes.append(shape)
                allSet.add(shape)
    
    if not outShapes:
        raise TypeError("No objects of type %s were found%s!" % (
            "/".join(typ), nicerError
            ))
    
    return outShapes

    
def getPointPositions(objs=[]):
    #Get objects
    if not objs:
        objs = pm.ls(sl=1, fl=1)
        if not objs: raise TypeError('No points or objects found!')
    else:
        objs = pm.ls(objs, fl=1)
            
    # Get points of objects
    posList = []
    for obj in objs:
        if '.' in str(obj):
            # Get position of component
            posList.append(pm.pointPosition(obj, w=1))
        else:
            posList.append(pm.xform(obj, q=1, ws=1, rp=1))  # Or try parent constraint to grp
            
    return posList
    
    