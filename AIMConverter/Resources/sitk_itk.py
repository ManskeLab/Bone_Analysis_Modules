#----------------------------------------------------- 
# sitk_itk.py
#
# Created by:   Michael Kuczynski
# Created on:   26/01/2021
#
# Description: Converts between SimpleITK and ITK images.
#-----------------------------------------------------

import itk
import SimpleITK as sitk

import numpy as np

def sitk2itk(sitkImage):
    itkImage = itk.GetImageFromArray( sitk.GetArrayFromImage(sitkImage), is_vector=sitkImage.GetNumberOfComponentsPerPixel()>1 )
    itkImage.SetOrigin( sitkImage.GetOrigin() )
    itkImage.SetSpacing( sitkImage.GetSpacing() )   
    itkImage.SetDirection( itk.GetMatrixFromArray(np.reshape(np.array(sitkImage.GetDirection()), [3]*2)) )

    return itkImage


def itk2sitk(itkImage):
    sitkImage = sitk.GetImageFromArray( itk.GetArrayFromImage(itkImage), isVector=itkImage.GetNumberOfComponentsPerPixel()>1 )
    sitkImage.SetOrigin( tuple(itkImage.GetOrigin()) )
    sitkImage.SetSpacing( tuple(itkImage.GetSpacing()) )
    sitkImage.SetDirection(itk.GetArrayFromMatrix( itkImage.GetDirection()).flatten() ) 

    return sitkImage