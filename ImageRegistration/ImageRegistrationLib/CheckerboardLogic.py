#-----------------------------------------------------
# CheckerboardLogic.py
#
# Created by:  Ryan Yan
# Created on:  16-02-2022
#
# Description: This module creates a checkerboard comparison for longitudinal registrations.
#
#-----------------------------------------------------
# Usage:       Implemented in the Image Registration Module        
#
#-----------------------------------------------------
import SimpleITK as sitk
import numpy as np

class CheckerboardLogic:
  def __init__(self) -> None:
    self.base = None
    self.reg = None
    self.size = 10
  
  def setImages(self, base:sitk.Image, reg:sitk.Image, size:int) -> None:
    '''Set the images and checkerboard size'''
    self.base = base
    self.reg = reg
    self.size = size
  
  def execute(self) -> sitk.Image:
    '''Execute the checkerboard algorithm'''

    #check intensity range
    self.intensity_check()

    #create checkerboard with filter
    checker = sitk.CheckerBoardImageFilter()
    checker.SetCheckerPattern(self.size)
    out_img = checker.Execute(self.base, self.reg)
    return out_img
  
  def checkerboard_mask(self) -> sitk.Image:
    '''Create a binary grid for reference'''
    #create black image and white image
    black = sitk.Image(self.base.GetSize(), 0)
    white = (black + 1)

    #apply checkerboard filter
    checker = sitk.CheckerBoardImageFilter()
    checker.SetCheckerPattern(self.size)
    out_mask = checker.Execute(black, white)
    return out_mask

  def intensity_check(self) -> None:
    '''Check the intensity values of an image'''
    #get intensity range
    stats = sitk.StatisticsImageFilter()
    stats.Execute(self.base)
    base_min = stats.GetMinimum()
    base_max = stats.GetMaximum()

    stats.Execute(self.reg)
    reg_min = stats.GetMinimum()
    reg_max = stats.GetMaximum()

    #check if images in same range
    if base_min - reg_min > 1000 or base_max - reg_max > 2000:
        self.intensity_scale(base_min, base_max)
    
  def intensity_scale(self, min, max) -> None:
    '''Scale intensity values linearly to similar range for checkerboard'''
    #apply intensity rescale filter
    scale = sitk.RescaleIntensityImageFilter()
    scale.SetOutputMinimum(min)
    scale.SetOutputMaximum(max)
    self.reg = scale.Execute(self.reg)