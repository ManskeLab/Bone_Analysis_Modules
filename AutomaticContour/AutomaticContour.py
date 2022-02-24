#-----------------------------------------------------
# AutomaticContour.py
#
# Created by:  Mingjie Zhao
# Created on:  20-10-2020
#
# Description: This module sets up the Automatic Contour 3D Slicer extension.
#
#-----------------------------------------------------
from sre_constants import SUCCESS
import vtk, qt, ctk, slicer
import sitkUtils
import numpy as np
from slicer.ScriptedLoadableModule import *
import logging
from AutomaticContourLib.AutomaticContourLogic import AutomaticContourLogic
from AutomaticContourLib.SegmentEditor import SegmentEditor

#
# AutomaticContour
#
class AutomaticContour(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Automatic Contour" # TODO make this more human readable by adding spaces
    self.parent.categories = ["Bone"]
    self.parent.dependencies = []
    self.parent.contributors = ["Mingjie Zhao"] # replace with "Firstname Lastname (Organization)"
    self.parent.helpText = """
Updated on January 27, 2022.
This module contains steps 1-3 of erosion analysis. 
Step 1 is to manually separate the bones by covering each bone with a different label. 
Step 2 is to perform automatic contouring on the greyscale image and generate a 
label map volume of the contour. 
Step 3 is to manually correct the contour. 
If a contour already exists and needs to be corrected, load it to slicer as a label map volume,
and jump to Step 3. 
"""
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = """
Updated on January 27, 2022.
""" # replace with organization, grant and thanks.

#
# AutomaticContourWidget
#
class AutomaticContourWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    # Initialize logics object
    self._logic = AutomaticContourLogic()
    self._logic.progressCallBack = self.setProgress

    ScriptedLoadableModuleWidget.__init__(self, parent)

  def setup(self):
    # Buttons for testing
    ScriptedLoadableModuleWidget.setup(self)

    # Collapsible buttons
    self.boneSeparationCollapsibleButton = ctk.ctkCollapsibleButton()
    self.automaticContourCollapsibleButton = ctk.ctkCollapsibleButton()
    self.manualCorrectionCollapsibleButton = ctk.ctkCollapsibleButton()

    # Set up widgets inside the collapsible buttons
    self.setupBoneSeparation()
    self.setupAutomaticContour()
    self.setupManualCorrection()

    # Add vertical spacer
    self.layout.addStretch(1)

    # Update buttons
    self.onSelect1()
    self.onSelect2()
    self.onSelect3()
    self.onSelectInputVolume()

  def setupBoneSeparation(self):
    """Set up widgets in step 1 bone separation"""
    # set text on collapsible button, and add collapsible button to layout
    self.boneSeparationCollapsibleButton.text = "Step 1 - Rough Mask"
    self.boneSeparationCollapsibleButton.collapsed = True
    self.layout.addWidget(self.boneSeparationCollapsibleButton)

    # layout within the collapsible button
    boneSeparationLayout = qt.QVBoxLayout(self.boneSeparationCollapsibleButton)

    # instructions
    boneSeparationLayout.addWidget(qt.QLabel("This step is only necessary if the bones are close to each other."))
    boneSeparationLayout.addWidget(qt.QLabel("Create a rough mask for each bone to assist contouring."))
    boneSeparationLayout.addWidget(qt.QLabel("")) # horizontal space

    # layout for input and output selectors
    selectorFormLayout = qt.QFormLayout()
    selectorFormLayout.setContentsMargins(0, 0, 0, 0)

    # master volume selector
    self.separateInputSelector = slicer.qMRMLNodeComboBox()
    self.separateInputSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.separateInputSelector.selectNodeUponCreation = False
    self.separateInputSelector.addEnabled = False
    self.separateInputSelector.removeEnabled = False
    self.separateInputSelector.noneEnabled = False
    self.separateInputSelector.showHidden = False
    self.separateInputSelector.showChildNodeTypes = False
    self.separateInputSelector.setMRMLScene(slicer.mrmlScene)
    self.separateInputSelector.setToolTip("Select the input scan")
    selectorFormLayout.addRow("Input Volume: ", self.separateInputSelector)

    # frame with selectors
    selectorFrame = qt.QFrame()
    selectorFrame.setLayout(selectorFormLayout)
    boneSeparationLayout.addWidget(selectorFrame)

    # layout for initialize and apply buttons
    initApplyGridLayout = qt.QGridLayout()
    initApplyGridLayout.setContentsMargins(0, 5, 0, 5)

    # initialize button
    self.initButton1 = qt.QPushButton("Initialize")
    self.initButton1.toolTip = "Initialize the parameters in segmentation editor for manual correction"
    self.initButton1.enabled = False
    initApplyGridLayout.addWidget(self.initButton1, 0, 0)

    # cancel button
    self.cancelButton1 = qt.QPushButton("Cancel")
    self.cancelButton1.toolTip = "Discard the manual correction"
    self.cancelButton1.enabled = False
    initApplyGridLayout.addWidget(self.cancelButton1, 0, 1)

    # apply button
    self.applyButton1 = qt.QPushButton("Apply")
    self.applyButton1.toolTip = "Apply the manual correction to the contour"
    self.applyButton1.enabled = False
    initApplyGridLayout.addWidget(self.applyButton1, 0, 2)

    # frame with initialize and apply buttons
    initApplyFrame = qt.QFrame()
    initApplyFrame.setLayout(initApplyGridLayout)
    boneSeparationLayout.addWidget(initApplyFrame)

    # segmentation editor
    self.segmentEditor = SegmentEditor(boneSeparationLayout)

    self.boneSeparationCollapsibleButton.connect('contentsCollapsed(bool)', self.onCollapsed1)
    self.initButton1.connect('clicked(bool)', self.onInitButton1)
    self.cancelButton1.connect('clicked(bool)', self.onCancelButton1)
    self.applyButton1.connect('clicked(bool)', self.onApplyButton1)
    self.separateInputSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect1)

  def setupAutomaticContour(self):
    """Set up widgets in step 2 automatic contour"""
    # set text on collapsible button, and add collapsible button to layout
    self.automaticContourCollapsibleButton.text = "Step 2 - Automatic Contour"
    self.layout.addWidget(self.automaticContourCollapsibleButton)

    # layout within the collapsible button
    automaticContourLayout = qt.QFormLayout(self.automaticContourCollapsibleButton)
    automaticContourLayout.setVerticalSpacing(5)

    # input volume selector
    self.inputVolumeSelector = slicer.qMRMLNodeComboBox()
    self.inputVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.inputVolumeSelector.selectNodeUponCreation = False
    self.inputVolumeSelector.addEnabled = False
    self.inputVolumeSelector.removeEnabled = True
    self.inputVolumeSelector.renameEnabled = True
    self.inputVolumeSelector.noneEnabled = False
    self.inputVolumeSelector.showHidden = False
    self.inputVolumeSelector.showChildNodeTypes = False
    self.inputVolumeSelector.setMRMLScene( slicer.mrmlScene )
    self.inputVolumeSelector.setToolTip("Select the input volume to get the contour from")
    self.inputVolumeSelector.setCurrentNode(None)
    automaticContourLayout.addRow("Input Volume: ", self.inputVolumeSelector)

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
    self.outputVolumeSelector.setMRMLScene( slicer.mrmlScene )
    self.outputVolumeSelector.baseName = "MASK"
    self.outputVolumeSelector.setToolTip( "Select the output volume to store the contour" )
    self.outputVolumeSelector.setCurrentNode(None)
    automaticContourLayout.addRow("Output Contour: ", self.outputVolumeSelector)

    # threshold spin boxes (default unit is HU)
    self.lowerThresholdText = qt.QSpinBox()
    self.lowerThresholdText.setMinimum(-9999)
    self.lowerThresholdText.setMaximum(999999)
    self.lowerThresholdText.setSingleStep(10)
    self.lowerThresholdText.value = 900
    automaticContourLayout.addRow("Lower Threshold: ", self.lowerThresholdText)
    self.upperThresholdText = qt.QSpinBox()
    self.upperThresholdText.setMinimum(-9999)
    self.upperThresholdText.setMaximum(999999)
    self.upperThresholdText.setSingleStep(10)
    self.upperThresholdText.value = 4000
    automaticContourLayout.addRow("Upper Threshold: ", self.upperThresholdText)

    # gaussian sigma spin box
    self.sigmaText = qt.QDoubleSpinBox()
    self.sigmaText.setMinimum(0.0001)
    self.sigmaText.setDecimals(4)
    self.sigmaText.value = 2
    self.sigmaText.setToolTip("Standard deviation in the Gaussian smoothing filter")
    automaticContourLayout.addRow("Gaussian Sigma: ", self.sigmaText)

    # bone number spin box
    self.boneNumSpinBox = qt.QSpinBox()
    self.boneNumSpinBox.setMinimum(1)
    self.boneNumSpinBox.setMaximum(9)
    self.boneNumSpinBox.setSingleStep(1)
    self.boneNumSpinBox.value = 1
    self.boneNumSpinBox.setToolTip("Enter the number of separate bone structures in the scan")
    automaticContourLayout.addRow("Number of Bones: ", self.boneNumSpinBox)

    #dilate/erode spin box
    self.dilateErodeRadiusText = qt.QSpinBox()
    self.dilateErodeRadiusText.setMinimum(1)
    self.dilateErodeRadiusText.setMaximum(9999)
    self.dilateErodeRadiusText.setSingleStep(1)
    self.dilateErodeRadiusText.value = 38
    self.dilateErodeRadiusText.setToolTip("Enter the dilate/erode kernel radius")
    automaticContourLayout.addRow("Dilate/Erode Radius [voxels]: ", self.dilateErodeRadiusText)
    
    # rough mask selector
    self.separateMapSelector = slicer.qMRMLNodeComboBox()
    self.separateMapSelector.nodeTypes = ["vtkMRMLLabelMapVolumeNode"]
    self.separateMapSelector.selectNodeUponCreation = False
    self.separateMapSelector.addEnabled = False
    self.separateMapSelector.removeEnabled = False
    self.separateMapSelector.renameEnabled = False
    self.separateMapSelector.noneEnabled = True
    self.separateMapSelector.showHidden = False
    self.separateMapSelector.showChildNodeTypes = False
    self.separateMapSelector.setMRMLScene( slicer.mrmlScene )
    self.separateMapSelector.setToolTip( "Select the rough mask from Step 1" )
    automaticContourLayout.addRow("Rough Mask(Optional): ", self.separateMapSelector)

    # Execution layout
    executeGridLayout = qt.QGridLayout()
    executeGridLayout.setRowMinimumHeight(0,20)
    executeGridLayout.setRowMinimumHeight(1,20)

    # Progress Bar
    self.progressBar = qt.QProgressBar()
    self.progressBar.hide()
    executeGridLayout.addWidget(self.progressBar, 0, 0)

    # Get Button
    self.getContourButton = qt.QPushButton("Get Contour")
    self.getContourButton.toolTip = "Get contour as a label map"
    self.getContourButton.enabled = False
    executeGridLayout.addWidget(self.getContourButton, 1, 0)

    # Execution frame with progress bar and get button
    executeFrame = qt.QFrame()
    executeFrame.setLayout(executeGridLayout)
    automaticContourLayout.addRow(executeFrame)

    # connections
    self.automaticContourCollapsibleButton.connect('contentsCollapsed(bool)', self.onCollapsed2)
    self.inputVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelectInputVolume)
    self.getContourButton.connect('clicked(bool)', self.onGetContour)
    self.inputVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect2)
    self.outputVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect2)

  def setupManualCorrection(self):
    """Set up widgets in step 3 manual correction"""
    # Set text on collapsible button, and add collapsible button to layout
    self.manualCorrectionCollapsibleButton.text = 'Step 3 - Manual Correction'
    self.manualCorrectionCollapsibleButton.collapsed = True
    self.layout.addWidget(self.manualCorrectionCollapsibleButton)

    # Layout within the collapsible button
    manualCorrectionLayout = qt.QVBoxLayout(self.manualCorrectionCollapsibleButton)

    # layout for input and output selectors
    selectorFormLayout = qt.QFormLayout()
    selectorFormLayout.setContentsMargins(0, 0, 0, 0)

    # contour selector
    self.contourVolumeSelector = slicer.qMRMLNodeComboBox()
    self.contourVolumeSelector.nodeTypes = ["vtkMRMLLabelMapVolumeNode"]
    self.contourVolumeSelector.selectNodeUponCreation = False
    self.contourVolumeSelector.addEnabled = False
    self.contourVolumeSelector.removeEnabled = False
    self.contourVolumeSelector.renameEnabled = False
    self.contourVolumeSelector.noneEnabled = False
    self.contourVolumeSelector.showHidden = False
    self.contourVolumeSelector.showChildNodeTypes = False
    self.contourVolumeSelector.setMRMLScene( slicer.mrmlScene )
    self.contourVolumeSelector.setToolTip( "Select the contour to be corrected" )
    selectorFormLayout.addRow("Contour to be Corrected: ", self.contourVolumeSelector)

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
    self.masterVolumeSelector.setToolTip("Select the scan associated with the contour")
    selectorFormLayout.addRow("Master Volume: ", self.masterVolumeSelector)

    # frame with selectors
    selectorFrame = qt.QFrame()
    selectorFrame.setLayout(selectorFormLayout)
    manualCorrectionLayout.addWidget(selectorFrame)

    # layout for initialize and apply buttons
    initApplyGridLayout = qt.QGridLayout()
    initApplyGridLayout.setContentsMargins(0, 5, 0, 5)

    # initialize button
    self.initButton3 = qt.QPushButton("Initialize")
    self.initButton3.toolTip = "Initialize the parameters in segmentation editor for manual correction"
    self.initButton3.enabled = False
    initApplyGridLayout.addWidget(self.initButton3, 0, 0)

    # cancel button
    self.cancelButton3 = qt.QPushButton("Cancel")
    self.cancelButton3.toolTip = "Discard the manual correction"
    self.cancelButton3.enabled = False
    initApplyGridLayout.addWidget(self.cancelButton3, 0, 1)

    # apply button
    self.applyButton3 = qt.QPushButton("Apply")
    self.applyButton3.toolTip = "Apply the manual correction to the contour"
    self.applyButton3.enabled = False
    initApplyGridLayout.addWidget(self.applyButton3, 0, 2)

    # frame with initialize and apply buttons
    initApplyFrame = qt.QFrame()
    initApplyFrame.setLayout(initApplyGridLayout)
    manualCorrectionLayout.addWidget(initApplyFrame)

    # segmentation editor
    self.segmentEditor = SegmentEditor(manualCorrectionLayout)

    # connections
    self.manualCorrectionCollapsibleButton.connect('contentsCollapsed(bool)', self.onCollapsed3)
    self.initButton3.connect('clicked(bool)', self.onInitButton3)
    self.applyButton3.connect('clicked(bool)', self.onApplyButton3)
    self.cancelButton3.connect('clicked(bool)', self.onCancelButton3)
    self.contourVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect3)
    self.masterVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect3)

    #logger
    self.logger = logging.getLogger("AutomaticContour")

  def onCollapsed1(self):
    if not self.boneSeparationCollapsibleButton.collapsed:
      self.automaticContourCollapsibleButton.collapsed = True
      self.manualCorrectionCollapsibleButton.collapsed = True

  def onCollapsed2(self):
    if not self.automaticContourCollapsibleButton.collapsed:
      self.boneSeparationCollapsibleButton.collapsed = True
      self.manualCorrectionCollapsibleButton.collapsed = True

  def onCollapsed3(self):
    if not self.manualCorrectionCollapsibleButton.collapsed:
      self.boneSeparationCollapsibleButton.collapsed = True
      self.automaticContourCollapsibleButton.collapsed = True
  
  def enter(self):
    """Run this whenever the module is reopened"""
    success = self._logic.enterSegmentEditor(self.segmentEditor)

    if not success: # if enter segmentation editor is not successful, some nodes are missing
      self.disableBoneSeparationWidgets()
      self.disableManualCorrectionWidgets()
  
  def exit(self):
    """Run this whenever the module is closed"""
    self._logic.exitSegmentEditor(self.segmentEditor)
  
  def onSelect1(self):
    """Update the state of the initialize button whenever the selector in step 1 change"""
    self.initButton1.enabled = self.separateInputSelector.currentNode()

  def onSelect2(self):
    """Update the state of the get contour button whenever the selectors in step 2 change"""
    self.getContourButton.enabled = (self.inputVolumeSelector.currentNode() and 
                                     self.outputVolumeSelector.currentNode())
  
  def onSelect3(self):
    """Update the state of the initialize button whenever the selectors in step 3 change"""
    self.initButton3.enabled = (self.contourVolumeSelector.currentNode() and
                               self.masterVolumeSelector.currentNode())

  def onInitButton1(self):
    """Run this whenever the initialize button in step 1 is clicked"""
    separateInputNode = self.separateInputSelector.currentNode()

    success = self._logic.initRoughMask(self.segmentEditor, separateInputNode)

    if success:
      # update widgets
      self.enableBoneSeparationWidgets()

  def onCancelButton1(self):
    """Run this whenever the cancel button in step 1 is clicked"""
    if slicer.util.confirmOkCancelDisplay('Do you want to discard the segmentation?'):
      separateInputNode = self.separateInputSelector.currentNode()
      
      self._logic.cancelRoughMask(separateInputNode)

      # update widgets
      self.disableBoneSeparationWidgets()

  def onApplyButton1(self):
    """Run this whenever the apply button in step 1 is clicked"""
    # get the current nodes in the toolkit
    separateInputNode = self.separateInputSelector.currentNode()
    separateOutputName = slicer.mrmlScene.GenerateUniqueName(separateInputNode.GetName()+"_separated")
    separateOutputNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", separateOutputName)

    self._logic.applyRoughMask(separateInputNode, separateOutputNode)

    # update widgets
    if separateOutputNode:
      self.inputVolumeSelector.setCurrentNodeID(separateInputNode.GetID())
      self.separateMapSelector.setCurrentNodeID(separateOutputNode.GetID())
    self.disableBoneSeparationWidgets()

  def onSelectInputVolume(self):
    """Run this whenever the input volume selector in step 2 changes"""
    inputVolumeNode = self.inputVolumeSelector.currentNode()

    if inputVolumeNode:
      # update the default output base name
      self.outputVolumeSelector.baseName = (inputVolumeNode.GetName()+"_MASK")
      # Update the default save directory
      self._logic.setDefaultDirectory(inputVolumeNode)
      # update viewer windows
      slicer.util.setSliceViewerLayers(background=inputVolumeNode)
      slicer.util.resetSliceViews() # centre the volume in the viewer windows

      #check if preset intensity units exist
      check = True
      if "Lower" in inputVolumeNode.__dict__.keys():
        self.lowerThresholdText.setValue(inputVolumeNode.__dict__["Lower"])
        check = False
      if "Upper" in inputVolumeNode.__dict__.keys():
        self.upperThresholdText.setValue(inputVolumeNode.__dict__["Upper"])
        check = False

      #check intensity units and display warning if not in HU
      if check:
        if not self._logic.intenstyCheck(inputVolumeNode):
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
      except:
        filename = 'share\\' + inputVolumeNode.GetName() + '.'
      finally:
        filename = 'share/' + inputVolumeNode.GetName() + '.'
      logHandler = logging.FileHandler(filename[:filename.rfind('.')] + '_LOG.log')
      self.logger.addHandler(logHandler)
      self.logger.info("Using Automatic Contour Module with " + inputVolumeNode.GetName() + "\n")

    else:
      self.outputVolumeSelector.baseName = "MASK"

  def onGetContour(self):
    """Run this whenever the get contour button in step 2 is clicked"""
    # update widgets
    self.disableAutomaticContourWidgets()

    inputVolumeNode = self.inputVolumeSelector.currentNode()
    outputVolumeNode = self.outputVolumeSelector.currentNode()
    separateMapNode = self.separateMapSelector.currentNode()

    # log info
    self.logger.info("Automatic Contour initialized with parameters:")
    self.logger.info("Input Volume: " + inputVolumeNode.GetName())
    self.logger.info("Output Volume: " + outputVolumeNode.GetName())
    if separateMapNode:
      self.logger.info("Rough Mask: " + separateMapNode.GetName())
    self.logger.info("Lower Threshold: " + str(self.lowerThresholdText.value))
    self.logger.info("Upper Threshold: " + str(self.upperThresholdText.value))
    self.logger.info("Gaussian Sigma: " + str(self.sigmaText.value))
    self.logger.info("Number of Bones: " + str(self.boneNumSpinBox.value))
    self.logger.info("Dilate/Erode Radius: " + str(self.dilateErodeRadiusText.value))

    ready = self._logic.setParameters(inputVolumeNode, 
                                     outputVolumeNode,
                                     self.lowerThresholdText.value,
                                     self.upperThresholdText.value,
                                     self.sigmaText.value,
                                     self.boneNumSpinBox.value,
                                     self.dilateErodeRadiusText.value,
                                     separateMapNode)
    if ready:
      # run the algorithm
      success = self._logic.getContour(inputVolumeNode, outputVolumeNode)
      if success:
        # update widgets
        self.contourVolumeSelector.setCurrentNodeID(self.outputVolumeSelector.currentNodeID)
        self.masterVolumeSelector.setCurrentNodeID(self.inputVolumeSelector.currentNodeID)
        self.outputVolumeSelector.setCurrentNodeID("") # reset the output volume selector
    # update widgets
    self.enableAutomaticContourWidgets()

    # store thresholds 
    inputVolumeNode.__dict__["Lower"] = self.lowerThresholdText.value
    inputVolumeNode.__dict__["Upper"] = self.upperThresholdText.value
    self.logger.info("Finished\n")
  
  def onInitButton3(self):
    """Run this whenever the initialize button in step 3 is clicked"""
    contourVolumeNode = self.contourVolumeSelector.currentNode()
    masterVolumeNode = self.masterVolumeSelector.currentNode()
    
    success = self._logic.initManualCorrection(self.segmentEditor, 
                                              contourVolumeNode, 
                                              masterVolumeNode)
    
    if success:
      self.enableManualCorrectionWidgets()

  def onCancelButton3(self):
    """Run this whenever the cancel button in step 3 is clicked"""
    if slicer.util.confirmOkCancelDisplay('Do you want to discard the manual correction?'):
      contourVolumeNode = self.contourVolumeSelector.currentNode()
      masterVolumeNode = self.masterVolumeSelector.currentNode()
      
      self._logic.cancelManualCorrection(contourVolumeNode, masterVolumeNode)

      self.disableManualCorrectionWidgets()

  def onApplyButton3(self):
    """Run this whenever the apply button in step 3 is clicked"""
    contourVolumeNode = self.contourVolumeSelector.currentNode()
    masterVolumeNode = self.masterVolumeSelector.currentNode()

    self._logic.applyManualCorrection(contourVolumeNode, masterVolumeNode)

    self.disableManualCorrectionWidgets()

  def enableBoneSeparationWidgets(self):
    """Enable widgets in the bone separation layout in step 1"""
    self.initButton1.enabled = False
    self.cancelButton1.enabled = True
    self.applyButton1.enabled = True
    self.separateInputSelector.enabled = False
    self.initButton3.enabled = False
    self.contourVolumeSelector.enabled = False
    self.masterVolumeSelector.enabled = False
  
  def disableBoneSeparationWidgets(self):
    """Disable widgets in the bone separation layout in step 1"""
    self.onSelect1()
    self.cancelButton1.enabled = False
    self.applyButton1.enabled = False
    self.separateInputSelector.enabled = True
    self.onSelect3()
    self.contourVolumeSelector.enabled = True
    self.masterVolumeSelector.enabled = True

  def enableAutomaticContourWidgets(self):
    """Enable widgets in the automatic contouring layout in step 2"""
    self.onSelect2()
    self.progressBar.hide()

  def disableAutomaticContourWidgets(self):
    """Disable widgets in the automatic contouring layout in step 2"""
    self.getContourButton.enabled = False
    self.progressBar.show()

  def enableManualCorrectionWidgets(self):
    """Enable widgets in the manual correction layout in step 3"""
    self.initButton1.enabled = False
    self.separateInputSelector.enabled = False
    self.initButton3.enabled = False
    self.cancelButton3.enabled = True
    self.applyButton3.enabled = True
    self.contourVolumeSelector.enabled = False
    self.masterVolumeSelector.enabled = False

  def disableManualCorrectionWidgets(self):
    """Disable widgets in the manual correction layout in step 3"""
    self.onSelect1()
    self.separateInputSelector.enabled = True
    self.onSelect3()
    self.cancelButton3.enabled = False
    self.applyButton3.enabled = False
    self.contourVolumeSelector.enabled = True
    self.masterVolumeSelector.enabled = True

  def setProgress(self, value):
    """Update the progress bar"""
    self.progressBar.setValue(value)

