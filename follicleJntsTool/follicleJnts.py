"""
#
# follicleJnts.py
# Version 1.02.00
#
# Based off my earlier follicleTools.py tool, version 1.09.00, with 
# significant improvements, especially in terms of versatility.
#
# @author Nathan Chisholm
# @email nathanchisholm.cgartist@gmail.com
# @web nathanchisholm.weebly.com
#
# --------------------------------------------------------------------
# Scripts for dealing with joint follicles on patches or ribbons.
#
"""


import sys
import re
import string

import pymel.core as pm

from follicleJntsTool import customQueries as cq
reload(cq)


class FolJntType(object):
    """
    This class represents follicle joint node and control arrangements.
    
    Supported base configurations (typeStrings): 
    (where f=follicle, t=transform, j=joint,
    / shape under, - transform under)
    Default follicle:         t/f    
        (follicle shape under transform; follicle drives transform)
        - Cannot be skinned to; used for ribbon control offsets;
    Standard follicle joint:  t/f-j  
        (follicle shape under transform; follicle drives transform)
        - Can be skinned to, supports extra offset;
    Reverse follicle joint:   t-j/f  
        (follicle shape under joint; follicle drives transform)
        - Can be skinned to, but disrupts the skinning RMB popup in 
        some maya versions; supports extra offset;
    Simplest follicle joint:  j/f    
        (follicle shape under joint; follicle drives joint)
        - Can be skinned to but disrupts the skinning RMB popup in 
        some maya versions.
    """
    
    _typeNames = {
        't/f':'defaultFollicle', 
        't/f-j':'follicleJointStandard', 
        't-j/f':'follicleJointReverse', 
        'j/f':'follicleJoint'
        }
    
    validTypes = _typeNames.keys()
    defaultType = validTypes[1]
    renameFormats={
        'main':"{pre}{num}{suf}",
        'j':"{pre}_J_{num}{suf}"
        }

    
    def __init__(self, typeString=None):
        self._name = None
        self._typeString = None  # property
        
        # Attribute for identifying which node has the main UV parameters;
        # This can be overridden by FollicleJoint.getFollicleJoint.
        self.controlNode = None
        
        # Populate attributes if possible
        if typeString:
            self.set(typeString)
        
    def __str__(self):
        if self.name is None: return 'Unnamed FollicleJoint'
        return self.name
        
    def __repr__(self):
        try:
            return '%s(%r)' % (self.__class__.__name__, self.typeString)
        except AttributeError:
            return '%s()' % self.__class__.__name__
    
    @property
    def typeString(self):
        """The DNA of the follicle type. Defines it's structure."""
        if self._typeString:
            return self._typeString
        else:
            raise AttributeError("typeString value has not been assigned!")
    
    @typeString.setter
    def typeString(self, value):
        self.set(value)
    
    @property
    def hasTransform(self):
        return 't' in self.typeString
    
    @property
    def hasJoint(self):
        return 'j' in self.typeString
    
    @property
    def hasOffsetTransform(self):
        return self.hasTransform and self.hasJoint
        
    @property
    def topTransform(self):
        if self.hasTransform:
            return 't'
        elif self.hasJoint:
            return 'j'
        else:
            raise AttributeError("Error identifying top transform!")
    
    @property
    def follicleParent(self):
        return self.typeString.partition('/f')[0][-1]
    
    @property
    def name(self):
        if self._name is None: 
            self._name = self._typeNames[self.typeString]
        return self._name
        
        
    def set(self, typeString):
        # For debugging only - ensure a valid type string was given
        vStrs = self.validTypes
        assert typeString in vStrs, (
            "%r is not a valid follicle joint type string!\n"
            "Valid types are '%s' or '%s'." % (
                typeString, "', '".join(vStrs[:-1]), vStrs[-1])
            )
            
        self._typeString = typeString
        
        # Set the default control node (joint if joint exists)
        if self.hasJoint:
            self.controlNode = 'j'
        else:
            self.controlNode = 'f'


