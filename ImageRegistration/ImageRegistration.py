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

    
    self.registerCollapsibleButton = ctk.ctkCollapsibleButton()
    self.registerCollapsibleButton.text = "Register Images"
    self.visualizeCollapsibleButton = ctk.ctkCollapsibleButton()
    self.visualizeCollapsibleButton.text = "Subtraction View"
    self.checkerboardCollapsibleButton = ctk.ctkCollapsibleButton()
    self.checkerboardCollapsibleButton.text = "Checkerboard View"

    # Setup collapsibles
    self.setupRegistration()
    self.setupVisualization()
    self.setupCheckerboard()

    # Add vertical spacer
    self.layout.addStretch(1)

  
  # Register Image -----------------------------------------------------------*
  
  def setupRegistration(self) -> None:
    # Layout within the dummy collapsible button
    registerFormLayout = qt.QFormLayout(self.registerCollapsibleButton)
    registerFormLayout.setVerticalSpacing(5)
    self.layout.addWidget(self.registerCollapsibleButton)

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
    self.optimizerSelector.setCurrentIndex(2)
    registerFormLayout.addRow("Similarity Metric: ", self.optimizerSelector)

    #
    # Output volume selector
    #
    self.outputSelector = slicer.qMRMLNodeComboBox()
    self.outputSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.outputSelector.selectNodeUponCreation = True
    self.outputSelector.addEnabled = True
    self.outputSelector.renameEnabled = True
    self.outputSelector.removeEnabled = True
    self.outputSelector.noneEnabled = False
    self.outputSelector.showHidden = False
    self.outputSelector.showChildNodeTypes = False
    self.outputSelector.setMRMLScene( slicer.mrmlScene )
    self.outputSelector.setToolTip( "Select the output image" )
    self.outputSelector.setCurrentNode(None)
    self.outputSelector.baseName = 'REG'
    registerFormLayout.addRow("Output: ", self.outputSelector)

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
    
    self.inputSelector1.currentNodeChanged.connect(self.onSelect)
    self.inputSelector2.currentNodeChanged.connect(self.onSelect)
    self.outputSelector.currentNodeChanged.connect(self.onSelect)

    self.registerCollapsibleButton.contentsCollapsed.connect(self.onCollapse1)

    # logger
    self.logger = logging.getLogger("image_registration")

  # Visualize Registration -----------------------------------------------------------*
  
  def setupVisualization(self) -> None:
    '''Setup Subtraction View collapsible'''
    self.visualizeCollapsibleButton.collapsed = True
    self.layout.addWidget(self.visualizeCollapsibleButton)

    # Layout within the dummy collapsible button
    visualizeFormLayout = qt.QFormLayout(self.visualizeCollapsibleButton)
    visualizeFormLayout.setVerticalSpacing(5)

    #
    # First input volume selector
    #
    self.visualSelector1 = slicer.qMRMLNodeComboBox()
    self.visualSelector1.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.visualSelector1.selectNodeUponCreation = True
    self.visualSelector1.addEnabled = False
    self.visualSelector1.removeEnabled = False
    self.visualSelector1.noneEnabled = False
    self.visualSelector1.showHidden = False
    self.visualSelector1.showChildNodeTypes = False
    self.visualSelector1.setMRMLScene( slicer.mrmlScene )
    self.visualSelector1.setToolTip( "Select the baseline image" )
    self.visualSelector1.setCurrentNode(None)
    visualizeFormLayout.addRow("Baseline: ", self.visualSelector1)

    #
    # Second input volume selector
    #
    self.visualSelector2 = slicer.qMRMLNodeComboBox()
    self.visualSelector2.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.visualSelector2.selectNodeUponCreation = True
    self.visualSelector2.addEnabled = False
    self.visualSelector2.removeEnabled = False
    self.visualSelector2.noneEnabled = False
    self.visualSelector2.showHidden = False
    self.visualSelector2.showChildNodeTypes = False
    self.visualSelector2.setMRMLScene( slicer.mrmlScene )
    self.visualSelector2.setToolTip( "Select the follow-up image" )
    self.visualSelector2.setCurrentNode(None)
    visualizeFormLayout.addRow("Registered Follow-up: ", self.visualSelector2)

    # visualization type button layout
    visualTypeLayout = qt.QGridLayout()

    # visualization type buttons
    self.threeDButton = qt.QRadioButton("3D")
    self.threeDButton.setChecked(True)
    self.grayButton = qt.QRadioButton("Grayscale")
    self.grayButton.setChecked(False)
    visualTypeLayout.addWidget(self.threeDButton, 0, 0)
    visualTypeLayout.addWidget(self.grayButton, 0, 1)
    # visualization type button frame
    fileTypeFrame = qt.QFrame()
    fileTypeFrame.setLayout(visualTypeLayout)
    visualizeFormLayout.addRow("Output Format: ", fileTypeFrame)

    #
    # Output volume selector
    #
    self.outputSelector2 = slicer.qMRMLNodeComboBox()
    self.outputSelector2.nodeTypes = ["vtkMRMLLabelMapVolumeNode"]
    self.outputSelector2.selectNodeUponCreation = True
    self.outputSelector2.addEnabled = True
    self.outputSelector2.renameEnabled = True
    self.outputSelector2.removeEnabled = True
    self.outputSelector2.noneEnabled = False
    self.outputSelector2.showHidden = False
    self.outputSelector2.showChildNodeTypes = False
    self.outputSelector2.setMRMLScene( slicer.mrmlScene )
    self.outputSelector2.setToolTip( "Select the output image" )
    self.outputSelector2.setCurrentNode(None)
    self.outputSelector2.baseName = ('SUBTRACTION')
    visualizeFormLayout.addRow("Output: ", self.outputSelector2)

    self.threshButton = qt.QCheckBox()
    self.threshButton.checked = True
    visualizeFormLayout.addRow("Use Automatic Thresholding", self.threshButton)

    self.threshSelector = qt.QComboBox()
    self.threshSelector.addItems(['Otsu', 'Huang', 'Max Entropy', 'Moments', 'Yen'])
    visualizeFormLayout.addRow("Thresholding Method", self.threshSelector)

    # Help button for thresholding methods
    self.helpButton2 = qt.QPushButton("Help")
    self.helpButton2.toolTip = "Tips for selecting a thresholding method"
    self.helpButton2.setFixedSize(50, 20)
    visualizeFormLayout.addRow("", self.helpButton2)


    # threshold spin boxes (default unit is HU)
    self.lowerThresholdText = qt.QSpinBox()
    self.lowerThresholdText.setMinimum(-9999)
    self.lowerThresholdText.setMaximum(999999)
    self.lowerThresholdText.setSingleStep(10)
    self.lowerThresholdText.value = 500
    visualizeFormLayout.addRow("Lower Threshold: ", self.lowerThresholdText)
    self.upperThresholdText = qt.QSpinBox()
    self.upperThresholdText.setMinimum(-9999)
    self.upperThresholdText.setMaximum(999999)
    self.upperThresholdText.setSingleStep(10)
    self.upperThresholdText.value = 4000
    visualizeFormLayout.addRow("Upper Threshold: ", self.upperThresholdText)

    # gaussian sigma spin box
    self.sigmaText = qt.QDoubleSpinBox()
    self.sigmaText.setRange(0.0001, 10)
    self.sigmaText.setDecimals(4)
    self.sigmaText.value = 1
    self.sigmaText.setSingleStep(0.1)
    self.sigmaText.setToolTip("Standard deviation in the Gaussian smoothing filter")
    visualizeFormLayout.addRow("Gaussian Sigma: ", self.sigmaText)

    #store labels
    self.labels = [visualizeFormLayout.itemAt(i, 0) for i in range(4, 8)]

    #
    # Visualize Button
    #
    self.visualButton = qt.QPushButton("Visualize")
    self.visualButton.toolTip = "Visualize difference in images after registration."
    self.visualButton.enabled = False
    visualizeFormLayout.addRow(self.visualButton)

    # Progress Bar
    self.progressBar2 = qt.QProgressBar()
    self.progressBar2.hide()
    visualizeFormLayout.addRow(self.progressBar2)

    # connections
    self.visualSelector1.currentNodeChanged.connect(self.onSelectVisual)
    self.visualSelector2.currentNodeChanged.connect(self.onSelectVisual)
    self.outputSelector2.currentNodeChanged.connect(self.onSelectVisual)
    self.helpButton2.clicked.connect(self.onHelpButton2)
    self.threeDButton.clicked.connect(self.onSwitchMode)
    self.grayButton.clicked.connect(self.onSwitchMode)
    self.visualButton.clicked.connect(self.onVisualize)
    self.threshButton.clicked.connect(self.onAutoThresh)

    self.visualizeCollapsibleButton.contentsCollapsed.connect(self.onCollapse2)

    self.onAutoThresh()
  
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
    self.outputSelector3 = slicer.qMRMLNodeComboBox()
    self.outputSelector3.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.outputSelector3.selectNodeUponCreation = True
    self.outputSelector3.addEnabled = True
    self.outputSelector3.renameEnabled = True
    self.outputSelector3.removeEnabled = True
    self.outputSelector3.noneEnabled = False
    self.outputSelector3.showHidden = False
    self.outputSelector3.showChildNodeTypes = False
    self.outputSelector3.setMRMLScene( slicer.mrmlScene )
    self.outputSelector3.setToolTip( "Select the output image" )
    self.outputSelector3.setCurrentNode(None) 
    self.outputSelector3.baseName = ('CHECKERBOARD')
    checkerLayout.addRow("Output: ", self.outputSelector3)

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
    self.progressBar3 = qt.QProgressBar()
    self.progressBar3.hide()
    checkerLayout.addRow(self.progressBar3)

    # Connections
    self.checkerSelector1.currentNodeChanged.connect(self.onSelectChecker)
    self.checkerSelector2.currentNodeChanged.connect(self.onSelectChecker)
    self.outputSelector3.currentNodeChanged.connect(self.onSelectChecker)

    self.gridCheckBox.clicked.connect(self.onGridChecked)
    self.checkerButton.clicked.connect(self.onCheckerButton)

    self.checkerboardCollapsibleButton.contentsCollapsed.connect(self.onCollapse3)



  def cleanup(self):
    pass
  
  def onSelect(self) -> None:
    '''Node for registration is selected'''
    #get selected nodes
    input1 = self.inputSelector1.currentNode()
    input2 = self.inputSelector2.currentNode()
    output = self.outputSelector.currentNode()

    #enable register button if both nodes selected
    self.applyButton.enabled = input1 and input2 and output

    #auto-fill nodes in other collapsibles, set output basename
    if input1:
      self.visualSelector1.setCurrentNode(input1)
      self.checkerSelector1.setCurrentNode(input1)
    if input2:
      self.outputSelector.baseName = input2.GetName() + '_REG'
      self.transformSelector.baseName = input2.GetName() + "_TRF"
    if output:
      self.visualSelector2.setCurrentNode(output)
      self.checkerSelector2.setCurrentNode(output)
    
    if input1 and input2 and not output:
      print("owo")
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
    self.logger.info("Output Volume: " + self.outputSelector.currentNode().GetName())
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
    self.logic.run(self.outputSelector.currentNode(), self.transformSelector.currentNode())

    self.logger.info("Finished\n")
    self.progressBar.hide()
  
  def onSelectVisual(self) -> None:
    '''Output node for visualization is selected'''
    visual1 = self.visualSelector1.currentNode()
    visual2 = self.visualSelector2.currentNode()
    output = self.outputSelector2.currentNode()
    self.visualButton.enabled = (visual1 and visual2 and output)
    if visual1:
      self.outputSelector2.baseName = visual1.GetName() + '_SUBTRACTION'

  def onSwitchMode(self) -> None:
    '''Mode changed between 3d and grayscale'''
    if self.threeDButton.checked:
      self.outputSelector2.nodeTypes = ["vtkMRMLLabelMapVolumeNode"]

      #show options
      self.lowerThresholdText.show()
      self.upperThresholdText.show()
      self.sigmaText.value = 1
      for label in self.labels:
        label.widget().show()

    elif self.grayButton.checked:
      self.outputSelector2.nodeTypes = ["vtkMRMLScalarVolumeNode"]

      #hide options
      self.lowerThresholdText.hide()
      self.upperThresholdText.hide()
      self.sigmaText.value = 0.5
      for label in self.labels:
        label.widget().hide()
    
  def onAutoThresh(self):
    use_auto = self.threshButton.checked
    self.lowerThresholdText.setEnabled(not use_auto)
    self.upperThresholdText.setEnabled(not use_auto)
    self.threshSelector.setEnabled(use_auto)

  def onHelpButton2(self) -> None:
    '''Help button is pressed'''
    txt = """Thresholding Methods\n
For images that only contain bone and soft tissue (no completely dark regions), use the 'Otsu', 'Huang', or 'Moments' Thresholds. \n
For images with completely dark regions, use the 'Max Entropy' or 'Yen' Thresholds.
          """
    slicer.util.infoDisplay(txt, 'Help: Similarity Metrics')

  def onVisualize(self) -> None:
    '''Visualize button is pressed'''

    print('\nCreating Subtraction Image')
    self.progressBar.show()

    # set parameters
    if self.threshButton.checked:
      self.logic.setVisualizeParameters(self.visualSelector1.currentNode(), 
                                self.visualSelector2.currentNode(),
                                self.sigmaText.value,
                                method=self.threshSelector.currentIndex)
    else:
      self.logic.setVisualizeParameters(self.visualSelector1.currentNode(), 
                                self.visualSelector2.currentNode(),
                                self.sigmaText.value,
                                lower=self.lowerThresholdText.value,
                                upper=self.upperThresholdText.value)

    #get output
    outnode = self.outputSelector2.currentNode()

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

    self.progressBar.hide()
  
  def onSelectChecker(self) -> None:
    '''Node for checkerboard is selected'''
    #get nodes
    checker1 = self.checkerSelector1.currentNode()
    checker2 = self.checkerSelector2.currentNode()
    output = self.outputSelector3.currentNode()

    #enable button if all selected
    self.checkerButton.enabled = (checker1 and checker2 and output)

    #change basenames
    if checker1:
      self.outputSelector3.baseName = checker1.GetName() + '_CHECKERBOARD'
      self.gridSelector.baseName = checker1.GetName() + '_GRID'
  
  def onGridChecked(self) -> None:
    '''Show grid option is checked'''
    if self.gridCheckBox.checked:
      self.gridCollapsibleBox.show()
    else:
      self.gridCollapsibleBox.hide()

  def onCheckerButton(self) -> None:
    '''Get checkerboard button is pressed'''
    #set parameters
    print('\nCreating checkerboard image')
    self.progressBar3.show()

    #set parameters and run
    self.logic.setCheckerboardParameters(self.checkerSelector1.currentNode(),
                    self.checkerSelector2.currentNode(),
                    self.checkerSizeText.value)
    self.logic.getCheckerboard(self.outputSelector3.currentNode())

    #get grid if option checked
    if self.gridCheckBox.checked:
      gridNode = self.gridSelector.currentNode()
      if not gridNode:
        slicer.util.warningDisplay("No volume selected, unable to create grid")
      else:
        self.logic.getCheckerboardGrid(gridNode)
    
    print("Completed")
    self.progressBar3.hide()

  # Functions for collapsibles in widget

  def onCollapse1(self):
    '''Registration collapsible clicked'''
    if not self.registerCollapsibleButton.collapsed:
      self.visualizeCollapsibleButton.collapsed = True
      self.checkerboardCollapsibleButton.collapsed = True
      self.onSelect()

  def onCollapse2(self):
    '''Visualization collapsible clicked'''
    if not self.visualizeCollapsibleButton.collapsed:
      self.registerCollapsibleButton.collapsed = True
      self.checkerboardCollapsibleButton.collapsed = True
      self.onSelectVisual()
  
  def onCollapse3(self):
    '''Checkerboard collapsible clicked'''
    if not self.checkerboardCollapsibleButton.collapsed:
      self.registerCollapsibleButton.collapsed = True
      self.visualizeCollapsibleButton.collapsed = True
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
        

        
        