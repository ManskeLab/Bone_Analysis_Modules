"""
file_converter.py

Created by:   Michael Kuczynski
Created on:   21-01-2020

Description: Converts between 3D image file formats.

Notes: 
1. File format conversion can be done using several different software libraries/packages. 
   However, when reading in images, VTK does not store the image orientation, direction, or origin. 
   This causes problems when trying to overlay images after conversion. ITK based libraries/packages 
   (like SimpleITK) are able to maintain the original image orientation, direction, and origin.
   Reading AIM images is only supported in ITK.
2. Some useful links that explain image orientation, direction, and origin:
   -https://www.slicer.org/wiki/Coordinate_systems
   -https://discourse.vtk.org/t/proposal-to-add-orientation-to-vtkimagedata-feedback-wanted/120
   -http://www.itksnap.org/pmwiki/pmwiki.php?n=Documentation.DirectionMatrices
   -https://fromosia.wordpress.com/2017/03/10/image-orientation-vtk-itk/
3. Be careful when converting to a DICOM series! This script can currently do this conversion, however,
   not all of the header information is copied over!
4. Be careful when converting from TIFF! Writing to TIFF currently works, but slice thickness is lost
   when writing TIFF images. Thus, when you try to convert back (or use a TIFF image from somewhere else),
   the image may look stretched as the slice thickness will be assumed to be 1.0

USAGE:
1. conda activate manskelab
2. python file_converter.py <inputImage.ext> <outputImage.ext>
"""

import os
import sys
import argparse

from ormir_xct.util.sitk_itk import sitk_itk, itk_sitk
from ormir_xct.util.image_to_dicom import image_to_dicom

import itk
import SimpleITK as sitk