class FollicleJoint(object):
    """FollicleJoint Maya node structure and methods.
    
    This class represents a setup where a joint object is driven by a 
    follicle object along a surface, with additional setups to 
    improve rigging workflow.
    """
    
    sidePrefix = ['L_', 'R_', 'M_']
    
    _sideChars = ['l', 'r', 'm']
    
    def __init__(self, folObject=None):
        """
        if 'folObject' is supplied, attempt to populate the class details.
        """
        # Initialise main node variables (follicle, transform and joint)
        self.fol = None
        self.xfm = None
        self.jnt = None
        
        # Initialise secondary node variables
        self._patch = None  # property
        self._controlObj = None  # property
        self._nameObj = None  # property
        #self.topObj = None  # property
        #self.allDagObjs = None  # property
        
        # Initialise other attributes
        #self.name = None  # property
        self._side = None  # property
        #self.isSide = None  # property
        self.type = None
        self.uv = None
        #self.uvDriverAttrs = None  # property
        #self.uvDriverRatio = None  # property
        #self.jntRadius = None  # property (on get)
        
        self.verbose = True
        
        # If an object is given when initialised, populate the class details
        if folObject:
            if not isinstance(folObject, list):
                folObject = [folObject]
            self.set(folObject)
    
    def __str__(self):
        return "%s of type '%s'; follicle node: '%s'" % (
            self.__class__.__name__, self.type, self.fol)
        
    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.fol)
        
    @property
    def controlObj(self):
        # Returns the uv parameter driver object
        if self.type is not None and self.type.controlNode:
            if not self._controlObj:
                self._controlObj = {
                    'f':self.fol, 't':self.xfm, 'j':self.jnt
                    }[self.type.controlNode]
            return self._controlObj
    
    @property
    def allDagObjs(self):
        """Return all DAG nodes, listing shapes last."""
        tempList = []
        for attr in ['xfm', 'jnt', 'fol']:
            checkObj = self.__dict__[attr]
            if checkObj:
                tempList.append(checkObj)
        return tempList
    
    @property
    def topObj(self):
        """The top of the follicle joint hierarchy"""
        if self.xfm:
            # If the transform is not the parent, it isn't relevant to 
            # the FollicleJoint.
            return self.xfm
        elif self.jnt:
            return self.jnt
        else:
            return None
        
    @property
    def nameObj(self):
        """The object that is named directly rather than with a suffix.
        
        If the FollicleJoint type contains a transform, the transform is used.
        """
        if not self.type: return None
        return {'t':self.xfm, 'j':self.jnt}[self.type.topTransform]
        
    @property
    def name(self):
        if self.nameObj is None: return None
        return self.nameObj.name()
        
    @name.setter
    def name(self, value):
        """If possible, rename the objects, using default rename args."""
        if self.nameObj is None: return
        if not isinstance(value, basestring):
            raise AttributeError("name attribute takes a string argument!")
        if value != self.nameObj.name():
            self.rename(name=value)
    
    @property
    def jntRadius(self):
        """A wrapper of the joint radius attribute"""
        if not self.jnt: return None
        return self.jnt.radius.get()
    
    @jntRadius.setter
    def jntRadius(self, value):
        if not self.jnt: return
        self.jnt.radius.set(value)
    
    @property
    def patch(self):
        if not self._patch:
            if self.fol:
                # Find the patch shape (mesh or nurbSurface)
                fol = self.fol
                nurbs = fol.inputSurface.inputs(t='nurbsSurface', shapes=1)
                meshs = fol.inputMesh.inputs(t='mesh', shapes=1)
                
                patch = None
                if nurbs:
                    patch = nurbs[0]
                elif meshs:
                    patch = meshs[0]
                else:
                    return False
                
                self._patch = patch
            else:
                self._patch = None
        return self._patch
    
    @patch.setter
    def patch(self, value):
        testPatch = pm.ls(value, typ=['nurbsSurface', 'mesh'])
        if testPatch:
            self._patch = testPatch
        else:
            raise AttributeError("Invalid patch surface!")
    
    @property
    def side(self):
        # Derive the side value (r, l or m for right, left, middle)
        if not self._side:
            nameStr = self.name
            if not nameStr:
                nameStr = self.fol.name()
            if not nameStr: return None
            
            for i in range(len(self.sidePrefix)):
                if nameStr.startswith(self.sidePrefix[i]):
                    self._side = self._sideChars[i]
                    break
            else:
                self._side = self._sideChars[2]  # Middle
        return self._side
    
    @side.setter
    def side(self, sideVal):
        # Only sets on the class; doesn't rename the objects
        if sideVal in self._sideChars:
            self._side = sideVal
        elif sideVal in self.sidePrefix:
            for i in range(len(self.sidePrefix)):
                if self.sidePrefix[i] == sideVal:
                    self._side = self._sideChars[i]
        else:
            raise AttributeError(
                "Invalid side value given! Valid values are '%s' or '%s'" % (
                    "', '".join(self.sidePrefix), 
                    "', '".join(self._sideChars))
                )
    
    @property
    def isSide(self):
        """Return True if left or right, False if middle, None if unknown"""
        if self.side is None: return None
        return self.side in self._sideChars[:2]
    
    @property
    def uvDriverAttrs(self):
        controlObj = self.controlObj
        if controlObj is None: return
        return (pm.attributeQuery('ou', n=controlObj, ex=1) and 
            pm.attributeQuery('ov', n=controlObj, ex=1))
    
    @property
    def uvDriverRatio(self):
        controlObj = self.controlObj
        if controlObj is None: return None
        
        uvRatio = []
        uvDrivNodes = self._driverRatioNodes
        if not uvDrivNodes: return None
        
        for i in range(2):
            if uvDrivNodes[i] is None:
                uvRatio.append(None)
            else:
                uvRatio.append(uvDrivNodes[i].i2.get())
        return uvRatio
    
    @property
    def _driverRatioNodes(self):
        """Return the nodes linking the offset values to the final uv"""
        uvRatioNodesFound = False
        uvRatioNodes = []
        controlObj = self.controlObj
        uvDrvAttrs = [controlObj.ou, controlObj.ov]
        folAttrs = [self.fol.pu, self.fol.pv]
        for i in range(2):
            # Check for slow attr node through inputs (as outputs may be 
            # connected to other things)
            uvRatioNode = None
            offsetAdd = folAttrs[i].inputs(t='addDoubleLinear')
            if offsetAdd:
                offsetDriver = offsetAdd[0].i2.inputs(t='multDoubleLinear')
                if offsetDriver:
                    offsetAttrChk = offsetDriver[0].i1.inputs(p=1)
                    if offsetAttrChk[0] == uvDrvAttrs[i]:
                        uvRatioNode = offsetDriver[0]
                        uvRatioNodesFound = True
            uvRatioNodes.append(uvRatioNode)
        
        if uvRatioNodesFound:
            return uvRatioNodes
        else:
            return None
        
    @property
    def _linkRatioAttrs(self):
        """Return the nodes linking other follicle joints to this one"""
        linkDriverFound = False
        linkRatioNodes = []
        controlObj = self.controlObj
        uvDrvAttrs = [controlObj.ou, controlObj.ov]
        for i in range(2):
            # Search for mult nodes connected to the control node;
            # Recursive search if add nodes merge multiple drivers.
            linkRatioNodes.append([])
            startAttrs = [uvDrvAttrs[i]]
            for attr in startAttrs:
                offsetInp = uvDrvAttrs[i].inputs()
                if offsetInp:
                    if offsetInp[0].type() == 'multDoubleLinear':
                        # offsetInp[0] is a link scale (mult) node
                        linkScaleDriver = offsetInp[0].i2.inputs(p=1)
                        if not linkScaleDriver:
                            # Attr directly on mult
                            linkRatioNodes[i].append(offsetInp[0].i2)
                            linkDriverFound = True
                        elif linkScaleDriver[0].node() == controlObj:
                            # Attr on control object
                            linkRatioNodes[i].append(linkScaleDriver[0])
                            linkDriverFound = True
                    elif offsetInp[0].type() == 'addDoubleLinear':
                        # offsetInp[0] is a connection merge (add) node
                        startAttrs.extend([offsetInp[0].i1, offsetInp[0].i2])
        
        if linkDriverFound:
            return linkRatioNodes
        else:
            return
    
    
    def new(self, patch=None, name=None, uv=[0.5, 0.5], folType='t/f-j',
            jntRadius=0.1, attrs=True, uvDriverRatio=0.1,
            normaliseUV=False, warnNormalised=True,
            useSmoothedMesh=False, nameFormats=None):
        """Create a new follicle, with the given settings.
        
        patch: (string/PyObj) mesh or nurbSurface object
        
        name: (string) name, with '#' to add a unique number
        
        uv: follicle u and v parameter values eg. [0.5, 0.5]
        
        folType: one of 't/f', 't/f-j', 't-j/f', 'j/f';
         see help(FolJntType) for more info
        
        jntRadius: joint radius
        
        attrs: if this is false, no attributes are created to drive the
         uv parameters, so the follicle must be selected manually.
        
        uvDriverRatio: default 0.1 means the offset attribute values
         are scaled by 10.
        
        normaliseUV: only affects nurbsSurfaces.  If true, the supplied
         uv values are treated as actual surface u and v values instead
         of normalised (0-1) values. (Which they will be converted to.)
        
        warnNormalised: print a warning if the nurbsSurface uv limits
         aren't (0-1)
        
        useSmoothedMesh: only affects meshes. If True, the smooth
         ('3' or display smooth) mesh is used as the surface.
        
        nameFormats: default is FolJntType.renameFormats; which adds
         the '_J_' string in front of the #/number in the name.
         Supplying an alternative dict (or supplying a FolJntType
         instance with customised .renameFormats) can allow a
         different convention to be used.
        """
        
        if uvDriverRatio and not isinstance(uvDriverRatio, list):
            uvDriverRatio = [uvDriverRatio, uvDriverRatio]
        
        # Create a new follicle on the surface at the given position
        returnList = []
        
        # Get patch
        patchTest = cq.filterSelectionForShapeType(
            patch, ['nurbsSurface', 'mesh'])[0]
        if patchTest:
            self._patch = patchTest
        patchIsNurb = pm.objectType(self.patch, i='nurbsSurface')
        
        # Adjust UV for UV ranges if not Normalised
        self.uv = list(uv)
        if patchIsNurb:
            self.uv = normalisedNurbsUV(
                self.patch, uv, warningOnly=not normaliseUV,
                giveWarning=warnNormalised)
        
        # Set the type specifier object (create new FolJntType if required)
        if isinstance(folType, FolJntType):
            self.type = folType
        else:
            if not folType:
                folType = FolJntType.defaultType
            # Create type object, or error if folType string is invalid.
            self.type = FolJntType(folType)
        
        # Generate a name if none supplied
        if nameFormats is None:
            nameFormats = dict(self.type.renameFormats)
        if not name:
            name = '%s_fol#' % str(self.patch.getParent())
        
        # Create a follicle
        fol = pm.createNode('follicle', ss=1)
        self.fol = fol
        folXform = fol.getParent()
        if self.type.hasTransform:
            self.xfm = folXform
        #folXform = pm.rename(fol.getParent(), 'tempName#')
        #fol = folXform.getShape()
        
        returnList = [fol, folXform, self.patch]
        
        paramObj = fol
        if self.type.hasJoint:
            # Create a joint (under the follicle transform if necessary)
            if self.type.topTransform == 't':
                newJnt = pm.createNode('joint', p=folXform, ss=1)
            else:
                newJnt = pm.createNode('joint', ss=1)
            #newJnt = pm.createNode('joint', p=folXform, n=jntName, ss=1)
            
            self.jnt = newJnt
            newJnt.radius.set(jntRadius)
            
            returnList.append(newJnt)
        
        if attrs:
            if self.type.controlNode == 'j':
                ctrlNode = self.jnt
            else:
                ctrlNode = self.xfm
            
            # Add attributes to adjust the follicle position with
            pm.addAttr(ctrlNode, ln='parameterU', sn='pu', k=1)
            pm.addAttr(ctrlNode, ln='parameterV', sn='pv', k=1)
            pm.addAttr(ctrlNode, ln='offsetU', sn='ou', k=1)
            pm.addAttr(ctrlNode, ln='offsetV', sn='ov', k=1)
            
            nameBase = name.rpartition('_')[0]
            for i in range(2):
                uvStr = ['U', 'V'][i]
                uvLow = uvStr.lower()
                ofName = '%saddOffset%s_#' % (nameBase, uvStr)
                offsetAdd = pm.createNode(
                    'addDoubleLinear', n=ofName, ss=1)
                
                offsetAttr = '%s.o%s' % (ctrlNode, uvLow)
                if uvDriverRatio and uvDriverRatio[i]:
                    # Multiply the offset value by .1 to enable fineTuning
                    mlName = '%saddOffset%s_#' % (nameBase, uvStr)
                    offsetMult = pm.createNode(
                        'multDoubleLinear', n=mlName, ss=1)
                    offsetMult.i2.set(uvDriverRatio[i])
                    
                    pm.connectAttr(offsetAttr, offsetMult.i1)
                    offsetAttr = offsetMult.o
                
                pm.connectAttr('%s.p%s' % (ctrlNode, uvLow), offsetAdd.i1)
                pm.connectAttr(offsetAttr, offsetAdd.i2)
                pm.connectAttr(offsetAdd.o, '%s.p%s' % (fol, uvLow))
            
            if self.type.controlNode == 'j':
                # Hide the follicle shape
                fol.visibility.set(0)
            paramObj = ctrlNode
        
        # Reparent the follicle if necessary
        topTransform = folXform
        if self.type.follicleParent == 'j':
            pm.parent(self.fol, self.jnt, r=1, s=1)
            # Delete the original follice transform if not required.
            if not self.type.hasTransform:
                pm.delete(folXform)
        if self.type.topTransform == 'j':
            topTransform = self.jnt
        
        # Set up the follicle
        pm.connectAttr(fol.outTranslate, topTransform.t)
        pm.connectAttr(fol.outRotate, topTransform.r)
        pm.connectAttr(self.patch.worldMatrix[0], fol.inputWorldMatrix)
        if patchIsNurb:
            pm.connectAttr(self.patch.local, fol.inputSurface)
        elif useSmoothedMesh:
            pm.connectAttr(self.patch.outSmoothMesh, fol.inputMesh)
        else:
            pm.connectAttr(self.patch.outMesh, fol.inputMesh)
        
        paramObj.parameterU.set(self.uv[0])
        paramObj.parameterV.set(self.uv[1])
        
        # Name the objects
        self.rename(name, skipPreRename=True, renameFormats=nameFormats)
        
        # Populate object values 
        # Should be able to be optimised by setting values here instead
        self.set(fol)
        
        return returnList
        
    def set(self, folObject=None):
        """Populate the self.fol, xfm and jnt fields if possible."""
        if not folObject:
            raise StandardError(
                "Please supply the name or PyObject "
                "that you want to treat as a FollicleJoint")
        self.getFollicleJoint(folObject)
        
    def getFollicleJoint(self, folObject=None, strict=True):
        """Populate the self.fol, xfm and jnt fields if possible.
        
        Looks for the relevant nodes in the scene.
        If 'strict' is specified, if any input object cannot be 
        identified as a sub follicle joint node, an exception is 
        raised.  Returns True if successful.
        """
        # Look for object type in objs, then in selection, 
        # then in components' objects
        # Return None if no match, unless 'strict'

        # Filter input values
        if not isinstance(folObject, list):
            folObject = [folObject]
        
        # Get as pymel object(s) (raise error if none found)
        objs = pm.ls(folObject)
        if not objs:
            raise StandardError(
                "No objects found for the given name(s) %s!" % (
                    ', '.join(folObject)))
        
        # Try to identify a valid follicle joint setup
        for obj in objs:
            # [transform, follicle, joint]
            possibleItem = [None, None, None]
            tmpFol = None
            folName = None
            folFormat = None
            
            # Setup must always include a 'follicle' shape node;
            # Setup may contain a 'joint' and/or 'transform'
            # A 'transform' is only relevant if it's the direct parent 
            # of a 'follicle' or 'joint'

            # Locate the follicle
            curType = obj.type()
            if curType == 'follicle':
                # Selection is follicle
                tmpFol = obj
            elif curType in ['transform', 'joint']:
                # Selection is joint; find follicle.
                fols = obj.getShapes(typ='follicle', ni=1)
                if not fols:
                    if curType == 'joint':
                        fols = obj.getSiblings(typ='follicle', ni=1)
                    else:
                        jnts = obj.getChildren(typ='joint')
                        if jnts:
                            # Could almost finish off here, but it's best to 
                            # leave it for connection checks later
                            fols = jnts[0].getShapes(typ='follicle', ni=1)
                if fols:
                    tmpFol = fols[0]
            
            # Get the necessary details
            if tmpFol:
                possibleItem[1] = tmpFol
                folName = tmpFol.name()
                
                # Identify the other nodes from the follicle
                par = tmpFol.getParent()
                if par.type()=='joint':
                    possibleItem[2] = par
                    folFormat = 'j/f'
                    
                    # Check for transform 
                    # (only useful if a parent is driven by the follicle)
                    checkOutputXforms = tmpFol.outputs(
                        t='transform', exactType=True)
                    jntPar = par.getParent()
                    if checkOutputXforms and jntPar in checkOutputXforms:
                        possibleItem[0] = jntPar
                        folFormat = 't-j/f'
                elif par.type()=='transform':
                    possibleItem[0] = par
                    folFormat = 't/f'
                    
                    # Check for a joint
                    sibJnt = par.getChildren(typ='joint')
                    if sibJnt:
                        possibleItem[2] = sibJnt[0]
                        folFormat = 't/f-j'
                
                # Check that the follicle actually drives the parent transform
                checkFolOutputs = tmpFol.outputs(
                    t=['transform', 'joint'], exactType=True)
                if not (
                    possibleItem[0] in checkFolOutputs or 
                    possibleItem[2] in checkFolOutputs):
                    folFormat = None
            
            # Check whether a follicle was identified
            if folName:
                # Store the object node values, finish search
                self.xfm, self.fol, self.jnt = possibleItem
                self.type = FolJntType(folFormat)
                # Stop searching for follicleJoint
                break
        
        # Get more accurate control node value than just type string
        if self.jnt and hasattr(self.jnt, 'pu') and hasattr(self.jnt, 'pv'):
            self.type.controlNode = 'j'
        elif self.xfm and hasattr(self.xfm, 'pu') and hasattr(self.xfm, 'pv'):
            self.type.controlNode = 't'
        
        # Return None/error if the result was invalid
        raiseMessage = ''
        if not self.type or not self.type.typeString in FolJntType.validTypes:
            raiseMessage = "Node arrangement was not recognised as a valid \
                follicle joint. "
        
        if not self.fol:
            raiseMessage += "No follicle was found!"
        elif not self.type.typeString in FolJntType.validTypes:
            if self.type.typeString is None:
                raiseMessage += "Check the follicle output connections!"
            elif not self.xfm or not self.jnt:
                # (Still allows a transform or joint to be missing if it is 
                # a valid setup)
                erList = []
                if not self.xfm: erList.append('transform')
                if not self.jnt: erList.append('joint')
                raiseMessage += "No %s was found! " % ' or '.join(erList)
        
        if raiseMessage:
            if strict: raise StandardError(raiseMessage)
            elif self.verbose: print "Warning: %s Skipped." % raiseMessage
            return None

        # Return True if successful
        return True
    
    def getMirrorObject(self, strict=True, justName=False):
        """Return the follicle joint named with right instead of left etc."""
        lrIndex = None
        
        # Check for left or right ("l" or "r")
        if self.side == self._sideChars[0]:
            lrIndex = 0
        elif self.side == self._sideChars[1]:
            lrIndex = 1
        else:
            if strict:
                raise StandardError("Follicle is neither left nor right!")
            return None
        lrIndexMirror = 1-lrIndex
        
        # Find a follicleJoint with the opposite name 
        # (left to right or vise versa)
        mirrorObj = None
        mirrorFolGuess = self.nameObj.name().replace(
            self.sidePrefix[lrIndex], self.sidePrefix[lrIndexMirror])
        if justName:
            return mirrorFolGuess
        elif pm.objExists(mirrorFolGuess):
            # Get as FollicleJoint (errors if none found)
            mirrorObj = FollicleJoint(mirrorFolGuess)
        
        if mirrorObj:
            return mirrorObj
        else:
            if strict:
                raise StandardError(
                    "No Mirror object found by the name %s!" % mirrorFolGuess)
            return False
    
    def rename(self, name="temp_fol#", dontApply=False, skipPreRename=False,
               renameFormats=None):
        """Rename the nodes that make up the FollicleJoint.
        
        Usual use:
        myFollicleJoint.rename("ribbonFollicle#")
        or
        myFollicleJoint.rename("ribbonFollicle5")
        
        Advanced use (reformatting name):
        myFollicleJoint.rename(
            name=None, renameFormats={
                'main':"{pre}_offset_{num}{suf}",
                'j':"{pre}{num}{suf}"
                }
            )
        
        Defaults: 
        # Names should include a hash where the number goes
        name="temp_fol#"
        name=None  # means keep the name but reformat it.
        
        # renameFormats defines how the transform and joint will be named.
        # The joint has '_J_' added by default.
        # 'main' is self.nameObj; 'j' is self.jnt if that isn't 'main'
        renameFormats={
            'main':"{pre}{num}{suf}",
            'j':"{pre}_J_{num}{suf}"
            }
        
        By default, the 'transform' node is named directly, and a 
        suffix is added for the 'joint'.  The 'follicle' is a shape 
        so will be named according to it's parent transform 
        (transform or joint) as is Maya convention.
        """
        # Ensure there is a node(s) to rename
        if not self.nameObj:
            raise StandardError(
                "No transform objects associated with FollicleJoint!"
                )
        
        if renameFormats is None:
            renameFormats = dict(self.type.renameFormats)
        
        num = 1
        numBuffer = 0
        numberPlaceholder = False
        if name is not None:
            # Check for number position
            if '#' in name:
                numberPlaceholder = True
                hasNum = True
                numBuffer = 1
                # Split the new name:
                pre, numNull, suf = splitNumberedName(name, "#")
        else:
            # Reformat existing name:
            name = self.name
            
        if not numberPlaceholder:
            # For existing name, or string without '#':
            # Split the name to get the number
            pre, numStr, suf = splitNumberedName(name)
            if numStr:
                hasNum = True
                numBuffer = len(numStr)
                num = int(numStr)
            else:
                hasNum = False
            
        # Choose which object is the main name one
        objs = {}
        objs['main'] = self.nameObj
        if self.jnt and objs['main'] != self.jnt:
            objs['j'] = self.jnt
        
        allMatch = True
        newNames = {}
        for abbr in objs:
            # Derive name for each object; compare to current name.
            firstNum = num
            if not hasNum:
                # Try without number first, if '#' was omitted.
                firstNum = None
            nameNew = joinNumberedName(
                pre, num, suf, numBuffer, nameFormat=renameFormats[abbr])
            newNames[abbr] = nameNew
            obj = objs[abbr]
            # Check against object name
            if nameNew != obj.name():
                allMatch = False
        # Return if both objects are already named that
        if allMatch:
            return objs, newNames
        
        # Rename all first to avoid unnecessary clashes
        if not skipPreRename:
            for obj in objs.values():
                pm.rename(obj, obj.name()+"various1___tempjunk3")
        
        # If a name already exists, find one that doesn't
        if hasNum:
            # First number has already been tested
            num += 1
        while _anyObjsExist(newNames):
            newNames = {}
            for abbr in objs:
                newNames[abbr] = joinNumberedName(
                    pre, num, suf, numBuffer, nameFormat=renameFormats[abbr])
            num += 1
        
        # Rename the objects!
        if not dontApply:
            for abbr in objs:
                pm.rename(objs[abbr], newNames[abbr])
            if self.fol:
                # Rename the follicle shape (Maya style)
                folParent = self.fol.getParent()
                folCorrect = folParent.name()+"Shape"
                if self.fol.name() != folCorrect:
                    if not pm.objExists(folCorrect):
                        pm.rename(self.fol, folCorrect)
                    else:
                        pm.rename(self.fol, folCorrect+"#")
            
        return objs, newNames
    
    def disconnectFromPatch(self):
        # Find the patch
        patch = self.patch
        
        # Find all connections to the patch, and disconnect them
        allInputConns = self.fol.inputs(c=1, p=1)
        patchConns = [
            conn for conn in allInputConns if conn[1].node() == patch
            ]
        for conn in patchConns:
            pm.disconnectAttr(conn[1], conn[0])
        
        return patch
    
    def freeze(self):
        """'Freeze' the follicle joint, zeroing values
        
        (Set the control values to the follicle ones,
        and zero the offset values, ie.
        shift any offsets into the base parameter value)
        """
        if (self.controlObj != self.fol and 
                pm.attributeQuery('pu', n=self.controlObj, ex=1)):
            if self.controlObj.ou.get() != 0 or self.controlObj.ov.get() != 0:
                endVals = [self.fol.pu.get(), self.fol.pv.get()]
                try:
                    # Ensure the offsets can be reset,
                    # before changing anything else
                    self.controlObj.ou.set(0)
                    self.controlObj.ov.set(0)
                except RuntimeError as e:
                    print "Maya Error - ", e
                    raise StandardError(
                        "Offsets on '%s' were not able to be frozen due to "
                        "connections or locked attributes!" % (
                            self.controlObj.name())
                        )
                else:
                    self.controlObj.pu.set(endVals[0])
                    self.controlObj.pv.set(endVals[1])
                    return True
            else:
                print "Skipped %s; offsets already zero." % str(
                    self.controlObj)
        else:
            print "Skipped %s; no offset attribute found." % str(
                self.controlObj)
    
    def copyValuesToMirror(self, baseValues=True, offsets=True, 
            axis='u', midVal=0.5, uvRange=[0.0, 1.0],
            strict=True, warnings=True, opposingOffsets=True,
            jntRadius=False, uvDriverRatio=False, drivenOffsetRatios=False):
        """Copy uv values across to a mirror follicle joint setup.
        
        Can copy just base values, offset values or both.
        """
        if not self.isSide:
            if strict:
                raise StandardError("Follicle is neither left nor right!")
            return
        
        # Find a follicleJoint with the opposite name 
        # (left to right or vise versa)
        mirrorObj = self.getMirrorObject(strict=strict)
        
        # Define what values to mirror, plus [2] value for ratios etc
        axisVal = 0
        if axis == 'v': axisVal = 1
        
        # Prepare the values
        toFromAttrs = []
        
        # Base uv parameters
        mirCtrl = mirrorObj.controlObj
        if baseValues:
            toFromAttrs.append(
                (mirCtrl.pu, self.controlObj.pu, 0, midVal, uvRange))
            toFromAttrs.append(
                (mirCtrl.pv, self.controlObj.pv, 1, midVal, uvRange))
        
        # Offsets
        if offsets and self.uvDriverAttrs and mirrorObj.uvDriverAttrs:
            if opposingOffsets:
                toFromAttrs.append((mirCtrl.ou, self.controlObj.ou, 2))
                toFromAttrs.append((mirCtrl.ov, self.controlObj.ov, 2))
            else:
                toFromAttrs.append((mirCtrl.ou, self.controlObj.ou, 0))
                toFromAttrs.append((mirCtrl.ov, self.controlObj.ov, 1))
        
        # Optional settings
        if jntRadius and self.jnt and mirrorObj.jnt:
            toFromAttrs.append((mirrorObj.jnt.radius, self.jnt.radius, 2))
        
        if uvDriverRatio:
            # Get UV ratio nodes
            uvDrivNodes = self._driverRatioNodes
            mirDrivNodes = mirrorObj._driverRatioNodes
            if uvDrivNodes and mirDrivNodes:
                for i in range(2):
                    if uvDrivNodes[i] and mirDrivNodes[i]:
                        toFromAttrs.append((
                            mirDrivNodes[i].i2, uvDrivNodes[i].i2, 
                            (i if opposingOffsets else 2)
                            ))
                    elif warnings:
                        print "%s ratio not found! Skipped." % ['U', 'V'][i]
        
        if drivenOffsetRatios:
            # Get link nodes linking other follicleJoint drivers
            uvLinkNodes = self._linkRatioAttrs
            mirLinkNodes = mirrorObj._linkRatioAttrs
            if uvLinkNodes and mirLinkNodes:
                for i in range(2):
                    # Go through u or v list of driver nodes
                    pairNum = min(len(uvLinkNodes[i]), len(mirLinkNodes[i]))
                    for j in range(pairNum):
                        if uvLinkNodes[i][j] and mirLinkNodes[i][j]:
                            toFromAttrs.append((
                                mirLinkNodes[i][j],
                                uvLinkNodes[i][j],
                                2))
        
        # Set the values
        for toFromAttr in toFromAttrs:
            toAttr, fromAttr, uvIndex = toFromAttr[:3]
            # Check that the attribute isn't locked or connected
            if (toAttr.isFreeToChange() == 'freeToChange' or
                toAttr.isFreeToChange() is True):  # Compatibility difference
                val = fromAttr.get()
                
                midValTmp = 0
                if len(toFromAttr) > 3:
                    midValTmp = toFromAttr[3]
                if uvIndex == axisVal:
                    # Mirror value if it is a value on the mirrored axis
                    val = 2*midValTmp - val
                # Clamp value to between min and max values, if given
                if len(toFromAttr) > 3:
                    minVal, maxVal = toFromAttr[4]
                    val = min(max(val, minVal), maxVal)
                
                toAttr.set(val)
            elif warnings:
                print "%s locked or connected! Skipped." % str(toAttr)
        
        return mirrorObj
    
    def transferToPatch(
            self, patch=None, newUV=None, closestPt=True, 
            useSmoothedMesh=True):
        """Transfer follicles from one patch to another
        
        Using closest point in worldspace
        Uses current follicle location, which may have offsets.
        """
        # Get patch
        patch = cq.filterSelectionForShapeType(
            patch, ['nurbsSurface', 'mesh'])[0]
        patchIsNurb = pm.objectType(patch, i='nurbsSurface')
        
        # If using the closest point, calculate the new uv values
        if closestPt and not newUV:
            outUVVals = getClosestUVs(patch, self.xfm, False)[0]
            newUV = outVals[0]
        
        # Disconnect the follicle from the old patch
        self.disconnectFromPatch()
        
        if closestPt:
            # Get the base UV parameter object
            uvObj = self.controlObj
            # Calculate UV offset from other offset drivers 
            # (assumes input is not scaled)
            ofsU = self.fol.pu.get() - uvObj.pu.get()
            ofsV = self.fol.pv.get() - uvObj.pv.get()
            # Set the UV values
            uvObj.pu.set(newUV[0]-ofsU)
            uvObj.pv.set(newUV[1]-ofsV)
        
        # Connect the follicle to the new patch
        pm.connectAttr(patch.worldMatrix[0], self.fol.inputWorldMatrix, f=1)
        if patchIsNurb:
            pm.connectAttr(patch.local, self.fol.inputSurface, f=1)
        elif useSmoothedMesh:
            pm.connectAttr(patch.outSmoothMesh, self.fol.inputMesh, f=1)
        else:
            pm.connectAttr(patch.outMesh, self.fol.inputMesh, f=1)
        
        return True
        
    def addOffsetDriver(
            self, driverObj=None, ratio=0.5, attrs=True, selectDriver=True):
        """Drive the offset by another follicle's offset
        
        Connects the offset of another follicle joint to drive this 
        one's offset with adjustable follow ratio attributes.
        """
        if driverObj is None:
            objs = getFollicleJoints(
                objs=None, useSelection=True, strict=True)
            if objs:
                driverObj = objs[0]
            
        if not driverObj:
            raise TypeError("A driver object must be supplied - "
                "select the driver follicle first")
            
        offsetMults = []
        nameBase = self.fol.name().rpartition('_')[0]
        driverNode = driverObj.controlObj
        print 'driverNode:', driverNode
        for uvStr in ['U', 'V']:
            uvLow = uvStr.lower()
            ofName = '%s_offsetScale%s_#' % (nameBase, uvStr)
            offsetRto = pm.createNode('multDoubleLinear', n=ofName, ss=1)
            offsetMults.append(offsetRto)
            
            pm.connectAttr('%s.o%s' % (driverNode, uvLow), offsetRto.i1)
            #pm.connectAttr(offsetRto.o, '%s.o%s' % (self.controlObj, uvLow))
            # Insert an add node if a connection exists already
            drivenAttr = pm.Attribute('%s.o%s' % (self.controlObj, uvLow))
            extraAddNode = connectAttrAdd(offsetRto.o, drivenAttr)
            ratioAttr = offsetRto.i2
            
            if attrs:
                # Get a unique name (allowing multiple drivers)
                attrNameTry = 'offsetScale%s' % uvStr
                attrShortTry = 'os%s' % uvLow
                num = 1
                attrName = attrNameTry
                attrShort = attrShortTry
                while pm.attributeQuery(attrName, n=self.controlObj, ex=1):
                    attrName = attrNameTry + str(num)
                    attrShort = attrShortTry + str(num)
                    num += 1
                
                pm.addAttr(
                    self.controlObj, ln=attrName, 
                    sn=attrShort, k=1)
                ratioAttr = pm.Attribute(
                    '%s.%s' % (self.controlObj, attrShort))
                pm.connectAttr(ratioAttr, offsetRto.i2)
            else:
                offsetRto.i2.set(k=1)
            ratioAttr.set(ratio)
        
        if selectDriver:
            if attrs:
                pm.select(self.controlObj, r=1)
            else:
                pm.select(offsetMults, r=1)
        
        return offsetMults, self.controlObj
    
    def duplicate(
            self, newPatch=None, name=None, freezeOffsets=False,
            selectNew=False, **kwargs):
        # Get patch
        if newPatch:
            try:
                patch = cq.filterSelectionForShapeType(
                    newPatch, ['nurbsSurface', 'mesh'])[0]
                patchIsNurb = pm.objectType(patch, i='nurbsSurface')
            except TypeError:
                patch = None
        else:
            # Use the patch that the follicle is on, 
            # if one wasn't supplied to copy to.
            patch = self.patch
        
        # Use original name if none given
        if name is None:
            name = self.name
        
        # Get the UV values, and the offset values
        uvObj = self.controlObj
        if freezeOffsets:
            uvObj = self.fol
        uv = [uvObj.pu.get(), uvObj.pv.get()]
        
        attrs = self.uvDriverAttrs
        
        # Setup for the follicle
        if not 'folType' in kwargs:
            kwargs['folType'] = self.type.typeString
        if self.type.hasJoint:
            if not 'jntRadius' in kwargs:
                kwargs['jntRadius'] = self.jntRadius
        
        # Create the duplicate follicle
        newFol = FollicleJoint()
        newFol.new(
            patch=patch, name=name, uv=uv, attrs=attrs,
            uvDriverRatio=self.uvDriverRatio,
            warnNormalised=False, **kwargs)
        
        dupControl = newFol.controlObj
        
        if attrs and dupControl and not freezeOffsets:
            dupControl.ou.set(uvObj.ou.get())
            dupControl.ov.set(uvObj.ov.get())
        
        if selectNew: pm.select(newFol, r=1)
        
        return newFol
    
    def createMirrorObject(
            self, newPatch=None, selectNew=False,
            axis='u', midVal=0.5, uvRange=[0.0, 1.0],
            strict=True, warnings=True, opposingOffsets=True, **kwargs):
        """Create a mirror version of this FollicleJoint.
        
        Extra kwargs, if supplied, serve as arguments to the 'new' 
        method, on creating the duplicate.
        If strict, calling this method on a FollicleJoint that hasn't 
        a side (left/right) will raise an exception.
        As also will trying to create a mirror item when one already 
        exists.
        """
        
        # Check for mirror obj first
        existingMir = self.getMirrorObject(strict=False)
        if existingMir is None:
            if strict:
                raise StandardError("Follicle is neither left nor right!")
        elif existingMir:
            if strict:
                raise StandardError(
                    "Mirror object %s already exists!" % existingMir)
            else:
                return existingMir
        
        # Otherwise create duplicate
        mirName = self.getMirrorObject(strict=strict, justName=True)
        mirObj = self.duplicate(name=mirName, newPatch=newPatch, **kwargs)
        
        # Mirror values
        self.copyValuesToMirror(baseValues=True, offsets=True, 
            axis=axis, midVal=midVal, uvRange=uvRange,
            strict=strict, warnings=warnings, opposingOffsets=opposingOffsets,
            jntRadius=True, uvDriverRatio=True, drivenOffsetRatios=True)
        
        return mirObj


