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
        self.lower = 500
        self.upper = 4000
        self.thresh_method = None
        self.auto_thresh = True
    
    def setVisualizeParameters(self, baseImg:sitk.Image, regImg:sitk.Image, sigma:float, auto_thresh:bool) -> None:
        '''
        Set paramaters for visualization method
        '''
        self.baseImg = baseImg
        self.regImg = regImg
        self.sigma = sigma
        self.auto_thresh = auto_thresh
    
    def setThresholdMethod(self, index:int) -> None:
        '''Set thresholding method for visualization'''
        if index == 0:
            self.thresh_method = sitk.OtsuThresholdImageFilter()
        elif index == 1:
            self.thresh_method = sitk.HuangThresholdImageFilter()
        elif index == 2:
            self.thresh_method = sitk.MaximumEntropyThresholdImageFilter()
        elif index == 3:
            self.thresh_method = sitk.MomentsThresholdImageFilter()
        elif index == 4:
            self.thresh_method = sitk.YenThresholdImageFilter()
        self.thresh_method.SetOutsideValue(1)
        self.thresh_method.SetInsideValue(0)
    
    def setManualThresholds(self, lower:int, upper:int) -> None:
        '''Set manual thresholds for visualization'''
        self.lower = lower
        self.upper = upper

    def threshold(self, img:sitk.Image) -> sitk.Image:
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

        if self.auto_thresh:
            thresh_img = self.thresh_method.Execute(gaussian_img)
        else:
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
    
    def subtract(self) -> sitk.Image:
        gauss = sitk.SmoothingRecursiveGaussianImageFilter()
        gauss.SetSigma(self.sigma)
        smooth_base = gauss.Execute(self.baseImg)
        smooth_reg = gauss.Execute(self.regImg)
        return (smooth_base - smooth_reg)
    

