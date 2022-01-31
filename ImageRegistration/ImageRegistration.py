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

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)
    # Instantiate and connect widgets ...

    #
    # Register Area -----------------------------------------------------------*
    #
    self.registerCollapsibleButton = ctk.ctkCollapsibleButton()
    self.registerCollapsibleButton.text = "Register Images"
    self.layout.addWidget(self.registerCollapsibleButton)

    # Layout within the dummy collapsible button
    registerFormLayout = qt.QFormLayout(self.registerCollapsibleButton)

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

    # connections
    self.applyButton.clicked.connect(self.onApplyButton)
    self.inputSelector1.currentNodeChanged.connect(self.onSelect)
    self.inputSelector2.currentNodeChanged.connect(self.onSelect)
    self.outputSelector.currentNodeChanged.connect(self.onSelect)

    self.registerCollapsibleButton.contentsCollapsed.connect(self.onCollapse1)

    #
    # Register Area -----------------------------------------------------------*
    #
    self.visualizeCollapsibleButton = ctk.ctkCollapsibleButton()
    self.visualizeCollapsibleButton.text = "Visualize Registraion"
    self.visualizeCollapsibleButton.collapsed = True
    self.layout.addWidget(self.visualizeCollapsibleButton)

    # Layout within the dummy collapsible button
    visualizeFormLayout = qt.QFormLayout(self.visualizeCollapsibleButton)

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

    #
    # Visualize Button
    #
    self.visualButton = qt.QPushButton("Visualize")
    self.visualButton.toolTip = "Visualize difference in images after registration."
    self.visualButton.enabled = False
    visualizeFormLayout.addRow(self.visualButton)

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
    self.applyButton.enabled = input1 and input2

    #auto-fill nodes in other collapsibles, set output basename
    if input1:
      self.visualSelector1.setCurrentNode(input1)
    if input2:
      self.outputSelector.baseName = input2.GetName() + '_REG'
    if output:
      self.visualSelector2.setCurrentNode(output)

    
  #Register button is pressed
  def onApplyButton(self):
    logic = ImageRegistrationLogic()
    print("Running Registration Algorithm")
    logic.setParamaters(self.inputSelector1.currentNode(), self.inputSelector2.currentNode())
    logic.run(self.outputSelector.currentNode())
  
  def onSelectVisual(self):
    self.visualButton.enabled = self.outputSelector2.currentNode() and self.visualSelector1.currentNode() and self.visualSelector2.currentNode()

  def onVisualize(self):
    logic = ImageRegistrationLogic()

    print('Creating Subtraction Image')
    logic.setVisualizeParameters(self.visualSelector1.currentNode(), self.visualSelector2.currentNode())

    outnode = self.outputSelector2.currentNode()
    logic.visualize(outnode)
    slicer.util.setSliceViewerLayers(label=outnode, labelOpacity=0.5)

  def onCollapse1(self):
    if not self.registerCollapsibleButton.collapsed:
      self.visualizeCollapsibleButton.collapsed = True

  def onCollapse2(self):
    if not self.visualizeCollapsibleButton.collapsed:
      self.registerCollapsibleButton.collapsed = True
