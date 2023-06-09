#-----------------------------------------------------
# ImageRegistration.py
#
# Created by:  Ryan Yan
# Created on:  24-01-2022
#
# Description: This module sets up the interface for the Image Registration 3D Slicer extension.
#
#-----------------------------------------------------
import os, unittest, logging
from __main__ import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
from ImageRegistrationLib.ImageRegistrationLogic import ImageRegistrationLogic
from ImageRegistrationLib.MarkupsTable import MarkupsTable
import sitkUtils

#
# ImageRegistration
#

class ImageRegistration(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Image Registration" # TODO make this more human readable by adding spaces
    self.parent.categories = ["Bone Analysis Module (BAM)"]
    self.parent.dependencies = []
    self.parent.contributors = ["Ryan Yan"] # replace with "Firstname Lastname (Organization)"
    self.parent.helpText = """
    Perform longitudinal image registration on a baseline and follow-up image. 
This proccess applies a transform to an image that will minimize the difference between the image 
based on a selected similarity metric. Can be used for unimodal or multi-modal images. <br>
Additionally, visualization tools are included for judging the quality of a registration. 
Grayscale subtraction, 3d visualization, and checkerboard views are available.
    """
    self.parent.helpText += "<br>For more information see the <a href=https://github.com/ManskeLab/3DSlicer_Erosion_Analysis/wiki/Image-Registration-Module>online documentation</a>."
    self.parent.helpText += "<br><td><img src=\"" + self.getLogo('bam') + "\" height=80> "
    self.parent.helpText += "<img src=\"" + self.getLogo('manske') + "\" height=80></td>"
    self.parent.acknowledgementText = """
    Updated on February 28, 2022 <br>
    Manske Lab <br>
    McCaig Institute for Bone and Joint Health <br>
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
# ImageRegistrationWidget
#

class ImageRegistrationWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """
  def __init__(self, parent):
    # Initialize logics object
    self.logic = ImageRegistrationLogic()
    # initialize call back object for updating progrss bar
    self.logic.progressCallBack = self.setProgress

    ScriptedLoadableModuleWidget.__init__(self, parent)

  def setup(self) -> None:
    '''Setup Registration widget'''
    ScriptedLoadableModuleWidget.setup(self)
    # Instantiate and connect widgets ...

    
    self.registrationCollapsibleButton = ctk.ctkCollapsibleButton()
    self.registrationCollapsibleButton.text = "Register Images"
    self.borderCollapsibleButton = ctk.ctkCollapsibleButton()
    self.borderCollapsibleButton.text = "Contour Border View"
    self.subtractionCollapsibleButton = ctk.ctkCollapsibleButton()
    self.subtractionCollapsibleButton.text = "Subtraction View"
    self.checkerboardCollapsibleButton = ctk.ctkCollapsibleButton()
    self.checkerboardCollapsibleButton.text = "Checkerboard View"

    # Setup collapsibles
    self.setupRegistration()
    self.setupContourBorderView()
    self.setupSubtractionView()
    self.setupCheckerboard()

    # Add vertical spacer
    self.layout.addStretch(1)

  
  # Register Image -----------------------------------------------------------*
  
  def setupRegistration(self) -> None:
    # Layout within the dummy collapsible button
    registerFormLayout = qt.QFormLayout(self.registrationCollapsibleButton)
    registerFormLayout.setVerticalSpacing(5)
    self.layout.addWidget(self.registrationCollapsibleButton)

    # master volume selector
    self.backgroundInputSelector = slicer.qMRMLNodeComboBox()
    self.backgroundInputSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.backgroundInputSelector.selectNodeUponCreation = False
    self.backgroundInputSelector.addEnabled = False
    self.backgroundInputSelector.removeEnabled = False
    self.backgroundInputSelector.noneEnabled = False
    self.backgroundInputSelector.showHidden = False
    self.backgroundInputSelector.showChildNodeTypes = False
    self.backgroundInputSelector.setMRMLScene(slicer.mrmlScene)
    self.backgroundInputSelector.setToolTip("Select the input scan")
    registerFormLayout.addRow("Background Volume: ", self.backgroundInputSelector)

    #
    # First input volume selector
    #
    self.inputSelector1 = slicer.qMRMLNodeComboBox()
    self.inputSelector1.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.inputSelector1.selectNodeUponCreation = True
    self.inputSelector1.addEnabled = False
    self.inputSelector1.removeEnabled = False
    self.inputSelector1.noneEnabled = False
    self.inputSelector1.showHidden = False
    self.inputSelector1.showChildNodeTypes = False
    self.inputSelector1.setMRMLScene( slicer.mrmlScene )
    self.inputSelector1.setToolTip( "Select the baseline image" )
    self.inputSelector1.setCurrentNode(None)
    registerFormLayout.addRow("Baseline (fixed): ", self.inputSelector1)

    #
    # Second input volume selector
    #
    self.inputSelector2 = slicer.qMRMLNodeComboBox()
    self.inputSelector2.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.inputSelector2.selectNodeUponCreation = True
    self.inputSelector2.addEnabled = False
    self.inputSelector2.removeEnabled = False
    self.inputSelector2.noneEnabled = False
    self.inputSelector2.showHidden = False
    self.inputSelector2.showChildNodeTypes = False
    self.inputSelector2.setMRMLScene( slicer.mrmlScene )
    self.inputSelector2.setToolTip( "Select the follow-up image" )
    self.inputSelector2.setCurrentNode(None)
    registerFormLayout.addRow("Follow-up (moving): ", self.inputSelector2)

    # 
    # bone selector
    # 
    self.boneSelector = qt.QComboBox()
    self.boneSelector.addItems(['Metacarpal', 'Phalanx'])
    self.boneSelector.setEnabled(True)
    self.boneSelector.currentTextChanged(self.boneChanged())
    registerFormLayout.addRow("Bone: ", self.boneSelector)
    self.maskedBone = self.boneSelector.currentText

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
    self.fiducialSelector.setCurrentNode(None)
    registerFormLayout.addRow("Seed Points: ", self.fiducialSelector)

    # seed point table
    self.markupsTableWidget = MarkupsTable(self.registrationCollapsibleButton)
    self.markupsTableWidget.setMRMLScene(slicer.mrmlScene)
    self.markupsTableWidget.setNodeSelectorVisible(False) # use the above selector instead
    self.markupsTableWidget.setButtonsVisible(False)
    self.markupsTableWidget.setPlaceButtonVisible(True)
    self.markupsTableWidget.setDeleteAllButtonVisible(True)
    self.markupsTableWidget.setJumpToSliceEnabled(True)

    #
    # Registration similarity metric selector
    #
    self.metricSelector = qt.QComboBox()
    self.metricSelector.addItems(['Mean Squares', 'Correlation', 'Mattes Mutual Information', 'ANTS Neighborhood Correlation'])
    registerFormLayout.addRow("Similarity Metric: ", self.metricSelector)

    # Help button for similarity metrics
    self.helpButton = qt.QPushButton("Help")
    self.helpButton.toolTip = "Description of each image similarity metric"
    self.helpButton.setFixedSize(50, 20)
    registerFormLayout.addRow("", self.helpButton)

    # sampling percentage
    self.samplingText = qt.QDoubleSpinBox()
    self.samplingText.setRange(0.0001, 1)
    self.samplingText.setDecimals(4)
    self.samplingText.value = 0.01
    self.samplingText.setSingleStep(0.01)
    self.samplingText.setToolTip("Standard deviation in the Gaussian smoothing filter")
    registerFormLayout.addRow("Metric Sampling Percentage: ", self.samplingText)

    #
    # Registration optimizer selector
    #
    self.optimizerSelector = qt.QComboBox()
    self.optimizerSelector.addItems(['Amoeba', 'Exhaustive', 'Powell', '1 + 1 Evolutionary', 
                                    'Gradient Descent', 'Gradient Descent Line Search', 'Regular Step Gradient Descent', 'L-BFGS'])
    self.optimizerSelector.setCurrentIndex(4)
    registerFormLayout.addRow("Similarity Metric: ", self.optimizerSelector)

    #
    # Output volume selector
    #
    self.regstrationOutputSelector = slicer.qMRMLNodeComboBox()
    self.regstrationOutputSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.regstrationOutputSelector.selectNodeUponCreation = True
    self.regstrationOutputSelector.addEnabled = True
    self.regstrationOutputSelector.renameEnabled = True
    self.regstrationOutputSelector.removeEnabled = True
    self.regstrationOutputSelector.noneEnabled = False
    self.regstrationOutputSelector.showHidden = False
    self.regstrationOutputSelector.showChildNodeTypes = False
    self.regstrationOutputSelector.setMRMLScene( slicer.mrmlScene )
    self.regstrationOutputSelector.setToolTip( "Select the output image" )
    self.regstrationOutputSelector.setCurrentNode(None)
    self.regstrationOutputSelector.baseName = 'REG'
    registerFormLayout.addRow("Output: ", self.regstrationOutputSelector)

    #
    # Output transform selector
    #
    self.transformSelector = slicer.qMRMLNodeComboBox()
    self.transformSelector.nodeTypes = ["vtkMRMLTransformNode"]
    self.transformSelector.selectNodeUponCreation = True
    self.transformSelector.addEnabled = True
    self.transformSelector.renameEnabled = True
    self.transformSelector.removeEnabled = True
    self.transformSelector.noneEnabled = True
    self.transformSelector.showHidden = False
    self.transformSelector.showChildNodeTypes = False
    self.transformSelector.setMRMLScene( slicer.mrmlScene )
    self.transformSelector.setToolTip( "Select the output transform" )
    self.transformSelector.setCurrentNode(None)
    self.transformSelector.baseName = 'TRF'
    registerFormLayout.addRow("Transform (optional): ", self.transformSelector)

    #
    # Apply Button
    #
    self.applyButton = qt.QPushButton("Apply")
    self.applyButton.toolTip = "Register the follow-up image."
    self.applyButton.enabled = False
    registerFormLayout.addRow(self.applyButton)

    # Progress Bar
    self.progressBar = qt.QProgressBar()
    self.progressBar.hide()
    registerFormLayout.addRow(self.progressBar)

    # connections
    self.helpButton.clicked.connect(self.onHelpButton)
    self.applyButton.clicked.connect(self.onApplyButton)
    
    self.backgroundInputSelector.currentNodeChanged.connect(self.onSelect)
    self.inputSelector1.currentNodeChanged.connect(self.onSelect)
    self.inputSelector2.currentNodeChanged.connect(self.onSelect)
    self.fiducialSelector.currentNodeChanged.connect(self.onSelectSeed)
    self.regstrationOutputSelector.currentNodeChanged.connect(self.onSelect)

    self.registrationCollapsibleButton.contentsCollapsed.connect(self.onCollapseRegister)

    # logger
    self.logger = logging.getLogger("image_registration")

  # Visualize Registration -----------------------------------------------------------*
  def setupContourBorderView(self):
    '''Setup Contours' Border View'''
    self.borderCollapsibleButton.collapsed = True
    self.layout.addWidget(self.borderCollapsibleButton)

    # Layout within the dummy collapsible button
    borderFormLayout = qt.QFormLayout(self.borderCollapsibleButton)
    borderFormLayout.setVerticalSpacing(5)

    #
    # First input volume selector
    #
    self.borderSelector1 = slicer.qMRMLNodeComboBox()
    self.borderSelector1.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.borderSelector1.selectNodeUponCreation = True
    self.borderSelector1.addEnabled = False
    self.borderSelector1.removeEnabled = False
    self.borderSelector1.noneEnabled = False
    self.borderSelector1.showHidden = False
    self.borderSelector1.showChildNodeTypes = False
    self.borderSelector1.setMRMLScene( slicer.mrmlScene )
    self.borderSelector1.setToolTip( "Select the baseline image" )
    self.borderSelector1.setCurrentNode(None)
    borderFormLayout.addRow("Baseline: ", self.borderSelector1)

    #
    # Second input volume selector
    #
    self.borderSelector2 = slicer.qMRMLNodeComboBox()
    self.borderSelector2.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.borderSelector2.selectNodeUponCreation = True
    self.borderSelector2.addEnabled = False
    self.borderSelector2.removeEnabled = False
    self.borderSelector2.noneEnabled = False
    self.borderSelector2.showHidden = False
    self.borderSelector2.showChildNodeTypes = False
    self.borderSelector2.setMRMLScene( slicer.mrmlScene )
    self.borderSelector2.setToolTip( "Select the follow-up image" )
    self.borderSelector2.setCurrentNode(None)
    borderFormLayout.addRow("Registered Follow-up: ", self.borderSelector2)

    # visualization type button layout
    borderTypeLayout = qt.QGridLayout()

    #
    # Output Segmenation selector
    #
    self.borderOutputSelector = slicer.qMRMLNodeComboBox()
    self.borderOutputSelector.nodeTypes = ["vtkMRMLSegmentationNode"]
    self.borderOutputSelector.selectNodeUponCreation = True
    self.borderOutputSelector.addEnabled = True
    self.borderOutputSelector.renameEnabled = True
    self.borderOutputSelector.removeEnabled = True
    self.borderOutputSelector.noneEnabled = False
    self.borderOutputSelector.showHidden = False
    self.borderOutputSelector.showChildNodeTypes = False
    self.borderOutputSelector.setMRMLScene( slicer.mrmlScene )
    self.borderOutputSelector.setToolTip( "Select the output segmenation" )
    self.borderOutputSelector.setCurrentNode(None)
    self.borderOutputSelector.baseName = ('BORDER')
    borderFormLayout.addRow("Output: ", self.borderOutputSelector)

    self.borderThreshButton = qt.QCheckBox()
    self.borderThreshButton.checked = True
    borderFormLayout.addRow("Use Automatic Thresholding", self.borderThreshButton)

    self.borderThreshSelector = qt.QComboBox()
    self.borderThreshSelector.addItems(['Otsu', 'Huang', 'Max Entropy', 'Moments', 'Yen'])
    borderFormLayout.addRow("Thresholding Method", self.borderThreshSelector)

    # Help button for thresholding methods
    self.borderHelpButton = qt.QPushButton("Help")
    self.borderHelpButton.toolTip = "Tips for selecting a thresholding method"
    self.borderHelpButton.setFixedSize(50, 20)
    borderFormLayout.addRow("", self.borderHelpButton)

    # threshold spin boxes (default unit is HU)
    self.borderLowerThresholdText = qt.QSpinBox()
    self.borderLowerThresholdText.setMinimum(-9999)
    self.borderLowerThresholdText.setMaximum(999999)
    self.borderLowerThresholdText.setSingleStep(10)
    self.borderLowerThresholdText.value = 500
    borderFormLayout.addRow("Lower Threshold: ", self.borderLowerThresholdText)
    self.borderUpperThresholdText = qt.QSpinBox()
    self.borderUpperThresholdText.setMinimum(-9999)
    self.borderUpperThresholdText.setMaximum(999999)
    self.borderUpperThresholdText.setSingleStep(10)
    self.borderUpperThresholdText.value = 4000
    borderFormLayout.addRow("Upper Threshold: ", self.borderUpperThresholdText)

    # gaussian sigma spin box
    self.borderSigmaText = qt.QDoubleSpinBox()
    self.borderSigmaText.setRange(0.0001, 10)
    self.borderSigmaText.setDecimals(4)
    self.borderSigmaText.value = 1
    self.borderSigmaText.setSingleStep(0.1)
    self.borderSigmaText.setToolTip("Standard deviation in the Gaussian smoothing filter")
    borderFormLayout.addRow("Gaussian Sigma: ", self.borderSigmaText)

    #
    # Visualize Button
    #
    self.borderVisualizeButton = qt.QPushButton("Visualize")
    self.borderVisualizeButton.toolTip = "Visualize contours of baseline and registered follow up image."
    self.borderVisualizeButton.enabled = False
    borderFormLayout.addRow(self.borderVisualizeButton)

    # Progress Bar
    self.progressBar2 = qt.QProgressBar()
    self.progressBar2.hide()
    borderFormLayout.addRow(self.progressBar2)

    # connections
    self.borderSelector1.currentNodeChanged.connect(self.onSelectBorder)
    self.borderSelector2.currentNodeChanged.connect(self.onSelectBorder)
    self.borderOutputSelector.currentNodeChanged.connect(self.onSelectBorder)
    self.borderHelpButton.clicked.connect(self.onThreshHelpButton)
    self.borderVisualizeButton.clicked.connect(self.onBorderVisualizeButton)
    self.borderThreshButton.clicked.connect(self.onAutoThreshBorder)

    self.borderCollapsibleButton.contentsCollapsed.connect(self.onCollapseBorder)

    self.onAutoThreshBorder

  def setupSubtractionView(self) -> None:
    '''Setup Subtraction View collapsible'''
    self.subtractionCollapsibleButton.collapsed = True
    self.layout.addWidget(self.subtractionCollapsibleButton)

    # Layout within the dummy collapsible button
    subtractionFormLayout = qt.QFormLayout(self.subtractionCollapsibleButton)
    subtractionFormLayout.setVerticalSpacing(5)

    #
    # First input volume selector
    #
    self.subtractionSelector1 = slicer.qMRMLNodeComboBox()
    self.subtractionSelector1.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.subtractionSelector1.selectNodeUponCreation = True
    self.subtractionSelector1.addEnabled = False
    self.subtractionSelector1.removeEnabled = False
    self.subtractionSelector1.noneEnabled = False
    self.subtractionSelector1.showHidden = False
    self.subtractionSelector1.showChildNodeTypes = False
    self.subtractionSelector1.setMRMLScene( slicer.mrmlScene )
    self.subtractionSelector1.setToolTip( "Select the baseline image" )
    self.subtractionSelector1.setCurrentNode(None)
    subtractionFormLayout.addRow("Baseline: ", self.subtractionSelector1)

    #
    # Second input volume selector
    #
    self.subtractionSelector2 = slicer.qMRMLNodeComboBox()
    self.subtractionSelector2.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.subtractionSelector2.selectNodeUponCreation = True
    self.subtractionSelector2.addEnabled = False
    self.subtractionSelector2.removeEnabled = False
    self.subtractionSelector2.noneEnabled = False
    self.subtractionSelector2.showHidden = False
    self.subtractionSelector2.showChildNodeTypes = False
    self.subtractionSelector2.setMRMLScene( slicer.mrmlScene )
    self.subtractionSelector2.setToolTip( "Select the follow-up image" )
    self.subtractionSelector2.setCurrentNode(None)
    subtractionFormLayout.addRow("Registered Follow-up: ", self.subtractionSelector2)

    # visualization type button layout
    subtractionTypeLayout = qt.QGridLayout()

    # visualization type buttons
    self.threeDButton = qt.QRadioButton("3D")
    self.threeDButton.setChecked(True)
    self.grayButton = qt.QRadioButton("Grayscale")
    self.grayButton.setChecked(False)
    subtractionTypeLayout.addWidget(self.threeDButton, 0, 0)
    subtractionTypeLayout.addWidget(self.grayButton, 0, 1)
    # visualization type button frame
    fileTypeFrame = qt.QFrame()
    fileTypeFrame.setLayout(subtractionTypeLayout)
    subtractionFormLayout.addRow("Output Format: ", fileTypeFrame)

    #
    # Output volume selector
    #
    self.subtractionOutputSelector = slicer.qMRMLNodeComboBox()
    self.subtractionOutputSelector.nodeTypes = ["vtkMRMLLabelMapVolumeNode"]
    self.subtractionOutputSelector.selectNodeUponCreation = True
    self.subtractionOutputSelector.addEnabled = True
    self.subtractionOutputSelector.renameEnabled = True
    self.subtractionOutputSelector.removeEnabled = True
    self.subtractionOutputSelector.noneEnabled = False
    self.subtractionOutputSelector.showHidden = False
    self.subtractionOutputSelector.showChildNodeTypes = False
    self.subtractionOutputSelector.setMRMLScene( slicer.mrmlScene )
    self.subtractionOutputSelector.setToolTip( "Select the output image" )
    self.subtractionOutputSelector.setCurrentNode(None)
    self.subtractionOutputSelector.baseName = ('SUBTRACTION')
    subtractionFormLayout.addRow("Output: ", self.subtractionOutputSelector)

    self.subtractionThreshButton = qt.QCheckBox()
    self.subtractionThreshButton.checked = True
    subtractionFormLayout.addRow("Use Automatic Thresholding", self.subtractionThreshButton)

    self.subtractionThreshSelector = qt.QComboBox()
    self.subtractionThreshSelector.addItems(['Otsu', 'Huang', 'Max Entropy', 'Moments', 'Yen'])
    subtractionFormLayout.addRow("Thresholding Method", self.subtractionThreshSelector)

    # Help button for thresholding methods
    self.subtractionHelpButton = qt.QPushButton("Help")
    self.subtractionHelpButton.toolTip = "Tips for selecting a thresholding method"
    self.subtractionHelpButton.setFixedSize(50, 20)
    subtractionFormLayout.addRow("", self.subtractionHelpButton)


    # threshold spin boxes (default unit is HU)
    self.subtractionLowerThresholdText = qt.QSpinBox()
    self.subtractionLowerThresholdText.setMinimum(-9999)
    self.subtractionLowerThresholdText.setMaximum(999999)
    self.subtractionLowerThresholdText.setSingleStep(10)
    self.subtractionLowerThresholdText.value = 500
    subtractionFormLayout.addRow("Lower Threshold: ", self.subtractionLowerThresholdText)
    self.subtractionUpperThresholdText = qt.QSpinBox()
    self.subtractionUpperThresholdText.setMinimum(-9999)
    self.subtractionUpperThresholdText.setMaximum(999999)
    self.subtractionUpperThresholdText.setSingleStep(10)
    self.subtractionUpperThresholdText.value = 4000
    subtractionFormLayout.addRow("Upper Threshold: ", self.subtractionUpperThresholdText)

    # gaussian sigma spin box
    self.subtractionSigmaText = qt.QDoubleSpinBox()
    self.subtractionSigmaText.setRange(0.0001, 10)
    self.subtractionSigmaText.setDecimals(4)
    self.subtractionSigmaText.value = 1
    self.subtractionSigmaText.setSingleStep(0.1)
    self.subtractionSigmaText.setToolTip("Standard deviation in the Gaussian smoothing filter")
    subtractionFormLayout.addRow("Gaussian Sigma: ", self.subtractionSigmaText)

    #store labels
    self.labels = [subtractionFormLayout.itemAt(i, 0) for i in range(4, 8)]

    #
    # Visualize Button
    #
    self.subtractionVisualizeButton = qt.QPushButton("Visualize")
    self.subtractionVisualizeButton.toolTip = "Visualize difference in images after registration."
    self.subtractionVisualizeButton.enabled = False
    subtractionFormLayout.addRow(self.subtractionVisualizeButton)

    # Progress Bar
    self.progressBar3 = qt.QProgressBar()
    self.progressBar3.hide()
    subtractionFormLayout.addRow(self.progressBar3)

    # connections
    self.subtractionSelector1.currentNodeChanged.connect(self.onSelectSubtraction)
    self.subtractionSelector2.currentNodeChanged.connect(self.onSelectSubtraction)
    self.subtractionOutputSelector.currentNodeChanged.connect(self.onSelectSubtraction)
    self.subtractionHelpButton.clicked.connect(self.onThreshHelpButton)
    self.threeDButton.clicked.connect(self.onSwitchMode)
    self.grayButton.clicked.connect(self.onSwitchMode)
    self.subtractionVisualizeButton.clicked.connect(self.onSubtractionVisualizeButton)
    self.subtractionThreshButton.clicked.connect(self.onAutoThreshSubtraction)

    self.subtractionCollapsibleButton.contentsCollapsed.connect(self.onCollapseSubtraction)

    self.onAutoThreshSubtraction
  
  def setupCheckerboard(self) -> None:
    self.checkerboardCollapsibleButton.collapsed = True
    self.layout.addWidget(self.checkerboardCollapsibleButton)

    checkerLayout = qt.QFormLayout(self.checkerboardCollapsibleButton)
    checkerLayout.setVerticalSpacing(5)

    #
    # First input volume selector
    #
    self.checkerSelector1 = slicer.qMRMLNodeComboBox()
    self.checkerSelector1.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.checkerSelector1.selectNodeUponCreation = True
    self.checkerSelector1.addEnabled = False
    self.checkerSelector1.removeEnabled = False
    self.checkerSelector1.noneEnabled = False
    self.checkerSelector1.showHidden = False
    self.checkerSelector1.showChildNodeTypes = False
    self.checkerSelector1.setMRMLScene( slicer.mrmlScene )
    self.checkerSelector1.setToolTip( "Select the baseline image" )
    self.checkerSelector1.setCurrentNode(None)
    checkerLayout.addRow("Baseline: ", self.checkerSelector1)

    #
    # Second input volume selector
    #
    self.checkerSelector2 = slicer.qMRMLNodeComboBox()
    self.checkerSelector2.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.checkerSelector2.selectNodeUponCreation = True
    self.checkerSelector2.addEnabled = False
    self.checkerSelector2.removeEnabled = False
    self.checkerSelector2.noneEnabled = False
    self.checkerSelector2.showHidden = False
    self.checkerSelector2.showChildNodeTypes = False
    self.checkerSelector2.setMRMLScene( slicer.mrmlScene )
    self.checkerSelector2.setToolTip( "Select the baseline image" )
    self.checkerSelector2.setCurrentNode(None)
    checkerLayout.addRow("Registered Follow-up: ", self.checkerSelector2)

    #
    # Output volume selector
    #
    self.checkerOutputSelector = slicer.qMRMLNodeComboBox()
    self.checkerOutputSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.checkerOutputSelector.selectNodeUponCreation = True
    self.checkerOutputSelector.addEnabled = True
    self.checkerOutputSelector.renameEnabled = True
    self.checkerOutputSelector.removeEnabled = True
    self.checkerOutputSelector.noneEnabled = False
    self.checkerOutputSelector.showHidden = False
    self.checkerOutputSelector.showChildNodeTypes = False
    self.checkerOutputSelector.setMRMLScene( slicer.mrmlScene )
    self.checkerOutputSelector.setToolTip( "Select the output image" )
    self.checkerOutputSelector.setCurrentNode(None) 
    self.checkerOutputSelector.baseName = ('CHECKERBOARD')
    checkerLayout.addRow("Output: ", self.checkerOutputSelector)

    # Checkerboard size
    self.checkerSizeText = qt.QSpinBox()
    self.checkerSizeText.setMinimum(1)
    self.checkerSizeText.setMaximum(25)
    self.checkerSizeText.setSingleStep(1)
    self.checkerSizeText.value = 10
    checkerLayout.addRow("Number of Cells: ", self.checkerSizeText)

    # check box for grid
    self.gridCheckBox = qt.QCheckBox('Show Checkerboard Grid')
    self.gridCheckBox.checked = False
    self.gridCheckBox.setToolTip('Display an overlay of a checkerboard grid. Recommended for unimodal images')
    checkerLayout.addRow(self.gridCheckBox)

    # grid collapsible box
    self.gridCollapsibleBox = ctk.ctkCollapsibleGroupBox()
    self.gridCollapsibleBox.collapsed = False
    self.gridCollapsibleBox.hide()
    checkerLayout.addRow(self.gridCollapsibleBox)

    gridCollapsibleLayout = qt.QGridLayout(self.gridCollapsibleBox)
    gridCollapsibleLayout.setColumnMinimumWidth(2, 15)

    #
    # Grid overlay selector
    #
    self.gridSelector = slicer.qMRMLNodeComboBox()
    self.gridSelector.nodeTypes = ["vtkMRMLLabelMapVolumeNode"]
    self.gridSelector.selectNodeUponCreation = True
    self.gridSelector.addEnabled = True
    self.gridSelector.renameEnabled = True
    self.gridSelector.removeEnabled = True
    self.gridSelector.noneEnabled = True
    self.gridSelector.showHidden = False
    self.gridSelector.showChildNodeTypes = False
    self.gridSelector.setMRMLScene( slicer.mrmlScene )
    self.gridSelector.setToolTip( "Select a volume to store the checkerboard grid overlay" )
    self.gridSelector.setCurrentNode(None)
    self.gridSelector.baseName = ('GRID')
    gridCollapsibleLayout.addWidget(qt.QLabel("Grid Overlay: "), 0, 0)
    gridCollapsibleLayout.addWidget(self.gridSelector, 0, 1)

    #
    # Checkerboard Button
    #
    self.checkerButton = qt.QPushButton("Create Checkerboard")
    self.checkerButton.toolTip = "Visualize difference in images after registration."
    self.checkerButton.enabled = False
    checkerLayout.addRow(self.checkerButton)

    # Progress Bar
    self.progressBar4 = qt.QProgressBar()
    self.progressBar4.hide()
    checkerLayout.addRow(self.progressBar4)

    # Connections
    self.checkerSelector1.currentNodeChanged.connect(self.onSelectChecker)
    self.checkerSelector2.currentNodeChanged.connect(self.onSelectChecker)
    self.checkerOutputSelector.currentNodeChanged.connect(self.onSelectChecker)

    self.gridCheckBox.clicked.connect(self.onGridChecked)
    self.checkerButton.clicked.connect(self.onCheckerVisualizeButton)

    self.checkerboardCollapsibleButton.contentsCollapsed.connect(self.onCollapseChecker)



  def cleanup(self):
    pass
  
  def onSelect(self) -> None:
    '''Node for registration is selected'''
    #get selected nodes
    background = self.backgroundInputSelector.currentNode()
    input1 = self.inputSelector1.currentNode()
    input2 = self.inputSelector2.currentNode()
    output = self.regstrationOutputSelector.currentNode()

    #enable register button if both nodes selected
    self.applyButton.enabled = input1 and input2 and output

    #auto-fill nodes in other collapsibles, set output basename
    if input1:
      self.borderSelector1.setCurrentNode(input1)
      self.subtractionSelector1.setCurrentNode(input1)
      self.checkerSelector1.setCurrentNode(input1)
    if input2:
      self.regstrationOutputSelector.baseName = input2.GetName() + '_REG'
      self.transformSelector.baseName = input2.GetName() + "_TRF"
    if output:
      self.borderSelector2.setCurrentNode(output)
      self.subtractionSelector2.setCurrentNode(output)
      self.checkerSelector2.setCurrentNode(output)

    slicer.util.resetSliceViews()
    slicer.util.setSliceViewerLayers(background=background)
    slicer.util.resetSliceViews()
    
    if input1 and input2 and not output:
      #remove existing loggers
      if self.logger.hasHandlers():
        for handler in self.logger.handlers:
          self.logger.removeHandler(handler)
          
       #initialize logger with filename
      try:
        filename = input1.GetStorageNode().GetFullNameFromFileName()
        filename = os.path.split(filename)[0] + '/LOG_' + os.path.split(filename)[1]
        filename = os.path.splitext(filename)[0] + '.log'
        print(filename)
      except:
        filename = 'share/' + input1.GetName() + '.'
      logHandler = logging.FileHandler(filename)
      
      self.logger.addHandler(logHandler)
      self.logger.info("Using Erosion Volume Module with " + input1.GetName() + " and " + input2.GetName() + "\n")

  def onSelectSeed(self):
    """Run this whenever the seed point selector in step 5 changes"""
    fiducialNode = self.fiducialSelector.currentNode()

    if fiducialNode:
      if(fiducialNode.GetName().split('_')[0] == 'separated'):
        # do nothing if the current node is already seperated
        return

    separatedFiducialNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode')
    
    controlPointPosition = [0,0,0]
    for i in range(fiducialNode.GetNumberOfControlPoints()):
      controlPointLabel = fiducialNode.GetNthControlPointLabel(i)

      boneId = controlPointLabel.split('_')[0]

      if(boneId == self.maskedBone):
        fiducialNode.GetNthControlPointPosition(i, controlPointPosition)
        separatedFiducialNode.AddFiducialFromArray(controlPointPosition, controlPointLabel)

    if separatedFiducialNode.GetNumberOfControlPoints() == 0:
      #TO DO CHECK IF NO Bone
      return

    separatedFiducialNode.SetName('separated_'+self.maskedBone+'_'+fiducialNode.GetName())
    self.fiducialSelector.addNode(separatedFiducialNode)
    
    self.fiducialSelector.setCurrentNodeID(separatedFiducialNode.GetID())
    self.markupsTableWidget.setCurrentNode(self.fiducialSelector.currentNode())

  def boneChanged(self):
    self.maskedBone = self.boneSelector.currentText

  def onHelpButton(self) -> None:
    '''Help button is pressed'''
    txt = """Registration Image Similarity Metrics\n
Mean Squares: Computes mean squared difference between pixel values. Requires intensity values to be within the same thresholds for images.\n
Correlation: Computes normal correlation between pixel values. Requires images in the same modality, but can be in any intensity range.\n
Mattes Mutual Information: Computes mutual information (ability to determine intensity of the second image based on the first). Can be used with multiple modalities.\n
ANTS Neighborhood: Computes correlation of a small neighbourhood for each pixel. Ideal for images that are very close.
          """
    slicer.util.infoDisplay(txt, 'Help: Similarity Metrics')
  
  def onApplyButton(self) -> None:
    '''Register button is pressed'''
    print("\nRunning Registration Algorithm")
    self.progressBar.show()

    #log parameters
    self.logger.info("Image registration initialized with parameters:")
    self.logger.info("Input Fixed Volume: " + self.inputSelector1.currentNode().GetName())
    self.logger.info("Input Moving Volume: " + self.inputSelector2.currentNode().GetName())
    self.logger.info("Output Volume: " + self.regstrationOutputSelector.currentNode().GetName())
    self.logger.info("Similarity Metric: " + self.metricSelector.currentText)
    self.logger.info("Metric Sampling Percentage: " + str(self.samplingText.value))
    self.logger.info("Optimizer: " + self.optimizerSelector.currentText)
    if self.transformSelector.currentNode():
      self.logger.info("Output Transform: " + self.transformSelector.currentNode().GetName())

    #set parameters and run registration
    self.logic.setParamaters(self.inputSelector1.currentNode(), 
                        self.inputSelector2.currentNode(),
                        self.samplingText.value)
    self.logic.setMetric(self.metricSelector.currentIndex)
    self.logic.setOptimizer(self.optimizerSelector.currentIndex)
    self.logic.run(self.regstrationOutputSelector.currentNode(), self.transformSelector.currentNode())

    voxelArray = slicer.util.arrayFromVolume(self.regstrationOutputSelector.currentNode())
    segmentNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentationNode')
    slicer.util.updateSegmentBinaryLabelmapFromArray(voxelArray, segmentNode, '0', self.backgroundInputSelector.currentNode())
    volumeLabelMapNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLabelMapVolumeNode')
    
    visibleSegmentIds = vtk.vtkStringArray()
    segmentNode.GetDisplayNode().GetVisibleSegmentIDs(visibleSegmentIds)

    slicer.vtkSlicerSegmentationsModuleLogic.ExportSegmentsToLabelmapNode(segmentNode,
                                                                          visibleSegmentIds,
                                                                          volumeLabelMapNode,
                                                                          self.backgroundInputSelector.currentNode())
    
    slicer.util.setSliceViewerLayers(background=self.backgroundInputSelector.currentNode(), 
                                     label=segmentNode)

    self.logger.info("Finished\n")
    self.progressBar.hide()

  def onSelectBorder(self) -> None:
    '''Output node for visualization is selected'''
    visual1 = self.borderSelector1.currentNode()
    visual2 = self.borderSelector2.currentNode()
    output = self.borderOutputSelector.currentNode()
    self.borderVisualizeButton.enabled = (visual1 and visual2 and output)
    if visual1:
      self.borderOutputSelector.baseName = visual1.GetName() + '_CONTOUR_SEGMENTATION'  
  
  def onSelectSubtraction(self) -> None:
    '''Output node for visualization is selected'''
    visual1 = self.subtractionSelector1.currentNode()
    visual2 = self.subtractionSelector2.currentNode()
    output = self.subtractionOutputSelector.currentNode()
    self.subtractionVisualizeButton.enabled = (visual1 and visual2 and output)
    if visual1:
      self.subtractionOutputSelector.baseName = visual1.GetName() + '_SUBTRACTION'

  def onSwitchMode(self) -> None:
    '''Mode changed between 3d and grayscale'''
    if self.threeDButton.checked:
      self.SubtractionOutputSelector.nodeTypes = ["vtkMRMLLabelMapVolumeNode"]

      #show options
      self.subtractionLowerThresholdText.show()
      self.subtractionUpperThresholdText.show()
      self.subtractionSigmaText.value = 1
      for label in self.labels:
        label.widget().show()

    elif self.grayButton.checked:
      self.SubtractionOutputSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]

      #hide options
      self.subtractionLowerThresholdText.hide()
      self.subtractionUpperThresholdText.hide()
      self.subtractionSigmaText.value = 0.5
      for label in self.labels:
        label.widget().hide()
    
  def onAutoThreshBorder(self):
    # enable/disable widgets depending on auto threshold checkbox in border contour collapsible
    use_auto = self.borderThreshButton.checked
    self.borderLowerThresholdText.setEnabled(not use_auto)
    self.borderUpperThresholdText.setEnabled(not use_auto)
    self.borderThreshSelector.setEnabled(use_auto)

  def onAutoThreshSubtraction(self):
    # enable/disable widgets depending on auto threshold checkbox in subtraction collapsible
    use_auto = self.subtractionThreshButton.checked
    self.subtractionLowerThresholdText.setEnabled(not use_auto)
    self.subtractionUpperThresholdText.setEnabled(not use_auto)
    self.subtractionThreshSelector.setEnabled(use_auto)

  def onThreshHelpButton(self) -> None:
    '''Help button is pressed'''
    txt = """Thresholding Methods\n
For images that only contain bone and soft tissue (no completely dark regions), use the 'Otsu', 'Huang', or 'Moments' Thresholds. \n
For images with completely dark regions, use the 'Max Entropy' or 'Yen' Thresholds.
          """
    slicer.util.infoDisplay(txt, 'Help: Similarity Metrics')

  def onBorderVisualizeButton(self) -> None:
    '''Contour Border Visualize button is pressed'''

    print('\nCreating Border Contour Image')
    self.progressBar2.show()

    # set parameters
    if self.borderThreshButton.checked:
      self.logic.setBorderVisualizeParameters(self.borderSelector1.currentNode(), 
                                self.borderSelector2.currentNode(),
                                self.borderSigmaText.value,
                                method=self.borderThreshSelector.currentIndex)
    else:
      self.logic.setBorderVisualizeParameters(self.borderSelector1.currentNode(), 
                                self.borderSelector2.currentNode(),
                                self.borderSigmaText.value,
                                lower=self.borderLowerThresholdText.value,
                                upper=self.borderUpperThresholdText.value)

    #get output
    baseContour, regContour = self.logic.borderVisualize()

    outputNode = self.borderOutputSelector.currentNode()
    slicer.mrmlScene.AddNode(outputNode)
    outputNode.CreateDefaultDisplayNodes()
    outputNode.SetReferenceImageGeometryParameterFromVolumeNode(self.borderSelector1.currentNode())
    segmentation = outputNode.GetSegmentation()
    segmentation.AddEmptySegment('0')
    segmentation.AddEmptySegment('1')

    segmentLabelMapNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", "baseContour")
    sitkUtils.PushVolumeToSlicer(baseContour, segmentLabelMapNode)
    voxelArray = slicer.util.arrayFromVolume(segmentLabelMapNode)
    slicer.util.updateSegmentBinaryLabelmapFromArray(voxelArray, outputNode, '0', self.borderSelector1.currentNode())

    segmentLabelMapNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", "registeredContour")
    sitkUtils.PushVolumeToSlicer(regContour, segmentLabelMapNode)
    voxelArray = slicer.util.arrayFromVolume(segmentLabelMapNode)
    slicer.util.updateSegmentBinaryLabelmapFromArray(voxelArray, outputNode, '1', self.borderSelector1.currentNode())

    slicer.util.setSliceViewerLayers(label=outputNode)

    self.progressBar2.hide()

  def onSubtractionVisualizeButton(self) -> None:
    '''Visualize button is pressed'''

    print('\nCreating Subtraction Image')
    self.progressBar3.show()

    # set parameters
    if self.subtractionThreshButton.checked:
      self.logic.setVisualizeParameters(self.subtractionSelector1.currentNode(), 
                                self.subtractionSelector2.currentNode(),
                                self.subtractionSigmaText.value,
                                method=self.subtractionThreshSelector.currentIndex)
    else:
      self.logic.setVisualizeParameters(self.subtractionSelector1.currentNode(), 
                                self.subtractionSelector2.currentNode(),
                                self.subtractionSigmaText.value,
                                lower=self.subtractionLowerThresholdText.value,
                                upper=self.subtractionUpperThresholdText.value)

    #get output
    outnode = self.subtractionOutputSelector.currentNode()

    #3D visualization
    if self.threeDButton.checked:
      self.logic.visualize(outnode)

      print("Displaying volume rendering of " + outnode.GetName())
      volRenLogic = slicer.modules.volumerendering.logic()
      displayNode = volRenLogic.CreateDefaultVolumeRenderingNodes(outnode)
      displayNode.SetVisibility(True)

    #grayscale visualization
    elif self.grayButton.checked:
      self.logic.subtractGray(outnode)

    self.progressBar3.hide()
  
  def onSelectChecker(self) -> None:
    '''Node for checkerboard is selected'''
    #get nodes
    checker1 = self.checkerSelector1.currentNode()
    checker2 = self.checkerSelector2.currentNode()
    output = self.checkerOutputSelector.currentNode()

    #enable button if all selected
    self.checkerButton.enabled = (checker1 and checker2 and output)

    #change basenames
    if checker1:
      self.checkerOutputSelector.baseName = checker1.GetName() + '_CHECKERBOARD'
      self.gridSelector.baseName = checker1.GetName() + '_GRID'
  
  def onGridChecked(self) -> None:
    '''Show grid option is checked'''
    if self.gridCheckBox.checked:
      self.gridCollapsibleBox.show()
    else:
      self.gridCollapsibleBox.hide()

  def onCheckerVisualizeButton(self) -> None:
    '''Get checkerboard button is pressed'''
    #set parameters
    print('\nCreating checkerboard image')
    self.progressBar4.show()

    #set parameters and run
    self.logic.setCheckerboardParameters(self.checkerSelector1.currentNode(),
                    self.checkerSelector2.currentNode(),
                    self.checkerSizeText.value)
    self.logic.getCheckerboard(self.checkerOutputSelector.currentNode())

    #get grid if option checked
    if self.gridCheckBox.checked:
      gridNode = self.gridSelector.currentNode()
      if not gridNode:
        slicer.util.warningDisplay("No volume selected, unable to create grid")
      else:
        self.logic.getCheckerboardGrid(gridNode)
    
    print("Completed")
    self.progressBar4.hide()

  # Functions for collapsibles in widget

  def onCollapseRegister(self):
    '''Registration collapsible clicked'''
    if not self.registrationCollapsibleButton.collapsed:
      self.borderCollapsibleButton.collapsed = True
      self.subtractionCollapsibleButton.collapsed = True
      self.checkerboardCollapsibleButton.collapsed = True
      self.onSelect()

  def onCollapseBorder(self):
    '''Contour Border View collapsible clicked'''
    if not self.borderCollapsibleButton.collapsed:
      self.registrationCollapsibleButton.collapsed = True
      self.subtractionCollapsibleButton.collapsed = True
      self.checkerboardCollapsibleButton.collapsed = True
      self.onSelectBorder()    

  def onCollapseSubtraction(self):
    '''Visualization collapsible clicked'''
    if not self.subtractionCollapsibleButton.collapsed:
      self.registrationCollapsibleButton.collapsed = True
      self.borderCollapsibleButton.collapsed = True
      self.checkerboardCollapsibleButton.collapsed = True
      self.onSelectSubtraction()
  
  def onCollapseChecker(self):
    '''Checkerboard collapsible clicked'''
    if not self.checkerboardCollapsibleButton.collapsed:
      self.registrationCollapsibleButton.collapsed = True
      self.borderCollapsibleButton.collapsed = True
      self.subtractionCollapsibleButton.collapsed = True
      self.onSelectChecker()
  
  def setProgress(self, value):
    """Update the progress bar"""
    self.progressBar.setValue(value)
    self.progressBar2.setValue(value)

