#-----------------------------------------------------
# CorticalBreak.py
#
# Created by:  Mingjie Zhao
# Created on:  23-07-2021
#
# Description: This module sets up the interface for the Cortical Break 3D Slicer extension.
#
#-----------------------------------------------------
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
from CorticalBreakLib.CorticalBreakLogic import CorticalBreakLogic
from CorticalBreakLib.MarkupsTable import MarkupsTable

#
# CorticalBreak
#
class CorticalBreak(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Cortical Break"
    self.parent.categories = ["Bone"]
    self.parent.dependencies = []  # TODO: add here list of module names that this module requires
    self.parent.contributors = ["Mingjie Zhao"]
    # TODO: update with short description of the module and a link to online module documentation
    self.parent.helpText = """
Updated on August 22, 2021.
This module inplements the automatic cortical break detection method by Michel Peters et al. Workflow:
1. Preprocess/binarize the bone. 2. Take the preprocessed image and the mask, identify cortical breaks 
and underlying trabecular bone loss using Peters et al's algorithm. The cortical break masks will be 
converted to seed points. Note that trabecular bone loss on CBCT will be segmented using a different 
algorithm (i.e. level set) from the original algorithm. 3. Manually add or remove seed points.
"""
    # TODO: replace with organization, grant and thanks
    self.parent.acknowledgementText = """
Updated on August 22, 2021.
""" # Additional initialization step after application startup is complete

#
# CorticalBreakWidget
#

class CorticalBreakWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent=None):
    """
    Called when the user opens the module the first time and the widget is initialized.
    """
    # Initialize logics object
    self._logic = CorticalBreakLogic()
    # initialize call back object for updating progrss bar
    self._logic.progressCallBack = self.setProgress2

    ScriptedLoadableModuleWidget.__init__(self, parent)

  def setup(self):
    """
    Called when the user opens the module the first time and the widget is initialized.
    """
    # Collapsible button
    self.corticalBreakCollapsibleButton = ctk.ctkCollapsibleButton()
    self.seedPointsCollapsibleButton = ctk.ctkCollapsibleButton()

    # Set up widgets inside the collapsible buttons
    self.setupCorticalBreak()
    self.setupSeedPoints()

    # Add vertical spacer
    self.layout.addStretch(1)

    # Update buttons
    self.onSelect1()
    self.onSelectInputVolume()
    self.onSelect2()
    self.onSelectMask()

  def setupCorticalBreak(self):
    """Set up widgets for automatic cortical break detection"""
    # Set text on collapsible button, and add collapsible button to layout
    self.corticalBreakCollapsibleButton.text = "Cortical Break"
    self.layout.addWidget(self.corticalBreakCollapsibleButton)
    
    # Layout within the collapsible button
    corticalBreakLayout = qt.QFormLayout(self.corticalBreakCollapsibleButton)
    corticalBreakLayout.setVerticalSpacing(5)

    # Input volume selector
    self.inputVolumeSelector = slicer.qMRMLNodeComboBox()
    self.inputVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.inputVolumeSelector.selectNodeUponCreation = False
    self.inputVolumeSelector.addEnabled = False
    self.inputVolumeSelector.removeEnabled = True
    self.inputVolumeSelector.renameEnabled = True
    self.inputVolumeSelector.noneEnabled = False
    self.inputVolumeSelector.showHidden = False
    self.inputVolumeSelector.showChildNodeTypes = False
    self.inputVolumeSelector.setMRMLScene(slicer.mrmlScene)
    self.inputVolumeSelector.setToolTip( "Select the greyscale image" )
    corticalBreakLayout.addRow("Input Volume: ", self.inputVolumeSelector)

    # Preprocessed output selector
    self.outputVolumeSelector = slicer.qMRMLNodeComboBox()
    self.outputVolumeSelector.nodeTypes = ["vtkMRMLLabelMapVolumeNode"]
    self.outputVolumeSelector.selectNodeUponCreation = True
    self.outputVolumeSelector.addEnabled = True
    self.outputVolumeSelector.renameEnabled = True
    self.outputVolumeSelector.removeEnabled = True
    self.outputVolumeSelector.noneEnabled = False
    self.outputVolumeSelector.showHidden = False
    self.outputVolumeSelector.showChildNodeTypes = False
    self.outputVolumeSelector.setMRMLScene(slicer.mrmlScene)
    self.outputVolumeSelector.setToolTip( "Select the node to store the preprocessed image in" )
    corticalBreakLayout.addRow("Output Volume: ", self.outputVolumeSelector)

    # threshold spin boxes
    self.lowerThresholdText = qt.QSpinBox()
    self.lowerThresholdText.setMinimum(-9999)
    self.lowerThresholdText.setMaximum(999999)
    self.lowerThresholdText.setSingleStep(10)
    self.lowerThresholdText.value = 3000
    corticalBreakLayout.addRow("Lower Threshold: ", self.lowerThresholdText)
    self.upperThresholdText = qt.QSpinBox()
    self.upperThresholdText.setMinimum(-9999)
    self.upperThresholdText.setMaximum(999999)
    self.upperThresholdText.setSingleStep(10)
    self.upperThresholdText.value = 10000
    corticalBreakLayout.addRow("Upper Threshold: ", self.upperThresholdText)

    # gaussian sigma spin box
    self.sigmaText = qt.QDoubleSpinBox()
    self.sigmaText.setMinimum(0.0001)
    self.sigmaText.setDecimals(4)
    self.sigmaText.value = 0.8
    self.sigmaText.setToolTip("Standard deviation in the Gaussian smoothing filter")
    corticalBreakLayout.addRow("Gaussian Sigma: ", self.sigmaText)

    # Execution layout
    executeGridLayout1 = qt.QGridLayout()
    executeGridLayout1.setRowMinimumHeight(0,15)
    executeGridLayout1.setRowMinimumHeight(1,15)

    # Progress Bar
    self.progressBar1 = qt.QProgressBar()
    self.progressBar1.maximum = 0
    self.progressBar1.minimum = 0
    self.progressBar1.hide()
    executeGridLayout1.addWidget(self.progressBar1, 0, 0)

    # Preprocess Button
    self.preprocessButton = qt.QPushButton("Preprocess")
    self.preprocessButton.toolTip = "Apply threshold and smoothing"
    self.preprocessButton.enabled = False
    executeGridLayout1.addWidget(self.preprocessButton, 1, 0)
    executeGridLayout1.addWidget(qt.QLabel(""), 2, 0)

    # Execution frame with progress bar and get button
    erosionButtonFrame = qt.QFrame()
    erosionButtonFrame.setLayout(executeGridLayout1)
    corticalBreakLayout.addRow(erosionButtonFrame)

    # master volume Selector
    self.masterVolumeSelector = slicer.qMRMLNodeComboBox()
    self.masterVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.masterVolumeSelector.selectNodeUponCreation = False
    self.masterVolumeSelector.addEnabled = False
    self.masterVolumeSelector.removeEnabled = True
    self.masterVolumeSelector.renameEnabled = True
    self.masterVolumeSelector.noneEnabled = True
    self.masterVolumeSelector.showHidden = False
    self.masterVolumeSelector.showChildNodeTypes = False
    self.masterVolumeSelector.setMRMLScene(slicer.mrmlScene)
    self.masterVolumeSelector.setToolTip( "Select the greyscale image" )
    corticalBreakLayout.addRow("Input Volume: ", self.masterVolumeSelector)

    # Input bone selector
    self.inputBoneSelector = slicer.qMRMLNodeComboBox()
    self.inputBoneSelector.nodeTypes = ["vtkMRMLScalarVolumeNode","vtkMRMLLabelMapVolumeNode"]
    self.inputBoneSelector.selectNodeUponCreation = False
    self.inputBoneSelector.addEnabled = False
    self.inputBoneSelector.removeEnabled = True
    self.inputBoneSelector.renameEnabled = True
    self.inputBoneSelector.noneEnabled = False
    self.inputBoneSelector.showHidden = False
    self.inputBoneSelector.showChildNodeTypes = False
    self.inputBoneSelector.setMRMLScene(slicer.mrmlScene)
    self.inputBoneSelector.baseName = "ER"
    self.inputBoneSelector.setToolTip( "Select the preprocessed image" )
    corticalBreakLayout.addRow("Preprocessed Volume: ", self.inputBoneSelector)

    # bone mask
    self.maskSelector = slicer.qMRMLNodeComboBox()
    self.maskSelector.nodeTypes = ["vtkMRMLScalarVolumeNode","vtkMRMLLabelMapVolumeNode"]
    self.maskSelector.selectNodeUponCreation = False
    self.maskSelector.addEnabled = False
    self.maskSelector.renameEnabled = True
    self.maskSelector.removeEnabled = True
    self.maskSelector.noneEnabled = False
    self.maskSelector.showHidden = False
    self.maskSelector.showChildNodeTypes = False
    self.maskSelector.setMRMLScene(slicer.mrmlScene)
    self.maskSelector.setToolTip( "Select the mask label map" )
    corticalBreakLayout.addRow("Contour: ", self.maskSelector)

    # output cortical breaks selector
    self.outputCorticalBreaksSelector = slicer.qMRMLNodeComboBox()
    self.outputCorticalBreaksSelector.nodeTypes = ["vtkMRMLLabelMapVolumeNode"]
    self.outputCorticalBreaksSelector.selectNodeUponCreation = True
    self.outputCorticalBreaksSelector.addEnabled = True
    self.outputCorticalBreaksSelector.renameEnabled = True
    self.outputCorticalBreaksSelector.removeEnabled = True
    self.outputCorticalBreaksSelector.noneEnabled = False
    self.outputCorticalBreaksSelector.showHidden = False
    self.outputCorticalBreaksSelector.showChildNodeTypes = False
    self.outputCorticalBreaksSelector.setMRMLScene(slicer.mrmlScene)
    self.outputCorticalBreaksSelector.setToolTip( "Select the node to store the cortical breaks in" )
    corticalBreakLayout.addRow("Output Cortical Breaks: ", self.outputCorticalBreaksSelector)

    # output seed point selector
    self.outputFiducialSelector = slicer.qMRMLNodeComboBox()
    self.outputFiducialSelector.nodeTypes = ["vtkMRMLMarkupsFiducialNode"]
    self.outputFiducialSelector.selectNodeUponCreation = True
    self.outputFiducialSelector.addEnabled = True
    self.outputFiducialSelector.removeEnabled = True
    self.outputFiducialSelector.renameEnabled = True
    self.outputFiducialSelector.noneEnabled = False
    self.outputFiducialSelector.showHidden = False
    self.outputFiducialSelector.showChildNodeTypes = False
    self.outputFiducialSelector.setMRMLScene(slicer.mrmlScene)
    self.outputFiducialSelector.baseName = "SEEDS"
    self.outputFiducialSelector.setToolTip( "Select the node to store the output seed points" )
    corticalBreakLayout.addRow("Output Seed Points: ", self.outputFiducialSelector)

    # cortical thickness spin box
    self.corticalThicknessText = qt.QSpinBox()
    self.corticalThicknessText.setMinimum(1)
    self.corticalThicknessText.setMaximum(99)
    self.corticalThicknessText.setSingleStep(1)
    self.corticalThicknessText.setSuffix(' voxels')
    self.corticalThicknessText.value = 4
    corticalBreakLayout.addRow("Cortical Thickness: ", self.corticalThicknessText)

    # dilate erode distance spin box
    self.dilateErodeDistanceText = qt.QSpinBox()
    self.dilateErodeDistanceText.setMinimum(0)
    self.dilateErodeDistanceText.setMaximum(99)
    self.dilateErodeDistanceText.setSingleStep(1)
    self.dilateErodeDistanceText.setSuffix(' voxels')
    self.dilateErodeDistanceText.value = 1
    corticalBreakLayout.addRow("Dilate/Erode Distance: ", self.dilateErodeDistanceText)

    # voxel size spin box
    self.voxelSizeText = qt.QDoubleSpinBox()
    self.voxelSizeText.setMinimum(0)
    self.voxelSizeText.setSuffix('mm')
    self.voxelSizeText.setDecimals(4)
    self.voxelSizeText.value = 0.082
    self.voxelSizeText.setToolTip("Voxel size of the greyscale scan in millimetres")
    corticalBreakLayout.addRow("Voxel Size: ", self.voxelSizeText)

    # ct type button layout
    ctTypeLayout = qt.QGridLayout()

    # ct type buttons
    self.xtremeCTIButton = qt.QRadioButton("XtremeCT I")
    self.xtremeCTIButton.setChecked(True)
    self.xtremeCTIIButton = qt.QRadioButton("XtremeCT II")
    self.xtremeCTIIButton.setChecked(False)
    self.cbCTButton = qt.QRadioButton("CBCT")
    self.cbCTButton.setChecked(False)
    ctTypeLayout.addWidget(self.xtremeCTIButton, 0, 0)
    ctTypeLayout.addWidget(self.xtremeCTIIButton, 0, 1)
    ctTypeLayout.addWidget(self.cbCTButton, 0, 2)

    # ct type button frame
    ctTypeFrame = qt.QFrame()
    ctTypeFrame.setLayout(ctTypeLayout)
    corticalBreakLayout.addRow(ctTypeFrame)

    # Execution layout
    executeGridLayout2 = qt.QGridLayout()
    executeGridLayout2.setRowMinimumHeight(0,15)
    executeGridLayout2.setRowMinimumHeight(1,15)
    
    # Progress Bar
    self.progressBar2 = qt.QProgressBar()
    self.progressBar2.hide()
    executeGridLayout2.addWidget(self.progressBar2, 0, 0)

    # Preprocess Button
    self.getCorticalBreaksButton = qt.QPushButton("Get Cortical Breaks")
    self.getCorticalBreaksButton.toolTip = "Apply the automatic cortical break algorithm"
    self.getCorticalBreaksButton.enabled = False
    executeGridLayout2.addWidget(self.getCorticalBreaksButton, 1, 0)

    # Execution frame with progress bar and preprocess button
    erosionButtonFrame2 = qt.QFrame()
    erosionButtonFrame2.setLayout(executeGridLayout2)
    corticalBreakLayout.addRow(erosionButtonFrame2)

    # conmections
    self.corticalBreakCollapsibleButton.connect("contentsCollapsed(bool)", self.onCollapsed1)
    self.inputVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect1)
    self.inputVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelectInputVolume)
    self.outputVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect1)
    self.masterVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect2)
    self.inputBoneSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect2)
    self.maskSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect2)
    self.maskSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelectMask)
    self.outputCorticalBreaksSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect2)
    self.xtremeCTIButton.connect("toggled(bool)", self.onCTTypeChanged)
    self.xtremeCTIIButton.connect("toggled(bool)", self.onCTTypeChanged)
    self.cbCTButton.connect("toggled(bool)", self.onCTTypeChanged)
    self.preprocessButton.connect("clicked(bool)", self.onPreprocessButton)
    self.getCorticalBreaksButton.connect("clicked(bool)", self.onGetCorticalBreaksButton)    

  def setupSeedPoints(self):
    """Set up widgets for seed points"""
    # Set text on collapsible button, and add collapsible button to layout
    self.seedPointsCollapsibleButton.text = "Seed Points"
    self.seedPointsCollapsibleButton.collapsed = True
    self.layout.addWidget(self.seedPointsCollapsibleButton)

    # Layout within the collapsible button
    seedPointsLayout = qt.QFormLayout(self.seedPointsCollapsibleButton)

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
    self.fiducialSelector.baseName = "SEEDS"
    self.fiducialSelector.setToolTip( "Select the seed points" )
    seedPointsLayout.addRow("Seed Points: ", self.fiducialSelector)

    # seed point table
    self.markupsTableWidget = MarkupsTable(self.seedPointsCollapsibleButton)
    self.markupsTableWidget.setMRMLScene(slicer.mrmlScene)
    self.markupsTableWidget.setNodeSelectorVisible(False) # use the above selector instead
    self.markupsTableWidget.setButtonsVisible(False)
    self.markupsTableWidget.setPlaceButtonVisible(True)
    self.markupsTableWidget.setDeleteAllButtonVisible(True)
    self.markupsTableWidget.setJumpToSliceEnabled(True)

    # connection
    self.seedPointsCollapsibleButton.connect("contentsCollapsed(bool)", self.onCollapsed2)
    self.fiducialSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelectSeed)

  def enter(self):
    """
    Called each time the user opens this module.
    """

  def exit(self):
    """
    Called each time the user opens a different module.
    """

  def onCollapsed1(self):
    """Run this whenever the cortical break collapsible button is clicked"""
    if not self.corticalBreakCollapsibleButton.collapsed:
      self.seedPointsCollapsibleButton.collapsed = True

  def onCollapsed2(self):
    """Run this whenever the seed points collapsible button is clicked"""
    if not self.seedPointsCollapsibleButton.collapsed:
      self.corticalBreakCollapsibleButton.collapsed = True

  def onSelect1(self):
    """Run this whenever the selectors in the preprocess step changes state."""
    self.preprocessButton.enabled = (self.inputVolumeSelector.currentNode() and
                                     self.outputVolumeSelector.currentNode())
  
  def onSelect2(self):
    """Run this whenever the selectors in the cortical break detection step changes state."""
    self.getCorticalBreaksButton.enabled = (self.masterVolumeSelector.currentNode() and
                                            self.inputBoneSelector.currentNode() and
                                            self.outputCorticalBreaksSelector.currentNode())

  def onSelectSeed(self):
    """Run this whenever the seed point selected in the seed point step changes state."""
    self.markupsTableWidget.setCurrentNode(self.fiducialSelector.currentNode())

  def onSelectInputVolume(self):
    """Run this whenever an input volume is selected."""
    inputVolumeNode = self.inputVolumeSelector.currentNode()

    if inputVolumeNode:
      self.masterVolumeSelector.setCurrentNodeID(inputVolumeNode.GetID())
      self.outputVolumeSelector.baseName = (inputVolumeNode.GetName()+"_SEG")
      # Update the default save directory
      self._logic.setDefaultDirectory(inputVolumeNode)
      # Update the spacing scale in the seed point table
      ras2ijk = vtk.vtkMatrix4x4()
      ijk2ras = vtk.vtkMatrix4x4()
      inputVolumeNode.GetRASToIJKMatrix(ras2ijk)
      inputVolumeNode.GetIJKToRASMatrix(ijk2ras)
      self.markupsTableWidget.setCoordsMatrices(ras2ijk, ijk2ras)

  def onSelectMask(self):
    """Run this whenever a periosteal contour/mask is selected."""
    maskNode = self.maskSelector.currentNode()

    if maskNode:
      self.outputCorticalBreaksSelector.baseName = (maskNode.GetName()+"_BREAKS")
      self.outputFiducialSelector.baseName = (maskNode.GetName()+"_SEEDS")

  def onCTTypeChanged(self):
    """Run this whenver the ct type buttons change state."""
    if self.xtremeCTIButton.checked:
      self.corticalThicknessText.value = 4
      self.dilateErodeDistanceText.value = 1
      self.voxelSizeText.value = 0.082
    elif self.xtremeCTIIButton.checked:
      self.corticalThicknessText.value = 5
      self.dilateErodeDistanceText.value = 2
      self.voxelSizeText.value = 0.0607
    elif self.cbCTButton.checked:
      self.corticalThicknessText.value = 1
      self.dilateErodeDistanceText.value = 0
      self.voxelSizeText.value = 0.25


  def onPreprocessButton(self):
    """Run this whenever the get cortical breaks button is clicked."""
    # update widgets
    self.disablePreprocessWidgets()

    inputVolumeNode = self.inputVolumeSelector.currentNode()
    outputVolumeNode = self.outputVolumeSelector.currentNode()
    ready = self._logic.setPreprocessParameters(inputVolumeNode, 
                                                self.lowerThresholdText.value,
                                                self.upperThresholdText.value,
                                                self.sigmaText.value)

    if ready:
      success = self._logic.preprocess(outputVolumeNode)
      if success:
        self.inputBoneSelector.setCurrentNode(self.outputVolumeSelector.currentNode())
        # update viewer windows
        slicer.util.setSliceViewerLayers(background=inputVolumeNode, 
                                         label=outputVolumeNode, 
                                         labelOpacity=0.5)
    # update widgets
    self.outputVolumeSelector.setCurrentNodeID("") # reset the output volume selector
    self.enablePreprocessWidgets()

  def onGetCorticalBreaksButton(self):
    """Run this whenever the preproecess button is clicked."""
    # update widgets
    self.disableCorticalBreaksWidgets()

    masterVolumeNode = self.masterVolumeSelector.currentNode()
    inputBoneNode = self.inputBoneSelector.currentNode()
    outputCorticalBreaksNode = self.outputCorticalBreaksSelector.currentNode()
    outputFiducialNode = self.outputFiducialSelector.currentNode()
    maskNode = self.maskSelector.currentNode()
    cbCT = self.cbCTButton.isChecked()
    
    ready = self._logic.setCorticalBreaksParameters(self.lowerThresholdText.value,
                                                    self.upperThresholdText.value,
                                                    masterVolumeNode,
                                                    inputBoneNode,
                                                    maskNode,
                                                    outputCorticalBreaksNode,
                                                    self.corticalThicknessText.value,
                                                    self.dilateErodeDistanceText.value,
                                                    self.voxelSizeText.value,
                                                    cbCT)
    if ready:
      success = self._logic.getCorticalBreaks(outputCorticalBreaksNode)
      if success:
        self._logic.getSeeds(inputBoneNode, outputFiducialNode)
        # update viewer windows
        slicer.util.setSliceViewerLayers(label=outputCorticalBreaksNode, 
                                         labelOpacity=0.5)
                                         
    # update widgets
    self.outputCorticalBreaksSelector.setCurrentNodeID("") # reset the output volume selector
    self.enableCorticalBreaksWidgets()

  def setProgress2(self, value):
    """Update the progress bar."""
    self.progressBar2.setValue(value)

  def enablePreprocessWidgets(self):
    """Enable widgets for preprocessing."""
    self.progressBar1.hide()

  def disablePreprocessWidgets(self):
    """Disable widgets for preprocessing."""
    self.preprocessButton.enabled = False
    self.progressBar1.show()

  def enableCorticalBreaksWidgets(self):
    """Enable widgets for cortical breaks detection."""
    self.progressBar2.hide()

  def disableCorticalBreaksWidgets(self):
    """Disable widgets for cortical breaks detection."""
    self.getCorticalBreaksButton.enabled = False
    self.progressBar2.show()