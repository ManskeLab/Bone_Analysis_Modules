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
import os

import SimpleITK as sitk
import sitkUtils
import numpy as np

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
    self.parent.categories = ["Bone Analysis Module (BAM)"]
    self.parent.dependencies = []
    self.parent.contributors = ["Mingjie Zhao"] # replace with "Firstname Lastname (Organization)"
    self.parent.helpText = """ 
This module contains steps 4-6 of erosion analysis. It requires a greyscale scan and a mask.
Erosions are identified by placing seed points in each of them. <br>
Step 4: Segment erosions given a seed point in each erosion. <br>
Step 5: Manually correct the erosion segmentations and combine them into a single segmentation. <br>
Step 6: Compute erosion statistics, such as volume, surface area, and roundness.
"""
    self.parent.helpText += "<br>For more information see the <a href=https://github.com/ManskeLab/3DSlicer_Erosion_Analysis/wiki/Erosion-Volume-Module>online documentation</a>."
    self.parent.helpText += "<br><td><img src=\"" + self.getLogo('bam') + "\" height=80> "
    self.parent.helpText += "<img src=\"" + self.getLogo('manske') + "\" height=80></td>"
    self.parent.acknowledgementText = """
Updated on January 27, 2022.<br>
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
class ErosionVolumeWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """
  def __init__(self, parent):
    # Initialize logics object
    self._logic = ErosionVolumeLogic()
    # initialize call back object for updating progrss bar
    self._logic.progressCallBack = self.setProgress
    self._ras2ijk = vtk.vtkMatrix4x4()
    self._ijk2ras = vtk.vtkMatrix4x4()

    ScriptedLoadableModuleWidget.__init__(self, parent)

  def setup(self):
    # Buttons for testing
    ScriptedLoadableModuleWidget.setup(self)

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

    # input mask selector
    self.inputMaskSelector = slicer.qMRMLNodeComboBox()
    self.inputMaskSelector.nodeTypes = ["vtkMRMLScalarVolumeNode","vtkMRMLLabelMapVolumeNode"]
    self.inputMaskSelector.selectNodeUponCreation = False
    self.inputMaskSelector.addEnabled = False
    self.inputMaskSelector.renameEnabled = True
    self.inputMaskSelector.removeEnabled = True
    self.inputMaskSelector.noneEnabled = False
    self.inputMaskSelector.showHidden = False
    self.inputMaskSelector.showChildNodeTypes = False
    self.inputMaskSelector.setMRMLScene(slicer.mrmlScene)
    self.inputMaskSelector.setToolTip( "Pick the mask label map" )
    self.inputMaskSelector.setCurrentNode(None)
    erosionsLayout.addRow("Input Mask: ", self.inputMaskSelector)

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

    # # threshold spin boxes (default unit is HU)
    # self.lowerThresholdText = qt.QSpinBox()
    # self.lowerThresholdText.setMinimum(-9999)
    # self.lowerThresholdText.setMaximum(999999)
    # self.lowerThresholdText.setSingleStep(10)
    # self.lowerThresholdText.value = 650
    # erosionsLayout.addRow("Lower Threshold: ", self.lowerThresholdText)
    # self.upperThresholdText = qt.QSpinBox()
    # self.upperThresholdText.setMinimum(-9999)
    # self.upperThresholdText.setMaximum(999999)
    # self.upperThresholdText.setSingleStep(10)
    # self.upperThresholdText.value = 9999
    # erosionsLayout.addRow("Upper Threshold: ", self.upperThresholdText)

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

    # glyph size 
    self.glyphSizeBox = qt.QDoubleSpinBox()
    self.glyphSizeBox.setMinimum(0.5)
    self.glyphSizeBox.setMaximum(25)
    self.glyphSizeBox.setSingleStep(0.5)
    self.glyphSizeBox.setSuffix(' %')
    self.glyphSizeBox.value = 1.0
    erosionsLayout.addRow("Seed Point Size ", self.glyphSizeBox)

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
    self.inputMaskSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelectInputMask)
    self.inputMaskSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.checkErosionsButton)
    self.outputErosionSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.checkErosionsButton)
    self.outputErosionSelector.connect("nodeAddedByUser(vtkMRMLNode*)", lambda node: self.onAddOutputErosion(node))
    self.markupsTableWidget.getMarkupsSelector().connect("currentNodeChanged(vtkMRMLNode*)", self.checkErosionsButton)
    self.markupsTableWidget.getMarkupsSelector().connect("currentNodeChanged(vtkMRMLNode*)", self.onSelectSeed)
    self.glyphSizeBox.valueChanged.connect(self.onGlyphSizeChanged)
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
    # self.deleteButton1.connect('clicked(bool)', self.onDeleteButton)
    # self.eraseBetweenSlicesButton.connect('clicked(bool)', self.onEraseBetweenSlicesButton)
    # self.applyEraseBetweenSlicesButton.connect('clicked(bool)', self.onApplyEraseBetweenSlicesButton)

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
      if self.inputVolumeSelector.currentNode() and self.inputMaskSelector.currentNode():
        self.inputErosionSelector.setCurrentNodeIndex(0)
        # self.masterVolumeSelector.setCurrentNodeIndex(0)
        self.outputTableSelector.addNode()

  def enter(self):
    """Run this whenever the module is reopened"""    
    self._logic.enterSegmentEditor(self.segmentEditor)

  def exit(self):
    """Run this whenever the module is closed"""
    self._logic.exitSegmentEditor(self.segmentEditor)

  def checkErosionsButton(self):
    self.getErosionsButton.enabled = (self.inputVolumeSelector.currentNode() and 
                                     self.inputMaskSelector.currentNode() and
                                     self.outputErosionSelector.currentNode() and
                                     self.markupsTableWidget.getCurrentNode())

  def onSelect4(self):
    """Update the state of the get erosions button whenever the selectors in step 4 change"""
    self.getErosionsButton.enabled = (self.inputVolumeSelector.currentNode() and 
                                     self.inputMaskSelector.currentNode() and
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
    inputMaskNode = self.inputMaskSelector.currentNode()

    if inputVolumeNode:
      # Update the default save directory
      self._logic.setDefaultDirectory(inputVolumeNode)

      # Update the spacing scale in the seed point table
      inputVolumeNode.GetRASToIJKMatrix(self._ras2ijk)
      inputVolumeNode.GetIJKToRASMatrix(self._ijk2ras)
      
      self.markupsTableWidget.setCoordsMatrices(self._ras2ijk, self._ijk2ras)
      # update the viewer windows
      slicer.util.setSliceViewerLayers(background=inputVolumeNode)
      slicer.util.resetSliceViews() # centre the volume in the viewer windows

      #Set master volume in statistics step
      self.masterVolumeSelector.setCurrentNode(inputVolumeNode)
      self.voxelSizeText.value = inputVolumeNode.GetSpacing()[0]

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
      

  def onSelectInputMask(self):
    """Run this whenever the input Mask selector in step 4 changes"""
    inputMaskNode = self.inputMaskSelector.currentNode()
    if inputMaskNode:
      # update the default output erosion base name, which matches the mask name
      erosion_baseName = inputMaskNode.GetName()+"_ER"
      self.outputErosionSelector.baseName = erosion_baseName
      self.segmentCopier.currSegmentationSelector.baseName = erosion_baseName
      self.segmentCopier.otherSegmentationSelector.baseName = erosion_baseName
      self.segmentationSelector.baseName = erosion_baseName
      self.inputErosionSelector.baseName = erosion_baseName
      seed_baseName = inputMaskNode.GetName()+"_SEEDS"
      # self.fiducialSelector.baseName = seed_baseName
      self.outputTableSelector.baseName = inputMaskNode.GetName()+"_TABLE"
      

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
    self.markupsTableWidget.onMarkupsNodeChanged()
    markupsDisplayNode = self.markupsTableWidget.getCurrentNode().GetMarkupsDisplayNode()
    markupsDisplayNode.SetGlyphScale(self.glyphSizeBox.value)
  
  def onGlyphSizeChanged(self):
    markupsDisplayNode = self.markupsTableWidget.getCurrentNode().GetMarkupsDisplayNode()
    markupsDisplayNode.SetGlyphScale(self.glyphSizeBox.value)

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
    # self.markupsTableWidget.updateLabels()

    inputVolumeNode = self.inputVolumeSelector.currentNode()
    inputMaskNode = self.inputMaskSelector.currentNode()
    outputVolumeNode = self.outputErosionSelector.currentNode()
    # fiducialNode = self.fiducialSelector.currentNode()
    markupsNode = self.markupsTableWidget.getCurrentNode()
    # minimalRadius = self.markupsTableWidget.getCurrentNodeMinimalRadii()
    # dilateErodeDistance = self.markupsTableWidget.getCurrentNodeDilateErodeDistances()

    self.logger.info("Erosion Volume initialized with parameters:")
    self.logger.info("Input Volume: " + inputVolumeNode.GetName())
    self.logger.info("Input Mask: " + inputMaskNode.GetName())
    self.logger.info("Output Volume: " + outputVolumeNode.GetName())

    img = sitkUtils.PullVolumeFromSlicer(inputVolumeNode.GetName())
    mask_img = sitk.Cast(sitkUtils.PullVolumeFromSlicer(inputMaskNode.GetName()), sitk.sitkUInt8)
    mask_img = sitk.BinaryThreshold(mask_img, lowerThreshold=1, insideValue=1)
    mask_img = sitk.Cast(mask_img, sitk.sitkUInt8)

    resampler = sitk.ResampleImageFilter()
    resampler.SetReferenceImage(img)
    resampler.SetInterpolator(sitk.sitkLinear)
    resampler.SetDefaultPixelValue(0)
    resampler.SetTransform(sitk.Transform())
    mask_img = resampler.Execute(mask_img)

    sigma_over_spacing = img.GetSpacing()[0]
    print(sigma_over_spacing)

    # gaussian smoothing filter
    print("Applying Smoothing filter")
    smooth_img = sitk.Median(img)
    smooth_img = sitk.LaplacianSharpening(smooth_img)
    smooth_img = sitk.Median(smooth_img)
    smooth_img = sitk.LaplacianSharpening(smooth_img)
    smooth_img = sitk.Median(smooth_img)
    smooth_img = sitk.LaplacianSharpening(smooth_img)
    smooth_img = sitk.Median(smooth_img)
    smooth_img = sitk.LaplacianSharpening(smooth_img)
    smooth_img = sitk.Median(smooth_img)
    smooth_img = sitk.LaplacianSharpening(smooth_img)
    gaussian_filter = sitk.SmoothingRecursiveGaussianImageFilter()

    # gaussian_filter.SetSigma(sigma_over_spacing*1.5)
    # gaussian_img = gaussian_filter.Execute(smooth_img)
    smooth_img = sitk.Normalize(smooth_img)

    # sitk.WriteImage(smooth_img, 'Z:/work2/manske/temp/seedpointfix/smooth.nii')

    stat = sitk.StatisticsImageFilter()
    stat.Execute(smooth_img)

    lower_threshold_img = (stat.GetMaximum()+stat.GetMinimum())/2

    # Edge detection
    lower_threshold = 0.4
    # canny_smoothing_variance = 0.07
    # edge = sitk.CannyEdgeDetection(smooth_img, lowerThreshold=lower_threshold, upperThreshold=0.99, variance = 3*[canny_smoothing_variance*sigma_over_spacing])
    # edge = sitk.Cast(edge, sitk.sitkUInt8)
    # sitk.WriteImage(edge, 'Z:/work2/manske/temp/seedpointfix/edge1.nii')
    lower_threshold_img = (stat.GetMaximum()+stat.GetMinimum())/2

    print(lower_threshold_img)

    # Edge detection
    edge = sitk.CannyEdgeDetection(smooth_img, lowerThreshold=0.3, upperThreshold=0.99, variance = 3*[0.03*sigma_over_spacing])
    edge = sitk.Cast(edge, sitk.sitkUInt8)
    # sitk.WriteImage(edge, 'Z:/work2/manske/temp/seedpointfix/edge1.nii')
    edge1 = sitk.GradientMagnitude(smooth_img)
    # sitk.WriteImage(edge1, 'Z:/work2/manske/temp/seedpointfix/edge2_pre.nii')
    edge1 = sitk.BinaryThreshold(edge1, lower_threshold_img*10, 999)
    # sitk.WriteImage(edge1, 'Z:/work2/manske/temp/seedpointfix/edge2.nii')
    edge2 = sitk.BinaryThreshold(smooth_img, lower_threshold_img/2, 999)
    # sitk.WriteImage(edge2, 'Z:/work2/manske/temp/seedpointfix/thresh.nii')

    edge = edge | edge1 | edge2
    # sitk.WriteImage(edge, 'Z:/work2/manske/temp/seedpointfix/edge4.nii')

    dilate_filter = sitk.BinaryDilateImageFilter()
    dilate_filter.SetForegroundValue(1)
    dilate_filter.SetKernelRadius(1)

    erode_filter = sitk.BinaryErodeImageFilter()
    erode_filter.SetForegroundValue(1)
    erode_filter.SetKernelRadius(1)

    dilate_filter_5 = sitk.BinaryDilateImageFilter()
    dilate_filter_5.SetForegroundValue(1)
    dilate_filter_5.SetKernelRadius(5)

    erode_filter_5 = sitk.BinaryErodeImageFilter()
    erode_filter_5.SetForegroundValue(1)
    erode_filter_5.SetKernelRadius(5)


    # # # Binary Closing
    # dilated_img = dilate_filter.Execute(edge)
    # erode_img = erode_filter.Execute(dilated_img)

    # dilated_img = dilate_filter.Execute(erode_img)
    # erode_img = erode_filter.Execute(dilated_img)

    erode_img = edge
    # edge = erode_img
    # sitk.WriteImage(edge, 'Z:/work2/manske/temp/seedpointfix/edge3.nii')
    # sitk.WriteImage(edge, 'Z:/work2/manske/temp/seedpointfix/edge.nii')

    invert_filter = sitk.InvertIntensityImageFilter()
    invert_filter.SetMaximum(1)
    full_void_volume_img = mask_img* invert_filter.Execute(erode_img)
    # sitk.WriteImage(full_void_volume_img, 'Z:/work2/manske/temp/seedpointfix/void.nii')

    final_img = mask_img * 0

    num_control_points = markupsNode.GetNumberOfControlPoints()
    success = False

    for id in range(num_control_points):
        point = [round(ax) for ax in self.markupsTableWidget.getNthControlPointIJKCoords(id)]
        points = [point]

        connected_filter = sitk.ConnectedThresholdImageFilter()
        connected_filter.SetLower(1)
        connected_filter.SetUpper(1)
        connected_filter.SetSeedList(points)
        connected_filter.SetReplaceValue(1)

        tmp_mask_img = connected_filter.Execute(mask_img)
        void_volume_img = tmp_mask_img * full_void_volume_img
        # void_volume_img = dilate_filter.Execute(void_volume_img)
        # sitk.WriteImage(void_volume_img, 'Z:/work2/manske/temp/seedpointfix/invert.nii')
        stat = sitk.LabelShapeStatisticsImageFilter()

        plane = None
        init_erosion = None
        x = 0
        l=10

        connected_img = connected_filter.Execute(void_volume_img)

        stat.Execute(connected_img)
        if(stat.GetNumberOfLabels() == 0):
            print('ERROR: Connected Component did not find erosion at the seed point location of {}'.format(point))
            continue

        filter = sitk.SimilarityIndexImageFilter()
        filter.Execute(void_volume_img, connected_img)

        if filter.GetSimilarityIndex() < 0.2:
            # Erosion is already disconnected from trabecular
            l=0
            comb_erosion = connected_img
        else:
            erode_times = 0
            original_axial_slice = connected_img[:, :, point[2]]
            original_coronal_slice = connected_img[:, point[1], :]
            original_sagittal_slice = connected_img[point[0], :, :]
            while True:
              # Get list of seed points
              points_saggital = [[point[1], point[2], 0]]
              points_coronal = [[point[0], point[2], 0]]
              points_axial = [[point[0], point[1], 0]]

              connected_filter.SetSeedList(points_axial)
              axial_slice = connected_img[:, :, point[2]]
              axial_con = connected_filter.Execute(axial_slice)
              filter.Execute(original_axial_slice, axial_con)
              # sitk.WriteImage(axial_slice, 'Z:/work2/manske/temp/seedpointfix/ax_slice.nii')
              # sitk.WriteImage(axial_con, 'Z:/work2/manske/temp/seedpointfix/ax.nii')
              self.logger.info(filter.GetSimilarityIndex())

              if filter.GetSimilarityIndex() > 0.2:
                  connected_filter.SetSeedList(points_coronal)
                  coronal_slice = connected_img[:, point[1], :]
                  coronal_con = connected_filter.Execute(coronal_slice)
                  filter.Execute(original_coronal_slice, coronal_con)
                  # sitk.WriteImage(coronal_slice, 'Z:/work2/manske/temp/seedpointfix/cor_slice.nii')
                  # sitk.WriteImage(coronal_con, 'Z:/work2/manske/temp/seedpointfix/cor.nii')
                  self.logger.info(filter.GetSimilarityIndex())

                  if filter.GetSimilarityIndex() > 0.2:
                      connected_filter.SetSeedList(points_saggital)
                      sagittal_slice = connected_img[point[0], :, :]
                      sagittal_con = connected_filter.Execute(sagittal_slice)
                      filter.Execute(original_sagittal_slice, sagittal_con)
                      # sitk.WriteImage(sagittal_slice, 'Z:/work2/manske/temp/seedpointfix/sag_slice.nii')
                      # sitk.WriteImage(sagittal_con, 'Z:/work2/manske/temp/seedpointfix/sag.nii')
                      self.logger.info(filter.GetSimilarityIndex())

                      if filter.GetSimilarityIndex() > 0.2:
                          print("ERROR: Invalid seed point placement.")
                          connected_img = erode_filter.Execute(connected_img)
                          erode_times += 1
                          stat.Execute(connected_img)
                          if stat.GetNumberOfLabels() == 0:
                            break
                          continue
                      else:
                          plane = 0
                          init_erosion = sagittal_con
                          points = np.argwhere(sitk.GetArrayFromImage(sagittal_con))
                          points = [[point[0], int(pt[1]), int(pt[0])] for pt in points]
                          break
                  else:
                      plane = 1
                      init_erosion = coronal_con
                      points = np.argwhere(sitk.GetArrayFromImage(coronal_con))
                      points = [[int(pt[1]), point[1], int(pt[0])] for pt in points]
                      break
              else:
                  plane = 2
                  init_erosion = axial_con
                  points = np.argwhere(sitk.GetArrayFromImage(axial_con))
                  points = [[int(pt[1]), int(pt[0]), point[2]] for pt in points]
                  break

            erode_img = void_volume_img
            # sitk.WriteImage(erode_img, 'Z:/work2/manske/temp/seedpointfix/erode_img.nii')
            dims = erode_img.GetSize()

            for i in range(erode_times):
              init_erosion = dilate_filter.Execute(init_erosion)

            comb_erosion = erode_img*0
            if plane == 0:
                comb_erosion[point[plane], :, :] = init_erosion
            elif plane == 1:
                comb_erosion[:, point[plane], :] = init_erosion
            else:
                comb_erosion[:, :, point[plane]] = init_erosion

            for slice_idx in range(point[plane]+1, dims[plane]-1):
                print(slice_idx+1)
                erode_slice = 0
                if plane == 0:
                    erode_slice = erode_img[slice_idx, :, :]
                    prev_slice = comb_erosion[slice_idx-1, :, :]
                    stat.Execute(prev_slice)

                elif plane == 1:
                    erode_slice = erode_img[:, slice_idx, :]
                    prev_slice = comb_erosion[:, slice_idx-1, :]
                    stat.Execute(prev_slice)

                else:
                    erode_slice = erode_img[:, :, slice_idx]
                    prev_slice = comb_erosion[:, :, slice_idx-1]
                    stat.Execute(prev_slice)

                if stat.GetNumberOfLabels() == 0:
                    break
                
                print(stat.GetNumberOfPixels(1))

                # deflate_times = int(np.sqrt(np.sqrt(stat.GetNumberOfPixels(1)))/2)
                # print("hi")
                # print(deflate_times)

                prev_slice = erode_filter_5.Execute(dilate_filter_5.Execute(prev_slice))
                
                print("***")
                while True:
                    stat.Execute(prev_slice)
                    print(stat.GetNumberOfPixels(1))
                    if stat.GetNumberOfPixels(1) < 60:
                       break
                    temp_prev_slice = erode_filter.Execute(prev_slice)
                    if not np.any(temp_prev_slice):
                       break
                    prev_slice = temp_prev_slice

                # print("****")
                # stat.Execute(prev_slice)
                # print(stat.GetNumberOfPixels(1))
                # print("****")

                points = np.argwhere(sitk.GetArrayFromImage(prev_slice))

                points = [[int(pt[1]), int(pt[0]), 0] for pt in points]
                connected_filter.SetSeedList(points)
                

                erode_con = connected_filter.Execute(erode_slice) 

                filter.Execute(erode_slice, erode_con)

                if filter.GetSimilarityIndex() > 0.1:
                    # original_slice = erode_slice
                    original_erode_slice = erode_slice
                    for i in range(l):
                        # Iteratively erode
                        erode_slice = erode_filter.Execute(erode_slice)
                        erode_con = connected_filter.Execute(erode_slice)

                        # if(slice_idx == 200):
                          # sitk.WriteImage(erode_con, 'Z:/work2/manske/temp/seedpointfix/connected_{}_{}.nii'.format(i, slice_idx))
                          # sitk.WriteImage(erode_slice, 'Z:/work2/manske/temp/seedpointfix/slice_eroded_{}_{}.nii'.format(i, slice_idx))
                    
                        # check if disconnected
                        stat.Execute(erode_con)
                        if stat.GetNumberOfLabels() == 0:
                            break

                        filter.Execute(original_erode_slice, erode_con)
                        print(filter.GetSimilarityIndex())
                        
                        # break if disconnected
                        if (filter.GetSimilarityIndex() < 0.1):
                            x = i+1
                            break
                    
                    # Dilate back to original size
                    for i in range(x):
                        erode_con = dilate_filter.Execute(erode_con)
                
                # append to 3d stack
                if plane == 0:
                    comb_erosion[slice_idx, :, :] = erode_con
                elif plane == 1:
                    comb_erosion[:, slice_idx, :] = erode_con
                else:
                    comb_erosion[:, :, slice_idx] = erode_con

            for slice_idx in range(point[plane]-1, 0, -1):
                print(slice_idx+1)
                erode_slice = 0

                if plane == 0:
                    erode_slice = erode_img[slice_idx, :, :]
                    prev_slice = comb_erosion[slice_idx+1, :, :]
                    stat.Execute(prev_slice)

                elif plane == 1:
                    erode_slice = erode_img[:, slice_idx, :]
                    prev_slice = comb_erosion[:, slice_idx+1, :]
                    stat.Execute(prev_slice)

                else:
                    erode_slice = erode_img[:, :, slice_idx]
                    prev_slice = comb_erosion[:, :, slice_idx+1]
                    stat.Execute(prev_slice)

                if stat.GetNumberOfLabels() == 0:
                    break
                
                # deflate_times = int(np.sqrt(np.sqrt(stat.GetNumberOfPixels(1)))/2)
                # print("hi")
                # print(deflate_times)
                prev_slice = erode_filter_5.Execute(dilate_filter_5.Execute(prev_slice))
                
                while True:
                    stat.Execute(prev_slice)
                    if stat.GetNumberOfPixels(1) < 60:
                       break
                    temp_prev_slice = erode_filter.Execute(prev_slice)
                    if not np.any(temp_prev_slice):
                       break
                    prev_slice = temp_prev_slice


                
                print("****")
                stat.Execute(prev_slice)
                print(stat.GetNumberOfPixels(1))
                print("****")
                # sitk.WriteImage(prev_slice, 'Z:/work2/manske/temp/seedpointfix/init_con_{}.nii'.format(slice_idx))

                points = np.argwhere(sitk.GetArrayFromImage(prev_slice))

                points = [[int(pt[1]), int(pt[0]), 0] for pt in points]
                connected_filter.SetSeedList(points)

                erode_con = connected_filter.Execute(erode_slice)

                # if(slice_idx == 183):
                #     sitk.WriteImage(erode_con, 'Z:/work2/manske/temp/seedpointfix/init_con_{}.nii'.format(slice_idx))
                #     sitk.WriteImage(erode_slice, 'Z:/work2/manske/temp/seedpointfix/slice_init_{}.nii'.format(slice_idx))
                
                filter.Execute(erode_slice, erode_con)
                
                print(filter.GetSimilarityIndex())
                if filter.GetSimilarityIndex() > 0.1:
                    original_erode_slice = erode_slice
                    for i in range(l):
                        # Iteratively erode
                        erode_slice = erode_filter.Execute(erode_slice)
                        erode_con = connected_filter.Execute(erode_slice)

                        # if(slice_idx == 181):
                        #     sitk.WriteImage(erode_con, 'Z:/work2/manske/temp/seedpointfix/connected_{}_{}.nii'.format(i, slice_idx))
                        #     sitk.WriteImage(erode_slice, 'Z:/work2/manske/temp/seedpointfix/slice_eroded_{}_{}.nii'.format(i, slice_idx))
                        
                        # check if disconnected
                        stat.Execute(erode_con)
                        if stat.GetNumberOfLabels() == 0:
                            break

                        filter.Execute(original_erode_slice, erode_con)
                        print(filter.GetSimilarityIndex())
                        
                        # break if disconnected
                        if (filter.GetSimilarityIndex() < 0.1):
                            x = i+1
                            break
                    
                    # Dilate back to original size
                    for i in range(x):
                        erode_con = dilate_filter.Execute(erode_con)
                # if(slice_idx == 181):
                #     # sitk.WriteImage(erode_slice, 'Z:/work2/manske/temp/seedpointfix/dilated_{}.nii'.format(slice_idx))
                
                # append to 3d stack
                if plane == 0:
                    comb_erosion[slice_idx, :, :] = erode_con
                elif plane == 1:
                    comb_erosion[:, slice_idx, :] = erode_con
                else:
                    comb_erosion[:, :, slice_idx] = erode_con

        # sitk.WriteImage(comb_erosion, 'Z:/work2/manske/temp/seedpointfix/comb.nii')

        distance_filter = sitk.SignedMaurerDistanceMapImageFilter()
        distance_filter.SetInsideIsPositive(True)
        distance_filter.SetUseImageSpacing(False)
        distance_filter.SetBackgroundValue(0)
        distance_img = distance_filter.Execute(comb_erosion)
        # sitk.WriteImage(distance_img, 'Z:/work2/manske/temp/seedpointfix/distance.nii')
        distance_img.SetSpacing([1,1,1])
        feature_img = sitk.Cast(sitk.Mask(img, mask_img), sitk.sitkFloat32)
        # sitk.WriteImage(feature_img, 'Z:/work2/manske/temp/seedpointfix/feature.nii')
        feature_img.SetSpacing([1,1,1])

        print("Applying level set filter")
        ls_filter = sitk.ThresholdSegmentationLevelSetImageFilter()
        ls_filter.SetLowerThreshold(-9999)
        ls_filter.SetUpperThreshold(1.5)
        ls_filter.SetMaximumRMSError(0.02)
        ls_filter.SetNumberOfIterations(1000)
        ls_filter.SetCurvatureScaling(1)
        ls_filter.SetPropagationScaling(1)
        ls_filter.SetReverseExpansionDirection(True)
        ls_img = ls_filter.Execute(distance_img, feature_img)

        ls_img.SetSpacing(img.GetSpacing())
        # sitk.WriteImage(ls_img, 'Z:/work2/manske/temp/seedpointfix/levelset.nii')

        output_img = ls_img>-4
        output_img = (output_img * tmp_mask_img) | comb_erosion
        # sitk.WriteImage(output_img, 'Z:/work2/manske/temp/seedpointfix/out.nii')
        
        stat.Execute(output_img)
        num_voxel = stat.GetNumberOfPixels(1)
        print(num_voxel)

        final_img = final_img + output_img * int(id+1)
        print("Erosion {} found!".format(int(id+1)))
        success = True
    
    if success:
      tempLabelMap = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", 
                                                      "TemporaryErosionNode")
      tempLabelMap.CreateDefaultDisplayNodes()
      tempLabelMap.GetDisplayNode().SetAndObserveColorNodeID(
        'vtkMRMLColorTableNodeFileGenericColors.txt')
      tempLabelMap.GetDisplayNode()
      # push result to temporary label map
      sitkUtils.PushVolumeToSlicer(final_img, tempLabelMap)
      # push erosions from temporary label map to output erosion node
      self._logic.labelmapToSegmentationNode(tempLabelMap, outputVolumeNode)
      # remove temporary label map
      slicer.mrmlScene.RemoveNode(tempLabelMap)

      error_message = ""
      error_flag = None

      # update widgets
      erosion_id = outputVolumeNode.GetName()[0]
      erosion_id = '_'.join(erosion_id)
    
      # update widgets
      self.outputErosionSelector.setCurrentNodeID("") # reset the output volume selector
      self.segmentEditor.setSegmentationNode(outputVolumeNode)
      self.segmentEditor.setMasterVolumeNode(inputVolumeNode)
      self.segmentEditor.checkEraseButtons()

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

  

  def onGetStatsButton(self):
    """Run this whenever the get statistics button in step 6 is clicked"""
    inputErosionNode = self.inputErosionSelector.currentNode()
    masterVolumeNode = self.masterVolumeSelector.currentNode()
    outputTableNode = self.outputTableSelector.currentNode()
    currentMarkupsData = self.markupsTableWidget.getCurrentMarkupsData()
    voxelSize = self.voxelSizeText.value
    self._logic.getStatistics(inputErosionNode,
                              masterVolumeNode,
                              currentMarkupsData,
                              voxelSize,
                              outputTableNode)

    # update widgets
    self.segmentEditor.setSegmentationNode(inputErosionNode)
    self.segmentEditor.setMasterVolumeNode(masterVolumeNode)

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

class ErosionVolumeTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_ErosionVolume()

  def test_ErosionVolume(self):
    '''
    Automatic Mask Tests: Runs the cortical break detection function on 3 sample images
    and compares the results to pre-generated masks and manually placed seed points

    Test Requires:

      mha files: 'SAMPLE_MHA1.mha', 'SAMPLE_MHA2.mha', 'SAMPLE_MHA3.mha'
      Mask masks: 'SAMPLE_MASK1.mha', 'SAMPLE_MASK2.mha', 'SAMPLE_MASK3.mha'
      seed lists: 'SAMPLE_SEEDS1.json', 'SAMPLE_SEEDS2.json', 'SAMPLE_SEEDS3.json'
      comparison segmentations: 'SAMPLE_ER1.seg.nrrd', 'SAMPLE_ER2.seg.nrrd', 'SAMPLE_ER3.seg.nrrd'
    
    Success Conditions:
      1. Erosion segmentation is successfully generated
      2. Number of segmentations is correct
      3. Each segmetation differs by less than 2% from the corresponding comparison
      4. Volume and Surface area are less than 0.5% from comparison values
    '''
    from ErosionVolumeLib.ErosionVolumeLogic import ErosionVolumeLogic
    from Testing.ErosionVolumeTestLogic import ErosionVolumeTestLogic

    self.delayDisplay("Starting the test")
    #
    # first, get some data
    #
    
    # setup logic
    logic = ErosionVolumeLogic()
    testLogic = ErosionVolumeTestLogic()
    scene = slicer.mrmlScene

    # run 3 tests
    passed = True
    for i in range(1, 4):
      index = str(i)
      print('\n*----------------------Test ' + index + '----------------------*')

      # get input files
      masterVolume = testLogic.newNode(scene, filename='SAMPLE_MHA' + index + '.mha', name='testMasterVolume' + index)
      maskVolume = testLogic.newNode(scene, filename='SAMPLE_MASK' + index + '.mha', name='testMaskVolume' + index, type='labelmap', display=False)
      seedsList = testLogic.newNode(scene, filename='SAMPLE_SEEDS' + index + '.json', name='testSeedsList' + index, type='fiducial')


      # setup volumes
      outputVolume = testLogic.newNode(scene, name='testOutputVolume' + index, type='segmentation')
      if i == 3:
        logic.setErosionParameters(masterVolume, maskVolume, 1, seedsList, 6, 6, lower=530, upper=4000)
      else:
        logic.setErosionParameters(masterVolume, maskVolume, 1, seedsList, 3, 4, lower=530, upper=4000)
      self.assertTrue(logic.getErosions(masterVolume, maskVolume, outputVolume, noProgress=True), 'Erosion volume operation failed')
      table = testLogic.newNode(scene, name='testTable' + index, type='table')
      logic.getStatistics(outputVolume, masterVolume, 0.0607, table)
      
      # check outputs against sample file
      if not testLogic.verifyErosion(outputVolume, i):
        self.delayDisplay('Output segments are incorrect for test ' + index, msec = 300)
        passed = False
      if not testLogic.verifyTale(table, i):
        self.delayDisplay('Statistics table is incorrect for test ' + index, msec = 300)
        passed = False

      self.delayDisplay('Test ' + index + ' complete')

    #Failure message
    self.assertTrue(passed, 'Incorrect results, check testing log')