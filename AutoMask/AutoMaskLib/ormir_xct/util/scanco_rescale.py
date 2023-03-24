"""
scanco_rescale.py

Created by:   Michael Kuczynski
Created on:   June 29, 2022

Description: Converts between Scanco native units, HU,
              BMD (mgHA/ccm), and linear attenuation (1/cm).
"""


def convert_scanco_to_linear_attenuation(image, mu_scaling):
    """
    Converts an image from Scanco native units to linear attenuation (1/cm).
    The following relationships are used:
    1. LinearAttenuation = ScancoUnits / mu_scaling
    """
    return image / mu_scaling


def convert_scanco_to_hu(image, mu_scaling, mu_water):
    """
    Converts an image from Scanco native units to Hounsfield Units.
    The following relationships are used:
    1. LinearAttenuation = ScancoUnits / mu_scaling
    2. HU = -1000 + LinearAttenuation * (1000 / mu_water)
    """
    image_lin_att = convert_scanco_to_linear_attenuation(image, mu_scaling)
    image_hu = -1000 + image_lin_att * (1000 / mu_water)
    return image_hu


def convert_scanco_to_bmd(image, mu_scaling, rescale_slope, rescale_intercept):
    """
    Converts an image from Scanco native units to bone denisty units (mgHA/ccm).
    The following relationships are used:
    1. LinearAttenuation = ScancoUnits / mu_scaling
    2. BMD = LinearAttenuation * rescale_slope + rescale_intercept
    """
    image_lin_att = convert_scanco_to_linear_attenuation(image, mu_scaling)
    image_bmd = image_lin_att * rescale_slope + rescale_intercept
    return image_bmd


def convert_hu_to_linear_attenuation(image, mu_water):
    """
    Converts an image from HU to linear attenuation (1/cm).
    The following relationships are used:
    1. LinearAttenuation = (HU + 1000) * (mu_water / 1000)
    """
    image_lin_att = (image + 1000) * (mu_water / 1000)
    return image_lin_att


def convert_hu_to_scanco(image, mu_water, mu_scaling):
    """
    Converts an image from HU to Scanco native units.
    The following relationships are used:
    1. LinearAttenuation = (HU + 1000) * (mu_water / 1000)
    2. ScancoUnits = LinearAttenuation * mu_scaling
    """
    image_lin_att = convert_hu_to_linear_attenuation(image, mu_water)
    return image_lin_att * mu_scaling


def convert_hu_to_bmd(image, mu_water, rescale_slope, rescale_intercept):
    """
    Converts an image from HU to bone denisty units (mgHA/ccm).
    The following relationships are used:
    1. LinearAttenuation = (HU + 1000) * (mu_water / 1000)
    2. BMD = LinearAttenuation * rescale_slope + rescale_intercept
    """
    image_lin_att = convert_hu_to_linear_attenuation(image, mu_water)
    image_bmd = image_lin_att * rescale_slope + rescale_intercept
    return image_bmd


def convert_linear_attenuation_to_hu(image, mu_water):
    """
    Converts an image from linear attenuation (1/cm) to HU.
    The following relationships are used:
    1. HU = LinearAttenuation * (1000 / mu_water) - 1000
    """
    image_hu = image * (1000 / mu_water) - 1000
    return image_hu


def convert_linear_attenuation_to_scanco(image, mu_scaling):
    """
    Converts an image from linear attenuation to Scanco native units.
    The following relationships are used:
    1. ScancoUnits = LinearAttenuation * mu_scaling
    """
    return image * mu_scaling


def convert_linear_attenuation_to_bmd(image, rescale_slope, rescale_intercept):
    """
    Converts an image from linear attenuation to bone denisty units (mgHA/ccm).
    The following relationships are used:
    1. BMD = LinearAttenuation * rescale_slope + rescale_intercept
    """
    image_bmd = image * rescale_slope + rescale_intercept
    return image_bmd
