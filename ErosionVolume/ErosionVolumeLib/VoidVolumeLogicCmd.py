#-----------------------------------------------------
# VoidVolumeLogicCmd.py
#
# Created by:  Mingjie Zhao, Ryan Yan
# Created on:  13-01-2022
#
# Description: Uses VoidVolumeLogic.py
#
#-----------------------------------------------------
# Usage:       This module is designed to be run on command Line or terminal
#              python VoidVolume.py inputImage [--inputMask] [--outputImage] [--seeds]
#                                   [--lowerThreshold] [--upperThreshold] [--sigma]
#                                   [--minimumRadius] [--dilateErodeDistance]
#
# Param:       inputImage: The input scan file path
#              inputMask: The input mask file path, default=[inputImage]_MASK
#              outputImage: The output image file path, default=[inputImage]_ER
#              seeds: The seed points csv file path, default=[inputImage]_SEEDS
#              lowerThreshold, default=686
#              upperThreshold, default=15000
#              sigma: Standard deviation for the Gaussian smoothing filter, default=1
#              minimumRadius: Minimum erosion radius in voxels, default=3
#              dilateErodeDistance: Morphological kernel radius in voxels, default=5
#
#-----------------------------------------------------
import SimpleITK as sitk
import VoidVolumeLogic

class VoidVolumeLogicCmd:
    def __init__(self):
        pass


# execute this script on command line
if __name__ == "__main__":
    import argparse

    # Read the input arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('inputImage', help='The input scan file path')
    parser.add_argument('-im', '--inputMask', help='The input mask file path, default=[inputImage]_MASK', default="_MASK.mha", metavar='')
    parser.add_argument('-oi', '--outputImage', help='The output image file path, default=[inputImage]_ER', default="_ER.nrrd", metavar='')
    parser.add_argument('-sd', '--seeds', help='The seed points csv file path, default=[inputImage]_SEEDS', default="_SEEDS.csv", metavar='')
    parser.add_argument('-lt', '--lowerThreshold', help='default=686', type=int, default=686, metavar='')
    parser.add_argument('-ut', '--upperThreshold', help='default=15000', type=int, default=15000, metavar='')
    parser.add_argument('-sg', '--sigma', type=float, help='Standard deviation for the Gaussian smoothing filter, default=1', default=1, metavar='')
    parser.add_argument('-mr', '--minimumRadius', type=int, default=3, 
                        help='Minimum erosion radius in voxels, default=3', metavar='')
    parser.add_argument('-ded', '--dilateErodeDistance', type=int, default=4,
                        help='Morphological kernel radius in voxels, default=4', metavar='')
    args = parser.parse_args()

    input_dir = args.inputImage
    mask_dir = args.inputMask
    output_dir = args.outputImage
    seeds_dir = args.seeds
    lower = args.lowerThreshold
    upper = args.upperThreshold
    sigma = args.sigma
    minimumRadius = args.minimumRadius
    dilateErodeDistance = args.dilateErodeDistance

    #correct file directories
    if mask_dir == "_MASK.mha":
        mask_dir = input_dir[:input_dir.index('.')] + mask_dir
    if output_dir == "_ER.nrrd":
        output_dir = input_dir[:input_dir.index('.')] + output_dir
    elif output_dir.find('.') == -1:
        output_dir += ".nrrd"
    if seeds_dir == "_SEEDS.csv":
        seeds_dir = input_dir[:input_dir.index('.')] + seeds_dir

    # read images
    img = sitk.ReadImage(input_dir)
    mask = sitk.ReadImage(mask_dir)
    # read seadpoints
    seeds = []
    HEADER = 3
    lineCount = 0
    with open(seeds_dir) as fcsv:
        for line in fcsv:
            # line = 'id,x,y,z,ow,ox,oy,oz,vis,sel,lock,label,desc,associatedNodeID'
            if lineCount >= HEADER:
                seed = line.split(',')
                x = int(float(seed[1]))
                y = int(float(seed[2]))
                z = int(float(seed[3]))
                seeds.append((x,y,z))
            lineCount += 1

    # create erosion logic object
    erosion = VoidVolumeLogic.VoidVolumeLogic(img, mask, lower, upper, sigma, seeds,
                              minimumRadius, dilateErodeDistance)

    # identify erosions
    print("Running erosion detection script")
    step = 1
    while (erosion.execute(step)):
        step += 1
    erosion_img = erosion.getOutput()

    # store erosions
    print("Storing image in {}".format(output_dir))
    sitk.WriteImage(erosion_img, output_dir)
