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
    self.parent.categories = ["Bone"]
    self.parent.dependencies = []
    self.parent.contributors = ["Ryan Yan"] # replace with "Firstname Lastname (Organization)"
    self.parent.helpText = """Compares two longitudinally registered scans to determine the development of erosions in the bone.
                            Ideally, the Erosion Volume module should be used to obtain erosion segmentations, but the module can be used with the scans directly, with lower accuracy."""
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = """
Updated on February 17, 2022.
""" # replace with organization, grant and thanks.

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
        compareSegLayout.addRow("Baseline Segmentation: ", self.inputSegSelector1)

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
        compareSegLayout.addRow("Follow-up Segmentation: ", self.inputSegSelector2)

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
        self.inputVolumeSelector.currentNodeChanged.connect(self.onNodeChanged)
        self.inputSegSelector1.currentNodeChanged.connect(self.onNodeChanged)
        self.inputSegSelector2.currentNodeChanged.connect(self.onNodeChanged)
        self.outputImageSelector.currentNodeChanged.connect(self.onNodeChanged)
        self.compareSegButton.clicked.connect(self.onCompareSeg)

        
    
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
        '''Any node changed in step 1'''
        input1 = self.inputSegSelector1.currentNode()
        input2 = self.inputSegSelector2.currentNode()
        output = self.outputImageSelector.currentNode()

        self.compareSegButton.enabled = (input1 and input2 and output)
        if input1:
            self.outputImageSelector.baseName = input1.GetName() + '_COMPARISON'
            self.outputTableSelector.baseName = input1.GetName() + '_TABLE'

    def onCompareSeg(self) -> None:
        '''Compare erosion segmentation button pressed'''
        self.logic.setMasterImage(self.inputVolumeSelector.currentNode())
        self.logic.setSegments(self.inputSegSelector1.currentNode(),
                                    self.inputSegSelector2.currentNode())
        
        outNode = self.outputImageSelector.currentNode()
        self.logic.compareSegments(outNode)

        self.logic.getStatistics(outNode, self.outputTableSelector.currentNode())
        print("Finished/n")

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