class ImageRegistrationTest(ScriptedLoadableModuleTest):
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
    self.test_Registration()

  def test_Registration(self):
    '''
    Automatic Contour Tests: Runs the cortical break detection function on 3 sample images
    and compares the results to pre-generated masks and manually placed seed points

    Test Requires:

      mha files: 'SAMPLE_MHA1.mha', 'SAMPLE_MHA2.mha', 'SAMPLE_MHA3.mha'
      contour masks: 'SAMPLE_MASK1.mha', 'SAMPLE_MASK2.mha', 'SAMPLE_MASK3.mha'
      seed lists: 'SAMPLE_SEEDS1.json', 'SAMPLE_SEEDS2.json', 'SAMPLE_SEEDS3.json'
      comparison segmentations: 'SAMPLE_ER1.seg.nrrd', 'SAMPLE_ER2.seg.nrrd', 'SAMPLE_ER3.seg.nrrd'
    
    Success Conditions:
      1. Erosion segmentation is successfully generated
      2. Number of segmentations is correct
      3. Each segmetation differs by less than 0.5% from the corresponding comparison
      4. Volume and Surface area are less than 0.01% from comparison values
    '''
    from ImageRegistrationLib.ImageRegistrationLogic import ImageRegistrationLogic
    #from Testing.ErosionVolumeTestLogic import ErosionVolumeTestLogic

    self.delayDisplay("Starting the test")
    #
    # first, get some data
    #
    
    # setup logic
    logic = ImageRegistrationLogic()
    logic.progressCallBack = self.foo
    testLogic = ImageRegistrationTestLogic()
    scene = slicer.mrmlScene

    # run 3 tests
    passed = True
    for i in range(1, 2):
      index = str(i)
      print('\n*----------------------Test ' + index + '----------------------*')

      # get input files
      baseVolume = testLogic.newNode(scene, filename='SAMPLE_REG_BL' + index + '.mha', name='testBaselineVolume' + index, display=False)
      followVolume = testLogic.newNode(scene, filename='SAMPLE_REG_FU' + index + '.mha', name='testFollowupVolume' + index, display=False)

      # setup volumes
      outputVolume = testLogic.newNode(scene, name='testOutputVolume' + index)
      logic.setParamaters(baseVolume, followVolume, 0.005)
      logic.run(outputVolume)
      
      # check outputs against sample file
      if not testLogic.verifyRegistration(baseVolume, outputVolume):
        self.delayDisplay('Output registration is incorrect for test ' + index, msec = 300)
        passed = False

      self.delayDisplay('Test ' + index + ' complete')

    #Failure message
    self.assertTrue(passed, 'Incorrect results, check testing log')
    
  def foo(self, progress):
    pass

