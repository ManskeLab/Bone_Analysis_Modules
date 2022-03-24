#-----------------------------------------------------
# ErosionVolumeLogic.py
#
# Created by:  Mingjie Zhao
# Created on:  23-10-2020
#
# Description: This module contains the logics class 
#              for the 3D Slicer Erosion Volume extension.
#
#-----------------------------------------------------
import slicer
from slicer.ScriptedLoadableModule import *
import vtk
import SimpleITK as sitk
import sitkUtils
import numpy as np
from numpy import copy
import logging, os
from ErosionVolumeLib.SegmentEditor import SegmentEditor
from ErosionVolumeLib.VoidVolumeLogic import VoidVolumeLogic
from ErosionVolumeLib.ErosionStatisticsLogic import ErosionStatisticsLogic

#
# ErosionVolumeLogic
#
class ErosionVolumeLogic(ScriptedLoadableModuleLogic):
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

  def RASToIJKCoords(self, ras_3coords:list, ras2ijk) -> tuple:
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
    return tuple((round(i) for i in ras2ijk.MultiplyPoint(ras_4coords)[:3]))

  def setDefaultDirectory(self, inputVolumeNode) -> None:
    """
    Set the default directory to be the same as where the inputVolumeNode is stored.
    Files created after this method is called will be saved in that directory.

    Args:
      inputVolumeNode (vtkMRMLScalarVolumeNode)
    """
    storageNode = inputVolumeNode.GetStorageNode()
    if storageNode:
      dir = os.path.dirname(storageNode.GetFullNameFromFileName())
      slicer.mrmlScene.SetRootDirectory(dir)

  def setErosionParameters(self, inputVolumeNode, inputContourNode, sigma:float, fiducialNode, minimalRadius:int, dilateErodeDistance:int,
        method:int=None, lower:int=None, upper:int=None) -> bool:
    """
    Set parameters used by the Erosion Volume algorithm. 

    Args:
      inputVolumeNode (vtkMRMLScalarVolumeNode)
      inputContourNode (vtkMRMLLabelMapVolumeNode)
      lower (int)
      upper (int)
      sigma (float): Gaussian sigma
      fiducialNode (vtkMRMLFiducialNode)
      minimalRadius (int) : used in the SimpleITK Distance Transformation filter.
      dilateErodeDistance (int) : used in the SimpleITK Dilate/Erode filters.

    Returns:
      bool: True for success, False if inputs are not valid.
    """
    # check input validity
    if method is None:
      if (lower > upper):
        slicer.util.errorDisplay('Lower threshold cannot be greater than upper threshold.')
        return False
    
    fiducialNum = fiducialNode.GetNumberOfFiducials()
    if (fiducialNum == 0):
      slicer.util.errorDisplay('No seed points have been plotted.')
      return False

    # segmentation parameters
    if method is not None:
      self.voidVolume.setThreshMethod(method)
    else:
      self.voidVolume.setThresholds(lower, upper)
    self.voidVolume.setSigma(sigma)
    self.voidVolume.setRadii(minimalRadius, dilateErodeDistance)

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
    for i in range(fiducialNum):
      # store seed point coordinates in the variable seeds
      fiducialNode.GetNthFiducialPosition(i,physical_coord) # slicer seed coordinates
      itk_coord = self.RASToIJKCoords(physical_coord, ras2ijk) # SimpleITK coordinates
      seeds.append(itk_coord)
      # store seed point numbers in the variable erosion_ids
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

  def getErosions(self, inputVolumeNode, inputContourNode, outputErosionNode, noProgress=False) -> bool:
    """
    Run the Erosion Volume algorithm and store the result in the output erosion node. 
    The erosions will have label values that match the seed point postfixes

    Args:
      inputVolumeNode (vtkMRMLScalarVolumeNode)
      inputContourNode (ctkMRMLLabelMapVolumeNode)
      outputErosionNode (vtkMRMLSegmentationNode): will be modified.

    Returns:
      bool: True for success, False otherwise.
    """
    # initialize progress bar
    progress = 0
    if not noProgress:
      self.progressCallBack(progress)
    increment = 100 // self.voidVolume.stepNum # progress bar increment value
    logging.info('Processing started')
    
    # run Erosion Volume algorithm
    try:
      step = 1
      while (self.voidVolume.execute(step)): # execute the next step
        progress += increment
        if not noProgress:
          self.progressCallBack(progress) # update progress bar
        step += 1
    except Exception as e:
      slicer.util.errorDisplay('Error')
      print(e)
      return False
    erosion_img = self.voidVolume.getOutput()

    #check if output failed (matches input mask)
    erosion_arr = sitk.GetArrayFromImage(erosion_img)
    contour_arr = slicer.util.arrayFromVolume(inputContourNode)
    print(np.count_nonzero(erosion_arr), np.count_nonzero(contour_arr), contour_arr.size * 0.05)
    if abs(np.count_nonzero(erosion_arr) - np.count_nonzero(contour_arr)) < contour_arr.size * 0.05:
      text = """Unable to detect erosions. Check the set parameters in the module.\n
-Thresholds may be incorrect for the image
-Seed points may be incorrect
-Minimum erosion radius may need to be increased or decreased
-Large erosion may need to be enabled"""
      slicer.util.errorDisplay(text, "Erosion Analysis Failed")
      return False

    # move mask and erosion segments to output erosion node
    self._initOutputErosionNode(erosion_img, inputVolumeNode, inputContourNode, outputErosionNode)
    # record the seed points, source, and advanced parameters for each erosion
    self._setErosionInfo(outputErosionNode)

    logging.info('Processing completed')

    return True

  def labelmapToSegmentationNode(self, labelMapNode, segmentNode) -> None:
    """
    Import the label map volume to the segmentation, with each label to a different 
    segment. 

    Args:
      labelMapNode(vtkMRMLLabelMapVolume)
      segmentNode(vtkSegmentationNode): will be modified.
    """
    slicer.vtkSlicerSegmentationsModuleLogic.ImportLabelmapToSegmentationNode(labelMapNode, segmentNode, "")
  
  def segmentationNodeToLabelmap(self, segmentNode, labelMapNode) -> None:
    """
    Export the segmentation to the label map volume. Labels go from 1, 2,..., to N
    based on the order of the segments. Only visible segmentations will be exported.

    Args:
      segmentNode (vtkMRMLSegmentationNode)
      labelMapNode (vtkMRMLLabelMapVolumeNode): will be modified.
    """
    visibleSegmentIds = vtk.vtkStringArray()
    segmentNode.GetDisplayNode().GetVisibleSegmentIDs(visibleSegmentIds)
    referenceVolumeNode = segmentNode.GetNodeReference(
      slicer.vtkMRMLSegmentationNode.GetReferenceImageGeometryReferenceRole())
    slicer.vtkSlicerSegmentationsModuleLogic.ExportSegmentsToLabelmapNode(segmentNode, 
                                                                          visibleSegmentIds,
                                                                          labelMapNode, 
                                                                          referenceVolumeNode)

  def exportErosionsToLabelmap(self, segmentNode, labelMapNode) -> None:
    """
    Export the erosion segmentations to the label map volume. 
    Labels will be consistent with the names of the erosion segments.
    For example, the segment with id 'Erosion_2' will be labeled 2 in the label map volume.

    Args:
      segmentNode (vtkMRMLSegmentationNode)
      labelMapNode (vtkMRMLLabelMapVolumeNode): will be modified
    """
    # create a list that decides which value each erosion will be labeled with;
    #  the ith element of the list stores the label value for the ith visible segment
    visibleSegmentIds = vtk.vtkStringArray()
    segmentNode.GetDisplayNode().GetVisibleSegmentIDs(visibleSegmentIds)
    segmentNum = visibleSegmentIds.GetNumberOfValues()
    label_ids = []
    for i in range(segmentNum):
      segmentId = visibleSegmentIds.GetValue(i)
      try:
        label = int(segmentId.split('_')[-1])
        label_ids.append(label)
      except ValueError:
        label_ids.append(i)

    # export erosion segmentation to label map
    self.segmentationNodeToLabelmap(segmentNode, labelMapNode)

    # relabel erosions
    erosionVolumeArray = slicer.util.arrayFromVolume(labelMapNode)
    copyArray = copy(erosionVolumeArray)
    for key, value in enumerate(label_ids):
      erosionVolumeArray[copyArray==key+1] = value
    slicer.util.arrayFromVolumeModified(labelMapNode)

    # update label map display
    labelMapNode.GetDisplayNode().SetAndObserveColorNodeID(
      'vtkMRMLColorTableNodeFileGenericColors.txt')

  def enterSegmentEditor(self, segmentEditor):
    """
    Run this whenever the module is reopened. 
    Prepare the segmentation editor for manual correction of the erosions. 
    Set segmentation node in the segmentation editor, if node has been created. 
    The intensity mask is on, voxels with low intensities is editable. 
    The overwrite mode is set to overwrite visible segments. 
    #The mask mode is set to paint allowed inside the contour. 

    Args:
      segmentEditor (SegmentEditor): will be modified
    """
    segmentEditor.enter()
    segmentEditor.setMasterVolumeIntensityMask(True)
    segmentEditor.setOverWriteMode(slicer.vtkMRMLSegmentEditorNode.OverwriteVisibleSegments)

  def exitSegmentEditor(self, segmentEditor):
    """
    Run this whenever the module is closed. 
    Remove the segmentation editor keyboard shortcuts. 

    Args:
      segmentEditor (SegmentEditor): will be modified
    """
    segmentEditor.exit()

  def _initOutputErosionNode(self, erosion_img:sitk.Image, inputVolumeNode, 
                            inputContourNode, outputErosionNode) -> None:
    """
    Set the parent of the output erosion node. 
    Move the mask to the output erosion node.
    Import the itk erosion results into the output erosion node.

    Args:
      erosion_img (Image): itk erosion mask
      inputVolumeNode (vtkMRMLScalarVolumeNode)
      inputContourNode (vtkMRMLLabelMapVolumeNode)
      outputErosionNode (vtkMRMLSegmentationNode)
    """
    # clear output erosion node and set its parent to be greyscale scan
    outputErosionNode.GetSegmentation().RemoveAllSegments()
    outputErosionNode.SetReferenceImageGeometryParameterFromVolumeNode(inputVolumeNode)

    # binarize contour
    tempLabelMap = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode",
                                                      "MASK_Keep_Invisible")
    slicer.vtkSlicerVolumesLogic().CreateLabelVolumeFromVolume(slicer.mrmlScene, 
                                                               tempLabelMap, 
                                                               inputContourNode)
    contourArray = slicer.util.arrayFromVolume(inputContourNode)
    tempLabelArray = slicer.util.arrayFromVolume(tempLabelMap)
    tempLabelArray[contourArray > 0] = 1
    slicer.util.arrayFromVolumeModified(tempLabelMap)
    # push contour to output erosion node
    self.labelmapToSegmentationNode(tempLabelMap, outputErosionNode)
    contourSegmentId = outputErosionNode.GetSegmentation().GetNthSegmentID(0) # first segment ID
    outputErosionNode.GetDisplayNode().SetSegmentVisibility(contourSegmentId, False)
    # remove temporary label map
    slicer.mrmlScene.RemoveNode(tempLabelMap)

    # create temporary label map to hold erosions
    tempLabelMap = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", 
                                                      "TemporaryErosionNode")
    tempLabelMap.CreateDefaultDisplayNodes()
    tempLabelMap.GetDisplayNode().SetAndObserveColorNodeID(
      'vtkMRMLColorTableNodeFileGenericColors.txt')
    tempLabelMap.GetDisplayNode()
    # push result to temporary label map
    sitkUtils.PushVolumeToSlicer(erosion_img, tempLabelMap)
    # push erosions from temporary label map to output erosion node
    self.labelmapToSegmentationNode(tempLabelMap, outputErosionNode)
    # remove temporary label map
    slicer.mrmlScene.RemoveNode(tempLabelMap)

  def _setErosionInfo(self, outputErosionNode):
    """
    Store the corresponding seed point, advanced parameters and name of the source node
    in the tag of each erosion segment.

    Args:
      outputErosionNode (vtkMRMLSegmentationNode)
    """
    minimalRadius = self.voidVolume.minimalRadius
    dilateErodeDistance = self.voidVolume.dilateErodeDistance
    seeds = self.voidVolume.seeds
    # erosionIds is a list that indicates which erosion each seed is in
    erosionIds = self.voidVolume.erosionIds
    segmentation = outputErosionNode.GetSegmentation()
    segmentNum = segmentation.GetNumberOfSegments()
    erosionSource = outputErosionNode.GetName()

    for i in range(1,segmentNum): # skip the first segment, the mask
      segment = segmentation.GetNthSegment(i)
      try:
        # record corresponding seed point(s) in each erosion
        erosionIndexStr = segment.GetName().split('_')[-1]
        segment.SetName(erosionSource+'| Erosion_'+erosionIndexStr)
        erosionIndex = int(erosionIndexStr) # erosion index matches seed point name
        separator = '; '
        seedStr = separator.join([str(seeds[i]) for i, erosionId in enumerate(erosionIds)
                                  if erosionId == erosionIndex]) # string of seed points separated by '; '
        segment.SetTag("Seed", seedStr)
      except ValueError:
        pass
      # record advanced parameters
      segment.SetTag("MinimalRadius", minimalRadius)
      segment.SetTag("DilateErodeDistance", dilateErodeDistance)
      # record name of erosion source node
      segment.SetTag("Source", erosionSource)

  def getStatistics(self, inputErosionNode, masterVolumeNode, voxelSize:float, outputTableNode) -> None:
    """
    Get erosion statistics from the erosion segmentation. 
    Store the numeric data in the output table. 
    Each erosion will be named 'Erosion_XXX' in the table. 
    Supported statistics include volume, surface area, sphericity, and location. 

    Args:
      inputErosionNode (vtkMRMLSegmentationNode)
      masterVolumeNode (vtkMRMLScalarVolumeNode)
      voxelSize (double)
      outputTableNode (vtkMRMLTableNode): will be modified
    """
    # set parameters
    self.erosionStatistics.setSegmentationNode(inputErosionNode)
    self.erosionStatistics.setMasterVolumeNode(masterVolumeNode)
    self.erosionStatistics.setVoxelSize(voxelSize)
    self.erosionStatistics.setOutputTableNode(outputTableNode)

    # display statistics table and connect signals,
    #  erosions are centred in the viewer windows upon selection
    self.erosionStatistics.displayErosionStatistics()
    self.erosionStatistics.connectErosionSelection()

  def exitStatistics(self):
    """
    Disconnect erosion table selection signal. 
    Erosions will not be centred in the viewer windows upon selection.
    """
    self.erosionStatistics.disconnectErosionSelection()

  def intensityCheck(self, volumeNode) -> bool:
    '''
    Check if image intensity units are in HU

    Args:
      volumeNode (vtkMRMLVolumeNode)
    
    Returns:
      bool: True for HU units, false for other
    '''
    #create array and calculate statistics
    arr = slicer.util.arrayFromVolume(volumeNode)
    arr_max = np.where(arr > 4000, arr, 0)
    max_ratio = np.count_nonzero(arr_max) / arr.size
    arr_min = np.where(arr < -1000, arr, 0)
    min_ratio = np.count_nonzero(arr_min) / arr.size
    arr_avg = np.average(arr)
    arr_std = np.std(arr)

    #checks: 
    #-1000 < average < 1000
    #500 < standard deviation < 1000
    #out of range values < 10% of image
    return (arr_avg > -1000 and arr_avg < 1000 and arr_std > 500 and arr_std < 1000 and max_ratio + min_ratio < 0.1)