#-----------------------------------------------------
# ErosionDetectionLogic.py
#
# Created by:  Mingjie Zhao
# Created on:  23-10-2020
#
# Description: This module contains the logics class 
#              for the 3D Slicer Erosion Detection extension.
#
#-----------------------------------------------------
import slicer
from slicer.ScriptedLoadableModule import *
import vtk
import SimpleITK as sitk
import sitkUtils
import logging
from ErosionDetectionLib.SegmentEditor import SegmentEditor
from ErosionDetectionLib.VoidVolumeLogic import VoidVolumeLogic
from ErosionDetectionLib.ErosionStatisticsLogic import ErosionStatisticsLogic

#
# ErosionDetectionLogic
#
class ErosionDetectionLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module. 
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self):
    # initialize call back object for updating progrss bar
    self.progressCallBack = None

    self.voidVolume = VoidVolumeLogic()
    self.erosionStatistics = ErosionStatisticsLogic()
    self.voxelSize = 0.0607
    self._segmentNodeId = ""      # will be reused
    self._contourSegmentId = ""   # will be reused
    self._erosionSegmentIndex = 1 # will be incremented, used for relabeling segmentation names

  def RASToIJKCoords(self, ras_3coords, ras2ijk):
    """
    Convert from RAS coordinates to SimpleITK coordinates. 
    Normally this involves negating the x, y coordinates, 
    and scaling the coordinates with respect to the spacing. 

    Args:
      ras_3coords (list of Int)
      ras2ijk (vtkMatrix4x4): 4 by 4 matrix that converts from RAS to IJK

    Returns:
      tuple of int
    """
    ras_4coords = ras_3coords + [1]
    return tuple((int(i) for i in ras2ijk.MultiplyPoint(ras_4coords)[:3]))

  def setErosionParameters(self, inputVolumeNode, inputContourNode, outputVolumeNode,
    lower, upper, fiducialNode, minimalRadius, dilationErosionRadius):
    """
    Set parameters to be used by the erosion detection algorithm. 

    Args:
      inputVolumeNode (vtkMRMLScalarVolumeNode)
      inputContourNode (vtkMRMLLabelMapVolumeNode)
      outputVolumeNode (vtkMRMLLabelMapVolumeNode)
      lower (int)
      upper (int)
      fiducialNode (vtkMRMLFiducialNode)
      minimalRadius (int) : used in the SimpleITK Distance Transformation filter.
      dilationErosionRadius (int) : used in the SimpleITK Dilate/Erode filters.

    Returns:
      bool: True for success, False if inputs are not valid.
    """
    # check input validity
    if (inputContourNode.GetID() == outputVolumeNode.GetID()):
      slicer.util.errorDisplay('Input contour is the same as output volume. Choose a different output volume.')
      return False

    if (lower > upper):
      slicer.util.errorDisplay('Lower threshold cannot be greater than upper threshold.')
      return False
    
    fiducial_num = fiducialNode.GetNumberOfFiducials()
    if (fiducial_num == 0):
      slicer.util.errorDisplay('No seed points have been plotted.')
      return False

    self.voidVolume.setThresholds(lower, upper)
    self.voidVolume.setRadii(minimalRadius, dilationErosionRadius)

    model_img = sitkUtils.PullVolumeFromSlicer(inputVolumeNode.GetName())
    contour_img = sitkUtils.PullVolumeFromSlicer(inputContourNode.GetName())
    self.voidVolume.setModelImage(model_img)
    self.voidVolume.setContourImage(sitk.Cast(contour_img, sitk.sitkUInt8))

    # seed points
    physical_coord = [0,0,0]
    ras2ijk = vtk.vtkMatrix4x4()
    inputVolumeNode.GetRASToIJKMatrix(ras2ijk)
    seeds = []
    for i in range(fiducial_num):
      fiducialNode.GetNthFiducialPosition(i,physical_coord) # slicer coordinates
      itk_coord = self.RASToIJKCoords(physical_coord, ras2ijk) # SimpleITK coordinates
      seeds.append(itk_coord)
    self.voidVolume.setSeeds(seeds)
    
    return True

  def getErosions(self, inputVolumeNode, outputVolumeNode):
    """
    Run the erosion detection algorithm and store the result in the output volume. 
    Return False if fail, and return true if successful.

    Args:
      inputVolumeNode (vtkMRMLScalarVolumeNode)
      outputVolumeNode (vtkMRMLLabelMapVolumeNode): will be modified.

    Returns:
      bool: True for success, False otherwise.
    """
    # initialize progress value
    progress = 0
    self.progressCallBack(progress)
    increment = 100 // self.voidVolume.stepNum # progress bar increment value
    logging.info('Processing started')
    
    # run the erosion detection algorithm
    try:
      while (self.voidVolume.execute()): # execute the next step
        progress += increment
        self.progressCallBack(progress) # update progress bar
    except Exception as e:
      slicer.util.errorDisplay('Error')
      print(e)
      return False

    # push result to outputVolumeNode
    void_volume_img = self.voidVolume.getOutput()
    sitkUtils.PushVolumeToSlicer(void_volume_img, outputVolumeNode)
    logging.info('Processing completed')

    # update viewer windows
    slicer.util.setSliceViewerLayers(background=inputVolumeNode,
                                     label=outputVolumeNode, 
                                     labelOpacity=0.5)
    return True

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

  def relabelSegments(self, segmentNode, beginIndex, endIndex, baseName):
    """
    Label each erosion 'baseName_XXX' and give each erosion a different colour.

    Args:
      segmentNode (vtkSegmentationNode): will be modified.
      beginIndex (int): the index of the first segmentation to be relabeled.
      endIndex (int): the index of the last segmentation to be relabeled, plus 1
      baseName (Str): Each erosion will be labeled baseName + '_' + Index.
    """
    colorNode = slicer.mrmlScene.GetFirstNodeByName('Labels')
    colorNum = colorNode.GetNumberOfColors()   # number of available colours
    color = [0,0,0,0]   # will be modified
    for segmentIndex in range(beginIndex, endIndex):
      segment = segmentNode.GetSegmentation().GetNthSegment(segmentIndex)
      # set name
      segment.SetName("%s_%d" % (baseName, self._erosionSegmentIndex))
      # set colour
      colorNode.GetColor(self._erosionSegmentIndex, color)
      segment.SetColor(color[0:3])
      self._erosionSegmentIndex += 1
      if (self._erosionSegmentIndex >= colorNum):
        self._erosionSegmentIndex = 1
    
  def enterSegmentEditor(self, segmentEditor):
    """
    Run this whenever the module is reopened. 
    Prepare the segmentation editor for manual correction of the erosions. 
    Set segmentation node in the segmentation editor, if node has been created. 
    The intensity mask is on, voxels with low intensities is editable. 
    The overwrite mode is set to overwrite visible segments. 
    The mask mode is set to paint allowed inside the contour. 

    Args:
      segmentEditor (SegmentEditor): will be modified

    Returns:
      bool: True if segmentation has previously been created, False otherwise.
    """
    segmentNode = slicer.mrmlScene.GetNodeByID(self._segmentNodeId)

    segmentEditor.enter()
    segmentEditor.setMasterVolumeIntensityMask(True)
    segmentEditor.setOverWriteMode(slicer.vtkMRMLSegmentEditorNode.OverwriteVisibleSegments)
    if segmentNode: # if the segmentation node exists, switch to it
      segmentEditor.setSegmentationNode(segmentNode)
      segmentEditor.setMaskMode(slicer.vtkMRMLSegmentEditorNode.PaintAllowedInsideSingleSegment,
                                self._contourSegmentId)
                                     
      return True
    return False

  def exitSegmentEditor(self, segmentEditor):
    """
    Run this whenever the module is closed. 
    Remove the segmentation editor keyboard shortcuts. 

    Args:
      segmentEditor (SegmentEditor): will be modified

    Returns:
      bool: True always.
    """
    segmentEditor.exit()
    
    return True

  def initManualCorrection(self, segmentEditor, erosionVolumeNode, 
                           masterVolumeNode, contourVolumeNode):
    """
    Set up the segmentation editor for manual correction of erosions. 
    Create new segmentation node if not created. 
    Load contour to the segmentation editor if not loaded.
    Load erosions to the segmentation editor. 
    The mask mode is set to paint allowed inside the contour. 

    Args:
      segmentEditor (SegmentEditor): will be modified
      erosionVolumeNode (vtkMRMLLabelMapVolumeNode)
      masterVolumeNode (vtkMRMLScalarVolumeNode)
      contourVolumeNode (vtkMRMLLabelMapVolumeNode)

    Returns:
      bool: True for success, False otherwise.
    """
    segmentNode = slicer.mrmlScene.GetNodeByID(self._segmentNodeId)

    if (erosionVolumeNode and masterVolumeNode and contourVolumeNode):
      if not segmentNode:
        # create new segmentation node
        segmentNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", 
                                                         "TemporarySegmentationNode")
        segmentNode.SetReferenceImageGeometryParameterFromVolumeNode(masterVolumeNode)
        # binarize contour
        tempLabelVolumeNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode",
                                                                 "MASK_Dont_Modify")
        slicer.vtkSlicerVolumesLogic().CreateLabelVolumeFromVolume(slicer.mrmlScene, 
                                                                   tempLabelVolumeNode, 
                                                                   contourVolumeNode)
        contourArray = slicer.util.arrayFromVolume(contourVolumeNode)
        tempLabelArray = slicer.util.arrayFromVolume(tempLabelVolumeNode)
        tempLabelArray[contourArray > 0] = 1
        slicer.util.arrayFromVolumeModified(tempLabelVolumeNode)
        # push contour to segmentation node
        self.labelmapToSegmentationNode(tempLabelVolumeNode, segmentNode)
        self._contourSegmentId = segmentNode.GetSegmentation().GetNthSegmentID(0) # first segment ID
        segmentNode.GetDisplayNode().SetSegmentVisibility(self._contourSegmentId, False)
        # store current widget info
        self._erosionSegmentIndex = 1
        self._segmentNodeId = segmentNode.GetID()
        slicer.mrmlScene.RemoveNode(tempLabelVolumeNode)
      # load erosions
      segmentNumBefore = segmentNode.GetSegmentation().GetNumberOfSegments()
      self.labelmapToSegmentationNode(erosionVolumeNode, segmentNode)
      segmentNumAfter = segmentNode.GetSegmentation().GetNumberOfSegments()
      self.relabelSegments(segmentNode, segmentNumBefore, segmentNumAfter, "Segment")
      # set parameters in segmentation editor
      segmentEditor.setSegmentationNode(segmentNode)
      segmentEditor.setMasterVolumeNode(masterVolumeNode)
      segmentEditor.setMaskMode(slicer.vtkMRMLSegmentEditorNode.PaintAllowedInsideSingleSegment,
                                     self._contourSegmentId)
      # update viewer windows
      slicer.util.setSliceViewerLayers(background=masterVolumeNode)

      return True
    return False

  def cancelManualCorrection(self, erosionVolumeNode, masterVolumeNode):
    """
    Cancel the manual correction. 
    Remove the segmentation node in the segmentation editor. 
    
    Args:
      erosionVolumeNode (vtkMRMLLabelMapVolumeNode)
      masterVolumeNode (vtkMRMLScalarVolumeNode)

    Returns:
      bool: True for success, False if nodes are missing. 
    """
    segmentNode = slicer.mrmlScene.GetNodeByID(self._segmentNodeId)

    if segmentNode:
      # remove the current segmentation node
      slicer.mrmlScene.RemoveNode(segmentNode)
    if (erosionVolumeNode and masterVolumeNode):
      # update viewer windows
      slicer.util.setSliceViewerLayers(background=masterVolumeNode,
                                       label=erosionVolumeNode, 
                                       labelOpacity=0.5)

    return (segmentNode and erosionVolumeNode and masterVolumeNode)

  def applyManualCorrection(self, erosionVolumeNode, masterVolumeNode):
    """
    Apply the manual correction. 
    Load the manual correction back to the input node. 
    Remove the segmentation node in the segmentation editor.

    Args:
      erosionVolumeNode (vtkMRMLLabelMapVolumeNode): will be modified
      masterVolumeNode (vtkMRMLScalarVolumeNode)
    
    Returns:
      bool: True for success, False otherwise.
    """
    segmentNode = slicer.mrmlScene.GetNodeByID(self._segmentNodeId)

    if (erosionVolumeNode and masterVolumeNode and segmentNode):
      segmentNode.GetSegmentation().RemoveSegment(self._contourSegmentId)
      self.segmentationNodeToLabelmap(segmentNode, erosionVolumeNode, masterVolumeNode)
      # remove the current segmentation node
      slicer.mrmlScene.RemoveNode(segmentNode)
      # update viewer windows
      slicer.util.setSliceViewerLayers(background=masterVolumeNode,
                                       label=erosionVolumeNode, 
                                       labelOpacity=0.5)

      return True
    return False

  def getStatistics(self, inputErosionNode, outputTableNode):
    """
    Get erosion statistics from the label map volume and store them in the 
    output table. Each erosion will be labeled 'erosion_XXX' in the table. 
    Supported statistics include volume, surface area, sphericity, and location. 

    Args:
      inputErosionNode (vtkMRMLLabelMapVolumeNode)
      outputTableNode (vtkMRMLTableNode): will be modified
    """
    # initialize node, each erosion is labeled 'erosion_XXX'
    segmentNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", 
                                                     "TemporarySegmentationNode")
    self.labelmapToSegmentationNode(inputErosionNode, segmentNode)
    for segmentIndex in range(segmentNode.GetSegmentation().GetNumberOfSegments()):
      segment = segmentNode.GetSegmentation().GetNthSegment(segmentIndex)
      segment.SetName("erosion_%03d" % (segmentIndex+1))

    # display statistics table and connect signals
    #  erosions are centred in the viewer windows upon selection
    self.erosionStatistics.setSegmentNode(segmentNode)
    self.erosionStatistics.setInputErosionNode(inputErosionNode)
    self.erosionStatistics.setOutputTableNode(outputTableNode)
    self.erosionStatistics.displayErosionStatistics()
    
    # update widgets
    self.segmentationNodeToLabelmap(segmentNode, inputErosionNode, inputErosionNode)
    slicer.util.setSliceViewerLayers(label=inputErosionNode, 
                                     labelOpacity=0.5)
    slicer.mrmlScene.RemoveNode(segmentNode)
