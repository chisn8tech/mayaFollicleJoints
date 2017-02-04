"""
#
# follicleJntsTool
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

# Call to open the UI: (with follicleJntsTool in a maya scripts folder)
import follicleJntsTool.follicleJnts_UI as folUI
reload(folUI)
folWin = folUI.UI()

Old Version supports:
Maya 2011 32bit (Windows 7) - PyQt version: 4.7.3 - Qt version '4.5.3'
 - sip version '4.10.2', API 2
Maya 2013 64bit (Windows 7) - PyQt version: 4.9.5 - Qt version '4.7.1'
 - sip version '4.14', API 2

Current Version supports:
Maya 2017 64bit (Windows 7) - Native Maya PySide2 and Shiboken2 (Qt5):
#### Closing when no attribute editor causes glitch?


API code direct test calls:

## Test script calls
# Create single follicle joint
import follicleJntsTool.follicleJnts as folTools
reload(folTools)
folJnt = folTools.newFollicle(name=None, uv=[0.5, 0.5])
print folJnt

# Freeze the selected object's offsets
import follicleJntsTool.follicleJnts as folTools
reload(folTools)
folJnts = folTools.getFollicleJoints(useSelection=True, strict=False)
folJnts[0].freeze()
#print folJnts[0].fol, folJnts[0].xfm, folJnts[0].jnt
#help(folJnts[0])

# Create follicles at closest surface point(s)
import follicleJntsTool.follicleJnts as folTools
reload(folTools)
folJnts = folTools.newFollicleAtClosestPt(
    patch=None, objs=None, name=None, keepCalcNodes=False)
print folJnts

# Transfer follicles from one surface to another
import follicleJntsTool.follicleJnts as folTools
reload(folTools)
folTools.transferFolliclesToPatch(
    patch=None, objs=None, useSmoothedMesh=True)

# Use a follicle to drive another
import follicleJntsTool.follicleJnts as folTools
reload(folTools)
folTools.addAsOffsetDriver(
    driverObj=None, objs=None, ratio=0.5, attrs=True, selectDriver=True)

# Freeze multiple offsets
import follicleJntsTool.follicleJnts as folTools
reload(folTools)
frozen = folTools.freezeOffsets(objs=None, useSelection=True)

# Mirror Offsets over to mirror follicles
import follicleJntsTool.follicleJnts as folTools
reload(folTools)
mirrors = folTools.mirrorFollicleOffsets(
    objs=None, axis='v', useSelection=True)

# Set mirror follicle offset directions to oppose each other and match
import follicleJntsTool.follicleJnts as folTools
reload(folTools)
frozen = folTools.mirrorFollicleOffsets(
    objs=None, axis='u', useSelection=True, uvDriverRatio=True)

# Create new follicles using a grid
import follicleJntsTool.follicleJnts as folTools
reload(folTools)
newFols = newFollicleGrid(
        patch=None, name=None, selectNew=True, edgeBounded=[1, 0],
        uvRows=[5, 1], uvRange=[None, None, None, None])

# Duplicate follicles
import follicleJntsTool.follicleJnts as folTools
reload(folTools)
dups = folTools.duplicateFollicles(
    objs=None, useSelection=True, newPatch=None, name=None, 
    freezeOffsets=False, selectNew=True)

# Create mirror follicles
import follicleJntsTool.follicleJnts as folTools
reload(folTools)
mirObjs = folTools.mirrorFollicles(
        objs=None, useSelection=True, newPatch=None, selectNew=False, 
        axis='u', midVal=0.5, uvRange=[0.0, 1.0],
        strict=True, warnings=True)

# Auto-Rename follicles (left/right)
import follicleJntsTool.follicleJnts as folTools
reload(folTools)
newNames = folTools.autoRename(
    objs=None, useSelection=True, patch=None, name="ribbonFol_#", 
    middleTolerance=0.04, uvAsXy=['u', 'v'], midVal=0.5, scaleY=4)

# Test name split
import follicleJntsTool.follicleJnts as folTools
reload(folTools)
dups = folTools.splitNumberedName("this45name", alternateFindChar=None)

# Test name split with merge (ie. change number padding amount)
import follicleJntsTool.follicleJnts as folTools
reload(folTools)
nameTest = "delivery2_pizza13_order"
print folTools.joinNumberedName(*folTools.splitNumberedName(nameTest), 
                                numPadding=5)


Log:
30.09.15 - Nathan
- Added support for linear UV offset when swapping surfaces by closest
 point
01.10.15
- Fixed duplicate to work for FollicleJoints with offsets driving other
 FollicleJoints
06.10.15
- Made mirrored follicle joint offsets work in mirrored directions

# To Do:
- populate other attrs created through 'new'?

# Known Bugs/Possible added features:
- surface scale offsets for the uv control ratios, for transferring
 from a normalised surface to non-normalised etc while keeping other
 values
- When creating a new follicle, enable patch to be derived from 
 selected follicle joint
- closest point nodes, when keeping nodes, don't operate in worldspace
- add remove and replace functions for eg. follicle driving follicles,
 patches
- extend 'freeze' method to be able to offset dependent (driven)
 follicles
- automatic mirror line/surface direction detection
"""