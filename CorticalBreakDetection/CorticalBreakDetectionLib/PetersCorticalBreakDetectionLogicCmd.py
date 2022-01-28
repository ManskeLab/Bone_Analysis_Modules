#-----------------------------------------------------
# PetersCorticalBreakDetectionLogicCmd.py
#
# Created by:  Mingjie Zhao
# Created on:  26-05-2021
#
# Description: This script implements the automatic cortical break detection script
#              by Michael Peters et al. It identifies all the cortical breaks
#              that connect to both the periosteal and the endosteal boundaries
#              as well as underlying trabecular bone loss.
#
# Updated 2021-09-30 Sarah Manske to run from command line, beginning at step 1 
#               i.e., generate the seg/preprocessed file within the script
#-----------------------------------------------------
# Usage:       python PetersCorticalBreakDetectionLogicCommandLine.py inputImage [--inputContour] [--outputImage]
#                                                 [--voxelSize] [--lowerThreshold] [--upperThreshold]
#                                                 [--corticalThickness] [--dilateErodeDistance] [--preset]
#
# Param:       inputImage: The input image file path
#              inputContour: The input contour file path, default=[inputImage]_MASK
#              outputImage: The output image file path, default=[inputImage]_BREAKS
#              outputSeeds: The output seeds csv file path, default=[inputImage]_SEEDS
#              voxelSize: Isotropic voxel size in micrometres, default=82
#              lowerThreshold: default=686
#              upperThreshold: default=4000
#              sigma: Standard deviation for the Gaussian smoothing filter, default=0.8
#              corticaThickness: Distance from the periosteal boundary
#                                to the endosteal boundary, only erosions connected
#                                to both the periosteal and the endosteal boundaries
#                                are labeled, default=4
#              dilateErodeDistance: kernel radius for morphological dilation and
#                                   erosion, default=1
#              preset: Preset configuration for scanners: 1 - XCT I, 2 - XCT II
#
#-----------------------------------------------------
import SimpleITK as sitk
import pdb
import csv
import PetersCorticalBreakDetectionLogic

class PetersCorticalBreakDetectionLogicCmd:
    def __init__(self):
        pass

# run this script on command line
if __name__ == "__main__":
    import argparse

    # Read the input arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('inputImage', help='The input scan file path')
    parser.add_argument('-ic', '--inputContour', help='The input contour file path, default=[inputImage]_MASK', default="_MASK.mha", metavar='')
    parser.add_argument('-oi', '--outputImage', help='The output image file path, default=[inputImage]_BREAKS', default="_BREAKS.nrrd", metavar='')
    parser.add_argument('-os', '--outputSeeds', help='The output seeds csv file path, default=[inputImage]_SEEDS', default="_SEEDS.csv", metavar='')
    parser.add_argument('-vs', '--voxelSize', type=float, help='Isotropic voxel size in micrometres, default=82', default=82, metavar='')
    parser.add_argument('-lt', '--lowerThreshold', help='default=686', type=int, default=686, metavar='')
    parser.add_argument('-ut', '--upperThreshold', help='default=15000', type=int, default=4000, metavar='')
    parser.add_argument('-sg', '--sigma', type=float, help='Standard deviation for the Gaussian smoothing filter, default=0.8', default=0.8, metavar='')
    parser.add_argument('-ct', '--corticalThickness', type=int, default=4,
                        help='Distance from the periosteal boundary to the endosteal boundary, only erosions connected to both the periosteal and the endosteal boundaries are labeled, default=4', metavar='')
    parser.add_argument('-ded', '--dilateErodeDistance', type=int, default=1,
                        help='kernel radius for morphological dilation and erosion, default=1', metavar='')
    parser.add_argument('-p', '--preset', type=int, help='Preset configuration for scanners: 1 - XCT I, 2 - XCT II', metavar='')
    args = parser.parse_args()

    input_dir = args.inputImage
    contour_dir = args.inputContour
    output_dir = args.outputImage
    seeds_dir = args.outputSeeds
    voxelSize = args.voxelSize
    lower = args.lowerThreshold
    upper = args.upperThreshold
    sigma = args.sigma
    corticalThickness = args.corticalThickness
    dilateErodeDistance = args.dilateErodeDistance
    preset = args.preset

    #correct file directiories (default or incorrect file extension)
    if contour_dir == "_MASK.mha":
        contour_dir = input_dir[:input_dir.index('.')] + contour_dir
    if output_dir == "_BREAKS.nrrd":
        output_dir = input_dir[:input_dir.index('.')] + output_dir
    elif output_dir.find('.') == -1:
        output_dir += ".nrrd"
    if seeds_dir == "_SEEDS.csv":
        seeds_dir = input_dir[:input_dir.index('.')] + seeds_dir
    elif seeds_dir[-4] != ".csv":
        seeds_dir += ".csv"

    #settings based on preset
    if preset == 1:
        voxelSize = 82
        corticalThickness = 4
        dilateErodeDistance = 1
    elif preset == 2:
        voxelSize = 60.7
        corticalThickness = 5
        dilateErodeDistance = 2

    # read images
    img = sitk.ReadImage(input_dir)
    contour = sitk.ReadImage(contour_dir)

    # create erosion logic object
    erosion = PetersCorticalBreakDetectionLogic.PetersCorticalBreakDetectionLogic(img, contour, voxelSize, lower, upper,
                                       sigma, corticalThickness, dilateErodeDistance)

    # identify erosions
    step = 1
    print("Running automatic erosion detection script")
    while (erosion.execute(step)):
        step += 1
    erosion_img = erosion.getOutput()
    seeds_list = erosion.getSeeds()

    # store erosion_img in output_dir
    print("Storing image in "+output_dir)
    sitk.WriteImage(erosion_img, output_dir)

    #store erosion seeds
    print("Storing seeds in "+seeds_dir)
    with open(seeds_dir, 'w', newline='') as f:
        writer = csv.writer(f)
        for i in range(len(seeds_list)):
            writer.writerow([i] + list(seeds_list[i]))
