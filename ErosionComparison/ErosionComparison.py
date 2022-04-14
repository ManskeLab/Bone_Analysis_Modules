#-----------------------------------------------------
# ErosionComparison.py
#
# Created by:  Ryan Yan
# Created on:  17-02-2022
#
# Description: This module sets up the interface for the Erosion Comparison module
#
#-----------------------------------------------------

import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
import SimpleITK as sitk
import sitkUtils
import os
from ErosionComparisonLib.ErosionComparisonLogic import *

#
# Module for CBCT Enhancement
#
class ErosionComparison(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Erosion Comparison" # TODO make this more human readable by adding spaces
    self.parent.categories = ["Bone Analysis Module (BAM)"]
    self.parent.dependencies = []
    self.parent.contributors = ["Ryan Yan"] # replace with "Firstname Lastname (Organization)"
    self.parent.helpText = """Compares two longitudinally registered scans to determine the development of erosions in the bone.
    Ideally, the Erosion Volume module should be used to obtain erosion segmentations, but the module can be used with the scans directly, with lower accuracy.
    """
    self.parent.helpText += "<br>For more information see the <a href=https://github.com/ManskeLab/3DSlicer_Erosion_Analysis/wiki/Erosion-Comparison-Module>online documentation</a>."
    self.parent.helpText += "<br><td><img src=\"" + self.getLogo('bam') + "\" height=80> "
    self.parent.helpText += "<img src=\"" + self.getLogo('manske') + "\" height=80></td>"
    self.parent.acknowledgementText = """
    Updated on February 17, 2022.<br>
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
# ErosionComparisonWidget
#
class ErosionComparisonWidget(ScriptedLoadableModuleWidget):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """
    def __init__(self, parent):
        # Initialize logics object
        self.logic = ErosionComparisonLogic()
        # initialize call back object for updating progrss bar
        self.logic.progressCallBack = self.setProgress

        ScriptedLoadableModuleWidget.__init__(self, parent)

    def setup(self) -> None:
        '''Setup Erosion Comparison Widget'''
        # Buttons for testing
        ScriptedLoadableModuleWidget.setup(self)
        
        self.collapsible1 = ctk.ctkCollapsibleButton()
        self.collapsible1.text = "Compare Erosion Segmentations"
        self.collapsible2 = ctk.ctkCollapsibleButton()
        self.collapsible2.collapsed = True
        self.collapsible2.text = "Compare Images"

        self.collapsible1.contentsCollapsed.connect(self.onCollapsible1)
        self.collapsible2.contentsCollapsed.connect(self.onCollapsible2)

        self.setupCompareSeg()
        #self.setupCompareImage()
        self.layout.addStretch(1)
    
    def setupCompareSeg(self) -> None:
        '''Setup Compare Erosion Segmentations collapsible'''
        compareSegLayout = qt.QFormLayout(self.collapsible1)
        compareSegLayout.setVerticalSpacing(5)
        self.layout.addWidget(self.collapsible1)

        #
        # Input MasterVolume
        #
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
        compareSegLayout.addRow("Master Volume: ", self.inputVolumeSelector)

        #
        # Input first segmentation
        #
        self.inputSegSelector1 = slicer.qMRMLNodeComboBox()
        self.inputSegSelector1.nodeTypes = ["vtkMRMLSegmentationNode"]
        self.inputSegSelector1.selectNodeUponCreation = False
        self.inputSegSelector1.addEnabled = False
        self.inputSegSelector1.renameEnabled = True
        self.inputSegSelector1.removeEnabled = True
        self.inputSegSelector1.noneEnabled = False
        self.inputSegSelector1.showHidden = False
        self.inputSegSelector1.showChildNodeTypes = False
        self.inputSegSelector1.setMRMLScene(slicer.mrmlScene)
        compareSegLayout.addRow("Input Segmentation 1: ", self.inputSegSelector1)

        #
        # Input second segmentation
        #
        self.inputSegSelector2 = slicer.qMRMLNodeComboBox()
        self.inputSegSelector2.nodeTypes = ["vtkMRMLSegmentationNode"]
        self.inputSegSelector2.selectNodeUponCreation = False
        self.inputSegSelector2.addEnabled = False
        self.inputSegSelector2.renameEnabled = True
        self.inputSegSelector2.removeEnabled = True
        self.inputSegSelector2.noneEnabled = False
        self.inputSegSelector2.showHidden = False
        self.inputSegSelector2.showChildNodeTypes = False
        self.inputSegSelector2.setMRMLScene(slicer.mrmlScene)
        compareSegLayout.addRow("Input Segmentation 2: ", self.inputSegSelector2)

        #
        # Output image
        #
        self.outputImageSelector = slicer.qMRMLNodeComboBox()
        self.outputImageSelector.nodeTypes = ["vtkMRMLSegmentationNode"]
        self.outputImageSelector.selectNodeUponCreation = True
        self.outputImageSelector.addEnabled = True
        self.outputImageSelector.renameEnabled = True
        self.outputImageSelector.removeEnabled = True
        self.outputImageSelector.noneEnabled = False
        self.outputImageSelector.showHidden = False
        self.outputImageSelector.showChildNodeTypes = False
        self.outputImageSelector.setMRMLScene(slicer.mrmlScene)
        self.outputImageSelector.baseName = 'COMPARISON'
        compareSegLayout.addRow("Output Segmentation: ", self.outputImageSelector)

        #
        # Output table selector
        #
        self.outputTableSelector = slicer.qMRMLNodeComboBox()
        self.outputTableSelector.nodeTypes = ["vtkMRMLTableNode"]
        self.outputTableSelector.selectNodeUponCreation = True
        self.outputTableSelector.addEnabled = True
        self.outputTableSelector.removeEnabled = True
        self.outputTableSelector.renameEnabled = True
        self.outputTableSelector.noneEnabled = False
        self.outputTableSelector.baseName = "TABLE"
        self.outputTableSelector.setMRMLScene(slicer.mrmlScene)
        self.outputTableSelector.setToolTip( "Pick the output table to store the joint space width statistics" )
        self.outputTableSelector.setCurrentNode(None)
        compareSegLayout.addRow("Output Table: ", self.outputTableSelector)

        #
        # Apply Button
        #
        self.compareSegButton = qt.QPushButton("Compare Erosions")
        self.compareSegButton.enabled = False
        compareSegLayout.addRow(self.compareSegButton)

        # Progress Bar
        self.progressBar = qt.QProgressBar()
        self.progressBar.hide()
        compareSegLayout.addRow(self.progressBar)

        #connections
        self.inputVolumeSelector.currentNodeChanged.connect(self.onMasterChanged)
        self.inputSegSelector1.currentNodeChanged.connect(self.onNodeChanged)
        self.inputSegSelector2.currentNodeChanged.connect(self.onNodeChanged)
        self.outputImageSelector.currentNodeChanged.connect(self.onNodeChanged)
        self.compareSegButton.clicked.connect(self.onCompareSeg)

        # logger
        self.logger = logging.getLogger("erosion_comparison")
    
    def setupCompareImage(self) -> None:
        '''Setup Compare Images collapsible'''
        compareImageLayout = qt.QFormLayout(self.collapsible2)
        compareImageLayout.setVerticalSpacing(5)
        self.layout.addWidget(self.collapsible2)

        #
        # Input first image
        #
        self.inputImageSelector1 = slicer.qMRMLNodeComboBox()
        self.inputImageSelector1.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        self.inputImageSelector1.selectNodeUponCreation = False
        self.inputImageSelector1.addEnabled = False
        self.inputImageSelector1.renameEnabled = True
        self.inputImageSelector1.removeEnabled = True
        self.inputImageSelector1.noneEnabled = False
        self.inputImageSelector1.showHidden = False
        self.inputImageSelector1.showChildNodeTypes = False
        self.inputImageSelector1.setMRMLScene(slicer.mrmlScene)
        compareImageLayout.addRow("Baseline Image: ", self.inputImageSelector1)

        #
        # Input second image
        #
        self.inputImageSelector2 = slicer.qMRMLNodeComboBox()
        self.inputImageSelector2.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        self.inputImageSelector2.selectNodeUponCreation = False
        self.inputImageSelector2.addEnabled = False
        self.inputImageSelector2.renameEnabled = True
        self.inputImageSelector2.removeEnabled = True
        self.inputImageSelector2.noneEnabled = False
        self.inputImageSelector2.showHidden = False
        self.inputImageSelector2.showChildNodeTypes = False
        self.inputImageSelector2.setMRMLScene(slicer.mrmlScene)
        compareImageLayout.addRow("Baseline Image: ", self.inputImageSelector2)

        #
        # Output image
        #
        self.outputImageSelector2 = slicer.qMRMLNodeComboBox()
        self.outputImageSelector2.nodeTypes = ["vtkMRMLLabelMapVolumeNode"]
        self.outputImageSelector2.selectNodeUponCreation = True
        self.outputImageSelector2.addEnabled = True
        self.outputImageSelector2.renameEnabled = True
        self.outputImageSelector2.removeEnabled = True
        self.outputImageSelector2.noneEnabled = False
        self.outputImageSelector2.showHidden = False
        self.outputImageSelector2.showChildNodeTypes = False
        self.outputImageSelector2.setMRMLScene(slicer.mrmlScene)
        self.outputImageSelector2.baseName = 'COMPARISON'
        compareImageLayout.addRow("Output Segmentation: ", self.outputImageSelector2)
        
        # threshold spin boxes (default unit is HU)
        self.lowerThresholdText = qt.QSpinBox()
        self.lowerThresholdText.setMinimum(-9999)
        self.lowerThresholdText.setMaximum(999999)
        self.lowerThresholdText.setSingleStep(100)
        self.lowerThresholdText.value = 686
        compareImageLayout.addRow("Lower Threshold: ", self.lowerThresholdText)
        self.upperThresholdText = qt.QSpinBox()
        self.upperThresholdText.setMinimum(-9999)
        self.upperThresholdText.setMaximum(999999)
        self.upperThresholdText.setSingleStep(100)
        self.upperThresholdText.value = 4000
        compareImageLayout.addRow("Upper Threshold: ", self.upperThresholdText)

        #
        # Apply Button
        #
        self.compareImageButton = qt.QPushButton("Compare Erosions")
        #self.compareImageButton.enabled = False
        compareImageLayout.addRow(self.compareImageButton)

        # Connections
        self.compareImageButton.clicked.connect(self.onCompareImage)

    
    # Functions for collapsibles
    def onCollapsible1(self) -> None:
        if not self.collapsible1.collapsed:
            self.collapsible2.collapsed = True

    def onCollapsible2(self) -> None:
        if not self.collapsible2.collapsed:
            self.collapsible1.collapsed = True

    
    def onNodeChanged(self) -> None:
        '''Any segmentation node changed'''
        input1 = self.inputSegSelector1.currentNode()
        input2 = self.inputSegSelector2.currentNode()
        output = self.outputImageSelector.currentNode()

        self.compareSegButton.enabled = (input1 and input2 and output)
        
    def onMasterChanged(self) -> None:
        '''Master volume not changed'''
        inputVolumeNode = self.inputVolumeSelector.currentNode()

        if inputVolumeNode:
            self.outputImageSelector.baseName = inputVolumeNode.GetName() + '_COMPARISON'
            self.outputTableSelector.baseName = inputVolumeNode.GetName() + '_TABLE'

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
        self.logger.info("Using Cortical Break Detection Module with " + inputVolumeNode.GetName() + "\n")

    def onCompareSeg(self) -> None:
        '''Compare erosion segmentation button pressed'''
        #log parameters used
        self.logger.info("Erosion Comparison Initialized with Parameters:")
        self.logger.info("Master Volume: " + self.inputVolumeSelector.currentNode().GetName())
        self.logger.info("Input Segmentation 1: " + self.inputSegSelector1.currentNode().GetName())
        self.logger.info("Input Segmentation 2: " + self.inputSegSelector2.currentNode().GetName())
        self.logger.info("Output Segmentation: " + self.outputImageSelector.currentNode().GetName())
        self.logger.info("Output Table: " + self.outputTableSelector.currentNode().GetName())

        self.logic.setMasterImage(self.inputVolumeSelector.currentNode())
        self.logic.setSegments(self.inputSegSelector1.currentNode(),
                                    self.inputSegSelector2.currentNode())
        
        outNode = self.outputImageSelector.currentNode()
        self.logic.compareSegments(outNode)

        self.logic.getStatistics(outNode, self.outputTableSelector.currentNode())
        self.logger.info("Finished\n")

    def onCompareImage(self) -> None:
        '''Compare image button pressed'''

        self.logic.compareImages(self.inputImageSelector1.currentNode(),
                                self.inputImageSelector2.currentNode(),
                                self.outputImageSelector2.currentNode(),
                                self.lowerThresholdText.value,
                                self.upperThresholdText.value)
        

    def enableErosionsWidgets(self):
        """Enable widgets in the layout"""
        self.onNodeChanged()
        self.progressBar.hide()

    def disableErosionsWidgets(self):
        """Disable widgets in the layout"""
        self.compareSegButton.enabled = False
        self.progressBar.show()
    
    def setProgress(self, value):
        """Update the progress bar"""
        self.progressBar.setValue(value)

