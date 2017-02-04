"""
#
# follicleJnts_UI.py - 2015 Nathan Chisholm
# Version 1.02.00
# PySide2 variant
#
# @author Nathan Chisholm
# @email nathanchisholm.cgartist@gmail.com
# @web nathanchisholm.weebly.com
#
# --------------------------------------------------------------------
# Scripts for dealing with joint follicles on patches or ribbons.
#


Log:
 1.01: UI changed to collapsable tabs, so that both sections can be
    visible at once (more practical to work with than tabs when tested.)
 
 1.10: UI adapted for Maya 2017 and PySide2/Qt5; 
    Qt designer output merged into this script and simplified.
    Collapsable sections made into derived widgets to be tidier.
    Tabs keep focus when docked (though Maya's own don't)
    
    Due to Maya 2017 allowing things to be docked anywhere, at current the
    attribute editor must be open for the UI to be opened non-floating, to
    define where it goes. (Default is to load floating anyway)

"""


import os
import sys

from shiboken2 import wrapInstance
from PySide2 import QtGui, QtCore, QtWidgets

import pymel.core as pm
import maya.OpenMayaUI as mayaUI
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

import follicleJntsTool.follicleJnts as folEng
reload(folEng)


allowMissingStylesheet = False


# Read the QSS file (stylesheet) data into a string
UIqss = ''
thisDir = os.path.dirname(__file__)
qssFilePath = os.path.join(thisDir, "follicleJnts_style.qss")
try:
    qssFile = open(qssFilePath, 'rU')
except IOError:
    if not allowMissingStylesheet:
        raise OSError("Could not find the QT Stylesheet file!")
except OSError:
    if not allowMissingStylesheet:
        raise OSError("Could not read the QT Stylesheet file!")
else:
    UIqss = ''.join(qssFile.readlines())
    qssFile.close()


def _getMayaWin():
    """Get the main Maya window as a QtGui.QMainWindow instance"""
    ptr = mayaUI.MQtUtil.mainWindow()
    if ptr is not None:
        qob = wrapInstance(long(ptr), QtWidgets.QMainWindow)
        return qob


def _getNamedMainChild(name):
    """Get the named child of the main window as a Qt object"""
    mainWin = _getMayaWin()
    if mainWin:
        mainChildren = mainWin.children()
        matching = []
        for child in mainChildren:
            if name == child.objectName():
                matching.append(child)
        
        return matching


def mayaPrint(message):
    """Print text so that it shows up in Maya's 'command response' bar."""
    message = message.replace("'", r"\'").replace('"', r'\"')
    pm.mel.eval('print "%s"' % message)


def undoableCall(uiSignal, uiFunction, *args, **kwargs):
    """Connect the Qt signal to a wrapped undoable command.
    
    If extra arguments are supplied (*args or **kwargs) these are given
    to the command when it is evaluated (shallow copy only.)
    
    Specifying 'noArgs=True' prevents the called function receiving 
    the signal's arguments.
    """
    tempCaller = undoableCaller(uiFunction, *args, **kwargs)
    return uiSignal.connect(tempCaller.runUndoable)


class undoableCaller(object):
    """Wrapper object around a function/method to enable Maya's 'undo'.
    
    Enables the commands triggered in the Qt UI to be undone in Maya
    in one step, by opening and closing undo chunks before and after
    the call.
    
    If extra arguments are supplied (*args or **kwargs) these are given
    to the command when it is evaluated (shallow copy only.)
    
    Specifying 'noArgs=True' prevents the called function receiving 
    the signal's arguments.
    
    Called by passing the function to be wrapped to the init, eg.
    wrp = undoableCaller(<function/method reference>, *presetArgs, **pKwargs)
    
    The resulting wrapped method is wrp.runUndoable(*args, **kwargs),
    which can be connected to a PyQt signal.
    """
    wrappersList = []
    
    def __init__(self, uiFunction, *args, **kwargs):
        """Create the wrapper object.
        
        First argument is the function to be wrapped.
        Any other arguments are forwarded to the wrapped function, and
        will be placed before the *args and **kwargs supplied when the
        function is 'signalled'.
        """
        self.uiFunction = uiFunction
        # Store predefined args
        self.args = list(args)
        self.kwargs = dict(kwargs)
        
        # Enable *args to be ignored
        self.noArgs = True
        if 'noArgs' in self.kwargs:
            self.noArgs = self.kwargs.pop('noArgs')
        
        undoableCaller.wrappersList.append(self)
        
    def runUndoable(self, *args, **kwargs):
        # Add predefined args to signal ones
        if self.noArgs:
            args = ()
        if self.args: args = self.args + list(args)
        if self.kwargs: kwargs.update(self.kwargs)
        
        # Start the undo block
        pm.undoInfo(openChunk=True)
        exc = None
        try:
            self.uiFunction(*args, **kwargs)
        except Exception:
            # Store the exception if raised
            exc, excInst, trac = sys.exc_info()
            raise
        finally:
            # End the undo block (re-enables undo)
            pm.undoInfo(closeChunk=True)
            
            # Re-raise the exception to ensure the Maya error bar goes red
            if exc:
                pm.mel.evalDeferred(r'error "%s: %s"' % (
                    exc.__name__, '; '.join(excInst.args).replace('\n', ' ')
                    ))
            
            # Return None to prevent 'raise' from breaking the QT win
            return


class CollapsingArea(QtWidgets.QWidget):
    """
    Class supplying a title bar with an arrow beside it;
    clicking the bar minimises or maximises it.
    Similar to Maya's own ones.
    
    Layout is accessible via self.contents or self.mainLayout()
    
    Text can be accessed with self.setText and self.text()
    For tab order, button is self.button
    
    collapseChanged signal is intended for a UI resize function.
    """
    
    collapseChanged = QtCore.Signal(bool)
    
    def __init__(self, parent=None, name='collapsingAreaWidget', 
                 collapseChangeCommand=None):
        super(CollapsingArea, self).__init__(parent=parent)
        self.setObjectName(name)
        
        # Font
        fontBold = QtGui.QFont()
        fontBold.setWeight(75)
        fontBold.setBold(True)
        
        # Internal components
        self.overallLayout = QtWidgets.QVBoxLayout()
        self.overallLayout.setSpacing(0)
        self.overallLayout.setMargin(0)
        self.setLayout(self.overallLayout)
        
        self.button = QtWidgets.QToolButton(self)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHeightForWidth(
            self.button.sizePolicy().hasHeightForWidth())
        self.button.setSizePolicy(sizePolicy)
        self.button.setMinimumSize(0, 24)
        self.button.setFont(fontBold)
        self.button.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.button.setArrowType(QtCore.Qt.DownArrow)
        self.button.setObjectName("button")
        self.overallLayout.addWidget(self.button)
        
        self.contentBox = QtWidgets.QWidget(self)
        self.contents = QtWidgets.QVBoxLayout(self.contentBox)
        self.contents.setSpacing(6)
        self.contents.setMargin(9)
        self.contents.setObjectName(name+"ContentsLayout")
        self.overallLayout.addWidget(self.contentBox)
        
        # Connect the change signal if target supplied
        if collapseChangeCommand:
            self.collapseChanged.connect(collapseChangeCommand)
        
        # Make the button minimise the lower section etc
        self.button.clicked.connect(self.toggleCollapsed)
        
        # Wrap button functions
        self.setText = self.button.setText
        self.text = self.button.text
    
    def toggleCollapsed(self, *args):
        self.setCollapsed(not self.collapsed())
    
    def setCollapsed(self, collapsed):
        arrow = [QtCore.Qt.DownArrow, QtCore.Qt.RightArrow][collapsed]
        self.button.setArrowType(arrow)
        self.contentBox.setVisible(not collapsed)
        
        self.collapseChanged.emit(collapsed)
        
    def collapsed(self):
        return self.contentBox.isHidden()
        
    def mainLayout(self):
        return self.contents


