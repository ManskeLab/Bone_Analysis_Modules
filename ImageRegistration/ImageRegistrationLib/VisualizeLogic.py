#-----------------------------------------------------
# VisualizeLogic.py
#
# Created by:  Ryan Yan
# Created on:  31-01-2022
#
# Description: This module creates a subtraction image for longitudinal registrations.
#
#-----------------------------------------------------
# Usage:       Implemented in the Image Registration Module
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
    
    def setVisualizeParameters(self, baseImg:sitk.Image, regImg:sitk.Image, sigma:float, lower:int, upper:int):
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

    def threshold(self, img:sitk.Image):
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

    def edgeTrim(self, baseImg:sitk.Image, regImg:sitk.Image):
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
    