class AutomaticContourTest(ScriptedLoadableModuleTest):
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
    self.test_AutoContour()

  def test_AutoContour(self):
    '''
    Automatic Contour Tests: Runs the contour function on 3 sample images and compares the results to masks generated in IPL

    Test Requires:

      mha files: 'SAMPLE_MHA1.mha', 'SAMPLE_MHA2.mha', 'SAMPLE_MHA3.mha'
      comparison masks: 'SAMPLE_MASK1.mha', 'SAMPLE_MASK2.mha', 'SAMPLE_MASK3.mha'
    
    Success Conditions:
      1. Contour mask is successfully generated
      2. Output contour mask differs by less than 2% from the comparison mask
    '''
    from Testing.AutomaticContourTestLogic import AutomaticContourTestLogic
    from AutomaticContourLib.AutomaticContourLogic import AutomaticContourLogic

    self.delayDisplay("Starting the test")
    #
    # first, get some data
    #
    
    # get test file
    
    # setup logic
    logic = AutomaticContourLogic()
    testLogic = AutomaticContourTestLogic()
    
    scene = slicer.mrmlScene

    # run 3 tests
    passed = True
    for i in range(1, 4):
      index = str(i)
      print('\n*----------------------Test ' + index + '----------------------*')

      # setup input volume
      inputVolume = testLogic.newNode(scene, filename='SAMPLE_MHA' + index + '.mha', name='testInputVolume' + index)

      # generate mask with default settings
      outputVolume = testLogic.newNode(scene, name='testOutputVolume' + index, type='labelmap')
      logic.setParameters(inputVolume, outputVolume, 686, 4000, 2, 1, 38, None)
      self.assertTrue(logic.getContour(inputVolume, outputVolume, noProgress=True), "Contour operation failed")

      # verify mask with comparison
      if not testLogic.verifyMask(outputVolume, i):
        self.delayDisplay('Output mask is incorrect', msec = 300)
        passed = False
        continue

      self.delayDisplay('Test ' + index + ' complete')
    
    # failure message
    self.assertTrue(passed, 'Incorrect results, check testing log')
      
    return SUCCESS