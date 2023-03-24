"""
Created by: Michael Kuczynski
Created on: June 18th, 2022
"""

import os
import sys
import itk
import SimpleITK as sitk

from ormir_xct.util.sitk_itk import itk_sitk

<<<<<<< HEAD
file_extensions = [".nii", ".mha", ".nrrd", ".aim", ".isq"]

=======
file_extensions = ['.nii', '.mha', '.nrrd', '.aim', '.isq']
>>>>>>> c4df9f22a7ffe233b63348f8a9cec4293a508ee6

def file_reader(input_file_path):
    """
    Read the input file using the correct reader. Scanco files can only be read
    using ITK Scanco image IO but MHA/NII images can be read using SimpleITK.

    Parameters
    ----------
    input_file_path : string

    Returns
    -------
    image : SimpleITK.Image
    """
    # Get the file extension and check if we can read it
    input_filename = os.path.split(input_file_path)[1]
    input_extension = os.path.splitext(input_filename)[1]

    input_extension = input_extension.lower()
    image = None

    if input_extension in file_extensions:
        if input_extension == ".aim" or input_extension == ".isq":
            # If the input AIM contains a version number, remove it and rename the file
            if ";" in input_extension:
                scanco_filename = input_file_path.rsplit(";", 1)[0]
                os.rename(input_file_path, scanco_filename)
                input_file_path = scanco_filename

            # For now, only read signed short Scanco images
            image_type = itk.Image[itk.ctype("signed short"), 3]
            reader = itk.ImageFileReader[image_type].New()
            image_io = itk.ScancoImageIO.New()
            reader.SetImageIO(image_io)
            reader.SetFileName(input_file_path)
            reader.Update()

            image = reader.GetOutput()
            image = itk_sitk(image)
        else:
            image = sitk.ReadImage(input_file_path, sitk.sitkFloat32)
    else:
        print("ERROR: File extension " + str(input_extension) + " not supported.")
        sys.exit(0)

    return image
