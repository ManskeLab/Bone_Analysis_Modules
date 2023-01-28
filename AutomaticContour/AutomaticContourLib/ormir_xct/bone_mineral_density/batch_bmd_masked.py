import os
import argparse
import numpy as np
import SimpleITK as sitk

from bmd_masked import bmd_masked

# Parse input arguments
parser = argparse.ArgumentParser()
parser.add_argument("input_dir", type=str, help="The input image directory")
parser.add_argument("output_csv", type=str, default="", help="The output CSV file name")
args = parser.parse_args()

input_dir = args.input_dir
output_csv = args.output_csv

bmd_param_stack = np.array(
    [["Filename", "Mean BMD (mgHA/ccm)", "Std BMD (mgHA/ccm)"]], dtype=object
)

# Loop through all files in the directory
for folder in os.listdir(input_dir):
    # Get the next folder
    next_folder = os.path.join(input_dir, folder)

    if os.path.isdir(next_folder):
        print("Calculating BMD for: " + str(next_folder))

        for file in os.listdir(next_folder):
            basename, extension = os.path.splitext(file)
            extension = extension.lower()

            if extension == ".nii" and "_MASKED_" in basename:
                image = sitk.ReadImage(
                    os.path.join(next_folder, file), sitk.sitkFloat32
                )
                mean, std = bmd_masked(
                    image, "hu", -1000, 8192, 0.2409, 1603.51904, -391.209015
                )

                bmd_parameters = np.array([[file, mean, std]], dtype=object)
            else:
                continue

            bmd_param_stack = np.vstack([bmd_param_stack, bmd_parameters])

    else:
        continue

output_string = bmd_param_stack.astype(str)
np.savetxt(output_csv, output_string.astype(str), delimiter=",", fmt="%s")
