#-----------------------------------------------------
# RegistrationLogic.py
#
# Created by:  Ryan Yan
# Created on:  24-01-2022
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

class RegistrationLogic:
    
    def __init__(self, baseImage=None, followImage=None):
        self.baseImage = baseImage
        self.followImgae = followImage
        self.sigma = 0.8
        self.lower = 686
        self.upper = 4000

        self.reg = sitk.ImageRegistrationMethod()

        #similarity metric
        self.reg.SetMetricAsMeanSquares()
        self.reg.SetMetricSamplingStrategy(self.reg.RANDOM)
        self.reg.SetMetricSamplingPercentage(0.001)

        #interprolator
        self.reg.SetInterpolator(sitk.sitkBSpline)

        #optimizer
        self.reg.SetOptimizerAsPowell(numberOfIterations=50)
        self.reg.SetOptimizerScalesFromPhysicalShift()

        #multi-resolution framework
        self.reg.SetShrinkFactorsPerLevel(shrinkFactors = [1, 1])
        self.reg.SetSmoothingSigmasPerLevel(smoothingSigmas=[1.0, 0])
        self.reg.SmoothingSigmasAreSpecifiedInPhysicalUnitsOn()

        self.reg.AddCommand( sitk.sitkIterationEvent, lambda: self.command_iteration(self.reg))

    def setRegistrationParamaters(self, baseImage, followImage):
        self.baseImage = baseImage
        self.followImage = followImage
    
    def execute(self, step):
        initalTransform_FU_to_BL = sitk.CenteredTransformInitializer(self.baseImage, self.followImage, sitk.Euler3DTransform(), sitk.CenteredTransformInitializerFilter.MOMENTS)

        self.reg.SetInitialTransform(initalTransform_FU_to_BL, inPlace=False)
        print('Start follow-up to baseline registration')
        FU_Transform = self.reg.Execute( sitk.Cast(self.baseImage, sitk.sitkFloat64), sitk.Cast(self.followImage, sitk.sitkFloat64) )

        # Resample registered FU grayscale image
        print('Resampling follow-up image')

        followImage_resampled = sitk.Resample(self.followImage, self.baseImage, FU_Transform, sitk.sitkBSpline, 0.0, self.followImage.GetPixelID())

        return followImage_resampled


    def command_iteration(self, method) :
        print( '{0:3} = {1:10.5f} : {2}'.format( method.GetOptimizerIteration(), method.GetMetricValue(), method.GetOptimizerPosition() ) )
    


    