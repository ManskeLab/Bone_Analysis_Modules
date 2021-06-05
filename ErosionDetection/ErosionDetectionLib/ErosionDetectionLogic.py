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
from numpy import copy
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
    self._segmentNodeId = ""      # temporary segment node in the segment editor
    self._contourSegmentId = ""   # temporary contour segment in the segment editor
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

    # segmentation parameters
    self.voidVolume.setThresholds(lower, upper)
    self.voidVolume.setRadii(minimalRadius, dilationErosionRadius)

    # images
    model_img = sitkUtils.PullVolumeFromSlicer(inputVolumeNode.GetName())
    contour_img = sitkUtils.PullVolumeFromSlicer(inputContourNode.GetName())
    self.voidVolume.setModelImage(model_img)
    self.voidVolume.setContourImage(sitk.Cast(contour_img, sitk.sitkUInt8))

    # seed points
    physical_coord = [0,0,0]
    ras2ijk = vtk.vtkMatrix4x4()
    inputVolumeNode.GetRASToIJKMatrix(ras2ijk)
    seeds = []
    erosion_ids = []
    for i in range(fiducial_num):
      # store seed point coordinates in the variable seeds
      fiducialNode.GetNthFiducialPosition(i,physical_coord) # slicer seed coordinates
      itk_coord = self.RASToIJKCoords(physical_coord, ras2ijk) # SimpleITK coordinates
      seeds.append(itk_coord)
      # store seed point number in the variable erosion_ids
      seed_id = fiducialNode.GetNthFiducialLabel(i).split('-')[-1] # seed name postfix
      erosion_id_max = 0
      try:
        erosion_id = int(seed_id)
        erosion_id_max = max(erosion_id, erosion_id_max)
      except ValueError: # if postfix does not end with a dash followed by a number
        erosion_id_max += 1
        erosion_id = erosion_id_max
      erosion_ids.append(erosion_id)
    self.voidVolume.setSeeds(seeds)
    self.voidVolume.setErosionIds(erosion_ids)
    
    return True

  def getErosions(self, inputVolumeNode, outputVolumeNode):
    """
    Run the erosion detection algorithm and store the result in the output volume. 
    Return False if fail, and return true if successful.
    The erosions will have label values that match the seed point postfixes

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
    outputVolumeNode.GetDisplayNode().SetAndObserveColorNodeID(
      'vtkMRMLColorTableNodeFileGenericColors.txt')

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
    Create new temporary segmentation node if not created. 
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
        #self._erosionSegmentIndex = 1
        self._segmentNodeId = segmentNode.GetID()
        slicer.mrmlScene.RemoveNode(tempLabelVolumeNode)
      # load erosions
      self.labelmapToSegmentationNode(erosionVolumeNode, segmentNode)
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
    Remove the temporary segmentation node in the segmentation editor. 
    
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
    Remove the temporary segmentation node in the segmentation editor.

    Args:
      erosionVolumeNode (vtkMRMLLabelMapVolumeNode): will be modified
      masterVolumeNode (vtkMRMLScalarVolumeNode)
    
    Returns:
      bool: True for success, False otherwise.
    """
    segmentNode = slicer.mrmlScene.GetNodeByID(self._segmentNodeId)

    if (erosionVolumeNode and masterVolumeNode and segmentNode):
      segmentation = segmentNode.GetSegmentation()

      # remove mask/contour from segment node
      segmentation.RemoveSegment(self._contourSegmentId)

      # create a mapping that decides which value each erosion will be labeled with.
      #  the keys are the erosion segment indices in the segment node, 
      #  and the values are the erosion label values, which match the seed point numbers
      label_ids = {}
      seg_num = segmentation.GetNumberOfSegments()
      for i in range(seg_num):
        segment_name = segmentation.GetNthSegment(i).GetName()
        try: # obtain the label value from the segment name
          label_id = int(segment_name.split('_')[-1])
          label_ids[i+1] = label_id
        except ValueError:
          pass
      self.segmentationNodeToLabelmap(segmentNode, erosionVolumeNode, masterVolumeNode)

      # relabel erosions
      erosionVolumeArray = slicer.util.arrayFromVolume(erosionVolumeNode)
      copyArray = copy(erosionVolumeArray)
      print(label_ids)
      for key, value in label_ids.items():
        erosionVolumeArray[copyArray==key] = value
      slicer.util.arrayFromVolumeModified(erosionVolumeNode)

      # remove the temporary segmentation node
      slicer.mrmlScene.RemoveNode(segmentNode)

      # update viewer windows
      slicer.util.setSliceViewerLayers(background=masterVolumeNode,
                                       label=erosionVolumeNode, 
                                       labelOpacity=0.5)
      erosionVolumeNode.GetDisplayNode().SetAndObserveColorNodeID(
        'vtkMRMLColorTableNodeFileGenericColors.txt')

      return True
    return False

  def getStatistics(self, inputErosionNode, outputTableNode):
    """
    Get erosion statistics from the label map volume and store them in the 
    output table. Each erosion will be labeled 'Erosion_XXX' in the table. 
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
      label_id = segment.GetName()
      segment.SetName("Erosion-"+label_id)

    # display statistics table and connect signals,
    #  erosions are centred in the viewer windows upon selection
    self.erosionStatistics.setSegmentNode(segmentNode)
    self.erosionStatistics.setInputErosionNode(inputErosionNode)
    self.erosionStatistics.setOutputTableNode(outputTableNode)
    self.erosionStatistics.displayErosionStatistics()
    
    # update widgets
    slicer.util.setSliceViewerLayers(label=inputErosionNode, 
                                     labelOpacity=0.5)
    slicer.mrmlScene.RemoveNode(segmentNode)