# - Generic utility functions -

def getClosestUVs(patch=None, objs=None, keepCalcNode=False,
                  notNormalised=False, defaultMeshMethod=False):
    """Get the closest UV points to given points.
    
    Returns the UV values of the closest point on the (first) surface
    to each input object/component.
    """
    returnList = []
    
    # Get patch, from keyword arg or from objs
    if patch:
        patch = cq.filterSelectionForShapeType(
            patch, ['nurbsSurface', 'mesh'])[0]
        patchIsNurb = pm.objectType(patch, i='nurbsSurface')
    else:
        patch = cq.filterSelectionForShapeType(
            objs, ['nurbsSurface', 'mesh'])[0]
        patchIsNurb = pm.objectType(patch, i='nurbsSurface')
    
    # Get objects, excluding the patch itself
    if not objs:
        objs = pm.ls(sl=1, fl=1)
        if objs and patch in objs or patch.getParent() in objs:
            objs = [obj for obj in objs
                if str(obj) != str(patch) and
                str(obj) != str(patch.getParent())]
        
        if not objs:
            raise StandardError('No points or objects found!')
            
    # Get point positions of objects
    posList = cq.getPointPositions(objs)
    
    outNodes = []
    outVals = []
    for point in posList:
        # Create a 'closestPointOnSurface' node and connect it to the surface
        name = '%s_cpt#' % str(patch.getParent())
        inPointAttr = None
        cptNodes = []
        if patchIsNurb:
            cpt = pm.createNode('closestPointOnSurface', n=name, ss=1)
            cptNodes = [cpt]
            pm.connectAttr(patch.worldSpace[0], cpt.inputSurface)
            inPointAttr = cpt.inPosition
        else:
            cpt = pm.createNode('closestPointOnMesh', n=name, ss=1)
            cptNodes = [cpt]
            pm.connectAttr(patch.worldMesh[0], cpt.inMesh)
            if defaultMeshMethod:
                # Use the worldspace mesh location
                pm.connectAttr(patch.worldMatrix[0], cpt.inputMatrix)
                inPointAttr = cpt.inPosition
            else:
                # Transfer the input position into local space instead
                # (avoids a UV value glitch on transformed meshes)
                mtxName = cpt.name().replace('cpt','invWorldMtx')
                mtx = pm.createNode('pointMatrixMult', n=mtxName, ss=1)
                pm.connectAttr(patch.worldInverseMatrix[0], mtx.inMatrix)
                pm.connectAttr(mtx.output, cpt.inPosition)
                inPointAttr = mtx.inPoint
                cptNodes.append(mtx)
        
        if keepCalcNode:
            closeLoc = pm.createNode('transform', ss=1)
            cptNodes.append(closeLoc)
            pm.connectAttr(closeLoc.t, inPointAttr)
            pm.xform(closeLoc, t=point)
            
            outNodes.append(list(cptNodes))
            outVals.append([cpt.u.get(), cpt.v.get()])
        else:
            inPointAttr.set(point)
            uv = [cpt.u.get(), cpt.v.get()]
            
            # Adjust UV for UV ranges if not Normalised
            if patchIsNurb:
               uv = normalisedNurbsUV(patch, uv, warningOnly=notNormalised)
            
            outVals.append(uv)
            
            pm.delete(cptNodes)
    
    return [outVals, outNodes, patch]


