"""
bmd_masked.py

Created by:   Michael Kuczynski
Created on:   June 29, 2022

Description: Calculates Bone Mineral Density (BMD) of
             an image in mgHA/ccm after masking with the input
             segmentation mask. The user must specify what
             the input image's units are
             (e.g., HU, Scanco native, linear attenuation)

Notes:
  1. For now, the mask cannot be an AIM/ISQ file as the ITK
      Scanco reader doesn't work properly with binary images.
  2. If using AIM/ISQ images as input, they are read in using
      the ITK Scanco reader which automatically converts the
      images from Scanco native units to HU.
  3. If using NII/MHA/etc. images as input, they are read in
      using the SimpleITK reader and you need to know the 
      units of your image to provide as input.
  4. Default values are provided for muScaling, muWater, 
      rescaleSlope, and rescaleIntercept, but you should
      try to provide your own values for improved accuracy.

Usage:
  python bmd.py inputImage.nii inputMask.nii
  python bmd.py inputImage.AIM inputMask.nii HU 8192 0.2396 1613.94397 -392.247009
"""

import sys
import argparse
import SimpleITK as sitk

from ormir_xct.util.scanco_rescale import *
from ormir_xct.util.file_reader import file_reader


def bmd_masked(
    image,
    image_units,
    background,
    mu_scaling,
    mu_water,
    rescale_slope,
    rescale_intercept,
):
    """
    Calculates Bone Mineral Density (BMD) of an image in mgHA/ccm after masking
    with the input segmentation mask. The user must specify what the input
    image's units are (e.g., HU, Scanco native, linear attenuation).

    Parameters
    ----------
    image : SimpleITK.Image

    image_units : string

    background : int

    mu_scaling : int

    mu_water : float

    rescale_slope : float

    rescale_intercept : float

    Returns
    -------
    list
        A list containing the mean and std BMD
    """
    mean, std = 0, 0

    # No conversion needed if we already have BMD units
    if image_units == "scanco":
        # Convert from Scanco native units to linear attenuation. Then convert to BMD.
        # Convert both the image and background value.
        image = convert_scanco_to_bmd(
            image, mu_scaling, rescale_slope, rescale_intercept
        )
        background = background / mu_scaling
        background = background * rescale_slope + rescale_intercept
    elif image_units == "attenuation":
        # Convert to BMD.
        # Convert both the image and background value.
        image = convert_linear_attenuation_to_bmd(
            image, rescale_slope, rescale_intercept
        )
        background = background * rescale_slope + rescale_intercept
    elif image_units == "hu":
        # Convert from HU to linear attenuation. Then convert to BMD.
        # Convert both the image and background value.
        image = convert_hu_to_bmd(image, mu_water, rescale_slope, rescale_intercept)
        background = (background + 1000) * (mu_water / 1000)
        background = background * rescale_slope + rescale_intercept
    elif image_units != "bmd":
        print(
            "ERROR: Invalid image units provided. Only BMD, SCANCO, ATTENUATION, or HU are accepted."
        )
        sys.exit(1)

    numpy_image = sitk.GetArrayFromImage(image)
    num_bone_voxels = (numpy_image > background).sum()
    mean = numpy_image[numpy_image > background].sum() / num_bone_voxels
    std = numpy_image[numpy_image > background].std()

    return mean, std


def main():
    # Parse input arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=str, help="The input image (path + filename)")
    parser.add_argument(
        "image_seg", type=str, help="The input image mask (path + filename)"
    )
    parser.add_argument(
        "image_units",
        type=str,
        nargs="?",
        default="BMD",
        help="The image voxel units (options: BMD, SCANCO, ATTENUATION, HU)",
    )
    parser.add_argument(
        "mu_scaling",
        type=int,
        nargs="?",
        default="8192",
        help="The Scanco defined scaling value (usually 8192 or 4096)",
    )
    parser.add_argument(
        "mu_water",
        type=float,
        nargs="?",
        default="0.25",
        help="Linear attenuation of water (default = 0.25)",
    )
    parser.add_argument(
        "rescale_slope",
        type=float,
        nargs="?",
        default="1600.0",
        help="Slope to scale to BMD (default = 1600.0)",
    )
    parser.add_argument(
        "rescale_intercept",
        type=float,
        nargs="?",
        default="-390.0",
        help="Intercept to scale to BMD (default = -390.0)",
    )
    parser.add_argument(
        "background",
        type=float,
        nargs="?",
        default="-1000",
        help="Background value for cropped images (default = -1000)",
    )
    args = parser.parse_args()

    image_path = args.image
    image_mask_path = args.image_seg
    image_units = (args.image_units).lower()
    mu_scaling = args.mu_scaling
    mu_water = args.mu_water
    rescale_slope = args.rescale_slope
    rescale_intercept = args.rescale_intercept
    background_value = args.background

    image = file_reader(image_path)

    # Mask the image
    mask = sitk.ReadImage(image_mask_path)
    background_value = -50000
    masked_image = sitk.Mask(image, mask, background_value, 0)

    # Images and masks from created in IPL often have different dimensions.
    # In SimpleITK, to use the MaskImageFilter, both the image and mask need
    # to have the same dimensions. However, even if you mask an image with a
    # GOBJ in IPL, when you convert it to NII/MHA/etc., the image isn't cropped
    # tight to the bone and we have some background values around the image.
    # (i.e., we will have the bone cropped and values of -1000 around the image)
    #
    # To avoid this, just convert the image to a NumPy array and find the mean
    #  and std of all values that aren't considered background.
    mean, std = bmd_masked(
        masked_image,
        image_units,
        background_value,
        mu_scaling,
        mu_water,
        rescale_slope,
        rescale_intercept,
    )
    print(mean)
    print(std)


if __name__ == "__main__":
    main()