import SimpleITK as sitk
import sitkUtils, os, slicer
import numpy as np

class ImageRegistrationTestLogic:

    def __init__(self):
        pass

    def getFilePath(self, filename:str) -> str:
        '''
        Find the full filepath of a file in the samme folder
        '''
        #REPLACE WHEN MOVED TO SUBCLASS
        #root = self.getParent(self.getParent(self.getParent(os.path.realpath(__file__))))
        root = self.getParent(self.getParent(os.path.realpath(__file__)))

        #Windows
        if '\\' in root:
            return root + '\\TestFiles\\' + filename
        
        #MacOS/Linux
        else:
            return root + '/TestFiles/' + filename

    def getParent(self, path):
        return os.path.split(path)[0]

    def volumeFromFile(self, filepath, volume, display=True):
        '''
        Import an image file into a Slicer volume

        Args:
            filepath (str): full path to the file
            volume (vtkVolumeNode): Slicer volume
            display (bool): option to display the volume in Slicer

        Returns:
            None
        '''
        #modify filepath
        fullpath = self.getFilePath(filepath)
        print('Reading in ' + fullpath)

        reader = sitk.ImageFileReader()
        reader.SetFileName(fullpath)

        outputImage = reader.Execute()

        sitkUtils.PushVolumeToSlicer(outputImage, targetNode=volume)
        if display:
            slicer.util.setSliceViewerLayers(background=volume, fit=True)

    def newNode(self, scene, filename='new', name='node', type='scalar', display=True):
        '''
        Create a new node for a Slicer volume

        Args:
            scene (mrmlScene): current Slicer scene
            filename (str)
            name (str): name of the node to be created
            type (str): type of volume created (use \'scalar\' or \'labelmap\')
            display (bool): option to display the volume in Slicer
        
        Returns:
            vtkMRMLVolumeNode
        '''
        if type == 'scalar':
            volume = slicer.vtkMRMLScalarVolumeNode()
        elif type == 'labelmap':
            volume = slicer.vtkMRMLLabelMapVolumeNode()
        elif type == 'segmentation':
            volume = slicer.vtkMRMLSegmentationNode()
        elif type == 'fiducial':
            volume = slicer.vtkMRMLMarkupsFiducialNode()
        elif type == 'table':
            volume = slicer.vtkMRMLTableNode()
        volume.SetScene(scene)
        volume.SetName(name)
        scene.AddNode(volume)
        if not filename == 'new':
            if type == 'fiducial':
                volume = slicer.util.loadMarkups(self.getFilePath(filename))
            elif type == 'seg':
                volume = slicer.util.loadSegmentation(self.getFilePath(filename))
            else:
                self.volumeFromFile(filename, volume, display)
        return volume


    def verifyRegistration(self, baseNode, regNode):
        '''
        Check registered image against original
        '''
        #Pull images
        base_img = sitkUtils.PullVolumeFromSlicer(baseNode)
        reg_img = sitkUtils.PullVolumeFromSlicer(regNode)

        #Threshold and convert to array
        base_arr = sitk.GetArrayFromImage(self.threshold(base_img))
        reg_arr = sitk.GetArrayFromImage(self.threshold(reg_img))

        #Calculate ratios
        subtraction = np.add(base_arr, np.multiply(reg_arr, 2))
        base_only = np.nonzero((subtraction == 1))
        reg_only = np.nonzero((subtraction == 2))

        ratio1 = np.count_nonzero(base_only) / np.count_nonzero(subtraction) * 100
        ratio2 = np.count_nonzero(reg_only) / np.count_nonzero(subtraction) * 100

        print(str.format("{:.6f}% of voxels are in the baseline image only", ratio1))
        print(str.format("{:.6f}% of voxels are in the registered image only", ratio2))

        return ratio1 < 15 and ratio2 < 15


    def threshold(self, img:sitk.Image) -> sitk.Image:
        '''Apply binary threshold for test images'''
        gauss = sitk.SmoothingRecursiveGaussian(img, 1)
        return sitk.OtsuThreshold(gauss)
        

        
        