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
#              python VoidVolume.py inputImages inputMasks inputSeeds outputFolder
#                                   [--lowerThreshold] [--upperThreshold] [--sigma]
#                                   [--minimumRadius] [--dilateErodeDistance]
#              Images, masks, and seeds, must be in separate folders
#              Mask and seed filenames must contain the full name of their corresponding image
#
# Param:       inputImage: The file path for the directory containing grayscale scans
#              inputMasks: The file path for the directory containing mask masks
#              inputSeeds: The file path for the directory containing seed point files
#              outputFolder: The output folder path
#              lowerThreshold, default=530
#              upperThreshold, default=15000
#              sigma: Standard deviation for the Gaussian smoothing filter, default=1
#              minimumRadius: Minimum erosion radius in voxels, default=3
#              dilateErodeDistance: Morphological kernel radius in voxels, default=5
#
#-----------------------------------------------------
import SimpleITK as sitk, os
import VoidVolumeLogic

class VoidVolumeLogicCmd:
    def __init__(self):
        pass


# execute this script on command line
if __name__ == "__main__":
    import argparse

    # Read the input arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('inputImages', help='The file path for the directory containing grayscale scans')
    parser.add_argument('inputMasks', help='The file path for the directory containing mask masks')
    parser.add_argument('inputSeeds', help='The file path for the directory containing seed point files')
    parser.add_argument('outputFolder', help='The output folder path')
    parser.add_argument('-im', '--inputMask', help='The input mask file path, default=[inputImage]_MASK', default="_MASK.mha", metavar='')
    parser.add_argument('-oi', '--outputImage', help='The output image file path, default=[inputImage]_ER', default="_ER.nrrd", metavar='')
    parser.add_argument('-sd', '--seeds', help='The seed points csv file path, default=[inputImage]_SEEDS', default="_SEEDS.csv", metavar='')
    parser.add_argument('-lt', '--lowerThreshold', help='default=530', type=int, default=530, metavar='')
    parser.add_argument('-ut', '--upperThreshold', help='default=15000', type=int, default=15000, metavar='')
    parser.add_argument('-sg', '--sigma', type=float, help='Standard deviation for the Gaussian smoothing filter, default=1', default=1, metavar='')
    parser.add_argument('-mr', '--minimumRadius', type=int, default=3, 
                        help='Minimum erosion radius in voxels, default=3', metavar='')
    parser.add_argument('-ded', '--dilateErodeDistance', type=int, default=4,
                        help='Morphological kernel radius in voxels, default=4', metavar='')
    args = parser.parse_args()

    input_dir = args.inputImages
    mask_dir = args.inputMasks
    seeds_dir = args.inputSeeds
    output_dir = args.outputFolder
    lower = args.lowerThreshold
    upper = args.upperThreshold
    sigma = args.sigma
    minimumRadius = args.minimumRadius
    dilateErodeDistance = args.dilateErodeDistance

    mask_list = os.listdir(mask_dir)
    seeds_list = os.listdir(seeds_dir)
    for file in os.listdir(input_dir):
        # read image
        try:
            img = sitk.ReadImage(input_dir + '/' + file)
        except:
            print('Could not read in ' + file)
            continue

        filename = os.path.splitext(file)[0]
        
        #read mask(s)
        masks = []
        for mask_name in mask_list:
            if filename in mask_name:
                masks.append(mask_name)
        if len(masks) == 0:
            print("No masks found for " + file)
            continue

        #read seeds
        seeds = []
        HEADER = 3
        lineCount = 0
        for seeds_name in seeds_list:
            if file in seeds_name:
                with open(seeds_dir + file + '_SEEDS') as fcsv:
                    for line in fcsv:
                        # line = 'id,x,y,z,ow,ox,oy,oz,vis,sel,lock,label,desc,associatedNodeID'
                        if lineCount >= HEADER:
                            seed = line.split(',')
                            x = int(float(seed[1]))
                            y = int(float(seed[2]))
                            z = int(float(seed[3]))
                            seeds.append((x,y,z))
                        lineCount += 1
        if len(seeds) == 0:
            print("No seeds found or 0 seeds set for " + file)

        for mask_name in masks:
            mask = sitk.Cast(sitk.ReadImage(mask_dir + '/' + mask_name), sitk.sitkUInt8)
            

            # create erosion logic object
            erosion = VoidVolumeLogic.VoidVolumeLogic(img, mask, lower, upper, sigma, seeds,
                                    minimumRadius, dilateErodeDistance)

            # identify erosions
            print("Running erosion detection script")
            step = 1
            while (erosion.execute(step)):
                step += 1
            erosion_img = erosion.getOutput()

            print("Saving output files")
            mask_filename = os.path.splitext(mask_name)[0]
            sitk.WriteImage(erosion_img, output_dir + '/' + mask_filename + '_ER.mha')