def normalisedNurbsUV(patch, uv, giveWarning=True, warningOnly=False):
    """Get Normalised UV values for UV points on a nurbsSurface.
    
    ('follicle' nodes treat their input UV parameters as normalised)
    """
    if pm.objectType(patch, i='nurbsSurface'):
        finalUV = list(uv)
        
        # Check if the surface is normalised (follicle values are normalised)
        minU = patch.minValueU.get()
        maxU = patch.maxValueU.get()
        minV = patch.minValueV.get()
        maxV = patch.maxValueV.get()
        if not (minU == 0.0 and maxU == 1.0 and minV == 0.0 and maxV == 1.0):
            if giveWarning: print "WARNING! surface isn't normalised!"
            if not warningOnly:
                uLength = maxU-minU
                vLength = maxV-minV
                
                finalUV[0] = uv[0]/float(uLength)+minU
                finalUV[1] = uv[1]/float(vLength)+minV
                if giveWarning: 
                    print 'Actual UV: %s %s   Normalised UV: %s %s' % (
                        uv[0], uv[1], finalUV[0], finalUV[1])
                
        return finalUV
    else:
        raise StandardError("Patch must be a nurbSurface shape PyNode!")


def splitNumberedName(name, alternateFindChar=None):
    """Split a name into prefix, number, suffix
    
    Where number is the LAST occuring number.
    """
    if alternateFindChar:
        findChars = alternateFindChar
    else:
        findChars = string.digits
    # Starting from the end, collect the suffix letters,
    # Then the number characters,
    # Then the rest of the name.
    splitStrs = ["", "", ""]
    i = 2
    digitLast = False
    for c in reversed(name):
        if i > 0:
            if c in findChars:
                if not digitLast:
                    i -= 1
                digitLast = True
            else:
                if digitLast:
                    i -= 1
                digitLast = False
        splitStrs[i] = c + splitStrs[i]
    
    # If no number was found, return everything as the prefix
    if not splitStrs[1]:
        splitStrs = [name, "", ""]
    return splitStrs


