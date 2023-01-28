#-----------------------------------------------------
# Training.py
#
# Created by:  Yousif Al-Khoury
# Created on:  12-12-2022
#
# Description: This module sets up the interface for the Erosion Volume 3D Slicer extension.
#
#-----------------------------------------------------
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
from TrainingLib.ErosionVolumeLogic import ErosionVolumeLogic
from TrainingLib.SegmentEditor import SegmentEditor
from TrainingLib.SegmentCopier import SegmentCopier
from TrainingLib.MarkupsTable import MarkupsTable
import os

#
# ErosionVolume
#
class Training(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Training" # TODO make this more human readable by adding spaces
    self.parent.categories = ["Bone Analysis Module (BAM)"]
    self.parent.dependencies = []
    self.parent.contributors = ["Yousif Al-Khoury"] # replace with "Firstname Lastname (Organization)"
    self.parent.helpText = """ 
TODO
"""
    self.parent.helpText += "<br>For more information see the <a href=https://github.com/ManskeLab/3DSlicer_Erosion_Analysis/wiki/Erosion-Volume-Module>online documentation</a>."
    self.parent.helpText += "<br><td><img src=\"" + self.getLogo('bam') + "\" height=80> "
    self.parent.helpText += "<img src=\"" + self.getLogo('manske') + "\" height=80></td>"
    self.parent.acknowledgementText = """
Updated on December 12, 2022.<br>
Manske Lab<br>
    McCaig Institue for Bone and Joint Health<br>
    University of Calgary
""" # replace with organization, grant and thanks.

  def getLogo(self, logo_type):
    #get directory
    directory = os.path.split(os.path.split(os.path.realpath(__file__))[0])[0]

    #set file name
    if logo_type == 'bam':
      name = 'BAM_Logo.png'
    elif logo_type == 'manske':
      name = 'Manske_Lab_Logo.png'

    #
    if '\\' in directory:
      return directory + '\\Logos\\' + name
    else:
      return directory + '/Logos/' + name

#
# ErosionVolumeWidget
#
class TrainingWidget(ScriptedLoadableModuleWidget):
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
    # Buttons for testing
    ScriptedLoadableModuleWidget.setup(self)

    self.warning = qt.QLabel(
      """WARNING: This module clears all current nodes in the current slicer scene, <br>
      including those worked on inside other modules. Please save your work <br>
      before pressing the 'Proceed' button below.""")
    self.layout.addWidget(self.warning)
    self.proceedButton = qt.QPushButton("Proceed")
    self.proceedButton.toolTip = "Warning before proceeding with the training module."
    self.proceedButton.setFixedSize(80, 25)
    self.layout.addWidget(self.proceedButton)
    self.proceedButton.clicked.connect(self.proceed)
    self.layout.addStretch(0)

    

  def proceed(self):
    self.proceedButton.deleteLater()
    self.warning.deleteLater()
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
    self.checkErosionsButton()
    self.onSelect5()
    self.onSelect6()
    self.onSelectInputVolume()
    # self.onSelectSeed()
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
    self.inputVolumeSelector.setCurrentNode(None)
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
    self.inputContourSelector.setCurrentNode(None)
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
    self.outputErosionSelector.setCurrentNode(None)
    erosionsLayout.addRow("Output Erosions: ", self.outputErosionSelector)

    # auto-threshold options
    self.threshButton = qt.QCheckBox()
    self.threshButton.checked = True
    erosionsLayout.addRow("Use Automatic Thresholding", self.threshButton)

    self.threshSelector = qt.QComboBox()
    self.threshSelector.addItems(['Otsu', 'Huang', 'Max Entropy', 'Moments', 'Yen'])
    #self.threshSelector.setCurrentIndex(2)
    erosionsLayout.addRow("Thresholding Method", self.threshSelector)

    # Help button for thresholding methods
    self.helpButton = qt.QPushButton("Help")
    self.helpButton.toolTip = "Tips for selecting a thresholding method"
    self.helpButton.setFixedSize(50, 20)
    erosionsLayout.addRow("", self.helpButton)

    # threshold spin boxes (default unit is HU)
    self.lowerThresholdText = qt.QSpinBox()
    self.lowerThresholdText.setMinimum(-9999)
    self.lowerThresholdText.setMaximum(999999)
    self.lowerThresholdText.setSingleStep(10)
    self.lowerThresholdText.value = 530
    erosionsLayout.addRow("Lower Threshold: ", self.lowerThresholdText)
    self.upperThresholdText = qt.QSpinBox()
    self.upperThresholdText.setMinimum(-9999)
    self.upperThresholdText.setMaximum(999999)
    self.upperThresholdText.setSingleStep(10)
    self.upperThresholdText.value = 4000
    erosionsLayout.addRow("Upper Threshold: ", self.upperThresholdText)

    # gaussian sigma spin box
    self.sigmaText = qt.QDoubleSpinBox()
    self.sigmaText.setMinimum(0.0001)
    self.sigmaText.setDecimals(4)
    self.sigmaText.value = 1
    self.sigmaText.setToolTip("Standard deviation in the Gaussian smoothing filter")
    erosionsLayout.addRow("Gaussian Sigma: ", self.sigmaText)

    # seed point selector
    # self.fiducialSelector = slicer.qMRMLNodeComboBox()
    # self.fiducialSelector.nodeTypes = ["vtkMRMLMarkupsFiducialNode"]
    # self.fiducialSelector.selectNodeUponCreation = True
    # self.fiducialSelector.addEnabled = True
    # self.fiducialSelector.removeEnabled = True
    # self.fiducialSelector.renameEnabled = True
    # self.fiducialSelector.noneEnabled = False
    # self.fiducialSelector.showHidden = False
    # self.fiducialSelector.showChildNodeTypes = False
    # self.fiducialSelector.setMRMLScene(slicer.mrmlScene)
    # self.fiducialSelector.baseName = "SEEDS"
    # self.fiducialSelector.setToolTip( "Pick the seed points" )
    # self.fiducialSelector.setCurrentNode(None)
    # erosionsLayout.addRow("Seed Points: ", self.fiducialSelector)

    # seed point table
    self.markupsTableWidget = MarkupsTable(self.erosionsCollapsibleButton)
    self.markupsTableWidget.setMRMLScene(slicer.mrmlScene)
    self.markupsTableWidget.setNodeSelectorVisible(True) # use the above selector instead
    self.markupsTableWidget.setButtonsVisible(False)
    self.markupsTableWidget.setPlaceButtonVisible(True)
    self.markupsTableWidget.setDeleteAllButtonVisible(True)
    self.markupsTableWidget.setJumpToSliceEnabled(True)

    # horizontal white space
    erosionsLayout.addRow(qt.QLabel(""))

    # advanced box
    self.advancedCheckBox = qt.QCheckBox('Advanced Parameters')
    self.advancedCheckBox.checked = False
    self.advancedCheckBox.setToolTip('Set internal parameters for segmenting erosions')
    erosionsLayout.addRow(self.advancedCheckBox)

    # check box for CBCT scans
    self.CBCTCheckBox = qt.QCheckBox('CBCT')
    self.CBCTCheckBox.checked = False
    self.CBCTCheckBox.setToolTip('Set internal parameters for segmenting CBCT scans')
    erosionsLayout.addRow(self.CBCTCheckBox)

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
    self.minimalRadiusText = []
    self.dilateErodeDistance = []

    # self.minimalRadiusText = qt.QSpinBox()
    # self.minimalRadiusText.setMinimum(1)
    # self.minimalRadiusText.setMaximum(99)
    # self.minimalRadiusText.setSingleStep(1)
    # self.minimalRadiusText.setSuffix(' voxels')
    # self.minimalRadiusText.value = 3
    # advancedParameterLayout.addWidget(qt.QLabel("Minimum Erosion Radius: "), 3, 0)
    # advancedParameterLayout.addWidget(self.minimalRadiusText, 3, 1)
    # self.dilateErodeDistanceText = qt.QSpinBox()
    # self.dilateErodeDistanceText.setMinimum(0)
    # self.dilateErodeDistanceText.setMaximum(99)
    # self.dilateErodeDistanceText.setSingleStep(1)
    # self.dilateErodeDistanceText.setSuffix(' voxels')
    # self.dilateErodeDistanceText.value = 4
    # advancedParameterLayout.addWidget(qt.QLabel("Dilate/Erode Distance: "), 4, 0)
    # advancedParameterLayout.addWidget(self.dilateErodeDistanceText, 4, 1)

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
    self.inputVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.checkErosionsButton)
    self.inputVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelectInputVolume)
    self.inputContourSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelectInputContour)
    self.inputContourSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.checkErosionsButton)
    self.outputErosionSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.checkErosionsButton)
    self.outputErosionSelector.connect("nodeAddedByUser(vtkMRMLNode*)", lambda node: self.onAddOutputErosion(node))
    self.markupsTableWidget.getMarkupsSelector().connect("currentNodeChanged(vtkMRMLNode*)", self.checkErosionsButton)
    # self.fiducialSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect4)
    # self.fiducialSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelectSeed)
    self.threshButton.clicked.connect(self.onAutoThresh)
    self.helpButton.clicked.connect(self.onHelpButton)
    self.advancedCheckBox.connect("clicked(bool)", self.onAdvancedChecked)
    self.CBCTCheckBox.connect("clicked(bool)", self.onCBCTChecked)
    self.getErosionsButton.connect("clicked(bool)", self.onGetErosionsButton)

    self.onAutoThresh()
  
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

    initApplyGridLayout = qt.QGridLayout()
    initApplyGridLayout.setContentsMargins(0, 5, 0, 5)

    # # delete button
    # self.deleteButton1 = qt.QPushButton("Delete Contours")
    # self.deleteButton1.toolTip = "Delete all contours in all slices"
    # self.deleteButton1.enabled = False
    # initApplyGridLayout.addWidget(self.deleteButton1, 1, 0)

    # Erase between slices button
    self.eraseBetweenSlicesButton = qt.QPushButton("Erase Between Slices")
    self.eraseBetweenSlicesButton.toolTip = "Interpolates between segments between slices and erases those segments"
    self.eraseBetweenSlicesButton.enabled = False
    initApplyGridLayout.addWidget(self.eraseBetweenSlicesButton, 0, 0)

    # Apply erase button
    self.applyEraseBetweenSlicesButton = qt.QPushButton("Apply Erase")
    self.applyEraseBetweenSlicesButton.toolTip = "Applies erase between slices"
    self.applyEraseBetweenSlicesButton.enabled = False
    initApplyGridLayout.addWidget(self.applyEraseBetweenSlicesButton, 0, 1)

    initApplyFrame = qt.QFrame()
    initApplyFrame.setLayout(initApplyGridLayout)
    manualCorrectionLayout.addWidget(initApplyFrame)

    # connections
    self.manualCorrectionCollapsibleButton.connect('contentsCollapsed(bool)', self.onCollapsed5)
    self.segmentationSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect5)
    self.labelMapSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect5)
    self.importExportButton.connect("clicked(bool)", self.onImportExportButton)
    # self.deleteButton1.connect('clicked(bool)', self.onDeleteButton)
    self.eraseBetweenSlicesButton.connect('clicked(bool)', self.onEraseBetweenSlicesButton)
    self.applyEraseBetweenSlicesButton.connect('clicked(bool)', self.onApplyEraseBetweenSlicesButton)

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
    self.inputErosionSelector.selectNodeUponCreation = True
    self.inputErosionSelector.addEnabled = False
    self.inputErosionSelector.renameEnabled = True
    self.inputErosionSelector.removeEnabled = True
    self.inputErosionSelector.noneEnabled = False
    self.inputErosionSelector.showHidden = False
    self.inputErosionSelector.showChildNodeTypes = False
    self.inputErosionSelector.setMRMLScene(slicer.mrmlScene)
    self.inputErosionSelector.setToolTip("Pick the final erosion segmentation that contains all the erosions")
    self.inputErosionSelector.setCurrentNode(None)
    statsLayout.addRow("Input Erosions: ", self.inputErosionSelector)

    self.masterVolumeSelector = slicer.qMRMLNodeComboBox()
    self.masterVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.masterVolumeSelector.selectNodeUponCreation = True
    self.masterVolumeSelector.addEnabled = False
    self.masterVolumeSelector.renameEnabled = True
    self.masterVolumeSelector.removeEnabled = False
    self.masterVolumeSelector.noneEnabled = False
    self.masterVolumeSelector.showHidden = False
    self.masterVolumeSelector.showChildNodeTypes = False
    self.masterVolumeSelector.setMRMLScene(slicer.mrmlScene)
    self.masterVolumeSelector.setToolTip("Pick the greyscale scan")
    self.masterVolumeSelector.setCurrentNode(None)
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
    self.outputTableSelector.setCurrentNode(None)
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

    # logger
    self.logger = logging.getLogger("erosion_volume")

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
      if self.inputVolumeSelector.currentNode() and self.inputContourSelector.currentNode():
        self.inputErosionSelector.setCurrentNodeIndex(0)
        self.masterVolumeSelector.setCurrentNodeIndex(0)
        self.outputTableSelector.addNode()

  def enter(self):
    """Run this whenever the module is reopened"""    
    self._logic.enterSegmentEditor(self.segmentEditor)

  def exit(self):
    """Run this whenever the module is closed"""
    self._logic.exitSegmentEditor(self.segmentEditor)

  def checkErosionsButton(self):
    self.getErosionsButton.enabled = (self.inputVolumeSelector.currentNode() and 
                                     self.inputContourSelector.currentNode() and
                                     self.outputErosionSelector.currentNode() and
                                     self.markupsTableWidget.getCurrentNode())

  def onSelect4(self):
    """Update the state of the get erosions button whenever the selectors in step 4 change"""
    self.getErosionsButton.enabled = (self.inputVolumeSelector.currentNode() and 
                                     self.inputContourSelector.currentNode() and
                                     self.outputErosionSelector.currentNode() and
                                     self.markupsTableWidget.getCurrentNode())

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
      # update the viewer windows
      slicer.util.setSliceViewerLayers(background=inputVolumeNode)
      slicer.util.resetSliceViews() # centre the volume in the viewer windows

      #Set master volume in statistics step
      self.masterVolumeSelector.setCurrentNode(inputVolumeNode)
      self.voxelSizeText.value = inputVolumeNode.GetSpacing()[0]

      #check if preset intensity units exist
      check = True
      if "Lower" in inputVolumeNode.__dict__.keys():
        self.lowerThresholdText.setValue(inputVolumeNode.__dict__["Lower"])
        check = False
      if "Upper" in inputVolumeNode.__dict__.keys():
        self.upperThresholdText.setValue(inputVolumeNode.__dict__["Upper"])
        check = False

      #check intensity units and display warning if not in HU
      if check and not self.threshButton.checked:
        if not self._logic.intensityCheck(inputVolumeNode):
          text = """The selected image likely does not use HU for intensity units. 
Default thresholds are set in HU and will not generate an accurate result. 
Change the lower and upper thresholds before initializing."""
          slicer.util.warningDisplay(text, windowTitle='Intensity Unit Warning')

      #remove existing loggers
      if self.logger.hasHandlers():
        for handler in self.logger.handlers:
          self.logger.removeHandler(handler)
          
       #initialize logger with filename
      try:
        filename = inputVolumeNode.GetStorageNode().GetFullNameFromFileName()
        filename = os.path.split(filename)[0] + '/LOG_' + os.path.split(filename)[1]
        filename = os.path.splitext(filename)[0] + '.log'
        print(filename)
      except:
        filename = 'share/' + inputVolumeNode.GetName() + '.'
      logHandler = logging.FileHandler(filename)
      
      self.logger.addHandler(logHandler)
      self.logger.info("Using Erosion Volume Module with " + inputVolumeNode.GetName() + "\n")

      #set name in statistics
      self.masterVolumeSelector.baseName = inputVolumeNode.GetName()
      

  def onSelectInputContour(self):
    """Run this whenever the input contour selector in step 4 changes"""
    inputContourNode = self.inputContourSelector.currentNode()
    if inputContourNode:
      # update the default output erosion base name, which matches the mask name
      erosion_baseName = inputContourNode.GetName()+"_ER"
      self.outputErosionSelector.baseName = erosion_baseName
      self.segmentCopier.currSegmentationSelector.baseName = erosion_baseName
      self.segmentCopier.otherSegmentationSelector.baseName = erosion_baseName
      self.segmentationSelector.baseName = erosion_baseName
      self.inputErosionSelector.baseName = erosion_baseName
      seed_baseName = inputContourNode.GetName()+"_SEEDS"
      # self.fiducialSelector.baseName = seed_baseName
      self.outputTableSelector.baseName = inputContourNode.GetName()+"_TABLE"
      

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
  
  def onAutoThresh(self):
    use_auto = self.threshButton.checked
    self.lowerThresholdText.setEnabled(not use_auto)
    self.upperThresholdText.setEnabled(not use_auto)
    self.threshSelector.setEnabled(use_auto)
    if not use_auto:
      self.onSelectInputVolume()

  def onHelpButton(self) -> None:
    '''Help button is pressed'''
    txt = """Thresholding Methods\n
For images that only contain bone and soft tissue (no completely dark regions), use the 'Otsu', 'Huang', or 'Moments' Thresholds. \n
For images with completely dark regions, use the 'Max Entropy' or 'Yen' Thresholds.
          """
    slicer.util.infoDisplay(txt, 'Help: Similarity Metrics')

  def onAdvancedChecked(self):
    """Run this whenever the check box for large erosions in step 4 changes"""

    if self.advancedCheckBox.checked:
      self.markupsTableWidget.advancedMarkupsControlPointsTableView()
      # self.minimalRadiusText.value = 6
      # self.dilateErodeDistanceText.value = 6
      self.CBCTCheckBox.checked = False
    else:
      self.markupsTableWidget.normalMarkupsControlPointsTableView()
      # self.minimalRadiusText.value = 3
      # self.dilateErodeDistanceText.value = 4
  
  def onCBCTChecked(self):
    """Run this whenever the check box for CBCT in step 4 changes"""
    if self.CBCTCheckBox.checked:
      self.minimalRadiusText.value = 1
      self.dilateErodeDistanceText.value = 0
      self.advancedCheckBox.checked = False
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
    self.markupsTableWidget.updateLabels()

    inputVolumeNode = self.inputVolumeSelector.currentNode()
    inputContourNode = self.inputContourSelector.currentNode()
    outputVolumeNode = self.outputErosionSelector.currentNode()
    # fiducialNode = self.fiducialSelector.currentNode()
    markupsNode = self.markupsTableWidget.getCurrentNode()
    minimalRadius = [1, 2, 2]
    dilateErodeDistance = [1, 2, 2]

    self.logger.info("Erosion Volume initialized with parameters:")
    self.logger.info("Input Volume: " + inputVolumeNode.GetName())
    self.logger.info("Input Contour: " + inputContourNode.GetName())
    self.logger.info("Output Volume: " + outputVolumeNode.GetName())
    # self.logger.info("Input Seeds: " + fiducialNode.GetName())
    if self.threshButton.checked:
      self.logger.info("Automatic Threshold Method: " + self.threshSelector.currentText)
    else:
      self.logger.info("Lower Theshold: " + str(self.lowerThresholdText.value))
      self.logger.info("Upper Theshold: " + str(self.upperThresholdText.value))
    self.logger.info("Gaussian Sigma: " + str(self.sigmaText.value))
    # self.logger.info("Minimum Erosion Radius: " + str(self.minimalRadiusText.value))
    # self.logger.info("Dilate/Erode Distance: " + str(self.dilateErodeDistanceText.value))

    if self.threshButton.checked:
      ready = self._logic.setErosionParameters(inputVolumeNode, 
                                            inputContourNode, 
                                            self.sigmaText.value,
                                            # fiducialNode,
                                            markupsNode,
                                            minimalRadius,
                                            dilateErodeDistance,
                                            method=self.threshSelector.currentIndex)
    else:
      ready = self._logic.setErosionParameters(inputVolumeNode, 
                                            inputContourNode, 
                                            self.sigmaText.value,
                                            # fiducialNode,
                                            markupsNode,
                                            # self.minimalRadiusText.value,
                                            # self.dilateErodeDistanceText.value,
                                            lower=self.lowerThresholdText.value,
                                            upper=self.upperThresholdText.value)
    if ready:
      success = self._logic.getErosions(inputVolumeNode, inputContourNode, outputVolumeNode)
      if success:
        # update widgets
        self.outputErosionSelector.setCurrentNodeID("") # reset the output volume selector
        self.segmentEditor.setSegmentationNode(outputVolumeNode)
        self.segmentEditor.setMasterVolumeNode(inputVolumeNode)

        self.enableEraseWidgets()
    
    # store thresholds 
    inputVolumeNode.__dict__["Lower"] = self.lowerThresholdText.value
    inputVolumeNode.__dict__["Upper"] = self.upperThresholdText.value

    # update widgets
    self.enableErosionsWidgets()

    self.logger.info("Finished\n")
  
  def onImportExportButton(self):
    """Run this whenever the import/export button in step 5 is clicked"""
    segmentationNode = self.segmentationSelector.currentNode()
    labelMapNode = self.labelMapSelector.currentNode()
    if self.exportRadioButton.checked: # segmentation to label map
      self._logic.exportErosionsToLabelmap(segmentationNode, labelMapNode)
    else:                              # label map to segmentation
      self._logic.labelmapToSegmentationNode(labelMapNode, segmentationNode)

  def onEraseBetweenSlicesButton(self):
    
    segmentationNode = self.segmentEditor.getEditor().segmentationNode()
    self.segmentIdToErase = self.segmentEditor.getEditor().currentSegmentID()

    eraseNodeID = segmentationNode.GetSegmentation().AddEmptySegment("Delete")
    self.segmentEditor.getEditor().setCurrentSegmentID(eraseNodeID)
    self.segmentEditor.getEditor().setActiveEffectByName("Paint")

    maskMode = segmentationNode.EditAllowedEverywhere
    self.segmentEditor.setMaskMode(maskMode, self.segmentIdToErase)

    self.applyEraseBetweenSlicesButton.enabled = True

    #TODO make slicer wait until you have atleast 2 slices with segments before enabling apply button

  def onApplyEraseBetweenSlicesButton(self):

    volumeNode = self.segmentEditor.getEditor().masterVolumeNode()
    segmentationNode = self.segmentEditor.getEditor().segmentationNode()
    eraseId = segmentationNode.GetSegmentation().GetSegmentIdBySegmentName("Delete")
    self.segmentEditor.getEditor().setCurrentSegmentID(eraseId)

    selectedSegmentIds = vtk.vtkStringArray()

    if(segmentationNode):
        segmentationNode.GetSegmentation().GetSegmentIDs(selectedSegmentIds)

    segmentArrays = []
    segments = []
    segmentIds = []

    # remove all segments
    for idx in range(selectedSegmentIds.GetNumberOfValues()):
      segmentId = selectedSegmentIds.GetValue(idx)
      if segmentId == "Delete":
        continue

      # Get mask segment as numpy array
      segmentArray = slicer.util.arrayFromSegmentBinaryLabelmap(segmentationNode, segmentId, volumeNode)

      segmentArrays.append(segmentArray)
      segments.append(segmentationNode.GetSegmentation().GetSegment(segmentId))
      segmentIds.append(segmentId)
      segmentationNode.GetSegmentation().RemoveSegment(segmentId)

    maskMode = segmentationNode.EditAllowedEverywhere
    self.segmentEditor.setMaskMode(maskMode, "")

    self.segmentEditor.getEditor().setActiveEffectByName("Fill between slices")
    effect = self.segmentEditor.getEditor().activeEffect()
    effect.self().onPreview()
    effect.self().onApply()

    # Get erase mask segment as numpy array
    eraseArray = slicer.util.arrayFromSegmentBinaryLabelmap(segmentationNode, eraseId, volumeNode)

    slices = eraseArray.shape[0]
    row = eraseArray.shape[1]
    col = eraseArray.shape[2]

    # Add all segments back but after erasing
    idx = 0
    for segmentArray in segmentArrays:
      segmentationNode.GetSegmentation().AddSegment(segments[idx], segmentIds[idx])

      if segmentIds[idx] == self.segmentIdToErase:
        # Iterate through voxels
        for i in range(slices):
          for j in range(row):
            for k in range(col):
              if(eraseArray[i, j, k]):
                segmentArray[i, j, k] = 0

      # Convert back to label map array
      slicer.util.updateSegmentBinaryLabelmapFromArray(segmentArray, segmentationNode, segmentIds[idx], volumeNode)
      idx = idx + 1

    segmentationNode.GetSegmentation().RemoveSegment(eraseId)
    maskSegmentId = segmentationNode.GetSegmentation().GetNthSegmentID(0)

    maskMode = segmentationNode.EditAllowedInsideSingleSegment
    self.segmentEditor.setMaskMode(maskMode, maskSegmentId)

    segmentationNode.GetDisplayNode().SetSegmentVisibility(maskSegmentId, False)
    self.segmentEditor.getEditor().setCurrentSegmentID(self.segmentIdToErase)
    print(maskSegmentId)

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

  def enableEraseWidgets(self):
    self.eraseBetweenSlicesButton.enabled = True

  def enableErosionsWidgets(self):
    """Enable widgets in the erosions layout in step 4"""
    self.checkErosionsButton()
    self.progressBar.hide()

  def disableErosionsWidgets(self):
    """Disable widgets in the erosions layout in step 4"""
    self.getErosionsButton.enabled = False
    self.progressBar.show()

  def setProgress(self, value):
    """Update the progress bar"""
    self.progressBar.setValue(value)
