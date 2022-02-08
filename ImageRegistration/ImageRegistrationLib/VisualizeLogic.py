#-----------------------------------------------------
# VisualizeLogic.py
#
# Created by:  Ryan Yan
# Created on:  31-01-2022
#
# Description: This module performs longitudinal image registration given a baseline and a follow-up image.
#
#-----------------------------------------------------
# Usage:       This module is plugged into 3D Slicer, but can run on its own. 
#              When running on its own, call:
#             
#
# Param:       baseImage: The input baseline scan file path
#              followImage: The input follow-up scan file path
#              
# Node:        Currently uses script from https://github.com/ManskeLab/BML_Turnover/blob/master/BML_T/BMLT_B_FU_reg.py
#
#-----------------------------------------------------
import SimpleITK as sitk
import numpy as np

class VisualizeLogic:
    def __init__(self):
        self.baseImg = None
        self.regImg = None
        self.sigma = 0.8
        self.lower = 686
        self.upper = 4000
    
    def setVisualizeParameters(self, baseImg, regImg, sigma, lower, upper):
        '''
        Set paramaters for visualization method

        Args:
            baseImg (SimpleITK Image): Baseline image
            regImg (SimpleITK Image): Registered follow-up image
            sigma (float): Gaussian sigma
            lower (int): Lower threshold
            upper (int): Upper threshold
        
        Returns:
            None
        '''
        self.baseImg = baseImg
        self.regImg = regImg
        self.sigma = sigma
        self.lower = lower
        self.upper = upper

    def threshold(self, img):
        '''
        Apply threshold operation to an image

        Args:
            img (SimpleITK Image): Input image
        
        Returns:
            SimpleITK Image: Image after threshold
        '''
        sigma_over_spacing = self.sigma * img.GetSpacing()[0]

        # gaussian smoothing filter
        print("Applying Gaussian filter")
        gaussian_filter = sitk.SmoothingRecursiveGaussianImageFilter()
        gaussian_filter.SetSigma(sigma_over_spacing)
        gaussian_img = gaussian_filter.Execute(img)

        thresh_img = sitk.BinaryThreshold(gaussian_img, 
                                          lowerThreshold=self.lower, 
                                          upperThreshold=self.upper)

        return thresh_img
    
    def getThresholds(self):
        '''
        Get thresholds for baseline and registered image set using parameters method

        Args:
            None

        Returns:
            (SimpleITK image, SimpleITK Image): Images after threshold
        '''
        return (self.threshold(self.baseImg), self.threshold(self.regImg))

    def edgeTrim(self, baseImg, regImg):
        '''
        Trim edge of images to match
        Registration results in blackspace at the edge of the image, 
        so this region needs to be ignored during viusalization.

        Args:
            baseImg (SimpleITK Image): Baseline image
            regImg (SimpleITK Image): Registered follow-up image
        
        Returns:
            (SimpleITK Image, SimpleITK Image): trimmed images
        '''
        #get binary mask of non-zero regions
        baseArr = sitk.GetArrayFromImage(baseImg)
        regArr = sitk.GetArrayFromImage(regImg)
        maskArr = np.logical_and((baseArr != 0), (regArr != 0)).astype('int32')

        #trim images
        baseCrop = np.multiply(maskArr, baseArr)
        regCrop = np.multiply(maskArr, regArr)

        return (sitk.GetImageFromArray(baseCrop), sitk.GetImageFromArray(regCrop))