def joinNumberedName(
        prefix=None, num=None, suffix=None, numPadding=0,
        nameFormat="{pre}{num}{suf}", nameDef=None):
    """Convenience function to format a name.
    
    Inserts a number with spacer zeroes, unless no number is given,
    where it will skip inserting a number.
    
    eg. 
    joinNumberedName('pizza_', 23, '_order', 3)
    # Result: 'pizza_023_order' # 
    
    Or if a 'nameDef' is given, with a # in it, put the number at
    that location.
    
    eg.
    joinNumberedName(nameDef="pizza_#_order", num=23, numPadding=3)
    """
    # Format the number
    numStr = ''
    if num is not None and num != '':
        if isinstance(num, basestring):
            # Remove pre-existing padding, +-
            num = int(num)
        numStr = "{num:0>{pad}}".format(num=num, pad=numPadding)
    
    if nameDef:
        # Replace the # with the number (or empty)
        if not '#' in nameDef:
            raise TypeError(
                "A nameTemplate must contain a # symbol for the number!")
        return nameDef.replace('#', numStr)
    else:
        # Concatenate the list, with any extra prefix etc. in format
        if not prefix: prefix = ''
        if not suffix: suffix = ''
        return nameFormat.format(pre=prefix, num=numStr, suf=suffix)


