#-----------------------------------------------------
# RegistrationLogic.py
#
# Created by:  Ryan Yan
# Created on:  24-01-2022
#
# Description: This module performs longitudinal image registration given a baseline and a follow-up image.
#
#-----------------------------------------------------
# Usage:       Implemented in the Image Registration Module
#              
# Note:        Uses script from https://github.com/ManskeLab/BML_Turnover/blob/master/BML_T/BMLT_B_FU_reg.py
#
#-----------------------------------------------------
import SimpleITK as sitk

class RegistrationLogic:
    
    def __init__(self, baseImage=None, followImage=None):
        '''
        Initialize Registration Logic class
        '''

        #initial variables
        self.baseImage = baseImage
        self.followImgae = followImage
        self.sigma = 0.8
        self.lower = 686
        self.upper = 4000
        self.progressCallBack = None

        #registration method
        self.reg = sitk.ImageRegistrationMethod()

        #similarity metric
        self.reg.SetMetricAsMeanSquares()
        self.reg.SetMetricSamplingStrategy(self.reg.RANDOM)
        self.reg.SetMetricSamplingPercentage(0.01)

        #interprolator
        self.reg.SetInterpolator(sitk.sitkBSpline)

        #optimizer
        self.reg.SetOptimizerAsPowell()
        self.reg.SetOptimizerScalesFromPhysicalShift()

        #multi-resolution framework
        self.reg.SetShrinkFactorsPerLevel(shrinkFactors = [1, 1])
        self.reg.SetSmoothingSigmasPerLevel(smoothingSigmas=[1.0, 0])
        self.reg.SmoothingSigmasAreSpecifiedInPhysicalUnitsOn()

        self.reg.AddCommand( sitk.sitkIterationEvent, lambda: self.command_iteration(self.reg))

    def setRegistrationParamaters(self, baseImage:sitk.Image, followImage:sitk.Image, sampling=0.01) -> None:
        '''
        Change parameters for registration

        Args:
            baseImage (SimpleITK Image): baseline image
            followImage (SimpleITK Image): follow-up image
            sampling (float): metric sampling percentage (increase for greater accuracy at higher time cost)

        Returns:
            None
        '''
        #change image
        self.baseImage = baseImage
        self.followImage = followImage

        #change sampling percent
        self.reg.SetMetricSamplingPercentage(sampling)
    
    def setSimilarityMetric(self, metric:str) -> None:
        '''
        Change the similarity metric used for registration. See help message in the widget for more information on each metric.

        Args:
            metric (str): type of metric to use (\'mean_squares\', \'correlation\', \'mattes\', or \'ants\')

        Returns:
            None
        '''
        #determine type of metric and change
        if metric == 'mean_squares':
            self.reg.SetMetricAsMeanSquares()
        elif metric == 'correlation':
            self.reg.SetMetricAsCorrelation()
        elif metric == 'mattes':
            self.reg.SetMetricAsMattesMutualInformation()
        elif metric == 'ants':
            self.reg.SetMetricAsANTSNeighborhoodCorrelation(2)
    
    def setOptimizer(self, optimizer:str) -> None:
        if optimizer == 'amoeba':
            self.reg.SetOptimizerAsAmoeba(1, 100)
        elif optimizer == 'exhaustive':
            self.reg.SetOptimizerAsExhaustive(100)
        elif optimizer == 'powell':
            self.reg.SetOptimizerAsPowell()
        elif optimizer == 'one_plus_one':
            self.reg.SetOptimizerAsOnePlusOneEvolutionary()
        elif optimizer == 'gradient':
            self.reg.SetOptimizerAsGradientDescent(1, 100)
        elif optimizer == 'gradient_ls':
            self.reg.SetOptimizerAsGradientDescentLineSearch(1, 100)
        elif optimizer == 'gradient_reg':
            self.reg.SetOptimizerAsRegularStepGradientDescent(1, 1, 100)
        elif optimizer == 'lbfgs2':
            self.reg.SetOptimizerAsLBFGS2()
    
    def execute(self) -> sitk.Image:
        '''
        Run the registration algorithm

        Args:

        Returns:
            SimpleITK Image: registered follow up image
        '''
        self.progress = 0

        initalTransform_FU_to_BL = sitk.CenteredTransformInitializer(self.baseImage, self.followImage, sitk.Euler3DTransform(), sitk.CenteredTransformInitializerFilter.MOMENTS)

        self.reg.SetInitialTransform(initalTransform_FU_to_BL, inPlace=False)
        print('Start follow-up to baseline registration')
        FU_Transform = self.reg.Execute( sitk.Cast(self.baseImage, sitk.sitkFloat64), sitk.Cast(self.followImage, sitk.sitkFloat64) )

        # Resample registered FU grayscale image
        print('Resampling follow-up image')

        followImage_resampled = sitk.Resample(self.followImage, self.baseImage, FU_Transform, sitk.sitkBSpline, 0.0, self.followImage.GetPixelID())

        return followImage_resampled


    def command_iteration(self, method:sitk.ImageRegistrationMethod) -> None:
        '''
        Print updates on registration status
        '''
        print( '{0:3} = {1:10.5f} : {2}'.format( method.GetOptimizerIteration(), method.GetMetricValue(), method.GetOptimizerPosition() ) )

        #update progress
        self.progress += (100 - self.progress) // 3
        self.progressCallBack(self.progress)
    


    