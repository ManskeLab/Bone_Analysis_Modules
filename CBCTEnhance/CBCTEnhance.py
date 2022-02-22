#-----------------------------------------------------
# CBCTEnhance.py
#
# Created by:  Ryan Yan
# Created on:  03-02-2022
#
# Description: This module sets up the interface for the CBCT enhancement module
#
#-----------------------------------------------------

import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
import SimpleITK as sitk
import sitkUtils

#
# Module for CBCT Enhancement
#
class CBCTEnhance(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "CBCT Enhance" # TODO make this more human readable by adding spaces
    self.parent.categories = ["Bone"]
    self.parent.dependencies = []
    self.parent.contributors = ["Ryan Yan"] # replace with "Firstname Lastname (Organization)"
    self.parent.helpText = """Enhance Cone Beam CT (CBCT) scans in order to perform image analysis. 
                            Uses edge enhancement and Laplacian sharpening filters."""
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = """
Updated on January 27, 2022.
""" # replace with organization, grant and thanks.

#
# CBCTEnhanceWidget
#
class CBCTEnhanceWidget(ScriptedLoadableModuleWidget):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """
    def __init__(self, parent):
        # Initialize logics object
        self.logic = CBCTEnhanceLogic()
        # initialize call back object for updating progrss bar
        self.logic.progressCallBack = self.setProgress

        ScriptedLoadableModuleWidget.__init__(self, parent)

    def setup(self) -> None:
        '''Setup CBCT Widget'''
        # Buttons for testing
        ScriptedLoadableModuleWidget.setup(self)
        
        self.collapsible = ctk.ctkCollapsibleButton()
        self.collapsible.text = "Enhance CBCT Image"

        self.setupEnhanceCBCT()
        self.layout.addStretch(1)
    
    def setupEnhanceCBCT(self) -> None:
        '''Setup Enhance CBCT Image collapsible'''
        enhanceLayout = qt.QFormLayout(self.collapsible)
        enhanceLayout.setVerticalSpacing(5)
        self.layout.addWidget(self.collapsible)

        #
        # Input CBCT Scan
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
        enhanceLayout.addRow("Input Volume: ", self.inputVolumeSelector)

        #
        # Output Enhanced CBCT Scan
        #
        self.outputVolumeSelector = slicer.qMRMLNodeComboBox()
        self.outputVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        self.outputVolumeSelector.selectNodeUponCreation = True
        self.outputVolumeSelector.addEnabled = True
        self.outputVolumeSelector.renameEnabled = True
        self.outputVolumeSelector.removeEnabled = True
        self.outputVolumeSelector.noneEnabled = False
        self.outputVolumeSelector.showHidden = False
        self.outputVolumeSelector.showChildNodeTypes = False
        self.outputVolumeSelector.setMRMLScene(slicer.mrmlScene)
        self.outputVolumeSelector.baseName = 'ENHANCED'
        enhanceLayout.addRow("Output Volume: ", self.outputVolumeSelector)

        #
        # Apply Button
        #
        self.enhanceButton = qt.QPushButton("Enhance")
        self.enhanceButton.enabled = False
        enhanceLayout.addRow(self.enhanceButton)

        # Progress Bar
        self.progressBar = qt.QProgressBar()
        self.progressBar.hide()
        enhanceLayout.addRow(self.progressBar)

        
        
        #connections
        self.inputVolumeSelector.currentNodeChanged.connect(self.onNodeChanged)
        self.outputVolumeSelector.currentNodeChanged.connect(self.onNodeChanged)
        self.enhanceButton.clicked.connect(self.onEnhance)
    
    def onNodeChanged(self):
        '''Any node changed in step 1'''
        input = self.inputVolumeSelector.currentNode()
        if input:
            self.outputVolumeSelector.baseName = input.GetName() + '_ENHANCED'
            if self.outputVolumeSelector.currentNode():
                self.enhanceButton.enabled = True

    def onEnhance(self):
        '''Enchance button pressed'''
        self.disableErosionsWidgets()

        #sharpen image
        self.logic.sharpen(self.inputVolumeSelector.currentNode(), self.outputVolumeSelector.currentNode())

        self.enableErosionsWidgets()

    def enableErosionsWidgets(self):
        """Enable widgets in the layout"""
        self.onNodeChanged()
        self.progressBar.hide()

    def disableErosionsWidgets(self):
        """Disable widgets in the layout"""
        self.enhanceButton.enabled = False
        self.progressBar.show()
    
    def setProgress(self, value):
        """Update the progress bar"""
        self.progressBar.setValue(value)


class CBCTEnhanceLogic(ScriptedLoadableModuleLogic):
    def __init__(self):
        self.progressCallBack = None

    def sharpen(self, inputNode, outputNode) -> None:
        '''
        Enhance CBCT scan

        Args:
            inputNode (vtkMRMLVolumeNode): volume with input image
            outputNode (vtkMRMLVolumeNode): volume to store enhanced image

        Returns:
            None
        '''
        img = sitk.Cast(sitkUtils.PullVolumeFromSlicer(inputNode), sitk.sitkFloat64)

        #edge enhancement filter
        sharp = sitk.UnsharpMaskImageFilter()
        sharp.SetAmount(2)
        outimg = sharp.Execute(img)
        self.progressCallBack(50)

        #laplacian sharpening fileter
        sharp2 = sitk.LaplacianSharpeningImageFilter()
        outimg = sharp2.Execute(outimg)
        #outimg.SetOrigin([0, 0, 0])
        #outimg.SetSpacing([1, 1, 1])
        self.progressCallBack(100)

        sitkUtils.PushVolumeToSlicer(outimg, outputNode)
        slicer.util.setSliceViewerLayers(background=outputNode)