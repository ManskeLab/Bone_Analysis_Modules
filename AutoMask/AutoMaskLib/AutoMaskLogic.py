#-----------------------------------------------------
# AutomaticMaskLogic.py
#
# Created by:  Mingjie Zhao
# Created on:  20-10-2020
#
# Description: This module contains the logics class
#              for the Automatic Mask 3D Slicer extension.
#
#-----------------------------------------------------
from re import T
import slicer
from slicer.ScriptedLoadableModule import *
import vtk
import SimpleITK as sitk
import sitkUtils
import logging
import os
import numpy as np
import traceback
from .MaskLogic import MaskLogic
from .SegmentEditor import SegmentEditor

#
# AutomaticMaskLogic
#
class AutoMaskLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """
  def __init__(self):
    # initialize call back object for updating progrss bar
    self.progressCallBack = None
    # initialize mask object containing logics from mask module
    self.mask = MaskLogic()
    self._segmentNodeId = ""

  def setDefaultDirectory(self, inputVolumeNode):
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

  def enterSegmentEditor(self, segmentEditor):
    """
    Run this whenever the module is reopened.
    Prepare the segmentation editor.
    Set segmentation node in the segmentation editor, if node has been created.
    The intensity mask is off.
    The overwrite mode is set to overwrite all segments.
    The mask mode is set to paint allowed everywhere.

    Args:
      segmentEditor (SegmentEditor): will be modified

    Returns:
      bool: True if segmentation has previously been created, False otherwise.
    """
    segmentNode = slicer.mrmlScene.GetNodeByID(self._segmentNodeId)

    segmentEditor.enter()
    segmentEditor.setMasterVolumeIntensityMask(False)
    segmentEditor.setOverWriteMode(slicer.vtkMRMLSegmentEditorNode.OverwriteAllSegments)
    segmentEditor.setMaskMode(slicer.vtkMRMLSegmentationNode.EditAllowedEverywhere)
    if segmentNode: # if the segmentation node exists, switch to it
      segmentEditor.setSegmentationNode(segmentNode)

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

  def initRoughMask(self, segmentEditor, separateInputNode):
    """
    Set up the segmentation editor for manual bone separation/rough mask.
    Create new segmentation node if not created.

    Args:
      segmentEditor (SegmentEditor): will be modified
      separateInputNode (vtkMRMLScalarVolumeNode)

    Returns:
      bools: True for success, False otherwise.
    """
    segmentNode = slicer.mrmlScene.GetNodeByID(self._segmentNodeId)
    if separateInputNode:
      if not segmentNode:
        segmentNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentationNode')
        segmentNode.SetReferenceImageGeometryParameterFromVolumeNode(separateInputNode)
        self._segmentNodeId = segmentNode.GetID()
        # set segmentation node and master volume node in segmentation editor
        segmentEditor.setSegmentationNode(segmentNode)
        segmentEditor.setMasterVolumeNode(separateInputNode)
        # reduce segmentation resolution for performance
        segmentEditor.setSegmentationGeometry(segmentNode, separateInputNode, oversamplingFactor=0.5)
        # update viewer windows and widgets
        slicer.util.setSliceViewerLayers(background=separateInputNode)

      return True
    return False

  def cancelRoughMask(self, separateInputNode):
    """
    Cancel the segmentation for in manual bone separation/rough mask.
    Remove the segmentation node in the segmentation editor.

    Args:
      separateInputNode (vtkMRMLScalarVolumeNode)

    Returns:
      bool: True for success, False if nodes are missing.
    """
    segmentNode = slicer.mrmlScene.GetNodeByID(self._segmentNodeId)
    if segmentNode:
      # remove the current segmentation node
      slicer.mrmlScene.RemoveNode(segmentNode)
    if separateInputNode:
      # update viewer windows
      slicer.util.setSliceViewerLayers(background=separateInputNode)

    return (segmentNode and separateInputNode)

  def applyRoughMask(self, separateInputNode, separateOutputNode):
    """
    Apply the segmentation in manual bone separation/rough mask.
    Load the segmentation to the output node.
    Remove the segmentation node in the segmentation editor.

    Args:
      separateInputNode (vtkMRMLScalarVolumeNode)
      separateOutputNode (vtkMRMLScalarVolumeNode): will be modified

    Returns:
      bool: True for success, False otherwise.
    """
    segmentNode = slicer.mrmlScene.GetNodeByID(self._segmentNodeId)

    if (segmentNode and separateInputNode and separateOutputNode):
      self.segmentationNodeToLabelmap(segmentNode, separateOutputNode, separateInputNode)

      # remove the current segmentation node in the toolkit
      # slicer.mrmlScene.RemoveNode(segmentNode)
      # update viewer windows and widgets
      # slicer.util.setSliceViewerLayers(background=separateInputNode,
      #                                  label=separateOutputNode,
      #                                  labelOpacity=0.5)

      return True
    return False

  def applyDeleteMask(self, start, finish, inputNode, segmentEditor):
    #get mask segments
    segmentationNode = slicer.mrmlScene.GetNodeByID(self._segmentNodeId)
    selectedSegmentIds = vtk.vtkStringArray()

    if(segmentationNode):
        segmentationNode.GetSegmentation().GetSegmentIDs(selectedSegmentIds)

    for idx in range(selectedSegmentIds.GetNumberOfValues()):
      segmentId = selectedSegmentIds.GetValue(idx)
      segment = segmentationNode.GetSegmentation().GetSegmentIdBySegmentName(segmentId)

      # Get mask segment as numpy array
      segmentArray = slicer.util.arrayFromSegmentBinaryLabelmap(segmentationNode, segment, inputNode)

      # Iterate through voxels
      for vox in range(start, finish+1):
        segmentArray[vox, :, :] = 0

      # Convert back to label map array
      slicer.util.updateSegmentBinaryLabelmapFromArray(segmentArray, segmentationNode, segment, inputNode)

    # slicer.util.setSliceViewerLayers(background=inputNode,
    #                                    label=segmentationNode,
    #                                    labelOpacity=0.3)

  def getSegmentNode(self):
    return slicer.mrmlScene.GetNodeByID(self._segmentNodeId)

  def changeRoughMask(self, roughMaskNode, masterVolumeNode, segmentEditor):
    segmentNode = slicer.mrmlScene.GetNodeByID(self._segmentNodeId)
    slicer.mrmlScene.RemoveNode(segmentNode)

    if (roughMaskNode and masterVolumeNode):
      segmentNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentationNode')
      segmentNode.SetReferenceImageGeometryParameterFromVolumeNode(masterVolumeNode)
      self._segmentNodeId = segmentNode.GetID()
      self.labelmapToSegmentationNode(roughMaskNode, segmentNode)
      # set segmentation node and master volume node in segmentation editor
      segmentEditor.setSegmentationNode(segmentNode)
      segmentEditor.setMasterVolumeNode(masterVolumeNode)
      # update viewer windows
      slicer.util.setSliceViewerLayers(background=masterVolumeNode,
                                      label= segmentNode,
                                      labelOpacity=0.5)
      slicer.util.resetSliceViews()

      return True
    return False

  def setParameters(self, inputVolumeNode, outputVolumeNode, sigma,
                    boneNum, dilateErodeRadius, separateMapNode, method=None, lower=None, upper=None):
    """
    Set parameters to be used by the automatic mask algorithm.

    Args:
      inputVolumeNode (vtkMRMLScalarVolumeNode)
      outputVolumeNode (vtkMRMLLabelMapVolumeNode)
      lower (int)
      upper (int)
      sigma (double)
      boneNum (int)
      dilateErodeRadius (int)
      separateMapNode (vtkMRMLLabelMapVolumeNode)

    Returns:
      bool: True for success, False if inputs are not valid.
    """
    if (inputVolumeNode.GetID() == outputVolumeNode.GetID()):
      slicer.util.errorDisplay('Input volume is the same as output volume. Select a different output volume.')
      return False

    if method is None:
      if (lower > upper):
        slicer.util.errorDisplay('Lower threshold cannot be greater than upper threshold.')
        return False

    # images
    model_img = sitk.ReadImage(sitkUtils.GetSlicerITKReadWriteAddress(inputVolumeNode.GetName()), sitk.sitkFloat32)
    self.mask.setModel(model_img)
    if (separateMapNode is None):
      self.mask.setRoughMask(None)
    else:
      separate_map = sitkUtils.PullVolumeFromSlicer(separateMapNode.GetName())
      self.mask.setRoughMask(sitk.Cast(separate_map, sitk.sitkUInt8))

    # numeric parameters
    if method is not None:
      self.mask.setThreshMethod(method)
    else:
      self.mask.setThreshold(lower, upper)
    self.mask.setSigma(sigma)
    self.mask.setBoneNum(boneNum)
    self.mask.setDilateErodeRadius(dilateErodeRadius)

    return True

  def getMask(self, inputVolumeNode, outputVolumeNode, algorithm, noProgress=False):
    """
    Run the automatic mask algorithm.

    Args:
      inputVolumeNode (vtkMRMLScalarVolumeNode)
      outputVolumeNode (vtkMRMLLabelMapVolumeNode): will be modified

    Returns:
      bool: True for success, False otherwise.
    """

    if(algorithm == 1):
      print("Using Dual Threshold Algorithm.")
      # initialize progress value
      increment = 100 // self.mask.getStepNum() # progress bar increment value
      progress = 0
      if not noProgress:
        self.progressCallBack(progress)
      logging.info('Processing started')

      # run the automatic mask algorithm
      try:
        step = 1
        while (self.mask.execute(step, algorithm)): # execute the next step
          print(step)
          logging.info("in while loop")
          progress += increment
          if not noProgress:
            self.progressCallBack(progress) # update progress bar
          step += 1
      except Exception as e:
        slicer.util.errorDisplay('Error')
        print(e)
        print(traceback.format_exc())
        return False

    if(algorithm == 0):
      self.mask.execute(0, algorithm)

    dir = os.path.split(inputVolumeNode.GetStorageNode().GetFullNameFromFileName())

    # push result to outputVolumeNode
    mask_img = self.mask.getMask()
    sitkUtils.PushVolumeToSlicer(mask_img, outputVolumeNode)
    sitk.WriteImage(mask_img, dir[0]+'/'+os.path.splitext(dir[1])[0]+"_Segment_Mask.nrrd")
    logging.info('Processing completed')

    # #get mask segments
    # individual_masks = self.mask.getIndividualMasks()
    # for idx in range(len(individual_masks)):
    #   sitk.WriteImage(individual_masks[idx], dir[0]+'/'+os.path.splitext(dir[1])[0]+"_Segment_Mask"+str(idx)+".nrrd")
    
    segmentationNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentationNode')
    segmentationNode.SetReferenceImageGeometryParameterFromVolumeNode(inputVolumeNode)
    self.labelmapToSegmentationNode(outputVolumeNode, segmentationNode)
    selectedSegmentIds = vtk.vtkStringArray()

    if(segmentationNode):
        segmentationNode.GetSegmentation().GetSegmentIDs(selectedSegmentIds)

    for idx in range(selectedSegmentIds.GetNumberOfValues()):
      segmentId = selectedSegmentIds.GetValue(idx)
      visibleSegmentIds = vtk.vtkStringArray()
      visibleSegmentIds.InsertValue(0, segmentId)

      segmentLabelMapNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode")

      slicer.vtkSlicerSegmentationsModuleLogic.ExportSegmentsToLabelmapNode(segmentationNode,
                                                                          visibleSegmentIds,
                                                                          segmentLabelMapNode,
                                                                          inputVolumeNode)

      storageNode = segmentLabelMapNode.CreateDefaultStorageNode()
      storageNode.SetFileName(dir[0]+'/'+os.path.splitext(dir[1])[0]+"_Segment_Mask_"+str(idx)+".nrrd")

      storageNode.WriteData(segmentLabelMapNode)

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

  def initManualCorrection(self, segmentEditor, maskSegmentNode, maskVolumeNode, masterVolumeNode):
    """
    Set up the segmentation editor for manual correction of mask.
    Create new segmentation node if not created.
    Load mask to the segmentation editor.

    Args:
      segmentEditor (SegmentEditor): will be modified
      maskVolumeNode (vtkMRMLLabelMapVolumeNode)
      masterVolumeNode (vtkMRMLScalarVolumeNode)

    Returns:
      bool: True for success, False otherwise.
    """
    segmentNode = slicer.mrmlScene.GetNodeByID(self._segmentNodeId)

    if (maskVolumeNode and masterVolumeNode):
      if not segmentNode:
        segmentNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentationNode')
        segmentNode.SetReferenceImageGeometryParameterFromVolumeNode(masterVolumeNode)
      self._segmentNodeId = segmentNode.GetID()
      self.labelmapToSegmentationNode(maskVolumeNode, segmentNode)
      # set segmentation node and master volume node in segmentation editor
      segmentEditor.setSegmentationNode(segmentNode)
      segmentEditor.setMasterVolumeNode(masterVolumeNode)
      # update viewer windows
      slicer.util.setSliceViewerLayers(background=masterVolumeNode)

      return True
    return False

  def cancelManualCorrection(self, maskVolumeNode, masterVolumeNode):
    """
    Cancel the manual correction.
    Remove the segmentation node in the segmentation editor.

    Args:
      maskVolumeNode (vtkMRMLLabelMapVolumeNode)
      masterVolumeNode (vtkMRMLScalarVolumeNode)

    Returns:
      bool: True for success, False if nodes are missing.
    """
    segmentNode = slicer.mrmlScene.GetNodeByID(self._segmentNodeId)

    if segmentNode:
      # remove the current segmentation node
      slicer.mrmlScene.RemoveNode(segmentNode)
    if (maskVolumeNode and masterVolumeNode):
      # update viewer windows
      slicer.util.setSliceViewerLayers(background=masterVolumeNode,
                                       label=maskVolumeNode,
                                       labelOpacity=0.5)

    return (segmentNode and maskVolumeNode and masterVolumeNode)

  def applyManualCorrection(self, maskVolumeNode, masterVolumeNode):
    """
    Apply the manual correction.
    Load the mask back to the input node.
    Remove the segmentation node in the segmentation editor.

    Args:
      maskVolumeNode (vtkMRMLLabelMapVolumeNode): will be modified
      masterVolumeNode (vtkMRMLScalarVolumeNode)

    Returns:
      bool: True for success, False otherwise.
    """
    segmentNode = slicer.mrmlScene.GetNodeByID(self._segmentNodeId)
    outputVolumeNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode")

    if (segmentNode and maskVolumeNode and masterVolumeNode):

      #get mask segments
      selectedSegmentIds = vtk.vtkStringArray()

      segmentNode.GetSegmentation().GetSegmentIDs(selectedSegmentIds)

      dir = os.path.split(masterVolumeNode.GetStorageNode().GetFullNameFromFileName())

      for idx in range(selectedSegmentIds.GetNumberOfValues()):
        segmentId = selectedSegmentIds.GetValue(idx)
        visibleSegmentIds = vtk.vtkStringArray()
        visibleSegmentIds.InsertValue(0, segmentId)

        segmentLabelMapNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode")

        slicer.vtkSlicerSegmentationsModuleLogic.ExportSegmentsToLabelmapNode(segmentNode,
                                                                            visibleSegmentIds,
                                                                            segmentLabelMapNode,
                                                                            masterVolumeNode)

        storageNode = segmentLabelMapNode.CreateDefaultStorageNode()
        storageNode.SetFileName(dir[0]+'/'+os.path.splitext(dir[1])[0]+"_Segment_Mask_"+str(idx)+".nrrd")

        storageNode.WriteData(segmentLabelMapNode)

      self.segmentationNodeToLabelmap(segmentNode, maskVolumeNode, masterVolumeNode)

      storageNode = maskVolumeNode.CreateDefaultStorageNode()
      storageNode.SetFileName(dir[0]+'/'+os.path.splitext(dir[1])[0]+"_Segment_Mask.nrrd")
      storageNode.WriteData(maskVolumeNode)

      binaryThresh = sitk.BinaryThresholdImageFilter()
      binaryThresh.SetLowerThreshold(1)
      binaryThresh.SetUpperThreshold(255)
      binaryThresh.SetInsideValue(1)

      combinedMask = sitkUtils.PullVolumeFromSlicer(maskVolumeNode.GetName())

      out = binaryThresh.Execute(combinedMask)
      sitk.WriteImage(out, dir[0]+'/'+os.path.splitext(dir[1])[0]+"_MASK.nii")
      # remove the current segmentation node
      # slicer.mrmlScene.RemoveNode(segmentNode)
      # update viewer windows
      slicer.util.setSliceViewerLayers(background=masterVolumeNode,
                                      label=maskVolumeNode,
                                      labelOpacity=0.5)

      return True
    return False

  def intensityCheck(self, volumeNode):
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