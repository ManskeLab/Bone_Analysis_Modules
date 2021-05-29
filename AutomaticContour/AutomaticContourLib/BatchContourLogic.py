#-----------------------------------------------------
# BatchContourLogic.py
#
# Created by:  Mingjie Zhao
# Created on:  14-05-2021
#
# Description: This script runs contour algorithm on a batch of greyscale scans.
#              It only suuports MHA and Nifti. All the scans need to be in one folder.
#              All the rough masks, if any provided, need to be in one folder.
#
#-----------------------------------------------------
# Usage:       python BatchContourLogic.py inputDirectory outputDirectory 
#                                          lowerThreshold upperThreshold
#                                          boneNum [roughMaskDirectory]
#
# Param:       inputDirectory: The input image folder directory
#              outputImage: The output image folder directory
#              lowerThreshold
#              upperThreshold
#              boneNum: Number of separate bone structures
#              roughMask: The directory of the optional rough mask folder
#
#-----------------------------------------------------
import os
import sys
import argparse
import SimpleITK as sitk
from ContourLogic import ContourLogic

# Valid file extensions
fileExtensions = ['mha','nii']
roughMaskPostfix = "_separated"
maskPostfix = "_MASK"

# Parse input arguments
parser = argparse.ArgumentParser()
parser.add_argument('inputDirectory', type=str, help='The input image directory' )
parser.add_argument('outputDirectory', type=str, help='The output image directory')
parser.add_argument('lowerThreshold', type=int)
parser.add_argument('upperThreshold', type=int)
parser.add_argument('boneNum', type=int, default=1, help='Number of separate bone structures')
parser.add_argument('roughMaskDirectory', type=str, nargs='?', default="", 
                    help='The file path of optional rough mask that helps separate bones')
args = parser.parse_args()

input_dir = args.inputDirectory
output_dir = args.outputDirectory
lower = args.lowerThreshold
upper = args.upperThreshold
boneNum = args.boneNum
roughMask_dir = args.roughMaskDirectory

# Check if we have valid directories
if not os.path.isdir(input_dir):
    print(f'Error: Invalid input image directory {input_dir}')
    sys.exit(1)
if not os.path.isdir(output_dir):
    print(f'Error: Invalid output image directory {input_dir}')
    sys.exit(1)
if (roughMask_dir != "" and (not os.path.isdir(roughMask_dir))):
    print(f'Error: Invalid rough mask directory {input_dir}')
    sys.exit(1)

# create contour object
contour = ContourLogic()

# Loop through all files in the directory
for file in os.listdir(input_dir):
    # Get the next file
    input_filename = os.fsdecode(file)
    input_file = os.path.join(input_dir, input_filename)
    baseName, extension = os.path.splitext(input_filename)
    extension = extension.lower()

    # Skip files that are not the type we want to convert, 
    #  or files that are not greyscale scans
    if ((extension not in fileExtensions) or 
        (maskPostfix in baseName) or
        (roughMaskPostfix in baseName)):
        continue
    
    output_file = os.path.join(output_dir, baseName+maskPostfix+"."+extension)

    # read images
    print("Reading image in {}".format(input_file))
    img = sitk.ReadImage(input_file)
    roughMask = None
    if (roughMask_dir != ""):
        roughMask_file = os.path.join(roughMask_dir, baseName+roughMaskPostfix+"."+extension)
        print("Reading rough mask in {}".format(roughMask_dir))
        roughMask = sitk.ReadImage(roughMask_dir)

    # set contour algorithm parameters
    contour.setImage(img)
    contour.setRoughMask(roughMask)
    contour.setThreshold(lower, upper)
    contour.setBoneNum(boneNum)

    # run contour algorithm
    print("Running contour script")
    while (contour.execute()):
        pass
    contour_img = contour.getOutput()

    # store contour
    print("Storing image in {}".format(output_file))
    sitk.WriteImage(contour_img, output_file)
