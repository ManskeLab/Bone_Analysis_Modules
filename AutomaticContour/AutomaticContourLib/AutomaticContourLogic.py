#-----------------------------------------------------
# AutomaticContourLogic.py
#
# Created by:  Mingjie Zhao
# Created on:  20-10-2020
#
# Description: This module contains the logics class  
#              for the Automatic Contour 3D Slicer extension.
#
#-----------------------------------------------------
import slicer
from slicer.ScriptedLoadableModule import *
import vtk
import SimpleITK as sitk
import sitkUtils
import logging
import os
from .ContourLogic import ContourLogic
from .SegmentEditor import SegmentEditor

#
# AutomaticContourLogic
#
class AutomaticContourLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module. 
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """
  def __init__(self):
    # initialize call back object for updating progrss bar
    self.progressCallBack = None
    # initialize contour object containing logics from contour module
    self.contour = ContourLogic()
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
    segmentEditor.setMaskMode(slicer.vtkMRMLSegmentEditorNode.PaintAllowedEverywhere)
    if segmentNode: # if the segmentation node exists, switch to it
      self.segmentEditor.setSegmentationNode(segmentNode)

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
      slicer.mrmlScene.RemoveNode(segmentNode)
      # update viewer windows and widgets
      slicer.util.setSliceViewerLayers(background=separateInputNode,
                                       label=separateOutputNode, 
                                       labelOpacity=0.5)

      return True
    return False

  def setParameters(self, inputVolumeNode, outputVolumeNode, lower, upper, sigma,
                    boneNum, dilateErodeRadius, separateMapNode):
    """
    Set parameters to be used by the automatic contour algorithm.

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
    
    if (lower > upper):
      slicer.util.errorDisplay('Lower threshold cannot be greater than upper threshold.')
      return False

    # images
    model_img = sitkUtils.PullVolumeFromSlicer(inputVolumeNode.GetName())
    self.contour.setModel(model_img)
    if (separateMapNode is None):
      self.contour.setRoughMask(None)
    else:
      separate_map = sitkUtils.PullVolumeFromSlicer(separateMapNode.GetName())
      self.contour.setRoughMask(sitk.Cast(separate_map, sitk.sitkUInt8))

    # numeric parameters
    self.contour.setThreshold(lower, upper)
    self.contour.setSigma(sigma)
    self.contour.setBoneNum(boneNum)
    self.contour.setDilateErodeRadius(dilateErodeRadius)

    return True

  def getContour(self, inputVolumeNode, outputVolumeNode, noProgress=False):
    """
    Run the automatic contour algorithm.

    Args:
      inputVolumeNode (vtkMRMLScalarVolumeNode)
      outputVolumeNode (vtkMRMLLabelMapVolumeNode): will be modified

    Returns:
      bool: True for success, False otherwise.
    """
    # initialize progress value
    increment = 100 // self.contour.getStepNum() # progress bar increment value
    progress = 0
    if not noProgress:
      self.progressCallBack(progress)
    logging.info('Processing started')

    # run the automatic contour algorithm
    try:
      step = 1
      while (self.contour.execute(step)): # execute the next step
        progress += increment
        if not noProgress:
          self.progressCallBack(progress) # update progress bar
        step += 1
    except Exception as e: 
      slicer.util.errorDisplay('Error')
      print(e)
      return False

    # push result to outputVolumeNode
    contour_img = self.contour.getOutput()
    sitkUtils.PushVolumeToSlicer(contour_img, outputVolumeNode)
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
