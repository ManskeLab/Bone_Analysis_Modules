#-----------------------------------------------------
# ContourLogicCommandLine.py
#
# Created by:  Mingjie Zhao, Ryan Yan
# Created on:  10-01-2022
#
# Description: Uses ContourLogic.py
#
#-----------------------------------------------------
# Usage:       This module is designed to be run on command line or terminal
#              python ContourLogic.py inputImage [--outputImage] [--lowerThreshold] [--upperThreshold]
#                                     [--boneNum] [--dilateErodeRadius] [--roughMask]
#
# Param:       inputImage: The input greyscale image to be contoured
#              outputImage: The output image to store the contour, default=[filename]_MASK
#              sigma, default=2
#              lowerThreshold, default=900
#              upperThreshold, default=4000
#              dilateErodeRadius: morphological dilate/erode kernel radius in voxels, default=38
#              boneNum: Number of separate bone structures, default=1
#              roughMask: The file path of optional rough mask that helps separate bones
#
#-----------------------------------------------------
import SimpleITK as sitk
import ContourLogic

class ContourLogicCmd:
    def __init__(self):
        pass


# execute this script on command line
if __name__ == "__main__":
    import argparse

    # Read the input arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('inputImage', help='The input image file path')
    parser.add_argument('-oi', '--outputImage', help='The output image file path, default=[inputImage]_MASK', default=None, metavar='')
    parser.add_argument('-lt', '--lowerThreshold', help='default=900', type=int, default=900, metavar='')
    parser.add_argument('-ut', '--upperThreshold', help='default=4000', type=int, default=4000, metavar='')
    parser.add_argument('-sg', '--sigma', type=float, help='Standard deviation for the Gaussian smoothing filter, default=2', default=2, metavar='')
    parser.add_argument('-bn', '--boneNum', type=int, help='Number of separate bone structures, default=1', default=1, metavar='')
    parser.add_argument('-ded', '--dilateErodeRadius', type=int, default=38,
                         help='Dilate/erode kernel radius in voxels, default=38', metavar='')
    parser.add_argument('-rm', '--roughMask', default="",
                         help='The file path of optional rough mask that helps separate bones', metavar='')
    args = parser.parse_args()

    input_dir = args.inputImage
    output_dir = args.outputImage
    lower = args.lowerThreshold
    upper = args.upperThreshold
    sigma = args.sigma
    boneNum = args.boneNum
    dilateErodeRadius = args.dilateErodeRadius
    roughMask_dir = args.roughMask

    #correct output file (default and invalid file extension)
    if not output_dir:
        output_dir = input_dir[:input_dir.index('.')] + '_MASK.mha'
    elif output_dir.find('.') == -1:
        output_dir += ".mha"

    # read images
    print("Reading image in {}".format(input_dir))
    model_img = sitk.ReadImage(input_dir)
    roughMask = None
    if (roughMask_dir != ""):
        print("Reading rough mask in {}".format(roughMask_dir))
        roughMask = sitk.ReadImage(roughMask_dir)

    # create contour object
    contour = ContourLogic.ContourLogic(model_img, lower, upper, sigma, boneNum, dilateErodeRadius, roughMask)

    # run contour algorithm
    print("Running contour script")
    step = 1
    while (contour.execute(step)):
        step += 1
    contour_img = contour.getOutput()

    # store contour
    print("Storing image in {}".format(output_dir))
    sitk.WriteImage(contour_img, output_dir)