def connectAttrAdd(sourceAttr, destAttr):
    """Connect an attribute to add to an already connected value"""
    # Check for an existing connection
    firstCon = destAttr.inputs(p=1)
    if firstCon:
        # Insert an add node to add the two inputs
        addName = str(destAttr).replace('.', '_')+"_add#"
        offsetAdd = pm.createNode('addDoubleLinear', n=addName, ss=1)
        pm.connectAttr(firstCon[0], offsetAdd.i1)
        pm.connectAttr(sourceAttr, offsetAdd.i2)
        pm.connectAttr(offsetAdd.o, destAttr, f=1)
        return offsetAdd
    else:
        # Normal connection
        pm.connectAttr(sourceAttr, destAttr)
        return None


def _anyObjsExist(nameDict):
    """Check for clashes with proposed names
    
    Helper function for loop;
    Returns True if any dict Values exist as nodes in the scene.
    """
    for abbr in nameDict:
        if pm.objExists(nameDict[abbr]):
            break
    else:
        # Nothing found by either name
        return False
    return True


# - Functions for multiple follicle joints etc -

def getFollicleJoints(
        objs=None, useSelection=False, strict=True, verbose=True):
    """Returns a list of FollicleJoint objects from input.
    
    Uses a list of objects or the selection.
    Can take in FollicleJoint class instances without changing them.
    """
    
    # Ordered list, and 
    outFols = []
    foundFols = set()
    
    # Filter input values, use selection if objects not supplied
    if objs:
        if not isinstance(objs, list): objs = [objs]
    elif useSelection:
        objs = pm.ls(sl=1, typ=['transform', 'follicle'])
    
    # Ensure a valid object list
    if not objs:
        raise StandardError(
            "No objects found to identify follicle joints from!")
    
    # Look for object type in objs/selection/components' objects
    for obj in objs:
        if isinstance(obj, FollicleJoint):
            testObj = obj
            checkVal = True
        elif hasattr(obj, 'getFollicleJoint'):
            # Shouldn't occur once dev stage is finished;
            # (engine reload mid operation)
            testObj = FollicleJoint()
            checkVal = testObj.getFollicleJoint(obj.fol, strict=strict)
        else:
            testObj = FollicleJoint()
            checkVal = testObj.getFollicleJoint(obj, strict=strict)
        testObj.verbose = verbose
        
        # If a valid follicle joint was identified, add it to the list
        if checkVal:
            fol = testObj.fol
            if not fol in foundFols:
                outFols.append(testObj)
                foundFols.add(fol)
            
        elif testObj.verbose:
            # Otherwise warn if verbose
            print "Warning: no follicle joint identified for %r!" % obj
    
    if not foundFols:
        raise StandardError("No follicle setups were found!")
    
    return outFols


def newFollicle(patch=None, name=None, uv=[0.5, 0.5], *args, **kwargs):
    """Wrapper to create a follicle joint and return it."""
    
    newObj = FollicleJoint()
    newObj.new(patch=patch, name=name, uv=uv, *args, **kwargs)
    return newObj


