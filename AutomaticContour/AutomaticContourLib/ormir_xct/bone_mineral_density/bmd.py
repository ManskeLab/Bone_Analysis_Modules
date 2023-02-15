"""
bmd.py

Created by:   Michael Kuczynski
Created on:   June 29, 2022

Description: Calculates Bone Mineral Density (BMD) of
             an image in mgHA/ccm. The user must specify
             what the input image's units are
             (e.g., HU, Scanco native, linear attenuation)

Notes:
  1. If using AIM/ISQ images as input, they are read in using
      the ITK Scanco reader which automatically converts the
      images from Scanco native units to HU.
  2. If using NII/MHA/etc. images as input, they are read in
      using the SimpleITK reader and you need to know the 
      units of your image to provide as input.
  3. Default values are provided for muScaling, muWater, 
      rescaleSlope, and rescaleIntercept, but you should
      try to provide your own values for improved accuracy.

Usage:
  python bmd.py inputImage.nii
  python bmd.py inputImage.AIM HU 8192 0.2396 1613.94397 -392.247009
"""
import sys
import argparse
import SimpleITK as sitk

from ormir_xct.util.scanco_rescale import *
from ormir_xct.util.file_reader import file_reader


def bmd(image, image_units, mu_scaling, mu_water, rescale_slope, rescale_intercept):
    """
    Compute bone mineral density (BMD) from the intensity information of the
    provided image. The image units need to be provided to convert voxels to
    BMD units (mg HA/ccm) before calculating BMD.

    Parameters
    ----------
    image : SimpleITK.Image

    image_units : string

    mu_scaling : int

    mu_water : float

    rescale_slope : float

    rescale_intercept : float

    Returns
    -------
    image_statistics_filter : SimpleITK.StatisticsImageFilter
    """
    image_statistics_filter = sitk.StatisticsImageFilter()

    # Now convert to BMD units if needed
    if image_units == "bmd":
        # No conversion needed
        image_statistics_filter.Execute(image)
    elif image_units == "scanco":
        # Convert from Scanco native units to linear attenuation
        # Then convert to BMD
        image = convert_scanco_to_bmd(
            image, mu_scaling, rescale_slope, rescale_intercept
        )
        image_statistics_filter.Execute(image)
    elif image_units == "attenuation":
        # Convert to BMD
        image = convert_linear_attenuation_to_bmd(
            image, rescale_slope, rescale_intercept
        )
        image_statistics_filter.Execute(image)
    elif image_units == "hu":
        # Convert from HU to linear attenuation
        # Then convert to BMD
        image = convert_hu_to_bmd(image, mu_water, rescale_slope, rescale_intercept)
        image_statistics_filter.Execute(image)
    else:
        print(
            "ERROR: Invalid image units provided. Only BMD, SCANCO, ATTENUATION, or HU are accepted."
        )
        sys.exit(1)

    return image_statistics_filter


def main():
    # Parse input arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=str, help="The input imagek (path + filename)")
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
        help="Linear attenuation of water",
    )
    parser.add_argument(
        "rescale_slope",
        type=float,
        nargs="?",
        default="1600.0",
        help="Slope to scale to BMD",
    )
    parser.add_argument(
        "rescale_intercept",
        type=float,
        nargs="?",
        default="-390.0",
        help="Intercept to scale to BMD",
    )
    args = parser.parse_args()

    image_path = args.image
    image_units = (args.image_units).lower()
    mu_scaling = args.mu_scaling
    mu_water = args.mu_water
    rescale_slope = args.rescale_slope
    rescale_intercept = args.rescale_intercept

    image = file_reader(image_path)

    # Get the image stats
    stats = bmd(
        image, image_units, mu_scaling, mu_water, rescale_slope, rescale_intercept
    )
    print(stats)


if __name__ == "__main__":
    main()
