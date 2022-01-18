#-----------------------------------------------------
# CorticalBreakDetection.py
#
# Created by:  Mingjie Zhao
# Created on:  23-07-2021
#
# Description: This module sets up the interface for the Cortical Break Detection 3D Slicer extension.
#
#-----------------------------------------------------
from cgi import test
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
from CorticalBreakDetectionLib.CorticalBreakDetectionLogic import CorticalBreakDetectionLogic
from CorticalBreakDetectionLib.MarkupsTable import MarkupsTable

#
# CorticalBreakDetection
#
class CorticalBreakDetection(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Cortical Break Detection"
    self.parent.categories = ["Bone"]
    self.parent.dependencies = []  # TODO: add here list of module names that this module requires
    self.parent.contributors = ["Mingjie Zhao and Ryan Yan"]
    # TODO: update with short description of the module and a link to online module documentation
    self.parent.helpText = """
Updated on August 22, 2021.
This module inplements the automatic Cortical Break Detection method by Michel Peters et al. Workflow:
1. Preprocess/binarize the bone. 2. Take the preprocessed image and the mask, identify Cortical Breaks 
and underlying trabecular bone loss using Peters et al's algorithm. The Cortical Break Detection masks will be 
converted to seed points. Note that trabecular bone loss on CBCT will be segmented using a different 
algorithm (i.e. level set) from the original algorithm. 3. Manually add or remove seed points.
"""
    # TODO: replace with organization, grant and thanks
    self.parent.acknowledgementText = """
Updated on August 22, 2021.
""" # Additional initialization step after application startup is complete

#
# CorticalBreakDetectionWidget
#

class CorticalBreakDetectionWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent=None):
    """
    Called when the user opens the module the first time and the widget is initialized.
    """
    # Initialize logics object
    self._logic = CorticalBreakDetectionLogic()
    # initialize call back object for updating progrss bar
    self._logic.progressCallBack = self.setProgress2

    ScriptedLoadableModuleWidget.__init__(self, parent)

  def setup(self):
    """
    Called when the user opens the module the first time and the widget is initialized.
    """
    # Buttons for testing
    ScriptedLoadableModuleWidget.setup(self)

    # Collapsible button
    self.CorticalBreakDetectionCollapsibleButton = ctk.ctkCollapsibleButton()
    self.seedPointsCollapsibleButton = ctk.ctkCollapsibleButton()

    # Set up widgets inside the collapsible buttons
    self.setupCorticalBreakDetection()
    self.setupSeedPoints()

    # Add vertical spacer
    self.layout.addStretch(1)

    # Update buttons
    self.onSelect1()
    self.onSelectInputVolume()
    self.onSelect2()
    self.onSelectMask()

  def setupCorticalBreakDetection(self):
    """Set up widgets for automatic Cortical Break Detection"""
    # Set text on collapsible button, and add collapsible button to layout
    self.CorticalBreakDetectionCollapsibleButton.text = "Cortical Break Detection"
    self.layout.addWidget(self.CorticalBreakDetectionCollapsibleButton)
    
    # Layout within the collapsible button
    CorticalBreakDetectionLayout = qt.QFormLayout(self.CorticalBreakDetectionCollapsibleButton)
    CorticalBreakDetectionLayout.setVerticalSpacing(5)

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
    self.inputVolumeSelector.setCurrentNode(None)
    CorticalBreakDetectionLayout.addRow("Input Volume: ", self.inputVolumeSelector)

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
    self.outputVolumeSelector.setCurrentNode(None)
    CorticalBreakDetectionLayout.addRow("Output Volume: ", self.outputVolumeSelector)

    # threshold spin boxes (default unit is HU)
    self.lowerThresholdText = qt.QSpinBox()
    self.lowerThresholdText.setMinimum(-9999)
    self.lowerThresholdText.setMaximum(999999)
    self.lowerThresholdText.setSingleStep(10)
    self.lowerThresholdText.value = 686
    CorticalBreakDetectionLayout.addRow("Lower Threshold [HU]: ", self.lowerThresholdText)
    self.upperThresholdText = qt.QSpinBox()
    self.upperThresholdText.setMinimum(-9999)
    self.upperThresholdText.setMaximum(999999)
    self.upperThresholdText.setSingleStep(10)
    self.upperThresholdText.value = 4000
    CorticalBreakDetectionLayout.addRow("Upper Threshold [HU]: ", self.upperThresholdText)

    # gaussian sigma spin box
    self.sigmaText = qt.QDoubleSpinBox()
    self.sigmaText.setMinimum(0.0001)
    self.sigmaText.setDecimals(4)
    self.sigmaText.value = 0.8
    self.sigmaText.setToolTip("Standard deviation in the Gaussian smoothing filter")
    CorticalBreakDetectionLayout.addRow("Gaussian Sigma: ", self.sigmaText)

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
    CorticalBreakDetectionLayout.addRow(erosionButtonFrame)

    # master volume Selector
    self.masterVolumeSelector = slicer.qMRMLNodeComboBox()
    self.masterVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.masterVolumeSelector.selectNodeUponCreation = False
    self.masterVolumeSelector.addEnabled = False
    self.masterVolumeSelector.removeEnabled = True
    self.masterVolumeSelector.renameEnabled = True
    self.masterVolumeSelector.noneEnabled = False
    self.masterVolumeSelector.showHidden = False
    self.masterVolumeSelector.showChildNodeTypes = False
    self.masterVolumeSelector.setMRMLScene(slicer.mrmlScene)
    self.masterVolumeSelector.setToolTip( "Select the greyscale image" )
    self.masterVolumeSelector.setCurrentNode(None)
    CorticalBreakDetectionLayout.addRow("Input Volume: ", self.masterVolumeSelector)

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
    self.inputBoneSelector.setCurrentNode(None)
    CorticalBreakDetectionLayout.addRow("Preprocessed Volume: ", self.inputBoneSelector)

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
    self.maskSelector.setCurrentNode(None)
    CorticalBreakDetectionLayout.addRow("Contour: ", self.maskSelector)

    # output Cortical Breaks selector
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
    self.outputCorticalBreaksSelector.setToolTip( "Select the node to store the Cortical Breaks in" )
    self.outputCorticalBreaksSelector.setCurrentNode(None)
    CorticalBreakDetectionLayout.addRow("Output Cortical Breaks: ", self.outputCorticalBreaksSelector)

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
    self.outputFiducialSelector.setCurrentNode(None)
    CorticalBreakDetectionLayout.addRow("Output Seed Points: ", self.outputFiducialSelector)

    # cortical thickness spin box
    self.corticalThicknessText = qt.QSpinBox()
    self.corticalThicknessText.setMinimum(1)
    self.corticalThicknessText.setMaximum(99)
    self.corticalThicknessText.setSingleStep(1)
    self.corticalThicknessText.setSuffix(' voxels')
    self.corticalThicknessText.value = 4
    CorticalBreakDetectionLayout.addRow("Cortical Thickness: ", self.corticalThicknessText)

    # dilate erode distance spin box
    self.dilateErodeDistanceText = qt.QSpinBox()
    self.dilateErodeDistanceText.setMinimum(0)
    self.dilateErodeDistanceText.setMaximum(99)
    self.dilateErodeDistanceText.setSingleStep(1)
    self.dilateErodeDistanceText.setSuffix(' voxels')
    self.dilateErodeDistanceText.value = 1
    CorticalBreakDetectionLayout.addRow("Dilate/Erode Distance: ", self.dilateErodeDistanceText)

    # voxel size spin box
    self.voxelSizeText = qt.QDoubleSpinBox()
    self.voxelSizeText.setMinimum(0)
    self.voxelSizeText.setSuffix(' mm')
    self.voxelSizeText.setDecimals(4)
    self.voxelSizeText.value = 0.082
    self.voxelSizeText.setToolTip("Voxel size of the greyscale scan in millimetres")
    CorticalBreakDetectionLayout.addRow("Voxel Size: ", self.voxelSizeText)

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
    CorticalBreakDetectionLayout.addRow(ctTypeFrame)

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
    self.getCorticalBreaksButton.toolTip = "Apply the automatic Cortical Break Detection algorithm"
    self.getCorticalBreaksButton.enabled = False
    executeGridLayout2.addWidget(self.getCorticalBreaksButton, 1, 0)

    # Execution frame with progress bar and preprocess button
    erosionButtonFrame2 = qt.QFrame()
    erosionButtonFrame2.setLayout(executeGridLayout2)
    CorticalBreakDetectionLayout.addRow(erosionButtonFrame2)

    # conmections
    self.CorticalBreakDetectionCollapsibleButton.connect("contentsCollapsed(bool)", self.onCollapsed1)
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
    self.getCorticalBreaksButton.connect("clicked(bool)", self.ongetCorticalBreaksButton)    

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

    # seed point file save button
    self.seedSaveFile = qt.QFileDialog()
    self.seedSaveFile.setNameFilter("*.csv")
    self.seedExportButton = qt.QPushButton("Export")
    self.seedExportButton.enabled = False
    seedPointsLayout.addRow("", self.seedExportButton)
    

    # connection
    self.seedPointsCollapsibleButton.connect("contentsCollapsed(bool)", self.onCollapsed2)
    self.fiducialSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelectSeed)
    self.seedExportButton.clicked.connect(self.onExportSelect)

    # logger
    self.logger = logging.getLogger("cortical_break_detection")

  def enter(self):
    """
    Called each time the user opens this module.
    """

  def exit(self):
    """
    Called each time the user opens a different module.
    """

  def onCollapsed1(self):
    """Run this whenever the Cortical Break Detection collapsible button is clicked"""
    if not self.CorticalBreakDetectionCollapsibleButton.collapsed:
      self.seedPointsCollapsibleButton.collapsed = True

  def onCollapsed2(self):
    """Run this whenever the seed points collapsible button is clicked"""
    if not self.seedPointsCollapsibleButton.collapsed:
      self.CorticalBreakDetectionCollapsibleButton.collapsed = True

  def onSelect1(self):
    """Run this whenever the selectors in the preprocess step changes state."""
    self.preprocessButton.enabled = (self.inputVolumeSelector.currentNode() and
                                     self.outputVolumeSelector.currentNode())
  
  def onSelect2(self):
    """Run this whenever the selectors in the Cortical Break Detection detection step changes state."""
    self.getCorticalBreaksButton.enabled = (self.masterVolumeSelector.currentNode() and
                                            self.inputBoneSelector.currentNode() and
                                            self.outputCorticalBreaksSelector.currentNode())

  def onSelectSeed(self):
    """Run this whenever the seed point selected in the seed point step changes state."""
    self.markupsTableWidget.setCurrentNode(self.fiducialSelector.currentNode())
    self.seedExportButton.enabled = self.fiducialSelector.currentNode()

  def onSelectInputVolume(self):
    """Run this whenever an input volume is selected."""
    inputVolumeNode = self.inputVolumeSelector.currentNode()

    if inputVolumeNode:
      self.masterVolumeSelector.setCurrentNodeID(inputVolumeNode.GetID())
      self.outputVolumeSelector.baseName = (inputVolumeNode.GetName()+"_SEG")

      # create default output node if none selected
      if not self.outputVolumeSelector.currentNode():
        self.outputVolumeSelector.addNode()
      # Update the default save directory
      self._logic.setDefaultDirectory(inputVolumeNode)

      # Update the spacing scale in the seed point table
      ras2ijk = vtk.vtkMatrix4x4()
      ijk2ras = vtk.vtkMatrix4x4()
      inputVolumeNode.GetRASToIJKMatrix(ras2ijk)
      inputVolumeNode.GetIJKToRASMatrix(ijk2ras)
      self.markupsTableWidget.setCoordsMatrices(ras2ijk, ijk2ras)

      #remove existing loggers
      if self.logger.hasHandlers():
        for handler in self.logger.handlers:
          self.logger.removeHandler(handler)
      #initialize logger with filename
      filename = inputVolumeNode.GetStorageNode().GetFullNameFromFileName()
      logHandler = logging.FileHandler(filename[:filename.rfind('.')] + '.log')
      
      self.logger.addHandler(logHandler)
      self.logger.info("Using Cortical Break Detection Module with " + inputVolumeNode.GetName() + "\n")

  def onSelectMask(self):
    """Run this whenever a periosteal contour/mask is selected."""
    maskNode = self.maskSelector.currentNode()

    if maskNode:
      self.outputCorticalBreaksSelector.baseName = (maskNode.GetName()+"_BREAKS")
      self.outputFiducialSelector.baseName = (maskNode.GetName()+"_SEEDS")
      # create default nodes if none selected
      if not self.outputCorticalBreaksSelector.currentNode():
        self.outputCorticalBreaksSelector.addNode()
      if not self.outputFiducialSelector.currentNode():
        self.outputFiducialSelector.addNode()

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
    """Run this whenever the get Cortical Break Detection button is clicked."""
    # update widgets
    self.disablePreprocessWidgets()

    inputVolumeNode = self.inputVolumeSelector.currentNode()
    outputVolumeNode = self.outputVolumeSelector.currentNode()
    ready = self._logic.setPreprocessParameters(inputVolumeNode, 
                                                self.lowerThresholdText.value,
                                                self.upperThresholdText.value,
                                                self.sigmaText.value)

    #logging
    self.logger.info("Preprocessing initialized with paramaters:")
    self.logger.info("Input Volume: " + inputVolumeNode.GetName())
    self.logger.info("Output Volume: " + outputVolumeNode.GetName())
    self.logger.info("Lower Theshold: " + str(self.lowerThresholdText.value))
    self.logger.info("Upper Theshold: " + str(self.upperThresholdText.value))
    self.logger.info("Gaussian Sigma: " + str(self.sigmaText.value))

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

    self.logger.info("Finished\n")


  def ongetCorticalBreaksButton(self):
    """Run this whenever the preproecess button is clicked."""
    # update widgets
    self.disableCorticalBreaksWidgets()

    masterVolumeNode = self.masterVolumeSelector.currentNode()
    inputBoneNode = self.inputBoneSelector.currentNode()
    outputCorticalBreaksNode = self.outputCorticalBreaksSelector.currentNode()
    outputFiducialNode = self.outputFiducialSelector.currentNode()
    maskNode = self.maskSelector.currentNode()
    cbCT = self.cbCTButton.isChecked()

    #logging info
    self.logger.info("Cortical Break Detection initialized with paramaters:")
    self.logger.info("Master Volume: " + masterVolumeNode.GetName())
    self.logger.info("Input Mask: " + maskNode.GetName())
    self.logger.info("Output Mask: " + outputCorticalBreaksNode.GetName())
    self.logger.info("Output Seeds: " + outputFiducialNode.GetName())
    self.logger.info("Cortical Thickness: " + str(self.corticalThicknessText.value))
    self.logger.info("Dilate/Erode Distance: " + str(self.dilateErodeDistanceText.value))
    self.logger.info("Voxel Size: " + str(self.voxelSizeText.value))
    
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

    self.logger.info("Finished\n")
  
  def onExportSelect(self):
    import csv
    '''save list of seeds to .csv file'''
    filename = self.fiducialSelector.currentNode().GetName() + ".csv"

    # save file
    filename = self.seedSaveFile.getSaveFileName(self.seedExportButton, 'Save Seeds to .csv', filename, "CSV Files(*.csv)")
    print("Writing to " + filename)
    
    # write out seeds
    seeds_list = self.fiducialSelector.currentNode()
    with open(filename, 'w', newline='') as f:
      writer = csv.writer(f)
      writer.writerow(['Label', 'X', 'Y', 'Z'])
      controlPointPosition = [0, 0, 0]
      for i in range(seeds_list.GetNumberOfFiducials()):
        seeds_list.GetNthControlPointPosition(i, controlPointPosition)
        ITKCoord = self.markupsTableWidget._logic.RASToIJKCoords(
                  controlPointPosition, self.markupsTableWidget._ras2ijk)
        writer.writerow([seeds_list.GetNthControlPointLabel(i)] + ITKCoord)

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
    """Enable widgets for Cortical Break Detection."""
    self.progressBar2.hide()

  def disableCorticalBreaksWidgets(self):
    """Disable widgets for Cortical Break Detection."""
    self.getCorticalBreaksButton.enabled = False
    self.progressBar2.show()

