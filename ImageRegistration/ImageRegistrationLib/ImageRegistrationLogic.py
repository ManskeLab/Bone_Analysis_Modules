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
        # initialize call back object for updating progrss bar
        self.progressCallBack = None
        self.registration = RegistrationLogic()


    def setParamaters(self, baseNode, followNode):
        baseImage = sitkUtils.PullVolumeFromSlicer(baseNode)
        followImage = sitkUtils.PullVolumeFromSlicer(followNode)
        self.registration.setRegistrationParamaters(baseImage, followImage)

    def run(self, outputNode):
        outImg = self.registration.execute(0)
        sitkUtils.PushVolumeToSlicer(outImg, outputNode)
        return True
