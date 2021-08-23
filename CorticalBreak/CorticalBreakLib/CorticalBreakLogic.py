#-----------------------------------------------------
# ErosionDetectionLogic.py
#
# Created by:  Mingjie Zhao
# Created on:  23-07-2021
#
# Description: This module contains the logics class 
#              for the 3D Slicer Cortical Break extension.
#
#-----------------------------------------------------
import slicer
from slicer.ScriptedLoadableModule import *
import vtk
import SimpleITK as sitk
import sitkUtils
import logging, os
from .PetersCorticalBreakLogic import PetersCorticalBreakLogic
from .CBCTCorticalBreakLogic import CBCTCorticalBreakLogic

#
# CorticalBreakLogic
#
class CorticalBreakLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module. 
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self):
    # initialize call back object for updating progrss bar
    self.progressCallBack = None

    self.corticalBreak = PetersCorticalBreakLogic()

  def IJKToRASCoords(self, ijk_3coords, ijk2ras):
    """
    Convert from SimpleITK coordinates to IJK coordinates. 
    Normally this involves negating the x, y coordinates, 
    and scaling the coordinates with respect to the spacing. 

    Args:
      ijk_3coords (list of Int)
      ijk2ras (vtkMatrix4x4): 4 by 4 matrix that converts from IJK to RAS

    Returns:
      tuple of int
    """
    ijk_4coords = ijk_3coords + [1]
    return tuple((i for i in ijk2ras.MultiplyPoint(ijk_4coords)[:3]))
  
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
      
  def setPreprocessParameters(self, inputVolumeNode, lower, upper, sigma):
    """
    Set parameters for preprocessing. 

    Args:
      inputVolumeNode (vtkMRMLScalarVolumeNode)
      lower (int)
      upper (int)
      sigma (float): Standard deviation in the Gaussian smoothing filter.

    Returns:
      bool: True for success, False if inputs are not valid.
    """
    # check input validity
    if (lower > upper):
      slicer.util.errorDisplay('Lower threshold cannot be greater than upper threshold.')
      return False

    # images
    model_img = sitkUtils.PullVolumeFromSlicer(inputVolumeNode.GetName())
    self.corticalBreak.setModel(model_img)
    
    # thresholds
    self.corticalBreak.setThresholds(lower, upper)

    # sigma
    self.corticalBreak.setSigma(sigma)

    return True

  def preprocess(self, outputVolumeNode):
    """
    Preprocess the input Volume and store the result in output volume.
    
    Args:
      outputVolumeNode (vtkMRMLLabelMapVolumeNode

    Returns:
      bool: True for success, False otherwise
    """
    logging.info('Preprocessing started')
    
    # run erosion detection algorithm
    try:
      step = 1
      self.corticalBreak.execute(step)
    except Exception as e:
      slicer.util.errorDisplay('Error')
      print(e)
      return False
    preprocessed_img = self.corticalBreak.getSeg()

    logging.info('Processing completed')

    sitkUtils.PushVolumeToSlicer(preprocessed_img, outputVolumeNode)

    return True

  def setCorticalBreaksParameters(self, lower, upper, inputVolumeNode, inputBoneNode, maskNode, 
                                  outputCorticalBreaksNode, corticalThickness, dilateErodeDistance, 
                                  voxelSize, cbCT):
    """
    Set parameters for automatic cortical break detection algorithm.
    
    Args:
      lower (int)
      upper (int)
      inputVolumeNode (vtkMRMLInputVolumeNode)
      inputBoneNode (vtkMRMLLabelMapVolumeNode)
      maskNode (vtkMRMLLabelMapVolumeNode)
      outputCorticalBreaksNode (vtkMRMLLabelMapVolumeNode)
      corticalThickness (Int)
      dilateErodeDistance (Int)
      voxelSize (Float)
      cbCT (bool): whether to use the original method or the CBCT version 
                   of the cortical break detection algorithm.

    Returns:
      bool: True if success, False otherwise
    """
    if (inputBoneNode.GetID() == outputCorticalBreaksNode.GetID() or
        maskNode.GetID() == outputCorticalBreaksNode.GetID()):
      slicer.util.errorDisplay('Input volume is the same as output volume. Select a different output volume.')
      return False

    if (lower > upper):
      slicer.util.errorDisplay('Lower threshold cannot be greater than upper threshold.')
      return False

    if cbCT: # only the CBCT version of the cortical break algorithm requires greyscale image
      self.corticalBreak = CBCTCorticalBreakLogic()
    else:
      self.corticalBreak = PetersCorticalBreakLogic()

    # images
    seg_img = sitkUtils.PullVolumeFromSlicer(inputBoneNode.GetName())
    self.corticalBreak.setSeg(seg_img)
    mask_img = sitkUtils.PullVolumeFromSlicer(maskNode.GetName())
    self.corticalBreak.setContour(mask_img)
    model_img = sitkUtils.PullVolumeFromSlicer(inputVolumeNode.GetName())
    self.corticalBreak.setModel(model_img)
    
    # distances
    self.corticalBreak.setCorticalThickness(corticalThickness)
    self.corticalBreak.setDilateErodeDistance(dilateErodeDistance)

    # thresholds
    self.corticalBreak.setThresholds(lower, upper)
    self.corticalBreak.setVoxelSize(voxelSize*1000)

    return True

  def getCorticalBreaks(self, outputCorticalBreaksNode):
    """
    Run the automatic cortical break detection algorithm.

    Args:
      outputCorticalBreaksNode (vtkMRMLLabelMapVolumeNode)
    """
    # initialize progress bar
    increment = 100 // self.corticalBreak.stepNum # progress bar increment value
    progress = increment                          # progress bar initial value
    self.progressCallBack(progress)
    logging.info('Processing started')
    
    # run erosion detection algorithm
    try:
      step = 2
      while (self.corticalBreak.execute(step)): # execute the next step
        progress += increment
        self.progressCallBack(progress) # update progress bar
        step += 1
    except Exception as e:
      slicer.util.errorDisplay('Error')
      print(e)
      return False
    cortical_breaks = self.corticalBreak.getOutput()

    logging.info('Processing completed')

    sitkUtils.PushVolumeToSlicer(cortical_breaks, outputCorticalBreaksNode)

    return True

  def getSeeds(self, inputBoneNode, fiducialNode):
    """
    Convert the cortical break masks into seed points.

    Args:
      inputBoneNode (vtkMRMLLabelMapVolumeNode)
      fiducialNode (vtkMRMLMarkupsFiducialNode)
    """
    ijk2ras = vtk.vtkMatrix4x4()
    inputBoneNode.GetIJKToRASMatrix(ijk2ras)

    for seed in self.corticalBreak.getSeeds():
      ras_coord = self.IJKToRASCoords(list(seed), ijk2ras)
      fiducialNode.AddFiducialFromArray(ras_coord)

