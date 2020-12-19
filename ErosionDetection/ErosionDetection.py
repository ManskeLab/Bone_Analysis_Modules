#-----------------------------------------------------
# ErosionDetection.py
#
# Created by:  Mingjie Zhao
# Created on:  23-10-2020
#
# Description: This module sets up the Erosion Detection 3D Slicer extension.
#
#-----------------------------------------------------
import vtk, qt, ctk, slicer
import SimpleITK as sitk
import sitkUtils
from slicer.ScriptedLoadableModule import *
import logging
from ErosionDetectionLib.ErosionDetectionLogic import ErosionDetectionLogic
from ErosionDetectionLib.SegmentEditor import SegmentEditor
from ErosionDetectionLib.MarkupsTable import MarkupsTable

#
# ErosionDetection
#
class ErosionDetection(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Erosion Detection" # TODO make this more human readable by adding spaces
    self.parent.categories = ["Bone"]
    self.parent.dependencies = []
    self.parent.contributors = ["Mingjie Zhao"] # replace with "Firstname Lastname (Organization)"
    self.parent.helpText = """
This module contains steps 4-6 of erosion analysis. It takes an image and its contour. 
Erosions are then identified by placing seed points in each of them. 
Step 4 is to detect erosions.
Step 5 is to manually correct erosions and combine them to a single output.
Step 6 is to compute erosion statistics, i.e. volume, surface area, and roundness.
"""
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = """
Acknowledgement Text
""" # replace with organization, grant and thanks.

#
# ErosionDetectionWidget
#
class ErosionDetectionWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """
  def __init__(self, parent):
    # Initialize logics object
    self._logic = ErosionDetectionLogic()
    self._logic.progressCallBack = self.setProgress

    self._segmentNodeId = ""
    self._contourSegmentId = ""

    ScriptedLoadableModuleWidget.__init__(self, parent)

  def setup(self):
    # Collapsible buttons
    self.erosionsCollapsibleButton = ctk.ctkCollapsibleButton()
    self.manualCorrectionCollapsibleButton = ctk.ctkCollapsibleButton()
    self.statsCollapsibleButton = ctk.ctkCollapsibleButton()

    # Set up widgets inside the collapsible buttons
    self.setupErosions()
    self.setupManualCorrection()
    self.setupStats()

    # Add vertical spacer
    self.layout.addStretch(1)

    # Update buttons
    self.onSelect4()
    self.onSelect5()
    self.onSelect6()
    self.onSelectInputVolume()
    self.onSelectSeed()
    self.onSelectInputErosion()

  def setupErosions(self):
    """Set up widgets in step 4 erosions"""
    # Set text on collapsible button, and add collapsible button to layout
    self.erosionsCollapsibleButton.text = "Step 4 - Erosions"
    self.layout.addWidget(self.erosionsCollapsibleButton)

    # Layout within the collapsible button
    erosionsLayout = qt.QFormLayout(self.erosionsCollapsibleButton)
    erosionsLayout.setVerticalSpacing(5)

    # input volume selector
    self.inputVolumeSelector = slicer.qMRMLNodeComboBox()
    self.inputVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.inputVolumeSelector.selectNodeUponCreation = False
    self.inputVolumeSelector.addEnabled = False
    self.inputVolumeSelector.renameEnabled = True
    self.inputVolumeSelector.removeEnabled = True
    self.inputVolumeSelector.noneEnabled = False
    self.inputVolumeSelector.showHidden = False
    self.inputVolumeSelector.showChildNodeTypes = False
    self.inputVolumeSelector.setMRMLScene(slicer.mrmlScene)
    self.inputVolumeSelector.setToolTip( "Pick the input volume to the erosion detection algorithm" )
    erosionsLayout.addRow("Input Volume: ", self.inputVolumeSelector)

    # input contour selector
    self.inputContourSelector = slicer.qMRMLNodeComboBox()
    self.inputContourSelector.nodeTypes = ["vtkMRMLLabelMapVolumeNode"]
    self.inputContourSelector.selectNodeUponCreation = False
    self.inputContourSelector.addEnabled = False
    self.inputContourSelector.renameEnabled = True
    self.inputContourSelector.removeEnabled = True
    self.inputContourSelector.noneEnabled = False
    self.inputContourSelector.showHidden = False
    self.inputContourSelector.showChildNodeTypes = False
    self.inputContourSelector.setMRMLScene(slicer.mrmlScene)
    self.inputContourSelector.setToolTip( "Pick the input contour label map to the erosion detection algorithm" )
    erosionsLayout.addRow("Input Contour: ", self.inputContourSelector)

    # output volume selector
    self.outputVolumeSelector = slicer.qMRMLNodeComboBox()
    self.outputVolumeSelector.nodeTypes = ["vtkMRMLLabelMapVolumeNode"]
    self.outputVolumeSelector.selectNodeUponCreation = True
    self.outputVolumeSelector.addEnabled = True
    self.outputVolumeSelector.removeEnabled = True
    self.outputVolumeSelector.renameEnabled = True
    self.outputVolumeSelector.noneEnabled = False
    self.outputVolumeSelector.showHidden = False
    self.outputVolumeSelector.showChildNodeTypes = False
    self.outputVolumeSelector.setMRMLScene(slicer.mrmlScene)
    self.outputVolumeSelector.baseName = "ERO"
    self.outputVolumeSelector.setToolTip( "Pick the output volume to store the erosions" )
    erosionsLayout.addRow("Output Volume: ", self.outputVolumeSelector)

    # threshold spin boxes
    self.lowerThresholdText = qt.QSpinBox()
    self.lowerThresholdText.setMinimum(0)
    self.lowerThresholdText.setMaximum(999999)
    self.lowerThresholdText.setSingleStep(10)
    self.lowerThresholdText.value = 3000
    erosionsLayout.addRow("Lower Threshold: ", self.lowerThresholdText)
    self.upperThresholdText = qt.QSpinBox()
    self.upperThresholdText.setMinimum(0)
    self.upperThresholdText.setMaximum(999999)
    self.upperThresholdText.setSingleStep(10)
    self.upperThresholdText.value = 10000
    erosionsLayout.addRow("Upper Threshold: ", self.upperThresholdText)

    # seed point selector
    self.fiducialSelector = slicer.qMRMLNodeComboBox()
    self.fiducialSelector.nodeTypes = ["vtkMRMLMarkupsFiducialNode"]
    self.fiducialSelector.selectNodeUponCreation = True
    self.fiducialSelector.addEnabled = True
    self.fiducialSelector.removeEnabled = True
    self.fiducialSelector.renameEnabled = True
    self.fiducialSelector.noneEnabled = False
    self.fiducialSelector.showHidden = False
    self.fiducialSelector.showChildNodeTypes = False
    self.fiducialSelector.setMRMLScene(slicer.mrmlScene)
    self.fiducialSelector.baseName = "Seed"
    self.fiducialSelector.setToolTip( "Pick the seed points" )
    erosionsLayout.addRow("Seed Points: ", self.fiducialSelector)

    # seed point table
    self.markupsTableWidget = MarkupsTable(self.erosionsCollapsibleButton)
    self.markupsTableWidget.setMRMLScene(slicer.mrmlScene)
    self.markupsTableWidget.setNodeSelectorVisible(False) # use the above selector instead
    self.markupsTableWidget.setButtonsVisible(False)
    self.markupsTableWidget.setPlaceButtonVisible(True)
    self.markupsTableWidget.setDeleteAllButtonVisible(True)
    self.markupsTableWidget.setJumpToSliceEnabled(True)

    # horizontal white space
    erosionsLayout.addRow(qt.QLabel(""))

    # check box for large erosions
    self.erosionCheckBox = qt.QCheckBox('Large Erosion')
    self.erosionCheckBox.checked = False
    self.erosionCheckBox.setToolTip('Set internal parameters for segmenting large erosions')
    erosionsLayout.addRow(self.erosionCheckBox)

    # advanced parameter box
    self.advancedParameterBox = ctk.ctkCollapsibleGroupBox()
    self.advancedParameterBox.title = "Advanced"
    self.advancedParameterBox.collapsed = True
    erosionsLayout.addRow(self.advancedParameterBox)

    # advanced parameter layout
    advancedParameterLayout = qt.QGridLayout(self.advancedParameterBox)
    advancedParameterLayout.setColumnMinimumWidth(2, 15)

    # erosion radius spin boxes
    self.minimalRadiusText = qt.QSpinBox()
    self.minimalRadiusText.setMinimum(1)
    self.minimalRadiusText.setMaximum(99)
    self.minimalRadiusText.setSingleStep(1)
    self.minimalRadiusText.value = 3
    advancedParameterLayout.addWidget(qt.QLabel("Minimum Erosion Radius: "), 0, 0)
    advancedParameterLayout.addWidget(self.minimalRadiusText, 0, 1)
    self.dilationErosionRadiusText = qt.QSpinBox()
    self.dilationErosionRadiusText.setMinimum(1)
    self.dilationErosionRadiusText.setMaximum(99)
    self.dilationErosionRadiusText.setSingleStep(1)
    self.dilationErosionRadiusText.value = 4
    advancedParameterLayout.addWidget(qt.QLabel("Dilate/Erode Radius: "), 0, 3)
    advancedParameterLayout.addWidget(self.dilationErosionRadiusText, 0, 4)

    # Execution layout
    executeGridLayout = qt.QGridLayout()
    executeGridLayout.setRowMinimumHeight(0,15)
    executeGridLayout.setRowMinimumHeight(1,15)

    # Progress Bar
    self.progressBar = qt.QProgressBar()
    self.progressBar.hide()
    executeGridLayout.addWidget(self.progressBar, 0, 0)

    # Get Button
    self.getErosionsButton = qt.QPushButton("Get Erosions")
    self.getErosionsButton.toolTip = "Get erosions stored in a label map"
    self.getErosionsButton.enabled = False
    executeGridLayout.addWidget(self.getErosionsButton, 1, 0)

    # Execution frame with progress bar and get button
    erosionButtonFrame = qt.QFrame()
    erosionButtonFrame.setLayout(executeGridLayout)
    erosionsLayout.addRow(erosionButtonFrame)

    # connections
    self.erosionsCollapsibleButton.connect("contentsCollapsed(bool)", self.onCollapsed4)
    self.getErosionsButton.connect("clicked(bool)", self.onGetErosionsButton)
    self.inputVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect4)
    self.inputVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelectInputVolume)
    self.inputContourSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect4)
    self.outputVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect4)
    self.fiducialSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect4)
    self.fiducialSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelectSeed)
    self.erosionCheckBox.connect("clicked(bool)", self.onLargeErosionChecked)
  
  def setupManualCorrection(self):
    """Set up widgets in step 5 manual correction"""
    # set text on collapsible button, and add collapsible button to layout
    self.manualCorrectionCollapsibleButton.text = "Step 5 - Manual Correction"
    self.manualCorrectionCollapsibleButton.collapsed = True
    self.layout.addWidget(self.manualCorrectionCollapsibleButton)

    # layout within the collapsible button
    manualCorrectionLayout = qt.QVBoxLayout(self.manualCorrectionCollapsibleButton)

    # layout for input and output selectors
    selectorFormLayout = qt.QFormLayout()
    selectorFormLayout.setContentsMargins(0, 0, 0, 0)

    # erosion volume selector
    self.erosionVolumeSelector = slicer.qMRMLNodeComboBox()
    self.erosionVolumeSelector.nodeTypes = ["vtkMRMLLabelMapVolumeNode"]
    self.erosionVolumeSelector.selectNodeUponCreation = False
    self.erosionVolumeSelector.addEnabled = False
    self.erosionVolumeSelector.removeEnabled = False
    self.erosionVolumeSelector.noneEnabled = False
    self.erosionVolumeSelector.showHidden = False
    self.erosionVolumeSelector.showChildNodeTypes = False
    self.erosionVolumeSelector.setMRMLScene( slicer.mrmlScene )
    self.erosionVolumeSelector.setToolTip( "Select the erosions to be corrected" )
    selectorFormLayout.addRow("Input Erosions: ", self.erosionVolumeSelector)

    # master volume selector
    self.masterVolumeSelector = slicer.qMRMLNodeComboBox()
    self.masterVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.masterVolumeSelector.selectNodeUponCreation = False
    self.masterVolumeSelector.addEnabled = False
    self.masterVolumeSelector.removeEnabled = False
    self.masterVolumeSelector.noneEnabled = False
    self.masterVolumeSelector.showHidden = False
    self.masterVolumeSelector.showChildNodeTypes = False
    self.masterVolumeSelector.setMRMLScene( slicer.mrmlScene )
    self.masterVolumeSelector.setToolTip("Select the master volume associated with the erosions")
    selectorFormLayout.addRow("Master Volume: ", self.masterVolumeSelector)

    # contour volume selector
    self.contourVolumeSelector = slicer.qMRMLNodeComboBox()
    self.contourVolumeSelector.nodeTypes = ["vtkMRMLLabelMapVolumeNode"]
    self.contourVolumeSelector.selectNodeUponCreation = False
    self.contourVolumeSelector.addEnabled = False
    self.contourVolumeSelector.removeEnabled = False
    self.contourVolumeSelector.noneEnabled = False
    self.contourVolumeSelector.showHidden = False
    self.contourVolumeSelector.showChildNodeTypes = False
    self.contourVolumeSelector.setMRMLScene( slicer.mrmlScene )
    self.contourVolumeSelector.setToolTip("Select the contour of the master volume")
    selectorFormLayout.addRow("Input Contour: ", self.contourVolumeSelector)

    # frame with selectors
    selectorFrame = qt.QFrame()
    selectorFrame.setLayout(selectorFormLayout)
    manualCorrectionLayout.addWidget(selectorFrame)

    # layout for initialize and apply buttons
    initApplyGridLayout = qt.QGridLayout()
    initApplyGridLayout.setContentsMargins(0, 5, 0, 5)

    # initialize button
    self.initButton = qt.QPushButton("Initialize")
    self.initButton.toolTip = "Initialize the parameters in segmentation editor for manual correction"
    self.initButton.enabled = False
    initApplyGridLayout.addWidget(self.initButton, 0, 0)

    # cancel button
    self.cancelButton = qt.QPushButton("Cancel")
    self.cancelButton.toolTip = "Discard the manual correction"
    self.cancelButton.enabled = False
    initApplyGridLayout.addWidget(self.cancelButton, 0, 1)
    
    # apply button
    self.applyButton = qt.QPushButton("Apply")
    self.applyButton.toolTip = "Apply the manual correction to the erosion image"
    self.applyButton.enabled = False
    initApplyGridLayout.addWidget(self.applyButton, 0, 2)

    # frame with initialize and apply buttons
    initApplyFrame = qt.QFrame()
    initApplyFrame.setLayout(initApplyGridLayout)
    manualCorrectionLayout.addWidget(initApplyFrame)

    # segmentation editor
    self.segmentEditor = SegmentEditor(self.manualCorrectionCollapsibleButton)

    # connections
    self.manualCorrectionCollapsibleButton.connect('contentsCollapsed(bool)', self.onCollapsed5)
    self.initButton.connect('clicked(bool)', self.onInitButton)
    self.applyButton.connect('clicked(bool)', self.onApplyButton)
    self.cancelButton.connect('clicked(bool)', self.onCancelButton)
    self.erosionVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect5)
    self.masterVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect5)
    self.contourVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect5)

  def setupStats(self):
    """Set up widgets in step 6 statistics"""
    # Set text on collapsible button, and add collapsible button to layout
    self.statsCollapsibleButton.text = "Step 6 - Statistics"
    self.statsCollapsibleButton.collapsed = True
    self.layout.addWidget(self.statsCollapsibleButton)

    # Layout within the collapsible button
    statsLayout = qt.QFormLayout(self.statsCollapsibleButton)
    statsLayout.setVerticalSpacing(5)

    # input erosion selector
    self.inputErosionSelector = slicer.qMRMLNodeComboBox()
    self.inputErosionSelector.nodeTypes = ["vtkMRMLLabelMapVolumeNode"]
    self.inputErosionSelector.selectNodeUponCreation = False
    self.inputErosionSelector.addEnabled = False
    self.inputErosionSelector.renameEnabled = True
    self.inputErosionSelector.removeEnabled = True
    self.inputErosionSelector.noneEnabled = False
    self.inputErosionSelector.showHidden = False
    self.inputErosionSelector.showChildNodeTypes = False
    self.inputErosionSelector.setMRMLScene(slicer.mrmlScene)
    self.inputErosionSelector.setToolTip( "Pick the input erosion label map for statistics" )
    statsLayout.addRow("Input Erosions: ", self.inputErosionSelector)

    # output table selector
    self.outputTableSelector = slicer.qMRMLNodeComboBox()
    self.outputTableSelector.nodeTypes = ["vtkMRMLTableNode"]
    self.outputTableSelector.selectNodeUponCreation = True
    self.outputTableSelector.addEnabled = True
    self.outputTableSelector.removeEnabled = True
    self.outputTableSelector.renameEnabled = True
    self.outputTableSelector.noneEnabled = False
    self.outputTableSelector.showHidden = False
    self.outputTableSelector.showChildNodeTypes = False
    self.outputTableSelector.setMRMLScene(slicer.mrmlScene)
    self.outputTableSelector.setToolTip( "Pick the output table to store the erosion statistics" )
    statsLayout.addRow("Output Table: ", self.outputTableSelector)

    # Execution layout
    statsGridLayout = qt.QGridLayout()
    statsGridLayout.setRowMinimumHeight(0,15)
    statsGridLayout.setRowMinimumHeight(1,15)

    # Get Button
    self.getStatsButton = qt.QPushButton("Get Statistics")
    self.getStatsButton.toolTip = "Get erosion statistics in a table"
    self.getStatsButton.enabled = False
    statsGridLayout.addWidget(self.getStatsButton, 1, 0)

    # Execution frame with progress bar and get button
    self.statsButtonFrame = qt.QFrame()
    self.statsButtonFrame.setLayout(statsGridLayout)
    statsLayout.addRow(self.statsButtonFrame)

    # connections
    self.statsCollapsibleButton.connect('contentsCollapsed(bool)', self.onCollapsed6)
    self.getStatsButton.connect('clicked(bool)', self.onGetStatsButton)
    self.inputErosionSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect6)
    self.inputErosionSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelectInputErosion)
    self.outputTableSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect6)

  def onCollapsed4(self):
    """Run this whenever the collapsible button in step 4 is clicked"""
    if not self.erosionsCollapsibleButton.collapsed:
      self.manualCorrectionCollapsibleButton.collapsed = True
      self.statsCollapsibleButton.collapsed = True

  def onCollapsed5(self):
    """Run this whenever the collapsible button in step 5 is clicked"""
    if not self.manualCorrectionCollapsibleButton.collapsed:
      self.erosionsCollapsibleButton.collapsed = True
      self.statsCollapsibleButton.collapsed = True

  def onCollapsed6(self):
    """Run this whenever the collapsible button in step 6 is clicked"""
    if not self.statsCollapsibleButton.collapsed:
      self.erosionsCollapsibleButton.collapsed = True
      self.manualCorrectionCollapsibleButton.collapsed = True

  def enter(self):
    """Run this whenever the module is reopened"""    
    success = self._logic.enterSegmentEditor(self.segmentEditor)

    if not success: # if enter segmentation editor is not successful, some nodes are missing
      self.disableManualCorrectionWidgets()

  def exit(self):
    """Run this whenever the module is closed"""
    self._logic.exitSegmentEditor(self.segmentEditor)

  def onSelect4(self):
    """Update the state of the get erosions button whenever the selectors in step 4 change"""
    self.getErosionsButton.enabled = (self.inputVolumeSelector.currentNode() and 
                                     self.inputContourSelector.currentNode() and
                                     self.outputVolumeSelector.currentNode() and
                                     self.fiducialSelector.currentNode())

  def onSelect5(self):
    """Update the state of the initialize button whenever the selectors in step 5 change"""
    self.initButton.enabled = (self.erosionVolumeSelector.currentNode() and
                               self.masterVolumeSelector.currentNode() and
                               self.contourVolumeSelector.currentNode())
                               
  def onSelect6(self):
    """Update the state of the get statistics button whenever the selectors in step 6 change"""
    self.getStatsButton.enabled = (self.inputErosionSelector.currentNode() and
                                  self.outputTableSelector.currentNode())
  
  def onSelectInputVolume(self):
    """Run this whenever the input volume selector in step 4 changes"""
    inputVolumeNode = self.inputVolumeSelector.currentNode()

    if inputVolumeNode:
      # Update the spacing scale in the seed point table
      ras2ijk = vtk.vtkMatrix4x4()
      ijk2ras = vtk.vtkMatrix4x4()
      inputVolumeNode.GetRASToIJKMatrix(ras2ijk)
      inputVolumeNode.GetIJKToRASMatrix(ijk2ras)
      self.markupsTableWidget.setCoordsMatrices(ras2ijk, ijk2ras)
      # update the default output base name
      self.outputVolumeSelector.baseName = (inputVolumeNode.GetName()+"_ERO")
      # update the viewer window
      slicer.util.setSliceViewerLayers(background=inputVolumeNode)
      slicer.util.resetSliceViews() # centre the volume in the viewer windows
    else:
      self.outputVolumeSelector.baseName = "ERO"

  def onSelectSeed(self):
    """Run this whenever the seed point selector in step 4 changes"""
    self.markupsTableWidget.setCurrentNode(self.fiducialSelector.currentNode())

  def onLargeErosionChecked(self):
    """Run this whenever the check box for large erosions in step 4 changes"""
    if self.erosionCheckBox.checked:
      self.minimalRadiusText.value = 6
      self.dilationErosionRadiusText.value = 6
    else:
      self.minimalRadiusText.value = 3
      self.dilationErosionRadiusText.value = 4

  def onSelectInputErosion(self):
    """Run this whenever the input erosion selector in step 6 changes"""
    inputErosionNode = self.inputErosionSelector.currentNode()

    if inputErosionNode:
      self.outputTableSelector.baseName = (inputErosionNode.GetName()+"_TABLE")
    else:
      self.outputTableSelector.baseName = "_TABLE"

  def onGetErosionsButton(self):
    """Run this whenever the get erosions button in step 4 is clicked"""
    # update widgets
    self.disableErosionsWidgets()

    inputVolumeNode = self.inputVolumeSelector.currentNode()
    inputContourNode = self.inputContourSelector.currentNode()
    outputVolumeNode = self.outputVolumeSelector.currentNode()
    fiducialNode = self.fiducialSelector.currentNode()
    ready = self._logic.setErosionParameters(inputVolumeNode, 
                                            inputContourNode, 
                                            outputVolumeNode,
                                            self.lowerThresholdText.value,
                                            self.upperThresholdText.value,
                                            fiducialNode,
                                            self.minimalRadiusText.value,
                                            self.dilationErosionRadiusText.value)
    if ready:
      success = self._logic.getErosions(inputVolumeNode, outputVolumeNode)
      if success:
        # update widgets
        self.erosionVolumeSelector.setCurrentNodeID(self.outputVolumeSelector.currentNodeID)
        self.masterVolumeSelector.setCurrentNodeID(self.inputVolumeSelector.currentNodeID)
        self.contourVolumeSelector.setCurrentNodeID(self.inputContourSelector.currentNodeID)
        self.outputVolumeSelector.setCurrentNodeID("") # reset the output volume selector

    # update widgets
    self.enableErosionsWidgets()
  
  def onInitButton(self):
    """Run this whenever the initialize button in step 5 is clicked"""
    erosionVolumeNode = self.erosionVolumeSelector.currentNode()
    masterVolumeNode = self.masterVolumeSelector.currentNode()
    contourVolumeNode = self.contourVolumeSelector.currentNode()

    success = self._logic.initManualCorrection(self.segmentEditor, 
                                              erosionVolumeNode,
                                              masterVolumeNode,
                                              contourVolumeNode)

    if success:
      self.enableManualCorrectionWidgets()

  def onCancelButton(self):
    """Run this whenever the cancel button in step 5 is clicked"""
    if slicer.util.confirmOkCancelDisplay('Do you want to discard the manual correction?'):
      erosionVolumeNode = self.erosionVolumeSelector.currentNode()
      masterVolumeNode = self.masterVolumeSelector.currentNode()

      self._logic.cancelManualCorrection(erosionVolumeNode, masterVolumeNode)

      # update widgets
      self.disableManualCorrectionWidgets()

  def onApplyButton(self):
    """Run this whenever the apply button in step 5 is clicked"""
    erosionVolumeNode = self.erosionVolumeSelector.currentNode()
    masterVolumeNode = self.masterVolumeSelector.currentNode()

    self._logic.applyManualCorrection(erosionVolumeNode, masterVolumeNode)

    # update widgets
    if erosionVolumeNode:
      self.inputErosionSelector.setCurrentNodeID(erosionVolumeNode.GetID())
    self.disableManualCorrectionWidgets()
    
  def onGetStatsButton(self):
    """Run this whenever the get statistics button in step 6 is clicked"""
    self._logic.getStatistics(self.inputErosionSelector.currentNode(),
                             self.outputTableSelector.currentNode())

  def enableErosionsWidgets(self):
    """Enable widgets in the erosions layout in step 4"""
    self.onSelect4()
    self.progressBar.hide()

  def disableErosionsWidgets(self):
    """Disable widgets in the erosions layout in step 4"""
    self.getErosionsButton.enabled = False
    self.progressBar.show()
  
  def enableManualCorrectionWidgets(self):
    """Enable widgets in the manual correction layout in step 5"""
    self.applyButton.enabled = True
    self.cancelButton.enabled = True
    self.masterVolumeSelector.enabled = False
    self.contourVolumeSelector.enabled = False

  def disableManualCorrectionWidgets(self):
    """Disable widgets in the manual correction layout in step 5"""
    self.applyButton.enabled = False
    self.cancelButton.enabled = False
    self.contourVolumeSelector.enabled = True
    self.masterVolumeSelector.enabled = True

  def setProgress(self, value):
    """Update the progress bar"""
    self.progressBar.setValue(value)
