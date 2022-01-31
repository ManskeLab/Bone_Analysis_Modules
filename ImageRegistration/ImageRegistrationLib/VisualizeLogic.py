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

class VisualizeLogic:
    def __init__(self):
        self.baseImg = None
        self.regImg = None
        self.sigma = 0.8
        self.lower = 686
        self.upper = 4000
    
    def setVisualizeParameters(self, baseImg, regImg, sigma, lower, upper):
        self.baseImg = baseImg
        self.regImg = regImg
        self.sigma = sigma
        self.lower = lower
        self.upper = upper

    def threshold(self, img):
        sigma_over_spacing = self.sigma * img.GetSpacing()[0]

        # gaussian smoothing filter
        print("Applying Gaussian filter")
        gaussian_filter = sitk.SmoothingRecursiveGaussianImageFilter()
        gaussian_filter.SetSigma(sigma_over_spacing)
        gaussian_img = gaussian_filter.Execute(img)

        thresh_img = sitk.BinaryThreshold(gaussian_img, 
                                          lowerThreshold=self.lower, 
                                          upperThreshold=self.upper, 
                                          insideValue=1)

        return thresh_img
    
    def getThresholds(self):
        return [self.threshold(self.baseImg), self.threshold(self.regImg)]
    