import numpy as np
import vtk
class ErosionComparisonLogic(ScriptedLoadableModuleLogic):
    def __init__(self):
        self.progressCallBack = None
        self.segNode1 = None
        self.segNode2 = None
        self.image = None

    def setMasterImage(self, imageNode) -> None:
        '''Set the master image (baseline is ideal, but can use follow-up)'''
        self.image = sitkUtils.PullVolumeFromSlicer(imageNode)
    
    def setSegments(self, segNode1, segNode2) -> None:
        '''Set the segmentations to compare'''
        self.segNode1 = segNode1
        self.segNode2 = segNode2

    def compareSegments(self, outputNode) -> None:
        '''Create a comparison mask from 2 segmentations'''
        print("Comparing Segmentations")

        #create base array
        arr = np.zeros(self.image.GetSize()[::-1])

        #loop through all segments
        for i in range(1, self.segNode2.GetSegmentation().GetNumberOfSegments()):
            #get segment IDs
            try:
                id1 = self.segNode1.GetSegmentation().GetNthSegmentID(i)
            except:
                break
            id2 = self.segNode2.GetSegmentation().GetNthSegmentID(i)

            #get segnments as arrays
            segment1 = slicer.util.arrayFromSegmentBinaryLabelmap(self.segNode1, id1)
            segment2 = slicer.util.arrayFromSegmentBinaryLabelmap(self.segNode2, id2)

            #get image representation for location data
            seg_img1 = self.segNode1.GetBinaryLabelmapInternalRepresentation(id1)
            seg_img2 = self.segNode2.GetBinaryLabelmapInternalRepresentation(id2)

            #get origins
            img_origin = [int(x) for x in np.round(np.divide(self.image.GetOrigin(), self.image.GetSpacing()[0]))]
            seg_origin1 = [int(abs(x)) for x in np.round(np.divide(seg_img1.GetOrigin(), seg_img1.GetSpacing()[0]))]
            seg_origin2 = [int(abs(x)) for x in np.round(np.divide(seg_img2.GetOrigin(), seg_img2.GetSpacing()[0]))]

            print("Origin:", img_origin, seg_origin1, seg_origin2)

            #get shift locations (extent + difference between origins)
            shift1 = [seg_img1.GetExtent()[x] for x in [4, 2, 0]]
            shift1 = [shift1[x] - img_origin[2-x] + seg_origin1[2-x] for x in range(3)]
            shift2 = [seg_img2.GetExtent()[x] for x in [4, 2, 0]]
            shift2 = [shift2[x] - img_origin[2-x] + seg_origin2[2-x] for x in range(3)]

            print("Shift:", shift1, shift2)

            #get coordinates of segment
            coord1 = np.nonzero(segment1)
            coord2 = np.nonzero(segment2)

            #shift coordinates
            for i in range(len(coord1[0])):
                coord1[0][i] += shift1[0]
                coord1[1][i] += shift1[1]
                coord1[2][i] += shift1[2]
            arr[coord1] -= 1

            for i in range(len(coord2[0])):
                coord2[0][i] += shift2[0]
                coord2[1][i] += shift2[1]
                coord2[2][i] += shift2[2]
            arr[coord2] += 1

        print("Generating ouput segmentation")
        #create output image
        outimg = sitk.GetImageFromArray(arr)
        outimg.CopyInformation(self.image)

        #push to slicer
        x = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode")
        sitkUtils.PushVolumeToSlicer(outimg, x)
        outputNode.GetSegmentation().RemoveAllSegments()
        slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(x, outputNode)
        slicer.mrmlScene.RemoveNode(x)
        
        #slicer.util.setSliceViewerLayers(label=outputNode, labelOpacity=0.5)

    #INCOMPLETE
    def compareImages(self, imageNode1, imageNode2, outNode, lower:int, upper:int) -> None:
        image1 = sitkUtils.PullVolumeFromSlicer(imageNode1)
        image2 = sitkUtils.PullVolumeFromSlicer(imageNode2)
        image2.CopyInformation(image1)

        spacing = image1.GetSpacing()[0]
        return
    
    def dilate(self, img:sitk.Image, dist:int) -> sitk.Image:
        '''
        Dilate a mask by a set distance
        '''
        #dilate with distance map
        distance_map = sitk.SignedMaurerDistanceMap(img)
        dilated_img = (distance_map <= dist)
        return dilated_img
    
    def erode(self, img:sitk.Image, dist:int) -> sitk.Image:
        '''
        Erode a mask by a set distance
        '''
        #erode with distance map
        distance_map = sitk.SignedMaurerDistanceMap(img)
        eroded_img = (distance_map <= -dist)
        return eroded_img
    
    def getStatistics(self, segNode, tableNode) -> None:
        '''Return the change in volume of the erosions'''
        import SegmentStatistics
        print("Calculating statistics")
        
        #create columns for new table
        tableNode.RemoveAllColumns()
        
        col_id = tableNode.AddColumn()
        col_id.SetName("Segment ID")
        col_vol = tableNode.AddColumn()
        col_vol.SetName("Change in Volume (mm3)")

        #get statistics
        segStats = SegmentStatistics.SegmentStatisticsLogic()
        segStats.getParameterNode().SetParameter("Segmentation", segNode.GetID())
        segStats.computeStatistics()
        
        #iterate through segments
        segment = segNode.GetSegmentation()
        for i in range(segment.GetNumberOfSegments() - 1):
            #create row of data
            tableNode.AddEmptyRow()
            seg_id = segment.GetNthSegmentID(i + 1)
            tableNode.SetCellText(i, 0, "Segment_" + str(i + 1))
            tableNode.SetCellText(i, 1, str.format('{:.6f}', segStats.getStatistics()[(seg_id, 'LabelmapSegmentStatisticsPlugin.volume_mm3')]))