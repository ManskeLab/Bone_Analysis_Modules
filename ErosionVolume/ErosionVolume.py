#-----------------------------------------------------
# ErosionVolume.py
#
# Created by:  Mingjie Zhao
# Created on:  23-10-2020
#
# Description: This module sets up the interface for the Erosion Volume 3D Slicer extension.
#
#-----------------------------------------------------
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
from ErosionVolumeLib.ErosionVolumeLogic import ErosionVolumeLogic
from ErosionVolumeLib.SegmentEditor import SegmentEditor
from ErosionVolumeLib.SegmentCopier import SegmentCopier
from ErosionVolumeLib.MarkupsTable import MarkupsTable

#
# ErosionVolume
#
class ErosionVolume(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Erosion Volume" # TODO make this more human readable by adding spaces
    self.parent.categories = ["Bone"]
    self.parent.dependencies = []
    self.parent.contributors = ["Mingjie Zhao"] # replace with "Firstname Lastname (Organization)"
    self.parent.helpText = """
Updated on August 22, 2021. 
This module contains steps 4-6 of erosion analysis. It requires a greyscale scan and a mask.
Erosions are identified by placing seed points in each of them. 
Step 4 is to segment erosions given a seed point in each erosion. 
Step 5 is to manually correct the erosion segmentations and combine them into a single segmentation. 
Step 6 is to compute erosion statistics, such as volume, surface area, and roundness.
"""
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = """
Updated on August 22, 2021.
""" # replace with organization, grant and thanks.

#
# ErosionVolumeWidget
#
class ErosionVolumeWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """
  def __init__(self, parent):
    # Initialize logics object
    self._logic = ErosionVolumeLogic()
    # initialize call back object for updating progrss bar
    self._logic.progressCallBack = self.setProgress

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
    self.inputVolumeSelector.setToolTip( "Pick the greyscale scan" )
    erosionsLayout.addRow("Input Volume: ", self.inputVolumeSelector)

    # input contour selector
    self.inputContourSelector = slicer.qMRMLNodeComboBox()
    self.inputContourSelector.nodeTypes = ["vtkMRMLScalarVolumeNode","vtkMRMLLabelMapVolumeNode"]
    self.inputContourSelector.selectNodeUponCreation = False
    self.inputContourSelector.addEnabled = False
    self.inputContourSelector.renameEnabled = True
    self.inputContourSelector.removeEnabled = True
    self.inputContourSelector.noneEnabled = False
    self.inputContourSelector.showHidden = False
    self.inputContourSelector.showChildNodeTypes = False
    self.inputContourSelector.setMRMLScene(slicer.mrmlScene)
    self.inputContourSelector.setToolTip( "Pick the mask label map" )
    erosionsLayout.addRow("Input Contour: ", self.inputContourSelector)

    # output volume selector
    self.outputErosionSelector = slicer.qMRMLNodeComboBox()
    self.outputErosionSelector.nodeTypes = ["vtkMRMLSegmentationNode"]
    self.outputErosionSelector.selectNodeUponCreation = True
    self.outputErosionSelector.addEnabled = True
    self.outputErosionSelector.removeEnabled = True
    self.outputErosionSelector.renameEnabled = True
    self.outputErosionSelector.noneEnabled = False
    self.outputErosionSelector.showHidden = False
    self.outputErosionSelector.showChildNodeTypes = False
    self.outputErosionSelector.setMRMLScene(slicer.mrmlScene)
    self.outputErosionSelector.baseName = "ER"
    self.outputErosionSelector.setToolTip( "Pick the output segmentation to store the erosions in" )
    erosionsLayout.addRow("Output Erosions: ", self.outputErosionSelector)

    # threshold spin boxes
    self.lowerThresholdText = qt.QSpinBox()
    self.lowerThresholdText.setMinimum(-9999)
    self.lowerThresholdText.setMaximum(999999)
    self.lowerThresholdText.setSingleStep(10)
    self.lowerThresholdText.value = 686
    erosionsLayout.addRow("Lower Threshold: ", self.lowerThresholdText)
    self.upperThresholdText = qt.QSpinBox()
    self.upperThresholdText.setMinimum(-9999)
    self.upperThresholdText.setMaximum(999999)
    self.upperThresholdText.setSingleStep(10)
    self.upperThresholdText.value = 15000
    erosionsLayout.addRow("Upper Threshold: ", self.upperThresholdText)

    # gaussian sigma spin box
    self.sigmaText = qt.QDoubleSpinBox()
    self.sigmaText.setMinimum(0.0001)
    self.sigmaText.setDecimals(4)
    self.sigmaText.value = 1
    self.sigmaText.setToolTip("Standard deviation in the Gaussian smoothing filter")
    erosionsLayout.addRow("Gaussian Sigma: ", self.sigmaText)

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

    # advanced parameter instructions
    advancedParameterLayout.addWidget(qt.QLabel(
      "Larger values for less leakage into the trabecular structure;"
      ), 0, 0, 1, 2)
    advancedParameterLayout.addWidget(qt.QLabel(
      "smaller values for more cortical breaks to be labeled."
      ), 1, 0, 1, 2)
    advancedParameterLayout.addWidget(qt.QLabel(""), 2, 0) # horizontal white space

    # advanced parameter spin boxes
    self.minimalRadiusText = qt.QSpinBox()
    self.minimalRadiusText.setMinimum(1)
    self.minimalRadiusText.setMaximum(99)
    self.minimalRadiusText.setSingleStep(1)
    self.minimalRadiusText.setSuffix(' voxels')
    self.minimalRadiusText.value = 3
    advancedParameterLayout.addWidget(qt.QLabel("Minimum Erosion Radius: "), 3, 0)
    advancedParameterLayout.addWidget(self.minimalRadiusText, 3, 1)
    self.dilateErodeDistanceText = qt.QSpinBox()
    self.dilateErodeDistanceText.setMinimum(1)
    self.dilateErodeDistanceText.setMaximum(99)
    self.dilateErodeDistanceText.setSingleStep(1)
    self.dilateErodeDistanceText.setSuffix(' voxels')
    self.dilateErodeDistanceText.value = 4
    advancedParameterLayout.addWidget(qt.QLabel("Dilate/Erode Distance: "), 4, 0)
    advancedParameterLayout.addWidget(self.dilateErodeDistanceText, 4, 1)

    # Execution layout
    executeGridLayout = qt.QGridLayout()
    executeGridLayout.setRowMinimumHeight(0,15)
    executeGridLayout.setRowMinimumHeight(1,15)

    # Progress Bar
    self.progressBar = qt.QProgressBar()
    self.progressBar.hide()
    executeGridLayout.addWidget(self.progressBar, 0, 0)

    # Get Erosion Button
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
    self.inputVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect4)
    self.inputVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelectInputVolume)
    self.inputContourSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelectInputContour)
    self.inputContourSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect4)
    self.outputErosionSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect4)
    self.outputErosionSelector.connect("nodeAddedByUser(vtkMRMLNode*)", lambda node: self.onAddOutputErosion(node))
    self.fiducialSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect4)
    self.fiducialSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelectSeed)
    self.erosionCheckBox.connect("clicked(bool)", self.onLargeErosionChecked)
    self.getErosionsButton.connect("clicked(bool)", self.onGetErosionsButton)
  
  def setupManualCorrection(self):
    """Set up widgets in step 5 manual correction"""
    # set text on collapsible button, and add collapsible button to layout
    self.manualCorrectionCollapsibleButton.text = "Step 5 - Manual Correction"
    self.manualCorrectionCollapsibleButton.collapsed = True
    self.layout.addWidget(self.manualCorrectionCollapsibleButton)

    # layout within the collapsible button
    manualCorrectionLayout = qt.QVBoxLayout(self.manualCorrectionCollapsibleButton)

    # instructions collapsible button
    instructionsCollapsibleButton = ctk.ctkCollapsibleButton()
    instructionsCollapsibleButton.collapsed = True
    instructionsCollapsibleButton.text = "Instructions"
    manualCorrectionLayout.addWidget(instructionsCollapsibleButton)

    # layout within the instructions collapsible button
    instructionsCollapsibleLayout = qt.QVBoxLayout(instructionsCollapsibleButton)

    # manual correction instructions
    label1 = qt.QLabel("1. Manually correct each erosion segmentation separately. Remove any bad segments and rerun step 4 as needed.")
    label1.setWordWrap(True)
    label2 = qt.QLabel("2. Create a new segmentation and copy all the good erosion segments to the new segmentation using 'Copy Segmentation'.")
    label2.setWordWrap(True)
    label3 = qt.QLabel("3. Convert the segmentation to a label map using 'Export Segmentation'. 'Segmentation' in Slicer can only be stored as an NRRD or Nifti, whereas 'labelmap' can be stored in more file formats.")
    label3.setWordWrap(True)
    instructionsCollapsibleLayout.addWidget(label1)
    instructionsCollapsibleLayout.addWidget(label2)
    instructionsCollapsibleLayout.addWidget(label3)
    instructionsCollapsibleLayout.addWidget(qt.QLabel(""))

    # import segmentation collapsible button
    copySegmentationCollapsibleButton = ctk.ctkCollapsibleButton()
    copySegmentationCollapsibleButton.collapsed = True
    copySegmentationCollapsibleButton.text = "Copy Segmentation"
    manualCorrectionLayout.addWidget(copySegmentationCollapsibleButton)

    # layout within the import segmentation collapsible button
    importSegmentationCollapsibleLayout = qt.QGridLayout(copySegmentationCollapsibleButton)

    # segmentation copier
    self.segmentCopier = SegmentCopier(copySegmentationCollapsibleButton)

    # export label map collapsible button
    exportLabelMapCollapsibleButton = ctk.ctkCollapsibleButton()
    exportLabelMapCollapsibleButton.collapsed = True
    exportLabelMapCollapsibleButton.text = "Export Segmentation"
    manualCorrectionLayout.addWidget(exportLabelMapCollapsibleButton)

    # layout within the export label map collapsible button
    exportLabelMapCollapsibleLayout = qt.QFormLayout(exportLabelMapCollapsibleButton)

    # segmentation exporter
    self.exportRadioButton = qt.QRadioButton("Segmentation to Labelmap")
    self.exportRadioButton.setChecked(True)
    self.importRadioButton = qt.QRadioButton("Labelmap to Segmentation")
    self.importRadioButton.setChecked(False)
    exportLabelMapCollapsibleLayout.addRow(self.exportRadioButton, self.importRadioButton)

    self.segmentationSelector = slicer.qMRMLNodeComboBox()
    self.segmentationSelector.nodeTypes = ["vtkMRMLSegmentationNode"]
    self.segmentationSelector.selectNodeUponCreation = True
    self.segmentationSelector.addEnabled = True
    self.segmentationSelector.renameEnabled = True
    self.segmentationSelector.removeEnabled = True
    self.segmentationSelector.noneEnabled = True
    self.segmentationSelector.showHidden = False
    self.segmentationSelector.showChildNodeTypes = False
    self.segmentationSelector.setMRMLScene(slicer.mrmlScene)
    self.segmentationSelector.setToolTip( "Pick the segmentation to import from/to" )
    exportLabelMapCollapsibleLayout.addRow("Segmentation: ", self.segmentationSelector)

    self.labelMapSelector = slicer.qMRMLNodeComboBox()
    self.labelMapSelector.nodeTypes = ["vtkMRMLLabelMapVolumeNode"]
    self.labelMapSelector.selectNodeUponCreation = True
    self.labelMapSelector.addEnabled = True
    self.labelMapSelector.renameEnabled = True
    self.labelMapSelector.removeEnabled = True
    self.labelMapSelector.noneEnabled = True
    self.labelMapSelector.showHidden = False
    self.labelMapSelector.showChildNodeTypes = False
    self.labelMapSelector.setMRMLScene(slicer.mrmlScene)
    self.labelMapSelector.setToolTip( "Pick the label map to import from/to" )
    exportLabelMapCollapsibleLayout.addRow("Labelmap: ", self.labelMapSelector)

    # import/export button layout
    importExportButtonLayout = qt.QVBoxLayout()

    # import/export button
    self.importExportButton = qt.QPushButton("Import/Export")
    self.importExportButton.toolTip = "Convert between segmentation and label map"
    self.importExportButton.enabled = False
    importExportButtonLayout.addWidget(self.importExportButton)
    importExportButtonLayout.addWidget(qt.QLabel(""))

    # import/export button frame
    importExportButtonFrame = qt.QFrame()
    importExportButtonFrame.setLayout(importExportButtonLayout)
    exportLabelMapCollapsibleLayout.addRow(importExportButtonFrame)

    # segmentation editor
    self.segmentEditor = SegmentEditor(self.manualCorrectionCollapsibleButton)

    # connections
    self.manualCorrectionCollapsibleButton.connect('contentsCollapsed(bool)', self.onCollapsed5)
    self.segmentationSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect5)
    self.labelMapSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect5)
    self.importExportButton.connect("clicked(bool)", self.onImportExportButton)

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
    self.inputErosionSelector.nodeTypes = ["vtkMRMLSegmentationNode"]
    self.inputErosionSelector.selectNodeUponCreation = False
    self.inputErosionSelector.addEnabled = False
    self.inputErosionSelector.renameEnabled = True
    self.inputErosionSelector.removeEnabled = True
    self.inputErosionSelector.noneEnabled = False
    self.inputErosionSelector.showHidden = False
    self.inputErosionSelector.showChildNodeTypes = False
    self.inputErosionSelector.setMRMLScene(slicer.mrmlScene)
    self.inputErosionSelector.setToolTip("Pick the final erosion segmentation that contains all the erosions")
    statsLayout.addRow("Input Erosions: ", self.inputErosionSelector)

    self.masterVolumeSelector = slicer.qMRMLNodeComboBox()
    self.masterVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.masterVolumeSelector.selectNodeUponCreation = False
    self.masterVolumeSelector.addEnabled = False
    self.masterVolumeSelector.renameEnabled = True
    self.masterVolumeSelector.removeEnabled = False
    self.masterVolumeSelector.noneEnabled = False
    self.masterVolumeSelector.showHidden = False
    self.masterVolumeSelector.showChildNodeTypes = False
    self.masterVolumeSelector.setMRMLScene(slicer.mrmlScene)
    self.masterVolumeSelector.setToolTip("Pick the greyscale scan")
    statsLayout.addRow("Master Volume: ", self.masterVolumeSelector)

    # voxel size spin box
    self.voxelSizeText = qt.QDoubleSpinBox()
    self.voxelSizeText.setMinimum(0)
    self.voxelSizeText.setSuffix('mm')
    self.voxelSizeText.setDecimals(4)
    self.voxelSizeText.value = 0.0607
    self.voxelSizeText.setToolTip("Voxel size of the greyscale scan in millimetres")
    statsLayout.addRow("Voxel Size: ", self.voxelSizeText)

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
    self.masterVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect6)
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
    self._logic.enterSegmentEditor(self.segmentEditor)

  def exit(self):
    """Run this whenever the module is closed"""
    self._logic.exitSegmentEditor(self.segmentEditor)

  def onSelect4(self):
    """Update the state of the get erosions button whenever the selectors in step 4 change"""
    self.getErosionsButton.enabled = (self.inputVolumeSelector.currentNode() and 
                                     self.inputContourSelector.currentNode() and
                                     self.outputErosionSelector.currentNode() and
                                     self.fiducialSelector.currentNode())

  def onSelect5(self):
    """Update the state of the import/export button whenever the selectors in step 5 change"""
    self.importExportButton.enabled = (self.segmentationSelector.currentNode() and
                                       self.labelMapSelector.currentNode())
                               
  def onSelect6(self):
    """Update the state of the get statistics button whenever the selectors in step 6 change"""
    self.getStatsButton.enabled = (self.inputErosionSelector.currentNode() and
                                   self.masterVolumeSelector.currentNode() and
                                   self.outputTableSelector.currentNode())
  
  def onSelectInputVolume(self):
    """Run this whenever the input volume selector in step 4 changes"""
    inputVolumeNode = self.inputVolumeSelector.currentNode()
    inputContourNode = self.inputContourSelector.currentNode()

    if inputVolumeNode:
      # Update the default save directory
      self._logic.setDefaultDirectory(inputVolumeNode)

      # Update the spacing scale in the seed point table
      ras2ijk = vtk.vtkMatrix4x4()
      ijk2ras = vtk.vtkMatrix4x4()
      inputVolumeNode.GetRASToIJKMatrix(ras2ijk)
      inputVolumeNode.GetIJKToRASMatrix(ijk2ras)
      self.markupsTableWidget.setCoordsMatrices(ras2ijk, ijk2ras)
      # update the default output base name
      erosion_baseName = inputVolumeNode.GetName()+"_ER"
      seed_baseName = inputVolumeNode.GetName()+"_SEEDS"
      self.outputErosionSelector.baseName = erosion_baseName
      self.segmentCopier.currSegmentationSelector.baseName = erosion_baseName
      self.segmentCopier.otherSegmentationSelector.baseName = erosion_baseName
      self.segmentationSelector.baseName = erosion_baseName
      self.fiducialSelector.baseName = seed_baseName
      # update the viewer windows
      slicer.util.setSliceViewerLayers(background=inputVolumeNode)
      slicer.util.resetSliceViews() # centre the volume in the viewer windows
    else:
      self.outputErosionSelector.baseName = "ER"
      self.fiducialSelector.baseName = "SEEDS"
      
    if inputContourNode:
      # update the default output erosion base name, which matches the mask name
      self.outputErosionSelector.baseName = (inputContourNode.GetName()+"_ER")

  def onSelectInputContour(self):
    """Run this whenever the input contour selector in step 4 changes"""
    inputContourNode = self.inputContourSelector.currentNode()
    if inputContourNode:
      # update the default output erosion base name, which matches the mask name
      erosion_baseName = inputContourNode.GetName()+"_ER"
      self.outputErosionSelector.baseName = erosion_baseName

  def onAddOutputErosion(self, node):
    """Run this whenever a new erosion segmentation is created from the selector in step 4"""
    # force the output erosion base name to have the post fix '_' plus an index
    #  i.e. baseName_1, baseName_2, ...
    baseName = node.GetName()
    index_str = baseName.split('_')[-1]
    if not index_str.isdigit(): # not postfixed with '_' plus an index
      node.SetName(slicer.mrmlScene.GenerateUniqueName(baseName))

  def onSelectSeed(self):
    """Run this whenever the seed point selector in step 4 changes"""
    self.markupsTableWidget.setCurrentNode(self.fiducialSelector.currentNode())

  def onLargeErosionChecked(self):
    """Run this whenever the check box for large erosions in step 4 changes"""
    if self.erosionCheckBox.checked:
      self.minimalRadiusText.value = 6
      self.dilateErodeDistanceText.value = 6
    else:
      self.minimalRadiusText.value = 3
      self.dilateErodeDistanceText.value = 4

  def onSelectInputErosion(self):
    """Run this whenever the input erosion selector in step 6 changes"""
    inputErosionNode = self.inputErosionSelector.currentNode()

    if inputErosionNode:
      self.outputTableSelector.baseName = (inputErosionNode.GetName()+"_TABLE")
    else:
      self.outputTableSelector.baseName = "_TABLE"
    self._logic.exitStatistics() # disconnect erosion table selection signal

  def onGetErosionsButton(self):
    """Run this whenever the get erosions button in step 4 is clicked"""
    # update widgets
    self.disableErosionsWidgets()

    inputVolumeNode = self.inputVolumeSelector.currentNode()
    inputContourNode = self.inputContourSelector.currentNode()
    outputVolumeNode = self.outputErosionSelector.currentNode()
    fiducialNode = self.fiducialSelector.currentNode()
    ready = self._logic.setErosionParameters(inputVolumeNode, 
                                            inputContourNode, 
                                            self.lowerThresholdText.value,
                                            self.upperThresholdText.value,
                                            self.sigmaText.value,
                                            fiducialNode,
                                            self.minimalRadiusText.value,
                                            self.dilateErodeDistanceText.value)
    if ready:
      success = self._logic.getErosions(inputVolumeNode, inputContourNode, outputVolumeNode)
      if success:
        # update widgets
        self.outputErosionSelector.setCurrentNodeID("") # reset the output volume selector
        self.segmentEditor.setSegmentationNode(outputVolumeNode)
        self.segmentEditor.setMasterVolumeNode(inputVolumeNode)

    # update widgets
    self.enableErosionsWidgets()
  
  def onImportExportButton(self):
    """Run this whenever the import/export button in step 5 is clicked"""
    segmentationNode = self.segmentationSelector.currentNode()
    labelMapNode = self.labelMapSelector.currentNode()
    if self.exportRadioButton.checked: # segmentation to label map
      self._logic.exportErosionsToLabelmap(segmentationNode, labelMapNode)
    else:                              # label map to segmentation
      self._logic.labelmapToSegmentationNode(labelMapNode, segmentationNode)

  def onGetStatsButton(self):
    """Run this whenever the get statistics button in step 6 is clicked"""
    inputErosionNode = self.inputErosionSelector.currentNode()
    masterVolumeNode = self.masterVolumeSelector.currentNode()
    outputTableNode = self.outputTableSelector.currentNode()
    voxelSize = self.voxelSizeText.value
    self._logic.getStatistics(inputErosionNode,
                              masterVolumeNode,
                              voxelSize,
                              outputTableNode)

    # update widgets
    self.segmentEditor.setSegmentationNode(inputErosionNode)
    self.segmentEditor.setMasterVolumeNode(masterVolumeNode)

  def enableErosionsWidgets(self):
    """Enable widgets in the erosions layout in step 4"""
    self.onSelect4()
    self.progressBar.hide()

  def disableErosionsWidgets(self):
    """Disable widgets in the erosions layout in step 4"""
    self.getErosionsButton.enabled = False
    self.progressBar.show()

  def setProgress(self, value):
    """Update the progress bar"""
    self.progressBar.setValue(value)
