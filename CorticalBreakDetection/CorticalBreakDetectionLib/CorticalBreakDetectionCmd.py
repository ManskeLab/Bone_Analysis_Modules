#-----------------------------------------------------
# PetersCorticalBreakDetectionLogicCmd.py
#
# Created by:  Mingjie Zhao
# Created on:  26-05-2021
#
# Description: Batch script for cortical break detection
#
# Updated 2021-09-30 Sarah Manske to run from command line, beginning at step 1 
#               i.e., generate the seg/preprocessed file within the script
#-----------------------------------------------------
# Usage:       python PetersCorticalBreakDetectionLogicCommandLine.py inputImage [--inputContour] [--outputImage]
#                                                 [--voxelSize] [--lowerThreshold] [--upperThreshold]
#                                                 [--corticalThickness] [--dilateErodeDistance] [--preset]
#              Images and contours must be in separate folders
#              Contour filenames must contain the full name of their corresponding image
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
# Notes:       Contour files must contain the name of the corresponding grayscale file
#
#-----------------------------------------------------
import SimpleITK as sitk
import os, csv
import PetersCorticalBreakDetectionLogic

class PetersCorticalBreakDetectionLogicCmd:
    def __init__(self):
        pass

# run this script on command line
if __name__ == "__main__":
    import argparse

    # Read the input arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('inputImages', help='The file path for the directory containing grayscale scans')
    parser.add_argument('inputContours', help='The file path for the directory containing contour masks')
    parser.add_argument('outputFolder', help='The output folder file path')
    parser.add_argument('-os', '--outputSeeds', help='The output seeds csv file path, default=[same as output folder]', default=None, metavar='')
    parser.add_argument('-vs', '--voxelSize', type=float, help='Isotropic voxel size in micrometres, default=82', default=82, metavar='')
    parser.add_argument('-lt', '--lowerThreshold', help='default=686', type=int, default=686, metavar='')
    parser.add_argument('-ut', '--upperThreshold', help='default=15000', type=int, default=4000, metavar='')
    parser.add_argument('-sg', '--sigma', type=float, help='Standard deviation for the Gaussian smoothing filter, default=0.8', default=0.8, metavar='')
    parser.add_argument('-ct', '--corticalThickness', type=int, default=4,
                        help='Distance from the periosteal boundary to the endosteal boundary, default=4', metavar='')
    parser.add_argument('-ded', '--dilateErodeDistance', type=int, default=1,
                        help='Kernel radius for morphological dilation and erosion, default=1', metavar='')
    parser.add_argument('-p', '--preset', type=int, help='Preset configuration for scanners: 1 - XCT I, 2 - XCT II', metavar='')
    parser.add_argument('-ot', '--outputTypes', type=int, help='Images to output: 0 - None, 1 - Breaks only, 2 - Erosions only, 3 - Both', default=1, metavar='')
    args = parser.parse_args()

    input_dir = args.inputImages
    contour_dir = args.inputContours
    output_dir = args.outputFolder
    seeds_dir = args.outputSeeds
    voxelSize = args.voxelSize
    lower = args.lowerThreshold
    upper = args.upperThreshold
    sigma = args.sigma
    corticalThickness = args.corticalThickness
    dilateErodeDistance = args.dilateErodeDistance
    preset = args.preset
    outputTypes = args.outputTypes

    #set seeds_dir if none
    if not seeds_dir:
        seeds_dir = output_dir

    #settings based on preset
    if preset == 1:
        voxelSize = 82
        corticalThickness = 4
        dilateErodeDistance = 2
    elif preset == 2:
        voxelSize = 60.7
        corticalThickness = 5
        dilateErodeDistance = 3

    contour_list = os.listdir(contour_dir)
    for file in os.listdir(input_dir):

        # read image
        try:
            img = sitk.ReadImage(input_dir + '/' + file)
        except:
            print('Could not read in ' + file)
            continue

        filename = os.path.splitext(file)[0]
        
        #read mask(s)
        contours = []
        for contour_name in contour_list:
            if filename in contour_name:
                contours.append(contour_name)
        if len(contours) == 0:
            print("No contours found for " + file)
            continue

        for contour_name in contours:
            contour = sitk.ReadImage(contour_dir + '/' + contour_name)
            # create erosion logic object
            erosion = PetersCorticalBreakDetectionLogic.PetersCorticalBreakDetectionLogic(img, contour, voxelSize, lower, upper,
                                            sigma, corticalThickness, dilateErodeDistance)

            # identify erosions
            step = 1
            print("Running automatic erosion detection script")
            while (erosion.execute(step)):
                step += 1
            break_img = erosion.getOutputBreaks()
            erosion_img = erosion.getOutputErosions()
            seeds_list = erosion.getSeeds()

            print("Saving output files")
            contour_filename = os.path.splitext(contour_name)[0]
            # store erosion_img in output_dir
            if outputTypes == 1 or outputTypes == 3:
                sitk.WriteImage(break_img, output_dir + '/' + contour_filename + '_BREAKS.mha')
            if outputTypes == 2 or outputTypes == 3:
                sitk.WriteImage(erosion_img, output_dir + '/' + contour_filename + '_EROSIONS.mha')

            #store erosion seeds
            with open(seeds_dir + '/' + contour_filename + '_SEEDS.csv', 'w', newline='') as f:
                writer = csv.writer(f)
                for i in range(len(seeds_list)):
                    writer.writerow([i] + list(seeds_list[i]))