def file_converter(input_image, output_image):
    """
    Converts an input image to the output image file type.

    Parameters
    ----------
    input_image : string
        Path to the input image

    output_image : string
        Path to the output image

    Returns
    -------
    """
    print("******************************************************")
    print(f"CONVERTING: {input_image} to {output_image}")

    # Extract directory, filename, basename, and extensions from the output image
    output_dir, output_filename = os.path.split(output_image)
    output_basename, output_extension = os.path.splitext(output_filename)

    # Check the output file format
    if output_extension.lower() == ".mha":
        output_image_filename = os.path.join(output_dir, output_basename + ".mha")
    elif output_extension.lower() == ".mhd" or output_extension.lower() == ".raw":
        output_image_filename = os.path.join(output_dir, output_basename + ".mhd")
        output_image_filename_raw = os.path.join(output_dir, output_basename + ".raw")
    elif output_extension.lower() == ".nii" or output_extension.lower() == ".nii.gz":
        output_image_filename = os.path.join(output_dir, output_basename + ".nii")
    elif output_extension.lower() == ".nrrd":
        output_image_filename = os.path.join(output_dir, output_basename + ".nrrd")
    elif output_extension.lower() == ".dcm":
        output_image_filename = os.path.join(output_dir, output_basename + ".dcm")
    elif output_extension.lower() == ".tif":
        output_image_filename = os.path.join(output_dir, output_basename + ".tif")
    elif output_extension.lower() == ".isq":
        output_image_filename = os.path.join(output_dir, output_basename + ".ISQ")
    else:
        print()
        print("Error: output file extension must be MHD, MHA, RAW, NRRD, TIFF or NII.")
        sys.exit(1)

    # Check if the input is a DICOM series directory
    if os.path.isdir(input_image):
        # Check if the directory exists
        if not os.path.exists(input_image):
            print()
            print("Error: DICOM directory does not exist!")
            sys.exit(1)
        else:
            reader = sitk.ImageSeriesReader()

            # Convert to 16-bit Int to ensure compatibility with ITK-Python functions
            # Needed for writing TIFF images
            if output_extension.lower() == ".tif":
                reader.SetOutputPixelType(sitk.sitkInt16)

            dicom_names = reader.GetGDCMSeriesFileNames(input_image)
            reader.SetFileNames(dicom_names)

            output_image = reader.Execute()
    else:
        # Extract directory, filename, basename, and extensions from the input image
        input_dir, input_filename = os.path.split(input_image)
        input_basename, input_extension = os.path.splitext(input_filename)

        # AIM image file
        if ".aim" in input_extension.lower():
            # If the input AIM contains a version number, remove it and rename the file
            if ";" in input_extension.lower():
                input_image_new = input_image.rsplit(";", 1)[0]
                os.rename(input_image, input_image_new)
                input_image = input_image_new

            # Read in the AIM using ITK
            # Only support short images for now
            image_type = itk.Image[itk.ctype("signed short"), 3]
            reader = itk.ImageFileReader[image_type].New()
            image_io = itk.ScancoImageIO.New()
            reader.SetImageIO(image_io)
            reader.SetFileName(input_image)
            reader.Update()

            output_image = itk_sitk(reader.GetOutput())

        # ISQ image file
        elif ".isq" in input_extension.lower():
            # If the input ISQ contains a version number, remove it and rename the file
            if ";" in input_extension.lower():
                input_image_new = input_image.rsplit(";", 1)[0]
                os.rename(input_image, input_image_new)
                input_image = input_image_new

            # Read in the ISQ using ITK
            image_type = itk.Image[itk.ctype("signed short"), 3]
            reader = itk.ImageFileReader[image_type].New()
            image_io = itk.ScancoImageIO.New()
            reader.SetImageIO(image_io)
            reader.SetFileName(input_image)
            reader.Update()

            output_image = itk_sitk(reader.GetOutput())

        # Other image file (e.g., MHA, NII, NRRD)
        elif os.path.isfile(input_image) and (
            ".nii" or ".mha" or ".mhd" or ".raw" or ".nrrd" in input_extension.lower()
        ):
            # Convert to 16-bit Int to ensure compatibility with ITK-Python functions for writing TIFFs
            if output_extension.lower() == ".tif":
                output_image = sitk.ReadImage(input_image, sitk.sitkInt16)
            else:
                # Use unkown pixel type (may cause errors if the pixel type is not supported by ITK-Python)
                output_image = sitk.ReadImage(input_image, sitk.sitkInt16)

        else:
            print()
            print("Error: Input image is an incorrect type!")
            sys.exit(1)

    # Setup the correct writer based on the output image extension
    if output_extension.lower() == ".mha":
        print("WRITING IMAGE: " + str(output_image_filename))
        sitk.WriteImage(output_image, str(output_image_filename))

    elif output_extension.lower() == ".mhd" or output_extension.lower() == ".raw":
        print("WRITING IMAGE: " + str(output_image_filename))
        sitk.WriteImage(output_image, str(output_image_filename))

    elif output_extension.lower() == ".nii" or output_extension.lower() == ".nii.gz":
        print("WRITING IMAGE: " + str(output_image_filename))
        sitk.WriteImage(output_image, str(output_image_filename))

    elif output_extension.lower() == ".nrrd":
        print("WRITING IMAGE: " + str(output_image_filename))
        sitk.WriteImage(output_image, str(output_image_filename))

    elif output_extension.lower() == ".tif":
        # SimpleITK TIFFImageIO is a bit buggy (sometimes writes out binary images...)
        # Use ITK instead. Need to force the use of a supported ITK-Python pixel type. Signed short is used as default
        image_type = itk.Image[itk.SS, 3]

        # Need to convert to ITK image
        # Should be read in as signed short by default so we shouldn't need to cast
        image = sitk_itk(output_image)

        # Image values need to rescaled
        rescaler = itk.RescaleIntensityImageFilter[image_type, image_type].New()
        rescaler.SetInput(image)
        rescaler.SetOutputMinimum(0)
        pixelTypeMaximum = itk.NumericTraits[itk.SS].max()
        rescaler.SetOutputMaximum(pixelTypeMaximum)

        print("WRITING IMAGE: " + str(output_image_filename))
        writer = itk.ImageFileWriter[image_type].New()
        writer.SetFileName(str(output_image_filename))
        writer.SetInput(rescaler.GetOutput())
        writer.Update()

    elif output_extension.lower() == ".dcm":
        print("WRITING IMAGE: " + str(output_image_filename))
        image_to_dicom(output_image, output_dir)

    elif output_extension.lower() == ".isq":
        outputImageISQ = sitk_itk(output_image)
        print("WRITING IMAGE: " + str(output_image_filename))

        image_type = itk.Image[itk.ctype("signed short"), 3]
        writer = itk.ImageFileWriter[image_type].New()
        image_io = itk.ScancoImageIO.New()
        writer.SetImageIO(image_io)
        writer.SetInput(outputImageISQ)
        writer.SetFileName(output_image_filename)
        writer.Update()

        # Set header information
        image_io.SetEnergy(68)
        image_io.SetIntensity(1.47)
        image_io.SetReconstructionAlg(3)
        image_io.SetSite(4)
        image_io.SetScannerID(3401)
        image_io.SetPatientIndex(2567)
        image_io.SetMeasurementIndex(12778)
        image_io.SetSampleTime(100)
        image_io.SetScannerType(9)
        image_io.SetMuScaling(8192)
        image_io.SetNumberOfProjections(900)
        image_io.SetSliceIncrement(0.0609)
        image_io.SetSliceThickness(0.0609)
        # image_io.SetScanDistance(139852)
        # image_io.SetReferenceLine(109737)
        # image_io.SetNumberOfSamples(2304)
        # image_io.SetStartPosition()

        writer.Write()

    print("DONE")
    print("******************************************************")
    print()


if __name__ == "__main__":
    # Parse input arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "input_image", type=str, help="The input image (path + filename)"
    )
    parser.add_argument(
        "output_image", type=str, help="The output image (path + filename)"
    )
    args = parser.parse_args()

    input_image = args.input_image
    output_image = args.output_image

    file_converter(input_image, output_image)
