#-----------------------------------------------------
# JointSpaceWidth.py
#
# Created by:  Ryan Yan
# Created on:  10-02-2022
#
# Description: This module sets up the interface for the CBCT enhancement module
#
#-----------------------------------------------------

import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
import SimpleITK as sitk
import sitkUtils
import os
from JointSpaceWidthLib.SegmentEditor import SegmentEditor

#
# Module for CBCT Enhancement
#
class JointSpaceWidth(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Joint Space Width (Beta)" # TODO make this more human readable by adding spaces
    self.parent.categories = ["Bone Analysis Module (BAM)"]
    self.parent.dependencies = []
    self.parent.contributors = ["Ryan Yan"] # replace with "Firstname Lastname (Organization)"
    self.parent.helpText = """Determines the width of the space in the metacarpal (MCP) joint.
    Can also be used for other joints, but may be suboptimal. Currently under development.
    """
    self.parent.helpText += "<br>For more information see the <a href=https://github.com/ManskeLab/3DSlicer_Erosion_Analysis/wiki/Joint-Space-Width-Module>online documentation</a>."
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
# CBCTEnhanceWidget
#
class JointSpaceWidthWidget(ScriptedLoadableModuleWidget):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """
    def __init__(self, parent):
        # Initialize logics object
        self.logic = JointSpaceWidthLogic()
        # initialize call back object for updating progrss bar
        self.logic.progressCallBack = self.setProgress

        ScriptedLoadableModuleWidget.__init__(self, parent)

    def setup(self) -> None:
        # Buttons for testing
        ScriptedLoadableModuleWidget.setup(self)

        
        
        self.collapsible = ctk.ctkCollapsibleButton()
        self.collapsible.text = "Joint Space Mask"
        self.manualCorrectionCollapsibleButton = ctk.ctkCollapsibleButton()
        self.manualCorrectionCollapsibleButton.text = 'Manual Correction'
        self.collapsible2 = ctk.ctkCollapsibleButton()
        self.collapsible2.text = "Width Analysis"
        
        #setup each collapsible
        self.setupJointMask()
        self.setupManualCorrection()
        self.setupWidthAnalysis()

        #setup buttons
        self.onNodeChanged()
        self.onNodeChanged2()
        self.onSelectManual()

        self.layout.addStretch(1)
        
    # Joint Space Mask-----------------------------------------------------------------*
    def setupJointMask(self) -> None:
        '''Setup Joint Space Mask collapsible'''

        jointMaskLayout = qt.QFormLayout(self.collapsible)
        jointMaskLayout.setVerticalSpacing(5)
        self.layout.addWidget(self.collapsible)

        #
        # Input Image
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
        self.inputVolumeSelector.setToolTip("Image of the bones to be analyzed")
        jointMaskLayout.addRow("Input Volume: ", self.inputVolumeSelector)

        #
        # Input Mask
        #
        self.maskVolumeSelector = slicer.qMRMLNodeComboBox()
        self.maskVolumeSelector.nodeTypes = ["vtkMRMLLabelMapVolumeNode"]
        self.maskVolumeSelector.selectNodeUponCreation = False
        self.maskVolumeSelector.addEnabled = False
        self.maskVolumeSelector.renameEnabled = True
        self.maskVolumeSelector.removeEnabled = True
        self.maskVolumeSelector.noneEnabled = False
        self.maskVolumeSelector.showHidden = False
        self.maskVolumeSelector.showChildNodeTypes = False
        self.maskVolumeSelector.setMRMLScene(slicer.mrmlScene)
        self.maskVolumeSelector.setToolTip("Contour mask of the bones to be analyzed")
        jointMaskLayout.addRow("Input Contour: ", self.maskVolumeSelector)

        #
        # Optional Second Mask
        #
        self.maskVolumeSelector2 = slicer.qMRMLNodeComboBox()
        self.maskVolumeSelector2.nodeTypes = ["vtkMRMLLabelMapVolumeNode"]
        self.maskVolumeSelector2.selectNodeUponCreation = False
        self.maskVolumeSelector2.addEnabled = False
        self.maskVolumeSelector2.renameEnabled = True
        self.maskVolumeSelector2.removeEnabled = True
        self.maskVolumeSelector2.noneEnabled = True
        self.maskVolumeSelector2.showHidden = False
        self.maskVolumeSelector2.showChildNodeTypes = False
        self.maskVolumeSelector2.setMRMLScene(slicer.mrmlScene)
        self.maskVolumeSelector2.setToolTip("Select the second mask if there are separate contour files for each bone")
        jointMaskLayout.addRow("Second Contour: \n(Optional)", self.maskVolumeSelector2)

        #
        # Output Binary Mask of Joint
        #
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
        self.outputVolumeSelector.baseName = 'JOINT'
        self.outputVolumeSelector.setToolTip("Select a volume to output a mask of the joint space to")
        jointMaskLayout.addRow("Output Volume: ", self.outputVolumeSelector)

        # threshold spin boxes (default unit is HU)
        self.lowerThresholdText = qt.QSpinBox()
        self.lowerThresholdText.setMinimum(-9999)
        self.lowerThresholdText.setMaximum(999999)
        self.lowerThresholdText.setSingleStep(100)
        self.lowerThresholdText.value = 686
        jointMaskLayout.addRow("Lower Threshold: ", self.lowerThresholdText)
        self.upperThresholdText = qt.QSpinBox()
        self.upperThresholdText.setMinimum(-9999)
        self.upperThresholdText.setMaximum(999999)
        self.upperThresholdText.setSingleStep(100)
        self.upperThresholdText.value = 4000
        jointMaskLayout.addRow("Upper Threshold: ", self.upperThresholdText)

        self.dilateErodeDistanceText = qt.QSpinBox()
        self.dilateErodeDistanceText.setMinimum(1)
        self.dilateErodeDistanceText.setMaximum(99)
        self.dilateErodeDistanceText.setSingleStep(5)
        self.dilateErodeDistanceText.setSuffix(' voxels')
        self.dilateErodeDistanceText.value = 50
        jointMaskLayout.addRow("Dilate/Erode Distance: ", self.dilateErodeDistanceText)

        #
        # Apply Button
        #
        self.maskButton = qt.QPushButton("Create Joint Mask")
        self.maskButton.enabled = False
        self.maskButton.toolTip = "Create a mask of the joint space between the bones"
        jointMaskLayout.addRow(self.maskButton)

        # Progress Bar
        self.progressBar = qt.QProgressBar()
        self.progressBar.hide()
        jointMaskLayout.addRow(self.progressBar)

        # Connections
        self.collapsible.contentsCollapsed.connect(self.onCollapse1)
        self.inputVolumeSelector.currentNodeChanged.connect(self.onNodeChanged)
        self.outputVolumeSelector.currentNodeChanged.connect(self.onNodeChanged)
        self.maskButton.clicked.connect(self.onJointMask)
    
    # Manual Correction -------------------------------------------------------------------
    def setupManualCorrection(self):
        """Set up widgets in step 3 manual correction"""
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
        self.manualCorrectionCollapsibleButton.connect('contentsCollapsed(bool)', self.onCollapse2)
        self.initButton3.connect('clicked(bool)', self.onInitButtonManual)
        self.applyButton3.connect('clicked(bool)', self.onApplyButtonManual)
        self.cancelButton3.connect('clicked(bool)', self.onCancelButtonManual)
        self.contourVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelectManual)
        self.masterVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelectManual)

    # Width Analysis -----------------------------------------------------------*
    def setupWidthAnalysis(self) -> None:
        '''Setup Width Analysis Collapsible'''
        
        self.collapsible2.collapsed = True
        widthLayout = qt.QFormLayout(self.collapsible2)
        widthLayout.setVerticalSpacing(5)
        self.layout.addWidget(self.collapsible2)

        #
        # Joint Space Mask
        #
        self.jointMaskSelector = slicer.qMRMLNodeComboBox()
        self.jointMaskSelector.nodeTypes = ["vtkMRMLLabelMapVolumeNode"]
        self.jointMaskSelector.selectNodeUponCreation = False
        self.jointMaskSelector.addEnabled = False
        self.jointMaskSelector.renameEnabled = True
        self.jointMaskSelector.removeEnabled = True
        self.jointMaskSelector.noneEnabled = False
        self.jointMaskSelector.showHidden = False
        self.jointMaskSelector.showChildNodeTypes = False
        self.jointMaskSelector.setMRMLScene(slicer.mrmlScene)
        self.jointMaskSelector.setToolTip("Select the joint space mask generated in the previous step")
        widthLayout.addRow("Joint Space Mask", self.jointMaskSelector)

        #
        # Output Distribution Map
        #
        self.outputVolumeSelector2 = slicer.qMRMLNodeComboBox()
        self.outputVolumeSelector2.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        self.outputVolumeSelector2.selectNodeUponCreation = True
        self.outputVolumeSelector2.addEnabled = True
        self.outputVolumeSelector2.renameEnabled = True
        self.outputVolumeSelector2.removeEnabled = True
        self.outputVolumeSelector2.noneEnabled = False
        self.outputVolumeSelector2.showChildNodeTypes = False
        self.outputVolumeSelector2.setMRMLScene(slicer.mrmlScene)
        self.outputVolumeSelector2.baseName = 'WIDTH'
        self.outputVolumeSelector2.setToolTip("Select a volume to output a mask of the joint space to")
        widthLayout.addRow("Output Volume: ", self.outputVolumeSelector2)

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
        widthLayout.addRow("Output Table: ", self.outputTableSelector)

        #
        # Apply Button
        #
        self.analyzeButton = qt.QPushButton("Analyze")
        self.analyzeButton.enabled = True
        self.analyzeButton.toolTip = "Determine the width along the joint space"
        widthLayout.addRow(self.analyzeButton)

        # Connections
        self.jointMaskSelector.currentNodeChanged.connect(self.onNodeChanged2)
        self.collapsible2.contentsCollapsed.connect(self.onCollapse3)
        self.analyzeButton.clicked.connect(self.onAnalyze)
        
        
    
    def onNodeChanged(self) -> None:
        '''Any node changed in first step'''
        #get current node
        inputNode = self.inputVolumeSelector.currentNode()
        maskNode = self.maskVolumeSelector.currentNode()
        output = self.outputVolumeSelector.currentNode()

        #update widget
        if inputNode:
            self.outputVolumeSelector.baseName = inputNode.GetName() + '_JOINT'
        if output:
            self.jointMaskSelector.setCurrentNode(output)
        self.maskButton.enabled = (inputNode and maskNode and output)
    
    def onJointMask(self) -> None:
        '''Create Joint Mask button pressed'''
        print("\nGenerating mask of joint space")
        self.progressBar.show()

        if not self.logic.setParameters(self.inputVolumeSelector.currentNode(),
                                self.maskVolumeSelector.currentNode(),
                                self.maskVolumeSelector2.currentNode(),
                                self.lowerThresholdText.value,
                                self.upperThresholdText.value,
                                self.dilateErodeDistanceText.value):
            print("Invalid input")
            return
        
        success = self.logic.getMask(self.outputVolumeSelector.currentNode())
        if success:
            print("Completed")
            slicer.util.setSliceViewerLayers(label=self.outputVolumeSelector.currentNode(), labelOpacity = 0.5)
        else:
            print("Failed. Check input and parameters")
        
        self.progressBar.hide()

    def onNodeChanged2(self) -> None:
        '''Mask node changed in second step'''
        #get current nodes
        joint = self.jointMaskSelector.currentNode()
        table = self.outputTableSelector.currentNode()

        #update widget
        self.analyzeButton.enabled = (joint and table)
        if joint:
            self.outputTableSelector.baseName = joint.GetName() + "_TABLE"
    
    def onAnalyze(self) -> None:
        '''Analyze button pressed'''
        self.logic.setAnalysisNode(self.jointMaskSelector.currentNode())
        self.logic.analyze(self.outputVolumeSelector2.currentNode(), self.outputTableSelector.currentNode())
    
    def onSelectManual(self):
        """Update the state of the initialize button whenever the selectors in step 3 change"""
        self.initButton3.enabled = (self.contourVolumeSelector.currentNode() and
                                self.masterVolumeSelector.currentNode())

    def onInitButtonManual(self):
        """Run this whenever the initialize button in step 3 is clicked"""
        contourVolumeNode = self.contourVolumeSelector.currentNode()
        masterVolumeNode = self.masterVolumeSelector.currentNode()
        
        self.logic.initManualCorrection(self.segmentEditor, 
                                                contourVolumeNode, 
                                                masterVolumeNode)
        
        self.initButton3.enabled = False
        self.applyButton3.enabled = True
        self.cancelButton3.enabled = True
        
    
    def onCancelButtonManual(self):
        """Run this whenever the cancel button in step 3 is clicked"""
        if slicer.util.confirmOkCancelDisplay('Do you want to discard the manual correction?'):
            contourVolumeNode = self.contourVolumeSelector.currentNode()
            masterVolumeNode = self.masterVolumeSelector.currentNode()
        
            self.logic.cancelManualCorrection(contourVolumeNode, masterVolumeNode)
        
        self.initButton3.enabled = True
        self.applyButton3.enabled = False
        self.cancelButton3.enabled = False
    
    def onApplyButtonManual(self):
        """Run this whenever the apply button in step 3 is clicked"""
        contourVolumeNode = self.contourVolumeSelector.currentNode()
        masterVolumeNode = self.masterVolumeSelector.currentNode()

        self.logic.applyManualCorrection(contourVolumeNode, masterVolumeNode)

        self.initButton3.enabled = True
        self.applyButton3.enabled = False
        self.cancelButton3.enabled = False

    #functions for collapsibles in widget
    def onCollapse1(self):
        '''Funtion for first collapsible'''
        if not self.collapsible.collapsed:
            self.collapsible2.collapsed = True
            self.manualCorrectionCollapsibleButton.collapsed = True

    def onCollapse2(self):
        '''Function for second collapsible'''
        if not self.manualCorrectionCollapsibleButton.collapsed:
            self.collapsible.collapsed = True
            self.collapsible2.collapsed = True
    
    def onCollapse3(self):
        '''Function for second collapsible'''
        if not self.collapsible2.collapsed:
            self.collapsible.collapsed = True
            self.manualCorrectionCollapsibleButton.collapsed = True
    
    def setProgress(self, value:int) -> None:
        """Update the progress bar"""
        self.progressBar.setValue(value)
    
class JointSpaceWidthLogic:
    def __init__(self):
        self.progressCallBack = None
        self.mask = JointSpaceMask()
        self.analysis = JointSpaceAnalysis()
        self.outImg = None
        self.jointNode = None
        self._segmentNodeId = ""

    def setParameters(self, inputNode, mask1, mask2, lower:int, upper:int, distance:int) -> bool:
        '''
        Set the parameters to create the joint space mask
        '''
        #Pull images
        inputImg = sitkUtils.PullVolumeFromSlicer(inputNode)
        mask1Img = sitkUtils.PullVolumeFromSlicer(mask1)
        mask2Img = sitkUtils.PullVolumeFromSlicer(mask2) if mask2 else None

        #Set parameters
        self.mask.setAnalysisParameters(inputImg, mask1Img, mask2Img, lower, upper, distance)

        return True

    def getMask(self, output) -> bool:
        '''
        Get the joint space mask
        '''
        #Setup
        print("Running Joint Space Width Algorithm")
        progress = 0
        numSteps = 6
        progressStep = 100 / numSteps

        #Run the steps of the algorithm
        for i in range(numSteps):
            self.mask.execute(i)
            
            progress += progressStep
            self.progressCallBack(progress)

        #Push output image to volume
        sitkUtils.PushVolumeToSlicer(self.mask.getOutput(), output)
        return True
    
    def setAnalysisNode(self, inputNode) -> bool:
        self.jointNode = inputNode
        try:
            self.analysis.setImage(sitkUtils.PullVolumeFromSlicer(inputNode))
            return True
        except:
            return False
    
    def analyze(self, output, table) -> None:
        #segNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode")
        #slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(self.jointNode, segNode)

        out_img = self.analysis.getWidth()
        sitkUtils.PushVolumeToSlicer(out_img, output)

        #create columns if new table
        if (table.GetNumberOfColumns == 0):
        
            col_max = table.AddColumn()
            col_max.SetName("Maximum JSW")
            col_min = table.AddColumn()
            col_min.SetName("Minimum JSW")
            col_avg = table.AddColumn()
            col_avg.SetName("Average JSW")
            col_std = table.AddColumn()
            col_std.SetName("Standard Deviation")

        #add data
        stats = self.analysis.getStats()
        table.AddEmptyRow()
        for i in range(4):
            table.SetCellText(0, i, str(stats[i]))

        # TODO: volume and visualization
        #self.analysis.getVolume(segNode)
    def labelmapToSegmentationNode(self, labelMapNode, segmentNode):
        """
        Load the label map volume to the segmentations, with each label to a different 
        segmentation. 

        Args:
            labelMapNode(vtkMRMLLabelMapVolume)
            segmentNode(vtkSegmentationNode): will be modified.
        """
        slicer.vtkSlicerSegmentationsModuleLogic.ImportLabelmapToSegmentationNode(labelMapNode, segmentNode, "")
  
    def segmentationNodeToLabelmap(self, segmentNode, labelMapNode, referenceVolumeNode):
        """
        Load the segmentations to the label map volume. Labels go from 1, 2,..., to N. 
        Order of the segmentations are maintained. 

        Args:
            segmentNode (vtkMRMLSegmentationNode)
            labelMapNode (vtkMRMLLabelMapVolumeNode): will be modified.
            referenceVolumeNode (vtkMRMLScalarVolumeNode): decides the size of the 
            resulting label map volume. 
        """
        visibleSegmentIds = vtk.vtkStringArray()
        segmentNode.GetDisplayNode().GetVisibleSegmentIDs(visibleSegmentIds)
        slicer.vtkSlicerSegmentationsModuleLogic.ExportSegmentsToLabelmapNode(segmentNode, 
                                                                            visibleSegmentIds,
                                                                            labelMapNode, 
                                                                            referenceVolumeNode)
    
    def initManualCorrection(self, segmentEditor, contourVolumeNode, masterVolumeNode):
        """
        Set up the segmentation editor for manual correction of contour. 
        Create new segmentation node if not created. 
        Load contour to the segmentation editor.
        
        Args:
            segmentEditor (SegmentEditor): will be modified
            contourVolumeNode (vtkMRMLLabelMapVolumeNode)
            masterVolumeNode (vtkMRMLScalarVolumeNode)

        Returns:
            bool: True for success, False otherwise.
        """
        segmentNode = slicer.mrmlScene.GetNodeByID(self._segmentNodeId)

        if (contourVolumeNode and masterVolumeNode):
            if not segmentNode:
                segmentNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentationNode')
                segmentNode.SetReferenceImageGeometryParameterFromVolumeNode(masterVolumeNode)
            self._segmentNodeId = segmentNode.GetID()
            self.labelmapToSegmentationNode(contourVolumeNode, segmentNode)
            # set segmentation node and master volume node in segmentation editor
            segmentEditor.setSegmentationNode(segmentNode)
            segmentEditor.setMasterVolumeNode(masterVolumeNode)
            # update viewer windows
            slicer.util.setSliceViewerLayers(background=masterVolumeNode)

            return True
        return False
    
    def cancelManualCorrection(self, contourVolumeNode, masterVolumeNode):
        """
        Cancel the manual correction. 
        Remove the segmentation node in the segmentation editor. 

        Args:
            contourVolumeNode (vtkMRMLLabelMapVolumeNode)
            masterVolumeNode (vtkMRMLScalarVolumeNode)

        Returns:
            bool: True for success, False if nodes are missing.
        """
        segmentNode = slicer.mrmlScene.GetNodeByID(self._segmentNodeId)

        if segmentNode:
            # remove the current segmentation node
            slicer.mrmlScene.RemoveNode(segmentNode)
        if (contourVolumeNode and masterVolumeNode):
            # update viewer windows
            slicer.util.setSliceViewerLayers(background=masterVolumeNode,
                                            label=contourVolumeNode, 
                                            labelOpacity=0.5)
        
        return (segmentNode and contourVolumeNode and masterVolumeNode)

    def applyManualCorrection(self, contourVolumeNode, masterVolumeNode):
        """
        Apply the manual correction.
        Load the contour back to the input node.
        Remove the segmentation node in the segmentation editor.

        Args:
            contourVolumeNode (vtkMRMLLabelMapVolumeNode): will be modified
            masterVolumeNode (vtkMRMLScalarVolumeNode)
        
        Returns:
            bool: True for success, False otherwise.
        """
        segmentNode = slicer.mrmlScene.GetNodeByID(self._segmentNodeId)

        if (segmentNode and contourVolumeNode and masterVolumeNode):
            self.segmentationNodeToLabelmap(segmentNode, contourVolumeNode, masterVolumeNode)
            # remove the current segmentation node
            slicer.mrmlScene.RemoveNode(segmentNode)
            # update viewer windows
            slicer.util.setSliceViewerLayers(background=masterVolumeNode,
                                            label=contourVolumeNode, 
                                            labelOpacity=0.5)

            return True
        return False

    
import numpy as np
class JointSpaceMask:

    def __init__(self):

        #set default params
        self.image = None
        self.mask1 = None
        self.mask2 = None
        self.lower = 686
        self.upper = 4000
        self.distance = 5

        #output images
        self.adj_mask = None
        self.working_img = None
        self.out_img = None

    def setAnalysisParameters(self, image:sitk.Image, mask1:sitk.Image, mask2:sitk.Image, lower:int, upper:int, distance:int) -> None:
        '''
        Set the parameters for joint space mask creation
        '''
        #set params
        self.image = image
        self.mask1 = mask1
        self.mask2 = mask2
        self.lower = lower
        self.upper = upper
        self.distance = distance / image.GetSpacing()[0]


    def execute(self, step: int) -> bool:
        '''
        Run the steps of the algorithm
        '''
        
        #step 1: Align mask with image and combine if 2 masks given
        if step == 0:
            if self.mask2:
                print("Combining masks and aligning to image")
                self.adj_mask = self.combine()
            else:
                print("Aligning mask to image")
                self.adj_mask = self.adjust()

        #step 2: Dilate to close joint space
        elif step == 1:
            print("Dilating image to close joint space")
            self.working_img = self.dilate(self.adj_mask)

        #step 3: Fill in holes in joint space
        elif step == 2:
            print("Filling in holes")
            self.working_img = self.fill_holes(self.working_img)

        #step 4: Erode the image back, forming original image with joint space added
        elif step == 3:
            print("Eroding image with joint space")
            self.working_img = self.erode(self.working_img)

        #step 5: Subtract the initial mask so that only the joint space remains
        elif step == 4:
            print("Subtracting initial mask")
            self.working_img = self.subtract()
        
        #step 6: Smoothen joint space mask and remove residual areas outside the joint
        elif step == 5:
            print("Smoothening joint space mask")
            self.distance = 0.1 / self.image.GetSpacing()[0]
            self.working_img = self.erode(self.working_img)
            self.working_img = self.dilate(self.working_img)

    
    def combine(self) -> sitk.Image:
        '''
        Combine two masks and align them with the image of the bone
        '''
        #create new images
        mask1Adj = sitk.Image(self.image.GetSize(), 0)
        mask1Adj.CopyInformation(self.image)

        mask2Adj = sitk.Image(self.image.GetSize(), 0)
        mask2Adj.CopyInformation(self.image)
        
        #paste image filter
        paste = sitk.PasteImageFilter()

        #paste first mask
        destination = np.round(np.divide(np.subtract(self.mask1.GetOrigin(), self.image.GetOrigin()), self.image.GetSpacing()[0]))
        destInt = [int(destination[i]) for i in range(3)]
        paste.SetDestinationIndex(destInt)
        paste.SetSourceSize(self.mask1.GetSize())
        mask1Adj = paste.Execute(mask1Adj, sitk.Cast(self.mask1, sitk.sitkInt8))

        #paste second mask
        destination = np.round(np.divide(np.subtract(self.mask2.GetOrigin(), self.image.GetOrigin()), self.image.GetSpacing()[0]))
        destInt = [int(destination[i]) for i in range(3)]
        paste.SetDestinationIndex(destInt)
        paste.SetSourceSize(self.mask2.GetSize())
        mask2Adj = paste.Execute(mask2Adj, sitk.Cast(self.mask2, sitk.sitkInt8))
        
        return sitk.Or(mask1Adj, mask2Adj)

    def adjust(self) -> sitk.Image:
        '''
        Align the mask with the bone
        '''
        #create new image
        maskAdj = sitk.Image(self.image.GetSize(), 0)
        maskAdj.CopyInformation(self.image)
        
        paste = sitk.PasteImageFilter()

        destination = np.round(np.divide(np.subtract(self.mask1.GetOrigin(), self.image.GetOrigin()), self.image.GetSpacing()[0]))
        destInt = [int(destination[i]) for i in range(3)]
        paste.SetDestinationIndex(destInt)
        paste.SetSourceSize(self.mask1.GetSize())
        maskAdj = paste.Execute(maskAdj, sitk.Cast(self.mask1, sitk.sitkInt8))
    
    def dilate(self, img:sitk.Image) -> sitk.Image:
        '''
        Dilate a mask by a set distance
        '''
        #dilate with distance map
        distance_map = sitk.SignedMaurerDistanceMap(img)
        dilated_img = (distance_map <= self.distance)
        return dilated_img

    def fill_holes(self, img:sitk.Image) -> sitk.Image:
        '''
        Fill in holes within a mask
        '''
        #fill in holes in the mask
        fillter = sitk.BinaryFillholeImageFilter()
        fillter.SetForegroundValue(1)
        fillter.SetFullyConnected(True)
        return fillter.Execute(img)

    def erode(self, img:sitk.Image) -> sitk.Image:
        '''
        Erode a mask by a set distance
        '''
        #erode with distance map
        distance_map = sitk.SignedMaurerDistanceMap(img)
        eroded_img = (distance_map <= -self.distance)
        return eroded_img

    def subtract(self) -> sitk.Image:
        '''
        Subtract the original mask from the mask with joint space
        '''
        #subtract mask to get joint space
        subtract_img = sitk.And(sitk.Cast(self.working_img, sitk.sitkInt8), sitk.Not(self.adj_mask))
        return subtract_img
        
    def getOutput(self) -> sitk.Image:
        '''
        Get the output joint space mask
        '''
        return self.working_img

class JointSpaceAnalysis():    
    def __init__(self) -> None:
        self.img = None
        self.stats = None

    def setImage(self, img:sitk.Image) -> None:
        '''
        Set the joint space mask created in the previous step
        '''
        self.img = img

    def getWidth(self) -> sitk.Image:
        '''
        Determine the joint space width
        '''
        #get distance map
        dist_map = sitk.SignedMaurerDistanceMapImageFilter()
        dist_map.SetInsideIsPositive(True)

        #use distance map to find radius of spheres for fit
        dist_img = dist_map.Execute(sitk.BinaryDilate(self.img, [10, 10, 10]))
        dist_img = sitk.Threshold(dist_img, lower=0, upper=1000)

        #get gradient of distance map, use to find median of joint
        grad_img = (sitk.GradientMagnitudeRecursiveGaussian(dist_img, sigma=self.img.GetSpacing()[0]))

        #find maximum point in image
        arr = sitk.GetArrayFromImage(dist_img)
        seed = np.argmax(arr)
        seed = np.unravel_index(seed, arr.shape)
        seed = (68, 146, 173)
        seed = [int(seed[2 - x]) for x in range(3)]
        print(seed)
        print(grad_img.GetPixel(seed[0], seed[1], seed[2]))

        # TODO: figure out a way to get median line/curve
        median = sitk.ConfidenceConnected(grad_img, [seed], numberOfIterations=0, multiplier=0.2)
        return median

        
        #get statistics with numpy
        out_img = sitk.Threshold(sitk.Multiply(out_img, sitk.Cast(median, sitk.sitkFloat32)), lower=50, upper=1000)
        arr = sitk.GetArrayFromImage(out_img)
        q = arr[np.nonzero(arr)]
        self.stats = (np.max(q), np.min(q), np.average(q), np.std(q))
        print(self.stats)
        
        return out_img

    def getStats(self) -> tuple:
        '''
        Return the max, min, average, and stdev of the joint space width

        Format: tuple(float, float, float, float)
        '''
        return self.stats

    def getVolume(self, segNode) -> None:
        '''
        Return the volume of the joint space (incomplete)
        '''
        import SegmentStatistics

        segStats = SegmentStatistics.SegmentStatisticsLogic()
        segStats.getParameterNode().SetParameter("Segmentation", segNode.GetID())
        segStats.computeStatistics()
        print(segStats.getStatistics()[('jake', 'LabelmapSegmentStatisticsPlugin.volume_mm3')])



