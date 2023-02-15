"""
ipl_seg.py

Created by:   Michael Kuczynski
Created on:   June 29, 2022

Description: Binarize an input image following the standard
              segmentation protocol performed in IPL. 

Notes:
  1. Gaussian smoothing is done in IPL with sigma = 0.5
      and support = 1. In ITK, this translates to using
      the SmoothingRecursiveGaussian filter with
      sigma = 0.5 * voxel size = 0.5 * 0.0606964.
  2. The output of the Guassian filter will be a float
      image so we may need to cast to a different type
      depending on what image you want to write to.
  3. The binarization is done using the same thresholds
      set in IPL, but we need to know the image units
      prior to binarization (default is set to BMD units).
"""

import sys
import argparse
import SimpleITK as sitk

from ormir_xct.util.scanco_rescale import *

# Default threshold values used in IPL
threshold_dict = {
    "HU_Lower": 1170.0,
    "HU_Upper": 10000.0,
    "BMD_Lower": 446.8,
    "BMD_Upper": 3000.0,
    "Native_Lower": 4259.0,
    "Native_Upper": 32767.0,
    "LinAtt_Lower": 0.52,
    "LinAtt_Upper": 4.00,
    "Per1000_Lower": 130.0,
    "Per1000_Upper": 1000.0,
}


def ipl_seg(
    input_image, lower_threshold, upper_threshold, voxel_size=0.0606964, sigma=0.5
):
    """
    Check the image units and get the correct thresholds.

    Parameters
    ----------
    input_image : SimpleITK.Image

    lower_threshold : float

    upper_threshold : float

    voxel_size : float

    sigma : float

    Returns
    -------
    seg : SimpleITK.Image
    """
    smooth = sitk.SmoothingRecursiveGaussian(input_image, sigma * voxel_size)
    seg = sitk.BinaryThreshold(smooth, lower_threshold, upper_threshold, 127, 0)
    return seg


def main():
    parser = argparse.ArgumentParser(
        prog="ipl_seg",
        description="""
        Binarize an input image following the standard segmentation protocol 
        performed in IPL (Scanco). This is roughly equivalent to the IPL 
        command '/seg_gauss' with sigma = 0.5.

        The binarization is done using the same thresholds set in IPL, but  
        we need to know the image units prior to binarization 
        (default is set to BMD units).
        """,
    )
    parser.add_argument("input_image", type=str, help="The input image")
    parser.add_argument("output_image", type=str, help="The output image")
    parser.add_argument(
        "image_units",
        type=str,
        nargs="?",
        default="BMD",
        help="Image voxel units (options: BMD, SCANCO, ATTENUATION, HU, PER1000)",
    )
    args = parser.parse_args()

    input_image_path = args.input_image
    output_image_path = args.output_image
    image_units = (args.image_units).lower()

    if image_units == "bmd":
        lower_threshold = threshold_dict.get("BMD_Lower")
        upper_threshold = threshold_dict.get("BMD_Upper")
    elif image_units == "scanco":
        lower_threshold = threshold_dict.get("Native_Lower")
        upper_threshold = threshold_dict.get("Native_Upper")
    elif image_units == "attenuation":
        lower_threshold = threshold_dict.get("LinAtt_Lower")
        upper_threshold = threshold_dict.get("LinAtt_Upper")
    elif image_units == "hu":
        lower_threshold = threshold_dict.get("HU_Lower")
        upper_threshold = threshold_dict.get("HU_Upper")
    elif image_units == "per1000":
        lower_threshold = threshold_dict.get("Per1000_Lower")
        upper_threshold = threshold_dict.get("Per1000_Upper")
    else:
        print(
            "ERROR: Invalid image units provided. Only BMD, SCANCO, ATTENUATION, HU, or PER1000 are accepted."
        )
        sys.exit(1)

    # Read in image as a 32-bit float so that we can rescale correctly if needed
    input_image = sitk.ReadImage(input_image_path, sitk.sitkFloat32)
    seg = ipl_seg(input_image, lower_threshold, upper_threshold)
    sitk.WriteImage(seg, output_image_path)


if __name__ == "__main__":
    main()
