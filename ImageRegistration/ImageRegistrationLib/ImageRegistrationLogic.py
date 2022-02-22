#-----------------------------------------------------
# ImageRegistrationLogic.py
#
# Created by:  Ryan Yan
# Created on:  23-01-2022
#
# Description: This module contains the logics class 
#              for the 3D Slicer Image Registration extension.
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
from .RegistrationLogic import RegistrationLogic
from .VisualizeLogic import VisualizeLogic
from .CheckerboardLogic import CheckerboardLogic

#
# ImageRegistration
#
class ImageRegistrationLogic(ScriptedLoadableModuleLogic):
    """This class should implement all the actual
    computation done by your module. 
    Uses ScriptedLoadableModuleLogic base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self):
        '''
        Initialize Image Registration Logic class
        '''
        # initialize call back object for updating progrss bar
        self.progressCallBack = None
        self.registration = RegistrationLogic()
        self.visualizer = VisualizeLogic()
        self.checkerboard = CheckerboardLogic()

        self.template = None


    def setParamaters(self, baseNode, followNode, sampling):
        '''
        Set Parameters for registration

        Args:
            baseNode (vtkMRMLVolumeNode): volume with baseline image
            followNode (vtkMRMLVolumeNode): volume with follow up image
            sampling (float): metric sampling percentage
        
        Returns:
            None
        '''
        baseImage = sitkUtils.PullVolumeFromSlicer(baseNode)
        followImage = sitkUtils.PullVolumeFromSlicer(followNode)
        self.registration.setRegistrationParamaters(baseImage, followImage, sampling)
        self.registration.progressCallBack = self.progressCallBack
    
    def setMetric(self, index):
        '''
        Set the similarity metric for registration

        Args:
            index (int): selected metric (index of combobox)
        
        Returns:
            None
        '''

        #get metric from index
        if index == 0:
            metric = 'mean_squares'
        elif index == 1:
            metric = 'correlation'
        elif index == 2:
            metric = 'mattes'
        elif index == 3:
            metric = 'ants'
        self.registration.setSimilarityMetric(metric)

    def run(self, outputNode):
        '''
        Run the registration algorithm

        Args:
            outputNode (vtkMRMLVolumeNode): Volume to store output image in

        Returns:
            None
        '''
        outImg = self.registration.execute()
        sitkUtils.PushVolumeToSlicer(outImg, outputNode)
        slicer.util.setSliceViewerLayers(background=outputNode)
        return True
    
    def setVisualizeParameters(self, baseNode, regNode, sigma:float, lower:int, upper:int) -> None:
        '''
        Set parameters from visualization

        Args:
            baseNode (vtkMRMLVolumeNode): volume with baseline image
            regNode (vtkMRMLVolumeNode): volume with registered image
            sigma (float): gaussian sigma for smoothening images
            lower (int): lower threshold
            upper (int): upper threshold

        Returns:
            None
        '''

        #pull images
        baseImg = sitkUtils.PullVolumeFromSlicer(baseNode)
        regImg = sitkUtils.PullVolumeFromSlicer(regNode)

        #store properties of base image
        self.template = sitk.Image(baseImg.GetSize(), 0)
        self.template.CopyInformation(baseImg)

        #crop base image to match registered
        (baseImg, regImg) = self.visualizer.edgeTrim(baseImg, regImg)

        self.visualizer.setVisualizeParameters(baseImg, regImg, sigma, lower, upper)
    
    def visualize(self, outputNode) -> None:
        '''
        Create subtraction image of registration

        Args:
            outputNode (vtkMRMLVolumeNode): volume to store subtraction in
        
        Returns:
            None
        '''
        #get thresholds for images
        (baseThresh, regThresh) = self.visualizer.getThresholds()
        self.progressCallBack(30)
        
        #get arrays from each image
        baseArr = sitk.GetArrayFromImage(baseThresh)
        regArr = sitk.GetArrayFromImage(regThresh)
        self.progressCallBack(60)

        #set base image to a different value
        outArr = np.add(np.multiply(baseArr, 2), regArr)
        self.progressCallBack(90)

        #push output to volume
        outImg = sitk.GetImageFromArray(outArr)
        outImg.CopyInformation(self.template)
        sitkUtils.PushVolumeToSlicer(outImg, outputNode)
        slicer.util.setSliceViewerLayers(label=outputNode, labelOpacity=0.5)
    
    def setCheckerboardParameters(self, baseNode, regNode, size:int) -> None:
        '''Set parameters for checkerboard image'''
        
        base_img = sitkUtils.PullVolumeFromSlicer(baseNode)
        reg_img = sitkUtils.PullVolumeFromSlicer(regNode)

        self.checkerboard.setImages(base_img, reg_img, size)

    def getCheckerboard(self, outNode) -> None:
        '''Generate checkerboard image and push to volume'''

        self.progressCallBack(50)
        outImg = self.checkerboard.execute()
        sitkUtils.PushVolumeToSlicer(outImg, outNode)
        slicer.util.setSliceViewerLayers(background = outNode)
    
    def getCheckerboardGrid(self, gridNode) -> None:
        '''Generate checkerboard grid and push to volume'''

        self.progressCallBack(80)
        gridImg = self.checkerboard.checkerboard_mask()
        sitkUtils.PushVolumeToSlicer(gridImg, gridNode)
        slicer.util.setSliceViewerLayers(label = gridNode, labelOpacity = 0.2)
