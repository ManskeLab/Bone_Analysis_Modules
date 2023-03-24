#-----------------------------------------------------
# MaskLogicCommandLine.py
#
# Created by:  Mingjie Zhao, Ryan Yan
# Created on:  10-01-2022
#
# Description: Uses MaskLogic.py
#
#-----------------------------------------------------
# Usage:       This module is designed to be run on command line or terminal
#              python MaskLogic.py inputImages outputFolder [--lowerThreshold] [--upperThreshold]
#                                     [--boneNum] [--dilateErodeRadius] [--roughMask]
#
# Param:       inputImages: The file path for the directory containing grayscale scans
#              outputFolder: The output folder path
#              sigma, default=2
#              lowerThreshold, default=900
#              upperThreshold, default=4000
#              dilateErodeRadius: morphological dilate/erode kernel radius in voxels, default=38
#              boneNum: Number of separate bone structures, default=1
#              roughMask: The file path of optional rough mask that helps separate bones
#
#-----------------------------------------------------
import SimpleITK as sitk, os
import MaskLogic

class MaskLogicCmd:
    def __init__(self):
        pass


# execute this script on command line
if __name__ == "__main__":
    import argparse

    # Read the input arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('inputImages', help='The file path for the directory containing grayscale scans')
    parser.add_argument('outputFolder', help='The output folder path')
    parser.add_argument('-lt', '--lowerThreshold', help='default=900', type=int, default=900, metavar='')
    parser.add_argument('-ut', '--upperThreshold', help='default=4000', type=int, default=4000, metavar='')
    parser.add_argument('-sg', '--sigma', type=float, help='Standard deviation for the Gaussian smoothing filter, default=2', default=2, metavar='')
    parser.add_argument('-bn', '--boneNum', type=int, help='Number of separate bone structures, default=1', default=1, metavar='')
    parser.add_argument('-ded', '--dilateErodeRadius', type=int, default=38,
                         help='Dilate/erode kernel radius in voxels, default=38', metavar='')
    parser.add_argument('-rm', '--roughMask', default="",
                         help='The file path of optional rough mask that helps separate bones', metavar='')
    args = parser.parse_args()

    input_dir = args.inputImages
    output_dir = args.outputFolder
    lower = args.lowerThreshold
    upper = args.upperThreshold
    sigma = args.sigma
    boneNum = args.boneNum
    dilateErodeRadius = args.dilateErodeRadius
    roughMask_dir = args.roughMask

    for file in os.listdir(input_dir):

        # read images
        print("Reading image in {}".format(input_dir + '/' + file))
        model_img = sitk.ReadImage(input_dir + '/' + file)
        roughMask = None
        if (roughMask_dir != ""):
            print("Reading in rough mask")
            for rough_name in os.listdir(roughMask_dir):
                if file in rough_name:
                    roughMask = sitk.ReadImage(roughMask_dir + '/' + rough_name)

        # create mask object
        mask = MaskLogic.MaskLogic(model_img, lower, upper, sigma, boneNum, dilateErodeRadius, roughMask)

        # run mask algorithm
        print("Running mask script")
        step = 1
        while (mask.execute(step)):
            step += 1
        mask_img = mask.getOutput()

        # store mask
        print("Storing image in {}".format(output_dir))
        filename = os.path.splitext(file)[0]
        sitk.WriteImage(mask_img, output_dir + '/' + file + '_MASK.mha')