class UI(MayaQWidgetDockableMixin, QtWidgets.QWidget):
    existing = None
    
    _toolSpecs = ("N. J. Chisholm", "Follicle Joint Tool")
    
    def __init__(self, openWindow=True, floating=None,
                 resetUI=False):
        self.normalWindowName = "follicleJointDockUI"
        
        # Float it if specified (defines 'Reset' placement)
        if floating is None:
            floating = True
        self._floating = floating
        
        # Init vars for UI layout fixes
        self._dockParentChanged = False
        self._claimFocusLater = False
        self._fixSizeLater = False
        self._alreadyClosed = False
        
        # Initialise this widget
        super(UI, self).__init__()
        
        # Set up the widget contents
        self.setObjectName(self.normalWindowName)
        self.setupUi()  # Also names self widget
        
        # Store initial settings for resetting UI
        self.defaultUIOptions, self.uiOptionElements = self.getUIVals()
        
        # Must remove existing UI (to use the same objectName for Maya ctrl)
        self._removePreexisting()
        
        # Pre stuff for dockable maya control
        # Set maya mixin dockable parameters 
        # (creates parent 'workspaceControl' maya layout widget)
        self.setDockableParameters(
            dockable=True, floating=floating, area='right', retain=False,
            width=self.width(), height=self.height(), x=None, y=None)
        
        # Add event filter to control parent maya-created widget events
        self.parent().installEventFilter(self)
        # Create custom event type for custom deferred events (UI fixes)
        customEventId = QtCore.QEvent.registerEventType(hint=1001)
        self.customEventType = QtCore.QEvent.Type(customEventId)
        
        self.setWindowTitle("Follicle Joint UI")
        
        workspaceCtrlName = self.parent().objectName()
        if not floating:
            # Tab beside attribute editor (using Maya commands)
            pm.workspaceControl(
                workspaceCtrlName, e=1, tabToControl=('AttributeEditor', -1),
                widthProperty='preferred', r=True,
                vcc=self._dockStateChanged)
        else:
            # Add visible change command
            pm.workspaceControl(
                workspaceCtrlName, e=1, vcc=self._dockStateChanged)
        
        # Set a stylesheet for the top UI widget (under the maya dock)
        self.setStyleSheet(UIqss)
        
        # Load the previous UI settings
        if not resetUI:
            self.loadUI(ignoreFloating=True)
        
        if openWindow:
            self.show()
    
    def setupUi(self):
        # Setup QT ui from designer
        #qtUI.Ui_FollicleToolsForm.setupUi(self, self)
        
        # To conveniently change later
        mainWidget = self
        
        # Set font types
        fontPlain = QtGui.QFont()
        fontPlain.setPointSize(8)
        fontBold = QtGui.QFont()
        fontBold.setWeight(75)
        fontBold.setBold(True)
        fontItalic = QtGui.QFont()
        fontItalic.setItalic(True)
        
        # Main Layouts
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHeightForWidth(True)
        mainWidget.setSizePolicy(sizePolicy)
        mainWidget.resize(365, 750)
        mainWidget.setMinimumSize(300, 0)
        
        self.verticalLayout_5 = QtWidgets.QVBoxLayout(mainWidget)
        self.verticalLayout_5.setSpacing(4)
        self.verticalLayout_5.setMargin(2)
        
        # -Add a menu bar
        self.mainMenuBar = QtWidgets.QMenuBar(mainWidget)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHeightForWidth(
            self.mainMenuBar.sizePolicy().hasHeightForWidth())
        self.mainMenuBar.setSizePolicy(sizePolicy)
        self.mainMenuBar.setMinimumSize(0, 22)
        
        #  - 'Options' Menu
        self.options_mn = self.mainMenuBar.addMenu("Options")
        self.optionReset_mi = QtWidgets.QAction('Reset UI', self)
        self.optionStore_mi = QtWidgets.QAction('Save UI Preferences', self)
        self.optionLoad_mi = QtWidgets.QAction('Load UI Preferences', self)
        self.optionClose_mi = QtWidgets.QAction('Close', self)
        self.options_mn.addAction(self.optionReset_mi)
        self.options_mn.addAction(self.optionStore_mi)
        self.options_mn.addAction(self.optionLoad_mi)
        self.options_mn.addSeparator()
        self.options_mn.addAction(self.optionClose_mi)
        
        self.verticalLayout_5.addWidget(self.mainMenuBar)
        
        # - Main Scroll area
        self.scrollArea = QtWidgets.QScrollArea(mainWidget)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHeightForWidth(
            self.scrollArea.sizePolicy().hasHeightForWidth())
        self.scrollArea.setSizePolicy(sizePolicy)
        self.scrollArea.setFont(fontPlain)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setObjectName("scrollArea")
        
        self.scrollAreaWidgetContents = QtWidgets.QWidget(self.scrollArea)
        self.scrollAreaWidgetContents.setGeometry(QtCore.QRect(0, 0, 359, 718))
        self.scrollAreaWidgetContents.setObjectName("scrollAreaWidgetContents")
        self.verticalLayout_6 = QtWidgets.QVBoxLayout(
            self.scrollAreaWidgetContents)
        self.verticalLayout_6.setMargin(0)
        
        # 'Setup' tab section
        self.setupSection = CollapsingArea(
            self.scrollAreaWidgetContents, name="setupSection", 
            collapseChangeCommand=self._adjustFloatingSize)
        self.setup_tly = self.setupSection.mainLayout()
        
        # Create button and mode options
        self.verticalLayout_3 = QtWidgets.QVBoxLayout()
        
        self.create_bn = QtWidgets.QPushButton(self.setupSection)
        sizePolicy_bn = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        sizePolicy_bn.setHeightForWidth(
            self.create_bn.sizePolicy().hasHeightForWidth())
        self.create_bn.setSizePolicy(sizePolicy_bn)
        self.create_bn.setMinimumSize(QtCore.QSize(0, 35))
        self.create_bn.setObjectName("create_bn")
        self.verticalLayout_3.addWidget(self.create_bn)
        
        # - Mode options grid
        self.gridLayout_5 = QtWidgets.QGridLayout()
        
        #  - Radio buttons
        self.arrange_rbnGrp = QtWidgets.QButtonGroup(mainWidget)
        self.arrange_rbnGrp.setObjectName("arrange_rbnGrp")
        
        self.arrangeSingle_rbn = QtWidgets.QRadioButton(self.setupSection)
        self.arrangeSingle_rbn.setFont(fontBold)
        self.arrangeSingle_rbn.setChecked(True)
        self.arrangeSingle_rbn.setObjectName("arrangeSingle_rbn")
        self.arrange_rbnGrp.addButton(self.arrangeSingle_rbn)
        self.gridLayout_5.addWidget(self.arrangeSingle_rbn, 0, 0, 1, 1)
        
        self.arrangeGrid_rbn = QtWidgets.QRadioButton(self.setupSection)
        self.arrangeGrid_rbn.setFont(fontBold)
        self.arrangeGrid_rbn.setObjectName("arrangeGrid_rbn")
        self.arrange_rbnGrp.addButton(self.arrangeGrid_rbn)
        self.gridLayout_5.addWidget(self.arrangeGrid_rbn, 1, 0, 1, 1)
        
        self.arrangeClosest_rbn = QtWidgets.QRadioButton(self.setupSection)
        self.arrangeClosest_rbn.setFont(fontBold)
        self.arrangeClosest_rbn.setObjectName("arrangeClosest_rbn")
        self.arrange_rbnGrp.addButton(self.arrangeClosest_rbn)
        self.gridLayout_5.addWidget(self.arrangeClosest_rbn, 3, 0, 1, 1)
        
        # Grid spin number boxes and checkboxes
        self.gridU_num = QtWidgets.QSpinBox(self.setupSection)
        self.gridU_num.setEnabled(False)
        self.gridU_num.setMinimumSize(QtCore.QSize(70, 0))
        self.gridU_num.setMinimum(1)
        self.gridU_num.setProperty("value", 5)
        self.gridU_num.setObjectName("gridU_num")
        self.gridLayout_5.addWidget(self.gridU_num, 1, 1, 1, 1)
        
        self.gridV_num = QtWidgets.QSpinBox(self.setupSection)
        self.gridV_num.setEnabled(False)
        self.gridV_num.setMinimumSize(QtCore.QSize(70, 0))
        self.gridV_num.setMinimum(1)
        self.gridV_num.setObjectName("gridV_num")
        self.gridLayout_5.addWidget(self.gridV_num, 1, 2, 1, 1)
        
        self.label_9 = QtWidgets.QLabel(self.setupSection)
        self.label_9.setEnabled(False)
        self.label_9.setFont(fontItalic)
        self.gridLayout_5.addWidget(self.label_9, 2, 0, 1, 1)
        
        self.gridBoundU_chk = QtWidgets.QCheckBox(self.setupSection)
        self.gridBoundU_chk.setEnabled(False)
        self.gridBoundU_chk.setText("")
        self.gridBoundU_chk.setChecked(True)
        self.gridBoundU_chk.setObjectName("gridBoundU_chk")
        self.gridLayout_5.addWidget(self.gridBoundU_chk, 2, 1, 1, 1)
        
        self.gridBoundV_chk = QtWidgets.QCheckBox(self.setupSection)
        self.gridBoundV_chk.setEnabled(False)
        self.gridBoundV_chk.setText("")
        self.gridBoundV_chk.setObjectName("gridBoundV_chk")
        self.gridLayout_5.addWidget(self.gridBoundV_chk, 2, 2, 1, 1)
        
        self.verticalLayout_3.addLayout(self.gridLayout_5)
        
        self.setup_tly.addLayout(self.verticalLayout_3)
        
        # Divider
        self.line = QtWidgets.QFrame(self.setupSection)
        self.line.setFrameShape(QtWidgets.QFrame.HLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.setup_tly.addWidget(self.line)
        
        # Name, follicle joint type and radius settings
        self.verticalLayout_2 = QtWidgets.QVBoxLayout()
        
        # - Naming/renaming options
        self.horizontalLayout_5 = QtWidgets.QHBoxLayout()
        
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.label_10 = QtWidgets.QLabel(self.setupSection)
        self.label_10.setFont(fontBold)
        self.horizontalLayout_2.addWidget(self.label_10)
        self.name_txt = QtWidgets.QLineEdit(self.setupSection)
        self.name_txt.setObjectName("name_txt")
        self.horizontalLayout_2.addWidget(self.name_txt)
        self.horizontalLayout_5.addLayout(self.horizontalLayout_2)
        
        self.rename_bn = QtWidgets.QPushButton(self.setupSection)
        self.rename_bn.setObjectName("rename_bn")
        self.horizontalLayout_5.addWidget(self.rename_bn)
        
        self.autoRename_bn = QtWidgets.QPushButton(self.setupSection)
        self.autoRename_bn.setObjectName("autoRename_bn")
        self.horizontalLayout_5.addWidget(self.autoRename_bn)
        
        self.verticalLayout_2.addLayout(self.horizontalLayout_5)
        
        # - Follicle Type options
        self.gridLayout_4 = QtWidgets.QGridLayout()
        
        self.label_3 = QtWidgets.QLabel(self.setupSection)
        self.label_3.setFont(fontBold)
        self.gridLayout_4.addWidget(self.label_3, 0, 0, 1, 1)
        
        self.folTyp_rbnGrp = QtWidgets.QButtonGroup(mainWidget)
        self.folTyp_rbnGrp.setObjectName("folTyp_rbnGrp")
        
        self.folTypStandard_rbn = QtWidgets.QRadioButton(self.setupSection)
        self.folTypStandard_rbn.setChecked(True)
        self.folTypStandard_rbn.setObjectName("folTypStandard_rbn")
        self.folTyp_rbnGrp.addButton(self.folTypStandard_rbn)
        self.gridLayout_4.addWidget(self.folTypStandard_rbn, 1, 0, 1, 1)
        
        self.folTypReverse_rbn = QtWidgets.QRadioButton(self.setupSection)
        self.folTypReverse_rbn.setObjectName("folTypReverse_rbn")
        self.folTyp_rbnGrp.addButton(self.folTypReverse_rbn)
        self.gridLayout_4.addWidget(self.folTypReverse_rbn, 1, 1, 1, 1)
        
        self.folTypPlain_rbn = QtWidgets.QRadioButton(self.setupSection)
        self.folTypPlain_rbn.setObjectName("folTypPlain_rbn")
        self.folTyp_rbnGrp.addButton(self.folTypPlain_rbn)
        self.gridLayout_4.addWidget(self.folTypPlain_rbn, 2, 0, 1, 1)
        
        self.folTypJoint_rbn = QtWidgets.QRadioButton(self.setupSection)
        self.folTypJoint_rbn.setObjectName("folTypJoint_rbn")
        self.folTyp_rbnGrp.addButton(self.folTypJoint_rbn)
        self.gridLayout_4.addWidget(self.folTypJoint_rbn, 2, 1, 1, 1)
        
        self.verticalLayout_2.addLayout(self.gridLayout_4)
        
        # - Left/Right Prefix options
        self.gridLayout_2 = QtWidgets.QGridLayout()
        
        self.label_7 = QtWidgets.QLabel(self.setupSection)
        self.label_7.setFont(fontBold)
        self.gridLayout_2.addWidget(self.label_7, 0, 0, 1, 2)
        
        self.label_4 = QtWidgets.QLabel(self.setupSection)
        self.label_4.setFont(fontItalic)
        self.gridLayout_2.addWidget(self.label_4, 1, 0, 1, 1)
        
        self.label_5 = QtWidgets.QLabel(self.setupSection)
        self.label_5.setFont(fontItalic)
        self.gridLayout_2.addWidget(self.label_5, 1, 1, 1, 1)
        
        self.label_6 = QtWidgets.QLabel(self.setupSection)
        self.label_6.setFont(fontItalic)
        self.gridLayout_2.addWidget(self.label_6, 1, 2, 1, 1)
        
        self.sidePreLeft_txt = QtWidgets.QLineEdit(self.setupSection)
        self.sidePreLeft_txt.setObjectName("sidePreLeft_txt")
        self.gridLayout_2.addWidget(self.sidePreLeft_txt, 2, 0, 1, 1)
        
        self.sidePreMid_txt = QtWidgets.QLineEdit(self.setupSection)
        self.sidePreMid_txt.setObjectName("sidePreMid_txt")
        self.gridLayout_2.addWidget(self.sidePreMid_txt, 2, 1, 1, 1)
        
        self.sidePreRight_txt = QtWidgets.QLineEdit(self.setupSection)
        self.sidePreRight_txt.setObjectName("sidePreRight_txt")
        self.gridLayout_2.addWidget(self.sidePreRight_txt, 2, 2, 1, 1)
        
        self.verticalLayout_2.addLayout(self.gridLayout_2)
        
        # - Joint Radius set
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        
        self.label_8 = QtWidgets.QLabel(self.setupSection)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHeightForWidth(
            self.label_8.sizePolicy().hasHeightForWidth())
        self.label_8.setSizePolicy(sizePolicy)
        self.label_8.setFont(fontBold)
        self.horizontalLayout.addWidget(self.label_8)
        
        self.jointRad_fl = QtWidgets.QDoubleSpinBox(self.setupSection)
        self.jointRad_fl.setSingleStep(0.1)
        self.jointRad_fl.setProperty("value", 0.5)
        self.jointRad_fl.setObjectName("jointRad_fl")
        self.horizontalLayout.addWidget(self.jointRad_fl)
        
        self.verticalLayout_2.addLayout(self.horizontalLayout)
        
        self.setup_tly.addLayout(self.verticalLayout_2)
        
        # Divider
        self.line_2 = QtWidgets.QFrame(self.setupSection)
        self.line_2.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_2.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.setup_tly.addWidget(self.line_2)
        
        # Misc fol creation and connection tools
        self.verticalLayout_4 = QtWidgets.QVBoxLayout()
        self.verticalLayout_4.setSizeConstraint(
            QtWidgets.QLayout.SetDefaultConstraint)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        
        # - Duplicate and Mirror
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        
        self.duplicate_bn = QtWidgets.QPushButton(self.setupSection)
        self.duplicate_bn.setSizePolicy(sizePolicy_bn)
        self.duplicate_bn.setMinimumSize(QtCore.QSize(0, 30))
        self.duplicate_bn.setObjectName("duplicate_bn")
        self.horizontalLayout_4.addWidget(self.duplicate_bn)
        
        self.mirror_bn = QtWidgets.QPushButton(self.setupSection)
        self.mirror_bn.setSizePolicy(sizePolicy_bn)
        self.mirror_bn.setMinimumSize(QtCore.QSize(0, 30))
        self.mirror_bn.setObjectName("mirror_bn")
        self.horizontalLayout_4.addWidget(self.mirror_bn)
        
        self.verticalLayout_4.addLayout(self.horizontalLayout_4)
        
        # - Driver connections and surface switch
        self.gridLayout_6 = QtWidgets.QGridLayout()
        self.gridLayout_6.setSizeConstraint(QtWidgets.QLayout.SetMaximumSize)
        self.gridLayout_6.setObjectName("gridLayout_6")
        
        self.offsetDriver_bn = QtWidgets.QPushButton(self.setupSection)
        self.offsetDriver_bn.setSizePolicy(sizePolicy_bn)
        self.offsetDriver_bn.setObjectName("offsetDriver_bn")
        self.gridLayout_6.addWidget(self.offsetDriver_bn, 0, 0, 1, 1)
        
        self.label_2 = QtWidgets.QLabel(self.setupSection)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHeightForWidth(
            self.label_2.sizePolicy().hasHeightForWidth())
        self.label_2.setSizePolicy(sizePolicy)
        self.label_2.setMinimumSize(QtCore.QSize(40, 0))
        self.gridLayout_6.addWidget(self.label_2, 0, 1, 1, 1)
        
        self.offsetDriveRatio_fl = QtWidgets.QDoubleSpinBox(self.setupSection)
        self.offsetDriveRatio_fl.setDecimals(3)
        self.offsetDriveRatio_fl.setMaximum(1.0)
        self.offsetDriveRatio_fl.setSingleStep(0.05)
        self.offsetDriveRatio_fl.setProperty("value", 0.5)
        self.offsetDriveRatio_fl.setObjectName("offsetDriveRatio_fl")
        self.gridLayout_6.addWidget(self.offsetDriveRatio_fl, 0, 2, 1, 1)
        
        self.switchPatch_bn = QtWidgets.QPushButton(self.setupSection)
        self.switchPatch_bn.setObjectName("switchPatch_bn")
        self.gridLayout_6.addWidget(self.switchPatch_bn, 1, 0, 1, 1)
        
        self.switchClosestPt_chk = QtWidgets.QCheckBox(self.setupSection)
        self.switchClosestPt_chk.setChecked(True)
        self.switchClosestPt_chk.setTristate(False)
        self.switchClosestPt_chk.setObjectName("switchClosestPt_chk")
        self.gridLayout_6.addWidget(self.switchClosestPt_chk, 1, 1, 1, 2)
        
        self.verticalLayout_4.addLayout(self.gridLayout_6)
        
        self.setup_tly.addLayout(self.verticalLayout_4)
        
        self.verticalLayout_6.addWidget(self.setupSection)
        
        
        # 'Helper' tab section
        self.helperSection = CollapsingArea(
            self.scrollAreaWidgetContents, name="helperSection", 
            collapseChangeCommand=self._adjustFloatingSize)
        self.helper_tly = self.helperSection.mainLayout()
        
        # Quick select buttons
        self.label = QtWidgets.QLabel(self.helperSection)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHeightForWidth(
            self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)
        self.label.setFont(fontBold)
        self.label.setObjectName("label")
        self.helper_tly.addWidget(self.label)
        
        self.gridLayout_7 = QtWidgets.QGridLayout()
        
        self.selectMain_bn = QtWidgets.QPushButton(self.helperSection)
        sizePolicy_bnMin = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy_bnMin.setHeightForWidth(
            self.selectMain_bn.sizePolicy().hasHeightForWidth())
        self.selectMain_bn.setSizePolicy(sizePolicy_bnMin)
        self.selectMain_bn.setObjectName("selectMain_bn")
        self.gridLayout_7.addWidget(self.selectMain_bn, 0, 0, 1, 1)
        
        self.selectTopNodes_bn = QtWidgets.QPushButton(self.helperSection)
        self.selectTopNodes_bn.setSizePolicy(sizePolicy_bnMin)
        self.selectTopNodes_bn.setObjectName("selectTopNodes_bn")
        self.gridLayout_7.addWidget(self.selectTopNodes_bn, 0, 1, 1, 1)
        
        self.selectJoints_bn = QtWidgets.QPushButton(self.helperSection)
        self.selectJoints_bn.setSizePolicy(sizePolicy_bnMin)
        self.selectJoints_bn.setObjectName("selectJoints_bn")
        self.gridLayout_7.addWidget(self.selectJoints_bn, 1, 0, 1, 1)
        
        self.selectFols_bn = QtWidgets.QPushButton(self.helperSection)
        self.selectFols_bn.setSizePolicy(sizePolicy_bnMin)
        self.selectFols_bn.setObjectName("selectFols_bn")
        self.gridLayout_7.addWidget(self.selectFols_bn, 1, 1, 1, 1)
        
        self.helper_tly.addLayout(self.gridLayout_7)
        
        # Separator
        self.line_3 = QtWidgets.QFrame(self.helperSection)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHeightForWidth(
            self.line_3.sizePolicy().hasHeightForWidth())
        self.line_3.setSizePolicy(sizePolicy)
        self.line_3.setMinimumSize(QtCore.QSize(20, 0))
        self.line_3.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_3.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.helper_tly.addWidget(self.line_3)
        
        # Offset value tools
        self.label_11 = QtWidgets.QLabel(self.helperSection)
        self.label_11.setFont(fontBold)
        self.helper_tly.addWidget(self.label_11)
        
        # - Mirror values options
        self.horizontalLayout_6 = QtWidgets.QHBoxLayout()
        
        self.valMirror_bn = QtWidgets.QPushButton(self.helperSection)
        self.valMirror_bn.setObjectName("valMirror_bn")
        self.horizontalLayout_6.addWidget(self.valMirror_bn)
        
        self.valMirrorOffsets_chk = QtWidgets.QCheckBox(self.helperSection)
        self.valMirrorOffsets_chk.setChecked(True)
        self.valMirrorOffsets_chk.setObjectName("valMirrorOffsets_chk")
        self.horizontalLayout_6.addWidget(self.valMirrorOffsets_chk)
        
        self.valMirrorDrivRatio_chk = QtWidgets.QCheckBox(self.helperSection)
        self.valMirrorDrivRatio_chk.setObjectName("valMirrorDrivRatio_chk")
        self.horizontalLayout_6.addWidget(self.valMirrorDrivRatio_chk)
        
        self.helper_tly.addLayout(self.horizontalLayout_6)
        
        # - Freeze button
        self.freeze_bn = QtWidgets.QPushButton(self.helperSection)
        self.freeze_bn.setSizePolicy(sizePolicy_bn)
        self.freeze_bn.setObjectName("freeze_bn")
        self.helper_tly.addWidget(self.freeze_bn)
        
        self.verticalLayout_6.addWidget(self.helperSection)
        spacerItem2 = QtWidgets.QSpacerItem(
            20, 40, QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_6.addItem(spacerItem2)
        
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)
        self.verticalLayout_5.addWidget(self.scrollArea)
    
        
        # UI translation (untested but default with designer)
        self.retranslateUi(mainWidget)
        
        # Set tab order
        itemOrder = [
            self.setupSection.button, self.helperSection.button,
            self.create_bn, self.arrangeSingle_rbn, self.arrangeGrid_rbn,
            self.arrangeClosest_rbn, self.gridU_num, self.gridV_num,
            self.gridBoundU_chk, self.gridBoundV_chk, self.name_txt,
            self.rename_bn, self.autoRename_bn, self.folTypStandard_rbn,
            self.folTypReverse_rbn, self.folTypPlain_rbn,
            self.folTypJoint_rbn, self.sidePreLeft_txt, self.sidePreMid_txt,
            self.sidePreRight_txt, self.jointRad_fl, self.duplicate_bn,
            self.mirror_bn, self.offsetDriver_bn, self.offsetDriveRatio_fl,
            self.switchPatch_bn, self.switchClosestPt_chk, self.selectMain_bn,
            self.selectTopNodes_bn, self.selectJoints_bn, self.selectFols_bn,
            self.valMirror_bn, self.valMirrorOffsets_chk,
            self.valMirrorDrivRatio_chk, self.freeze_bn, self.scrollArea
            ]
        firstItem = itemOrder.pop(0)
        for qItem in itemOrder:
            mainWidget.setTabOrder(firstItem, qItem)
            firstItem = qItem
        
        # Connect section enable/disable
        self.arrangeGrid_rbn.toggled.connect(self.gridU_num.setEnabled)
        self.arrangeGrid_rbn.toggled.connect(self.gridV_num.setEnabled)
        self.arrangeGrid_rbn.toggled.connect(self.label_9.setEnabled)
        self.arrangeGrid_rbn.toggled.connect(self.gridBoundU_chk.setEnabled)
        self.arrangeGrid_rbn.toggled.connect(self.gridBoundV_chk.setEnabled)
        
        # Link up buttons
        undoableCall(self.create_bn.clicked, self.create_call)
        undoableCall(self.rename_bn.clicked, self.rename_call)
        undoableCall(self.autoRename_bn.clicked, self.autoRename_call)
        undoableCall(self.duplicate_bn.clicked, self.duplicate_call)
        undoableCall(self.mirror_bn.clicked, self.mirror_call)
        undoableCall(self.offsetDriver_bn.clicked, self.offsetDriver_call)
        undoableCall(
            self.freeze_bn.clicked, folEng.freezeOffsets, useSelection=True)
        undoableCall(self.valMirror_bn.clicked, self.valMirror_call)
        
        sel = self.select_call
        undoableCall(
            self.selectMain_bn.clicked, sel, 'controlObj', noArgs=True)
        undoableCall(
            self.selectJoints_bn.clicked, sel, 'jnt', noArgs=True)
        undoableCall(
            self.selectTopNodes_bn.clicked, sel, 'topObj', noArgs=True)
        undoableCall(
            self.selectFols_bn.clicked, sel, 'fol', noArgs=True)
        
        undoableCall(self.switchPatch_bn.clicked, self.switchPatch_call)
        
        # Link up menu items
        undoableCall(
            self.optionReset_mi.triggered, self.resetUI, noArgs=True)
        undoableCall(
            self.optionStore_mi.triggered, self.storeUI, noArgs=True,
            textReply=True)
        undoableCall(
            self.optionLoad_mi.triggered, self.loadUI, noArgs=True,
            textReply=True)
        self.optionClose_mi.triggered.connect(self.close)
        
        # Add IDs to radiobuttons for saving settings
        self.arrange_rbnGrp.setId(self.arrangeSingle_rbn, 0)
        self.arrange_rbnGrp.setId(self.arrangeGrid_rbn, 1)
        self.arrange_rbnGrp.setId(self.arrangeClosest_rbn, 2)
        self.folTyp_rbnGrp.setId(self.folTypStandard_rbn, 0)
        self.folTyp_rbnGrp.setId(self.folTypReverse_rbn, 1)
        self.folTyp_rbnGrp.setId(self.folTypPlain_rbn, 2)
        self.folTyp_rbnGrp.setId(self.folTypJoint_rbn, 3)
    
    def retranslateUi(self, mainWidget):
        name = mainWidget.objectName()
        tr = lambda text:QtWidgets.QApplication.translate(
                            name, text, None)
        self.setupSection.setText(tr("Follicle Setup"))
        self.create_bn.setToolTip(
            tr("Create follicle(s) using the method chosen below"))
        self.create_bn.setText(tr("Create Follicles"))
        self.arrangeSingle_rbn.setToolTip(
            tr("A single follicle placed at uv value (0.5, 0.5)"))
        self.arrangeSingle_rbn.setText(tr("Single Follicle"))
        self.arrangeGrid_rbn.setToolTip(
            tr("New follicles distributed evenly across the 0 to 1 space"))
        self.arrangeGrid_rbn.setText(tr("Grid"))
        self.arrangeClosest_rbn.setToolTip(
            tr("Follicles created at the closest point on the surface to " 
               "each selected object/component"))
        self.arrangeClosest_rbn.setText(tr("Closest Points"))
        self.gridBoundV_chk.setToolTip(
            tr("Row starts on the edge instead of being centered"))
        self.gridBoundU_chk.setToolTip(
            tr("Row starts on the edge instead of being centered"))
        self.gridV_num.setToolTip(tr("Rows along the surface V direction"))
        self.gridV_num.setSuffix(tr(" rows"))
        self.gridU_num.setToolTip(tr("Rows along the surface U direction"))
        self.gridU_num.setSuffix(tr(" columns"))
        self.label_9.setToolTip(
            tr("Rows start on the edge instead of being centered"))
        self.label_9.setText(tr("Edge Bounded"))
        self.label_10.setText(tr("Name"))
        self.name_txt.setToolTip(tr("Name given to follicle joints"))
        self.name_txt.setText(tr("folJnt#"))
        self.rename_bn.setToolTip(
            tr("Rename the selected follicle joints (automatically assigns eg."
               " joint suffix to joint)"))
        self.rename_bn.setText(tr("Rename"))
        self.autoRename_bn.setToolTip(
        tr("Rename the selected follicles to Left/Right conventions based on "
           "uv parameters"))
        self.autoRename_bn.setText(tr("Auto Name"))
        self.folTypPlain_rbn.setToolTip(
            tr("The same as a normal follicle created through the dynamics "
               "menu"))
        self.folTypPlain_rbn.setText(tr("Plain Follicle"))
        self.folTypStandard_rbn.setToolTip(
            tr("Standard configuration is a joint parented to a normal "
               "follicle"))
        self.folTypStandard_rbn.setText(tr("Standard"))
        self.folTypReverse_rbn.setToolTip(
            tr("Same as \'Standard\' but with the follicle\'s Shape on the "
               "joint"))
        self.folTypReverse_rbn.setText(tr("Reverse"))
        self.folTypJoint_rbn.setToolTip(
            tr("The most basic follicle joint; a joint with a "
               "follicle \'Shape\'"))
        self.folTypJoint_rbn.setText(tr("Follicle Joint"))
        self.label_3.setText(tr("Follicle Joint Type"))
        self.sidePreLeft_txt.setToolTip(
            tr("The prefix given/recognised for objects on the left side"))
        self.sidePreLeft_txt.setText(tr("L_"))
        self.label_5.setText(tr("Middle"))
        self.label_6.setText(tr("Right"))
        self.sidePreMid_txt.setToolTip(
            tr("The prefix given/recognised for objects on neither side"))
        self.sidePreMid_txt.setText(tr("M_"))
        self.sidePreRight_txt.setToolTip(
            tr("The prefix given/recognised for objects on the right side"))
        self.sidePreRight_txt.setText(tr("R_"))
        self.label_4.setText(tr("Left"))
        self.label_7.setText(tr("Prefixes for sides"))
        self.label_8.setText(tr("Joint Radius"))
        self.jointRad_fl.setToolTip(
            tr("The radius given to new joints (doesn\'t affect Duplicate)"))
        self.duplicate_bn.setToolTip(
            tr("Make a copy of the selected follicle(s), but in the "
               "chosen type"))
        self.duplicate_bn.setText(tr("Duplicate"))
        self.mirror_bn.setToolTip(
            tr("Create a Left follicle to oppose a Right one, or vise versa"))
        self.mirror_bn.setText(tr("Mirror"))
        self.offsetDriver_bn.setToolTip(
            tr("Connect the first selected follicle to drive the second\'s "
               "offset"))
        self.offsetDriver_bn.setText(tr("Add as Offset Driver"))
        self.label_2.setText(tr("Ratio"))
        self.offsetDriveRatio_fl.setToolTip(
            tr("This is the amount that the driven follicle follows the "
               "driver\'s value"))
        self.switchPatch_bn.setToolTip(
            tr("Select follicles and the new surface and run"))
        self.switchPatch_bn.setText(tr("Switch Surface"))
        self.switchClosestPt_chk.setToolTip(
            tr("If enabled, the closest points in worldspace are used, "
               "updating the uv values"))
        self.switchClosestPt_chk.setText(tr("Use Closest Points"))
        self.helperSection.setText(tr("Helper Tools"))
        self.label.setText(tr("Quick Select"))
        self.selectMain_bn.setToolTip(
            tr("Select the node, in each selected follicle joint setup, with "
               "the uv parameters"))
        self.selectMain_bn.setText(tr("Main"))
        self.selectJoints_bn.setToolTip(
            tr("Select the joint, in each selected follicle joint setup"))
        self.selectJoints_bn.setText(tr("Joints"))
        self.selectTopNodes_bn.setToolTip(
            tr("Select the top transform in the follicle joint\'s hierarchy"))
        self.selectTopNodes_bn.setText(tr("Top Nodes"))
        self.selectFols_bn.setToolTip(
            tr("Select the follicle shape in each selected follicle "
               "joint setup"))
        self.selectFols_bn.setText(tr("Follicles"))
        self.label_11.setText(tr("Offset Values"))
        self.valMirror_bn.setToolTip(
            tr("Mirror the offset/driver ratios from a Left to a Right "
               "follicle, or vise versa"))
        self.valMirror_bn.setText(tr("Mirror Values"))
        self.valMirrorOffsets_chk.setToolTip(tr("Mirror UV Offsets"))
        self.valMirrorOffsets_chk.setText(tr("Offsets"))
        self.valMirrorDrivRatio_chk.setToolTip(
            tr("Mirror UV Driver Ratios (offset \'speed\' and driver "
               "follicle ratios)"))
        self.valMirrorDrivRatio_chk.setText(tr("Driver Ratios"))
        self.freeze_bn.setToolTip(
            tr("Zero the offsets by moving their UV values into the base "
               "UV parameters."))
        self.freeze_bn.setText(tr("Freeze Offsets"))
    
    def getUIVals(self):
        uiElements = [
            self, self.arrange_rbnGrp, self.folTyp_rbnGrp,
            self.gridV_num, self.gridU_num,
            self.gridBoundV_chk, self.gridBoundU_chk,
            self.name_txt, self.sidePreLeft_txt, self.sidePreMid_txt,
            self.sidePreRight_txt, self.jointRad_fl, self.offsetDriveRatio_fl,
            self.switchClosestPt_chk, self.valMirrorOffsets_chk,
            self.valMirrorDrivRatio_chk, self.setupSection, self.helperSection
            ]
        settingDict = {}
        for wdg in uiElements:
            if isinstance(wdg, self.__class__):
                # Store dock widget (effectively window) details
                pt = wdg.mapToGlobal(QtCore.QPoint(0,0))
                val = [
                    int( wdg.isFloating() ),
                    int( wdg.width() ),
                    int( wdg.height() ),
                    int( pt.x() ),
                    int( pt.y() ),
                    wdg.dockArea()
                    ]
            elif isinstance(wdg, CollapsingArea):
                val = int(wdg.collapsed())
            elif isinstance(wdg, QtWidgets.QButtonGroup):
                val = wdg.checkedId()
            elif isinstance(wdg, QtWidgets.QDoubleSpinBox):
                val = wdg.value()
            elif isinstance(wdg, QtWidgets.QSpinBox):
                val = wdg.value()
            elif isinstance(wdg, QtWidgets.QCheckBox):
                val = int( wdg.isChecked() )
            elif isinstance(wdg, QtWidgets.QLineEdit):
                val = wdg.text()
            elif isinstance(wdg, QtWidgets.QTabWidget):
                val = wdg.currentIndex()
            elif isinstance(wdg, QtWidgets.QToolBox):
                val = wdg.currentIndex()
            else:
                raise TypeError(
                    "UI Element type" + str(type(wdg)) +
                    "has not been set up to get settings!")
            settingDict[wdg.objectName()] = val
        return settingDict, uiElements
    
    def show(self):
        """Wrap the usual show method, adjusting size and storing on class"""
        # Show the window
        MayaQWidgetDockableMixin.show(self)  # Don't run normal widget show
        
        # Adjust floating dock size
        self._adjustFloatingSize()
        
        UI.existing = self
    
    def resetUI(self):
        self.loadUI(self.defaultUIOptions)
    
    def storeUI(self, textReply=False):
        """Store the UI settings as a QT ini file (platform independent)"""
        # Get the current UI values
        settingDict = self.getUIVals()[0]
        settings = QtCore.QSettings(*UI._toolSpecs)
        for name, val in settingDict.iteritems():
            settings.setValue(name, val)
        
        # Trigger the settings to be written to storage
        del settings
        
        if textReply:
            mayaPrint("Follicle Joints UI - Preferences Stored!")
    
    def loadUI(self, revertToDefault=False, textReply=False, 
               ignoreFloating=False):
        """Load the UI settings from the default or stored options"""
        if not revertToDefault:
            # Load Qt settings
            settings = QtCore.QSettings(*UI._toolSpecs)
        
        for wdg in self.uiOptionElements:
            name = wdg.objectName()
            val = None
            if revertToDefault:
                # Use default setting
                val = self.defaultUIOptions[name]
            else:
                # Use stored Qt setting
                val = settings.value(name, None)
            
            if val is not None:
                if isinstance(wdg, self.__class__):
                    # Load dock settings
                    dockVals = [int(item) for item in val[:5]]
                    if not ignoreFloating:
                        isFloating = dockVals[0]
                        workspaceCtrlName = self.parent().objectName()
                        if isFloating:
                            # Set floating 
                            pm.workspaceControl(
                                workspaceCtrlName, e=1, floating=True)
                            wdg.resize(dockVals[1], dockVals[2])
                            winParent = self._getFloatWindow(wdg)
                            winParent.move(dockVals[3], dockVals[4])
                        else:
                            # Dock to where the attribute editor is 
                            #(workaround as locations aren't named)
                            pm.workspaceControl(
                                workspaceCtrlName, e=1, 
                                tabToControl=('AttributeEditor', -1),
                                widthProperty='preferred', r=True)
                elif isinstance(wdg, CollapsingArea):
                    # Collapsing section
                    if int(wdg.collapsed()) != val:
                        wdg.toggleCollapsed()
                elif isinstance(wdg, QtWidgets.QButtonGroup):
                    chkdButton = wdg.button(val)
                    if chkdButton is not None:
                        chkdButton.setChecked(True)
                elif isinstance(wdg, QtWidgets.QDoubleSpinBox):
                    wdg.setValue( float(val) )
                elif isinstance(wdg, QtWidgets.QSpinBox):
                    wdg.setValue(val)
                elif isinstance(wdg, QtWidgets.QTabWidget):
                    wdg.setCurrentIndex(val)
                elif isinstance(wdg, QtWidgets.QToolBox):
                    wdg.setCurrentIndex(val)
                elif isinstance(wdg, QtWidgets.QCheckBox):
                    wdg.setChecked(val)
                elif isinstance(wdg, QtWidgets.QLineEdit):
                    wdg.setText(val)
                else:
                    raise TypeError("UI Element type " + str(type(wdg)) +
                        "has not been set up to get settings!")
        
        if textReply:
            mayaPrint("Follicle Joints UI - Preferences Loaded!")
    
    def close(self, saveSettings=True):
        # Prevent being called again if called manually
        self._alreadyClosed = True  
        
        # Store the UI options (Qt settings file)
        if saveSettings:
            self.storeUI(textReply=True)
        
        MayaQWidgetDockableMixin.close(self)
    
    def eventFilter(self, targetObj, event):
        # Intercept events from the (Maya-created) parent
        if targetObj == self.parent():
            if event.type() == event.ParentChange:
                # Record if the parent has changed for docking refocus
                self._dockParentChanged = True
                
            elif event.type() == self.customEventType:
                # Run delayed (Maya) interface fix(es)
                if (self._claimFocusLater and self._dockParentChanged and
                        self.isDockable() and not self.isVisible() ):
                    # Delayed update that happens after the dock is tabbed
                    self._dockedTabToTop()
                    self._claimFocusLater = False
                    self._dockParentChanged = False
                    
                if self._fixSizeLater and self.isVisible():
                    # Delayed update that happens after the dock tab changes
                    self._adjustDockedSize()
                    self._fixSizeLater = False
                    
                return True
            
            elif event.type() == event.Close:
                # When floating window is closed, ensure 
                if not self._alreadyClosed:
                    self.close()
            
            '''elif event.type() == event.DeferredDelete:
                # Run closing operations when the dock is closed.
                self.close()''' # Glitches on script reload (new window closes)
        
        # Let events continue
        return QtWidgets.QWidget.eventFilter(self, targetObj, event)
    
    def _getFloatWindow(self, widget):
        winParent = widget.parent()
        while winParent is not None:
            if winParent.isWindow():
                break
            winParent = winParent.parent()
        if winParent and winParent.objectName() != "MayaWindow":
            return winParent
    
    def _dockStateChanged(self, *args):
        """Fix Maya/Qt docked tab glitches.
        
        Triggered by Maya UI object 'visual change command',
        just BEFORE dock state change finishes.
        
        Fixes a newly docked tab to remain in focus:
        (isFloating() still returns True even though just 'docked')
        Posts a delayed (lower priority) event to raise the tab.
        
        Fixes the width of an un-minimised docked tab:
        Posts a delayed (lower priority) event to resize the parent of the tab.
        """
        isFloating = self.isFloating()  # Doesn't update before this def
        
        # Delay focus as new parenting isn't finalised.
        self._claimFocusLater = True
        
        # Send a delayed event (so that dock is ready before it runs)
        # (Lower priority than low priority)
        customEvent = QtCore.QEvent(self.customEventType)
        qtAp = QtWidgets.qApp
        qtAp.postEvent(
            self.parent(), customEvent, priority=QtCore.Qt.LowEventPriority-1)
        
        if not self._floating and not isFloating:
            self._fixSizeLater = True
        self._floating = isFloating
    
    def _removePreexisting(self):
        """Remove a window with the same name if it already exists"""
        # Check for workspace ctrl name-to-be (set in maya mixin)
        workspaceControlName = self.objectName() + 'WorkspaceControl'
        if pm.workspaceControl(workspaceControlName, q=1, ex=1):
            pm.deleteUI(workspaceControlName)
        
        # Check for a pre-existing window 
        if UI.existing is not None:
            try:
                UI.existing.close(saveSettings=False)
            except:
                pass
            UI.existing = None
        
        # Check also pre-existing windows in case this module is reloaded
        existingWdgs = _getNamedMainChild(self.normalWindowName)
        if existingWdgs:
            for wdg in existingWdgs:
                if hasattr(wdg, 'isVisible') and wdg.isVisible():
                    uiWdg = wdg.widget()
                    if isinstance(uiWdg, UI): #try:
                        uiWdg.close(saveSettings=False)
                    else:
                        wdg.close()
    
    def _dockedTabToTop(self):
        """ Raise docked tab to the the tab in focus
        
        Must be called after the docking is fully finished or it has no effect.
        """
        workspaceCtrlName = self.parent().objectName()
        pm.workspaceControl(workspaceCtrlName, e=1, r=True)
        
        self._adjustDockedSize()
        self._fixSizeLater = False
    
    def _adjustDockedSize(self):
        """ Fix width of tabbed dock when un-minimised """
        # Adjust size by setting minimum size of parent tab widgets
        # Prevents window being half-occluded
        tabWdg = self.parent()
        while tabWdg is not None:
            if type(tabWdg) == QtWidgets.QTabWidget:
                break
            tabWdg = tabWdg.parent()
        if tabWdg:
            tabWdg.setMinimumSize(365, 50)  # Affects floating window too
    
    def _adjustFloatingSize(self, *args):
        # Resize the window (if applicable)
        if self.isFloating():
            # Find the window widget above this one, and adjust size to fit.
            winParent = self._getFloatWindow(self)
            if winParent:
                winParent.adjustSize()
                winParent.resize(self.scrollAreaWidgetContents.sizeHint())
    
    def getSelectedFols(self, requireNum=1):
        folObjs = folEng.getFollicleJoints(useSelection=True, strict=False)
        if not folObjs or len(folObjs) < requireNum:
            plural = ''
            num = 'a'
            if requireNum > 1:
                plural = 's'
                num = str(requireNum)
            raise StandardError(
                "Please select %s follicle joint%s first!" % (num, plural))
        return folObjs
    
    def newName(self, strict=True):
        name = self.name_txt.text()
        if strict and not name:
            raise StandardError("No Name was given!")
        return name
    
    def jntRadius(self):
        return self.jointRad_fl.value()
    
    def folType(self):
        folTypes = {
            't/f':self.folTypPlain_rbn, 
            't/f-j':self.folTypStandard_rbn, 
            't-j/f':self.folTypReverse_rbn, 
            'j/f':self.folTypJoint_rbn, 
            }
        chosen = self.folTyp_rbnGrp.checkedButton()
        for folTypeStr in folTypes:
            if chosen == folTypes[folTypeStr]:
                return folTypeStr
    
    def sidePrefix(self):
        sideVals = [
            self.sidePreLeft_txt.text().strip(),
            self.sidePreRight_txt.text().strip(),
            self.sidePreMid_txt.text().strip()]
        return sideVals
    
    def create_call(self, *args):
        # Get generic new follicle keyword values
        kwargs = {
            'name':self.newName(),
            'jntRadius':self.jntRadius(),
            'folType':self.folType()}
        
        # Check method of creation
        method_rbn = self.arrange_rbnGrp.checkedButton()
        if method_rbn == self.arrangeSingle_rbn:
            folEng.newFollicle(uv=[0.5, 0.5], **kwargs)
        elif method_rbn == self.arrangeGrid_rbn:
            uvRows = [self.gridU_num.value(), self.gridV_num.value()]
            edges = [self.gridBoundU_chk.isChecked(), 
                     self.gridBoundV_chk.isChecked()]
            folEng.newFollicleGrid(
                uvRows=uvRows, edgeBounded=edges, 
                uvRange=[None, None, None, None], giveWarning=True, **kwargs)
        elif method_rbn == self.arrangeClosest_rbn:
            folEng.newFollicleAtClosestPt(**kwargs)
    
    def rename_call(self, *args):
        folObjs = self.getSelectedFols()
        newName = self.newName()
        folEng.multiRename(objs=folObjs, name=newName, skipSelect=False)
        
    def autoRename_call(self, *args):
        newName = self.newName(strict=False)
        folEng.autoRename(
            useSelection=True, name=newName, skipSelect=False, scaleY=4,
            uvAsXy=['u', 'v'], midVal=0.5, middleTolerance=0.04,
            sidePrefix=self.sidePrefix())
        
    def mirror_call(self, *args):
        folEng.mirrorFollicles(
            selectNew=True, axis='u', midVal=0.5, uvRange=[0.0, 1.0],
            sidePrefix=self.sidePrefix(), folType=self.folType(),
            strict=True, warnings=True)
    
    def duplicate_call(self, *args):
        folEng.duplicateFollicles(
            name=self.newName(), folType=self.folType(), selectNew=True)
    
    def offsetDriver_call(self, *args):
        folObjs = self.getSelectedFols(2)
        ratio = self.offsetDriveRatio_fl.value()
        folEng.addAsOffsetDriver(
            objs=folObjs, selectDriver=True, ratio=ratio)
        
    def valMirror_call(self, *args):
        offsets = self.valMirrorOffsets_chk.isChecked()
        drivRat = self.valMirrorDrivRatio_chk.isChecked()
        
        folEng.mirrorFollicleOffsets(
            axis='u', sidePrefix=self.sidePrefix(), offsets=offsets,
            uvDriverRatio=drivRat, drivenOffsetRatios=drivRat)
            
    def select_call(self, subNodeType):
        folObjs = self.getSelectedFols()
        folEng.getSubNodes(
            subNodeType=subNodeType, objs=folObjs, skipSelect=False)
        
    def switchPatch_call(self, *args):
        closestPts = self.switchClosestPt_chk.isChecked()
        folEng.transferFolliclesToPatch(closestPts=closestPts)