def newFollicleGrid(
        patch=None, name=None, selectNew=True,
        uvRows=[5, 1], edgeBounded=[1, 0], uvRange=[None, None, None, None],
        giveWarning=True, *args, **kwargs):
    """Generate rows and columns of follicle joints.
    
    uvRows = [(int) rows in U direction, (int) rows in V direction]
    edgeBounded [U, V] is whether the rows include rows on the edges.
    0 means just centered rows, 1 means edge bounded.
    
    uvRange defaults to the full range of the surface patch or mesh, 
    ie. [0.0, 1.0, 0.0, 1.0] (because follicles UV parameters are
    always normalised values)
    """
    # Check values
    for i in range(2):
        if uvRows[i]-edgeBounded[i] == 0:
            raise StandardError("Minimum 2 rows for edge-bounded rows!")
    
    # Check patch
    patchTest = cq.filterSelectionForShapeType(
        patch, ['nurbsSurface', 'mesh'])[0]
    if patchTest:
        patch = patchTest
        patchIsNurb = pm.objectType(patch, i='nurbsSurface')
        
        # Check for normalised UVs (just prints warning)
        if giveWarning and patchIsNurb:
            if (
              patch.minMaxRangeU.get() != (0.0, 1.0) or 
              patch.minMaxRangeV.get() != (0.0, 1.0)
              ):
                print "WARNING! surface isn't normalised!"
    else:
        raise StandardError("No valid patch identified!")
    
    # Get patch range
    if None in uvRange:
        uvRangeDefault = [0.0, 1.0, 0.0, 1.0]
        # Use defaults where None was specified
        for i in range(4):
            if uvRange[i] is None:
                uvRange[i] = uvRangeDefault[i]
    
    # Create the follicles by row/column
    newFols = []
    uv = [0.0, 0.0]
    for i in range(uvRows[0]):
        normU = (float(i)+(1-edgeBounded[0])/2.0)/(uvRows[0]-edgeBounded[0])
        uv[0] = uvRange[0] + normU*(uvRange[1]-uvRange[0])
        for j in range(uvRows[1]):
            normV = (
                (float(j)+(1-edgeBounded[1])/2.0)/(uvRows[1]-edgeBounded[1])
                )
            uv[1] = uvRange[2] + normV*(uvRange[3]-uvRange[2])
            
            newObj = FollicleJoint()
            newObj.new(
                patch=patch, name=name, uv=uv, 
                warnNormalised=False, normaliseUV=False, *args, **kwargs)
            newFols.append(newObj)
    
    if selectNew:
        pm.select([obj.controlObj for obj in newFols])
    
    return newFols


def newFollicleAtClosestPt(
        patch=None, objs=None, name=None, keepCalcNodes=False,
        *args, **kwargs):
    # Get closest UV values from objects' positions
    outVals, outNodes, patch = getClosestUVs(patch, objs, keepCalcNodes)
    
    allFols = []
    extraNodes = []
    for i in range(len(outVals)):
        uv = outVals[i]
        
        # Create follicle, retuning [fol, folXform, patch, ...jnt]
        folObj = newFollicle(patch, name, uv, *args, **kwargs)
        
        if keepCalcNodes:
            uvObj = folObj.controlObj
            
            # Connect the closest surface point node to the follicle/jnt
            cpt = outNodes[i][0]
            pm.connectAttr(cpt.u, uvObj.pu)
            pm.connectAttr(cpt.v, uvObj.pv)
            
            extraNodes.append(cpt)
        
        allFols.append(folObj)
        
    return allFols, extraNodes


def mirrorFollicleOffsets(
        baseValues=False, offsets=True, objs=None, axis='u', sidePrefix=None,
        useSelection=True, strict=True, **kwargs):
    folObjs = getFollicleJoints(
        objs, useSelection=useSelection, strict=strict)
    mirrorObjs = []
    for obj in folObjs:
        if sidePrefix:
            # Use the given left right prefixes
            obj.sidePrefix = sidePrefix
        
        # Mirror offsets of the objects to matching objects
        mirrorObj = obj.copyValuesToMirror(
            baseValues=baseValues, offsets=offsets, axis=axis, strict=strict,
            **kwargs)
        if mirrorObj:
            mirrorObjs.append(obj)
    return mirrorObjs


def freezeOffsets(objs=None, useSelection=True):
    folObjs = getFollicleJoints(objs, useSelection=useSelection, strict=False)
    frozenObjs = []
    for obj in folObjs:
        # Freeze offsets of the object
        if obj.freeze():
            frozenObjs.append(obj)
    return frozenObjs


def duplicateFollicles(
        objs=None, useSelection=True, newPatch=None, name=None,
        freezeOffsets=False, selectNew=False, **kwargs):
    folObjs = getFollicleJoints(objs, useSelection=useSelection, strict=False)
    dupObjs = []
    for obj in folObjs:
        # Duplicate the follicle joint
        dup = obj.duplicate(
            newPatch=newPatch, name=name, freezeOffsets=freezeOffsets,
            selectNew=False, **kwargs)
        dupObjs.append(dup)
    
    if selectNew:
        pm.select([obj.controlObj for obj in dupObjs])
    
    return dupObjs


def mirrorFollicles(
        objs=None, useSelection=True, newPatch=None, selectNew=False,
        axis='u', midVal=0.5, uvRange=[0.0, 1.0], sidePrefix=None,
        strict=True, warnings=True, **kwargs):
    folObjs = getFollicleJoints(objs, useSelection=useSelection, strict=False)
    mirObjs = []
    for obj in folObjs:
        if sidePrefix:
            # Use the given left right prefixes
            obj.sidePrefix = sidePrefix
        
        # Create Mirror of the follicle joint
        mir = obj.createMirrorObject(
            newPatch=newPatch, selectNew=False,
            axis=axis, midVal=midVal, uvRange=uvRange,
            strict=strict, warnings=warnings, **kwargs)
        mirObjs.append(mir)
    
    if selectNew:
        pm.select([obj.controlObj for obj in mirObjs])
    
    return mirObjs


def transferFolliclesToPatch(
        patch=None, objs=None, useSelection=True, closestPts=True,
        useSmoothedMesh=True):
    """Wrapper to transfer multiple follicles."""
    
    # Get patch
    patch = cq.filterSelectionForShapeType(patch, ['nurbsSurface', 'mesh'])[0]
    
    # Get follicle joint classes for objects
    folObjs = getFollicleJoints(objs, useSelection=useSelection, strict=False)
    
    if closestPts:
        # For optimisation, get all the UV values at once
        xforms = []
        validFols = []
        for obj in folObjs:
            if obj.xfm: xforms.append(obj.xfm)
            elif obj.jnt: xforms.append(obj.jnt)
            else: continue
            validFols.append(obj)
        outVals = getClosestUVs(patch, xforms, keepCalcNode=False)[0]
        
        for i in range(len(xforms)):
            uvVals = outVals[i]
            validFols[i].transferToPatch(
                patch=patch, newUV=uvVals, useSmoothedMesh=useSmoothedMesh)
    else:
        for obj in folObjs:
            obj.transferToPatch(
                patch=patch, closestPt=False, useSmoothedMesh=useSmoothedMesh)


def addAsOffsetDriver(
        driverObj=None, objs=None, ratio=0.5, attrs=True, selectDriver=True):
    """Drive one follicle joint's offset with another.
    
    With adjustable follow ratio attributes.
    Multiple objects can be driven by one driver.
    """
    if objs is not None and not isinstance(objs, list): objs = [objs]
    
    # Get given/selected objects as folObjs
    folObjs = getFollicleJoints(objs, useSelection=True, strict=True)
    
    # Get the first object as the driver object if not specified
    if driverObj:
        driverObj = FollicleJoint(driverObj)
    elif folObjs:
        driverObj = folObjs.pop(0)
    
    if not folObjs:
        raise StandardError(
            "At least two follicles must be supplied - "
            "select the driver follicle first")
    
    driverAttrObjs = []
    for obj in folObjs:
        returnObjs = obj.addOffsetDriver(
            driverObj=driverObj, ratio=ratio, attrs=attrs, selectDriver=False)
        if attrs:
            driverAttrObjs.append(returnObjs[1])
        else:
            driverAttrObjs.extend(returnObjs[0])
    
    if selectDriver:
        pm.select(driverAttrObjs)
        
    return driverAttrObjs