class CorticalBreakDetectionTest(ScriptedLoadableModuleTest):
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
    self.test_CortBreakQuick()

  def test_CortBreakQuick(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests sould exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """
    from Testing.CorticalBreakDetectionTestLogic import CorticalBreakDetectionTestLogic
    from CorticalBreakDetectionLib.CorticalBreakDetectionLogic import CorticalBreakDetectionLogic

    self.delayDisplay("Starting the test")
    #
    # first, get some data
    #

    # setup logic
    logic = CorticalBreakDetectionLogic()
    testLogic = CorticalBreakDetectionTestLogic()
    scene = slicer.mrmlScene
    
    # setup input file
    inputVolume = testLogic.newNode(scene, filename='\\SAMPLE_MHA.mha', name='testInputVolume')

    # check preprocessing
    processVolume = testLogic.newNode(scene, name='testProcessVolume', type='labelmap')
    logic.setPreprocessParameters(inputVolume, 686, 4000, 0.8)
    self.assertTrue(logic.preprocess(processVolume), 'Preprocessing Failed')
    
    # check cortical break detection
    maskVolume = testLogic.newNode(scene, filename='\\SAMPLE_MASK.mha', name='testMaskVolume', type='labelmap', display=False)
    outputVolume = testLogic.newNode(scene, name='testOutputNode', type='labelmap')
    logic.setCorticalBreaksParameters(686, 4000, inputVolume, processVolume, maskVolume, outputVolume, 4, 1, 0.0820, False)
    self.assertTrue(logic.getCorticalBreaks(outputVolume, noProgress=True))
    
    self.delayDisplay('Test passed!')