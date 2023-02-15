"""
sitk_itk.py

Created by:   Michael Kuczynski
Created on:   26/01/2021

Description: Converts between SimpleITK and ITK images.
"""

import itk
import SimpleITK as sitk

import numpy as np


def sitk_itk(sitk_image):
    """
    Convert a SimpleITK image to an ITK image.

    Parameters
    ----------
    sitk_image : SimpleITK.Image

    Returns
    -------
    itk_image : ITK.Image
    """
    itk_image = itk.GetImageFromArray(
        sitk.GetArrayFromImage(sitk_image),
        is_vector=sitk_image.GetNumberOfComponentsPerPixel() > 1,
    )
    itk_image.SetOrigin(sitk_image.GetOrigin())
    itk_image.SetSpacing(sitk_image.GetSpacing())
    itk_image.SetDirection(
        itk.GetMatrixFromArray(np.reshape(np.array(sitk_image.GetDirection()), [3] * 2))
    )

    return itk_image


def itk_sitk(itk_image):
    """
    Convert an ITK image to a SimpleITK image.

    Parameters
    ----------
    itk_image : ITK.Image

    Returns
    -------
    sitk_image : SimpleITK.Image
    """
    sitk_image = sitk.GetImageFromArray(
        itk.GetArrayFromImage(itk_image),
        isVector=itk_image.GetNumberOfComponentsPerPixel() > 1,
    )
    sitk_image.SetOrigin(tuple(itk_image.GetOrigin()))
    sitk_image.SetSpacing(tuple(itk_image.GetSpacing()))
    sitk_image.SetDirection(itk.GetArrayFromMatrix(itk_image.GetDirection()).flatten())

    return sitk_image
