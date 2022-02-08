#-----------------------------------------------------
# ImageRegistration.py
#
# Created by:  Ryan Yan
# Created on:  24-01-2022
#
# Description: This module sets up the interface for the Image Registration 3D Slicer extension.
#
#-----------------------------------------------------
import os
import unittest
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
    self.parent.categories = ["Bone"]
    self.parent.dependencies = []
    self.parent.contributors = ["Ryan Yan"] # replace with "Firstname Lastname (Organization)"
    self.parent.helpText = """
    Perform longitudinal image registration on a baseline and follow-up image. Currently under development.
    """
    self.parent.acknowledgementText = """
    This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc.
    and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
""" # replace with organization, grant and thanks.

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

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)
    # Instantiate and connect widgets ...

    #
    # Register Image -----------------------------------------------------------*
    #
    self.registerCollapsibleButton = ctk.ctkCollapsibleButton()
    self.registerCollapsibleButton.text = "Register Images"
    self.layout.addWidget(self.registerCollapsibleButton)

    # Layout within the dummy collapsible button
    registerFormLayout = qt.QFormLayout(self.registerCollapsibleButton)
    registerFormLayout.setVerticalSpacing(5)

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
    registerFormLayout.addRow("Baseline: ", self.inputSelector1)

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
    registerFormLayout.addRow("Follow-up: ", self.inputSelector2)

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
    registerFormLayout.addRow("Output: ", self.outputSelector)

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

    #
    # Visualize Registration -----------------------------------------------------------*
    #
    self.visualizeCollapsibleButton = ctk.ctkCollapsibleButton()
    self.visualizeCollapsibleButton.text = "Visualize Registraion"
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
    visualizeFormLayout.addRow("Follow-up: ", self.visualSelector2)

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

    # threshold spin boxes (default unit is HU)
    self.lowerThresholdText = qt.QSpinBox()
    self.lowerThresholdText.setMinimum(-9999)
    self.lowerThresholdText.setMaximum(999999)
    self.lowerThresholdText.setSingleStep(10)
    self.lowerThresholdText.value = 686
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
    self.outputSelector2.currentNodeChanged.connect(self.onSelectVisual)
    self.visualButton.clicked.connect(self.onVisualize)

    self.visualizeCollapsibleButton.contentsCollapsed.connect(self.onCollapse2)

    # Add vertical spacer
    self.layout.addStretch(1)

  def cleanup(self):
    pass
  
  #input node is selected
  def onSelect(self):
    #get selected nodes
    input1 = self.inputSelector1.currentNode()
    input2 = self.inputSelector2.currentNode()
    output = self.outputSelector.currentNode()

    #enable register button if both nodes selected
    self.applyButton.enabled = input1 and input2 and output

    #auto-fill nodes in other collapsibles, set output basename
    if input1:
      self.visualSelector1.setCurrentNode(input1)
    if input2:
      self.outputSelector.baseName = input2.GetName() + '_REG'
    if output:
      self.visualSelector2.setCurrentNode(output)

  #help button is pressed
  def onHelpButton(self):
    txt = """Registration Image Similarity Metrics\n
Mean Squares: Computes mean squared difference between pixel values. Requires intensity values to be within the same thresholds for images.\n
Correlation: Computes normal correlation between pixel values. Requires images in the same modality, but can be in any intensity range.\n
Mattes Mutual Information: Computes mutual information (ability to determine intensity of the second image based on the first). Can be used with multiple modalities.\n
ANTS Neighborhood: Computes correlation of a small neighbourhood for each pixel. Ideal for images that are very close.
          """
    slicer.util.infoDisplay(txt, 'Help: Similarity Metrics')
  
  #Register button is pressed
  def onApplyButton(self):
    print("Running Registration Algorithm")
    self.progressBar.show()

    self.logic.setParamaters(self.inputSelector1.currentNode(), 
                        self.inputSelector2.currentNode(),
                        self.samplingText.value)
    self.logic.setMetric(self.metricSelector.currentIndex)
    self.logic.run(self.outputSelector.currentNode())

    self.progressBar.hide()
  
  #output node for visualization is selected
  def onSelectVisual(self):
    self.visualButton.enabled = self.outputSelector2.currentNode() and self.visualSelector1.currentNode() and self.visualSelector2.currentNode()

  #visualize button is pressed
  def onVisualize(self):

    print('Creating Subtraction Image')
    self.progressBar.show()

    self.logic.setVisualizeParameters(self.visualSelector1.currentNode(), 
                                self.visualSelector2.currentNode(),
                                self.sigmaText.value,
                                self.lowerThresholdText.value,
                                self.upperThresholdText.value)

    outnode = self.outputSelector2.currentNode()
    self.logic.visualize(outnode)
    slicer.util.setSliceViewerLayers(label=outnode, labelOpacity=0.5)

    self.progressBar.hide()

  #functions for collapsibles in widget
  def onCollapse1(self):
    if not self.registerCollapsibleButton.collapsed:
      self.visualizeCollapsibleButton.collapsed = True

  def onCollapse2(self):
    if not self.visualizeCollapsibleButton.collapsed:
      self.registerCollapsibleButton.collapsed = True
  
  def setProgress(self, value):
    """Update the progress bar"""
    self.progressBar.setValue(value)
    self.progressBar2.setValue(value)