def autoRename(
        objs=None, useSelection=True, patch=None, name=None, skipSelect=False,
        scaleY=4, uvAsXy=['u', 'v'], midVal=0.5, middleTolerance=0.04,
        renameFormats=None, sidePrefix=None):
    """Auto-rename follicles to left/right and numbered.
    
    Uses parameter U and V values to sort into sides symmetrically.
    
    uvAsXy maps the 'across' (x) and 'up' (y) to the U/V directions 
     given.
    middleTolerance specifies the width of UV value that gets named as
     being the middle.
    midVal defines where (on the x direction) the mirror line is.
    scaleY defines how numbers count up; a higher number will separate
     horizontal rows from each other more, helping the counting script
     to count along in rows.
    patch is just an alternative to giving a specific name; if only 
     patch is supplied, the name will be the patch transform + '_fol#'
    """
    folObjs = getFollicleJoints(objs, useSelection=useSelection, strict=False)
    if not folObjs: raise TypeError("At least one follicle must be supplied")
    
    # Get specifications from first follicle object
    if sidePrefix:
        LRMStr = sidePrefix
    else:
        LRMStr = folObjs[0].sidePrefix
    if not renameFormats:
        renameFormats = folObjs[0].type.renameFormats
    
    pre = ''
    suf = ''
    # Generate a name if none supplied
    if not name:
        if patch:
            # Get patch
            try:
                patch = cq.filterSelectionForShapeType(
                    patch, ['nurbsSurface', 'mesh'])[0]
            except TypeError:
                patch = folObjs[0].patch
                if not patch:
                    patch = None
            pre = '%s_fol' % str(patch.getParent())
        else:
            # Use the first follicle joint
            name = folObjs[0].nameObj.name()
            pre, numStr, suf = splitNumberedName(name)
            if not numStr:
                pre = pre.rpartition('_')[0]
            
            # Remove prefix eg. "L_"
            for sideStr in LRMStr:
                if pre.startswith(sideStr):
                    pre = pre[len(sideStr):]
                    break
    elif "#" in name:
        # Split the new name template:
        pre, numNull, suf = splitNumberedName(name, "#")
    else:
        # Split the name at the number (value isn't required)
        pre, numNull, suf = splitNumberedName(name)
    
    # Sort uv points into sides (Right, left, middle)
    LRMside = [{}, {}, {}]
    prevNames = []
    toTempRename = []
    nodeUniqueOffset = 0.00001
    for folObj in folObjs:
        nodes = folObj.allDagObjs
        uv = folObj.fol.pu.get(), folObj.fol.pv.get()
        
        uvStr = ['u', 'v']
        # Figure out which way up the uv's are (x is across, y is up) 
        # (eg. uvAsXy=['v', '-u'] would be  V ->, and U down)
        for i in range(2):
            if uvStr[i] in uvAsXy[0]:
                x = uv[i]
                if '-' in uvAsXy[0]:
                    # Reverse around mid point
                    x = 2*midVal - x
            elif uvStr[i] in uvAsXy[1]:
                y = uv[i]
                if '-' in uvAsXy[1]:
                    # Reverse around mid point
                    y = 2*midVal - y

        # Find which side the follicle is on, and give a number to order it
        # favouring x (horizontal) to attempt to number horizontally first
        LRM = 2  # Right, left, middle
        if x <= midVal-middleTolerance/2:
            # Left;
            LRM = 0
            hashNum = (midVal-x) + scaleY*y
        else:
            # Mid/left
            if x >= midVal+middleTolerance/2:
                # Right;
                LRM = 1
            hashNum = (x-midVal) + scaleY*y
        # Avoid equal values being skipped
        while hashNum in LRMside[LRM]:
            hashNum += nodeUniqueOffset
        
        LRMside[LRM][hashNum] = folObj
        toTempRename.extend(nodes)
        for node in nodes:
            prevNames.append(node.name())
    
    # Generate regex for left/right prefix
    LRMRegex = '('
    for sideStr in LRMStr:
        if len(LRMRegex) > 1:
            LRMRegex += '|'
        LRMRegex += sideStr
    LRMRegex += ')'
    
    # Find existing objects with name 
    # To get highest number for padding zero amount
    existingObjs = pm.ls(regex=LRMRegex+pre+'[0-9]+'+suf)
    maxNum = 0
    if existingObjs:
        for obj in existingObjs:
            # Skip objects to be renamed
            if obj.name() in prevNames: continue
            
            # Get number ('[0-9]+' ensures one exists)
            numStr = splitNumberedName(obj.name())[1]
            numInt = int(numStr)
            if numInt > maxNum:
                maxNum = numInt
    print 'Highest pre-existing number:', maxNum
    
    # Find the new number of names, get the 00 spacer amount
    newMaxNum = 1
    for sideList in LRMside:
        sideCount = len(sideList)
        if sideCount > newMaxNum:
            newMaxNum = sideCount
    overallMax = maxNum + newMaxNum
    numBuffer = len(str(overallMax))
    print 'Final maximum number:', overallMax, "Padding:", numBuffer
    
    # Temporarily change the existing names, to enable name swaps
    # (PyNode objects update so the lists will still work)
    tempSuffix = '_temp_name_while_renaming__'
    for folNode in toTempRename:
        # Avoid renaming shapes twice (but some may not auto-rename)
        currentName = folNode.name()
        if not tempSuffix in currentName:
            pm.rename(folNode, currentName+tempSuffix)
    
    # Figure out and name the follicles by sides
    grpList = []
    parentObjs = set()
    newNames = []
    for i in range(3):
        hashDict = LRMside[i]
        
        # Order the follicles by their uv-based, scaleY biased value
        orderedFols = hashDict.keys()
        orderedFols.sort()
        j = 1
        for key in orderedFols:
            folObj = hashDict[key]
            # Ensure the given LRM values are used
            folObj.sidePrefix = LRMStr
            
            # Get the left/right/middle numbered name
            nameNew = joinNumberedName(LRMStr[i]+pre, j, suf, numBuffer)
            # Rename to the first unique set of names (variable number string)
            renameVals = folObj.rename(
                nameNew, skipPreRename=True, renameFormats=renameFormats)
            newNames = renameVals[1]
            renameNum = splitNumberedName(newNames['main'])[1]
            j = int(renameNum)
            
            parentObj = folObj.topObj.getParent()
            if parentObj:
                parentObjs.add(parentObj)
            grpList.append(folObj.topObj)
            j += 1
    
    # Reshuffle the follicles if not in separate hierarchies
    parentNum = len(parentObjs)
    if parentNum <= 1:
        tempGrp = pm.group(grpList)
        if parentNum == 1:
            pm.parent(grpList, list(parentObjs)[0])
        else:
            pm.parent(grpList, w=1)
        pm.delete(tempGrp)
    
    # Select the renamed objects
    if not skipSelect:
        pm.select(grpList, r=1)
    
    return newNames


def multiRename(
        objs=None, useSelection=True, name=None, skipSelect=False, **kwargs):
    """Rename all DAG nodes in each setup, using consecutive numbers"""
    folObjs = getFollicleJoints(objs, useSelection=useSelection, strict=False)
    if not folObjs:
        raise TypeError("At least one follicle must be supplied")
    selObjs = []
    for folObj in folObjs:
        folObj.rename(name=name, **kwargs)
        selObjs.append(folObj.topObj)
    if not skipSelect:
        pm.select(selObjs)
    return selObjs
    

def getSubNodes(
        subNodeType='topObj', objs=None, useSelection=True, skipSelect=False,
        allowReorder=True):
    """Select eg. the joint node of multiple follicle joint setups.
    
    Can take any attribute of the FollicleJoint class that is a PyMel 
    object, as the subNodeType string; eg.
    getSubNodes('topObj')       -The highest object in the maya hierarchy
    getSubNodes('controlObj')   -The object with the UV parameters
    getSubNodes('nameObj')      -The object used for the main name
    getSubNodes('patch')        -The surface patch (mesh or nurbsSurface)
    getSubNodes('jnt')          -The joint if existing
    getSubNodes('xfm')          -The transform if existing
    getSubNodes('fol')          -The follicle shape
    
    Note that some of these attributes may point to the same node, 
    depending on the follicle joint type.
    """
    folObjs = getFollicleJoints(objs, useSelection=useSelection, strict=True)
    if not folObjs:
        raise TypeError("At least one follicle must be supplied")
    selObjs = []
    grpObjs = {}
    for folObj in folObjs:
        if hasattr(folObj, subNodeType):
            checkObj = getattr(folObj, subNodeType)
            if checkObj:
                objType = checkObj.type()
                if allowReorder and subNodeType == 'controlObj':
                    # Separate into types
                    if not objType in grpObjs:
                        grpObjs[objType] = []
                    grpObjs[objType].append(checkObj)
                selObjs.append(checkObj)
    
    if allowReorder and subNodeType == 'controlObj':
        # Reorder list to ensure ctrl attributes are visible once selected
        selObjs = []
        for ctrlTyp in ['joint', 'follicle', 'transform']:
            if ctrlTyp in grpObjs:
                selObjs.extend(grpObjs.pop(ctrlTyp))
        for ctrlTyp in grpObjs:
            selObjs.extend(grpObjs[ctrlTyp])
    
    if not skipSelect:
        pm.select(selObjs)
    return selObjs