"""
sitk_vtk.py

Created by:   Michael Kuczynski
Created on:   21-01-2020

Description: Converts between SimpleITK and VTK image types
"""

import vtk
from vtk.util.numpy_support import vtk_to_numpy

import SimpleITK as sitk


def sitk_to_vtk(sitk_image):
    """
    Convert a SimpleITK image to a VTK image.

    Parameters
    ----------
    sitk_image : SimpleITK.Image

    Returns
    -------
    vtk_image : VTK.Image
    """
    size = list(sitk_image.GetSize())
    origin = list(sitk_image.GetOrigin())
    spacing = list(sitk_image.GetSpacing())
    ncomp = sitk_image.GetNumberOfComponentsPerPixel()

    # Cconvert the SimpleITK image to a numpy array
    raw_data = sitk.GetArrayFromImage(sitk_image)

    # Send the numpy array to VTK with a vtkImageImport object
    data_importer = vtk.vtkImageImport()
    data_importer.SetImportVoidPointer(raw_data)
    data_importer.SetNumberOfScalarComponents(ncomp)

    # VTK expects 3-dimensional parameters
    if len(size) == 2:
        size.append(1)

    if len(origin) == 2:
        origin.append(0.0)

    if len(spacing) == 2:
        spacing.append(spacing[0])

    # Set the new VTK image's parameters
    # For some reason we need to set both the data and whole extent...?
    # Output image orientation will be lost when converting to a VTK image
    data_importer.SetDataExtent(0, size[0] - 1, 0, size[1] - 1, 0, size[2] - 1)
    data_importer.SetWholeExtent(0, size[0] - 1, 0, size[1] - 1, 0, size[2] - 1)
    data_importer.SetDataOrigin(origin)
    data_importer.SetDataSpacing(spacing)
    data_importer.Update()

    vtk_image = data_importer.GetOutput()

    # Cast the image data to VTK_SHORT so we can read it with UCT_3D
    caster = vtk.vtkImageCast()
    caster.SetInputData(vtk_image)
    caster.SetOutputScalarType(vtk.VTK_CHAR)
    caster.ReleaseDataFlagOff()
    caster.Update()

    return caster.GetOutput()


def vtk_to_sitk(vtk_image):
    """
    Convert a VTK image to a SimpleITK image.

    Parameters
    ----------
    vtk_image : VTK.Image

    Returns
    -------
    sitk_image : SimpleITK.Image
    """
    vtk_data = vtk_image.GetPointData().GetScalars()
    numpy_data = vtk_to_numpy(vtk_data)
    dims = vtk_image.GetDimensions()
    numpy_data = numpy_data.reshape(dims[2], dims[1], dims[0])
    numpy_data = numpy_data.transpose(2, 1, 0)

    sitk_image = sitk.GetImageFromArray(numpy_data)

    return sitk_image
