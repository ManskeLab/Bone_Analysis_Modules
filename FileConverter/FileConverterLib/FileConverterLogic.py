#-----------------------------------------------------
# FileConverterLogic.py
#
# Created by:  Ryan Yan
# Created on:  17-01-2020
#
# Description: This module converts a .aim or .isq file to a slicer volume or .mha file
#              Uses itk to read aim files, specifically the ioscanco package
#              Convert to volume works for 1 file at a time, only used in 3D Slicer
#              Convert to file can convert multiple files and is uable with command line
#
#-----------------------------------------------------
# Usage:       This module is plugged into 3D Slicer, but can run on its own. 
#              When running on its own:
#              python FileConverterLogic.py mode filepath [filepath ...] [outputPath]
#
# Param:       mode: input format -> 'd' for directory, 'f' for files
#              filepath: name of folder/files to be converted (supports multiple arguments)
#              outputPath: destination folder for converted files, default is location of input file/folder
#              
#
#-----------------------------------------------------

from __main__ import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import SimpleITK as sitk
import sitkUtils
import itk
from . import sitk_itk


class FileConverterLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self):
    pass

  def convert(self, fileName, outputVolumeNode, inFormat):
    '''
    Convert a single file to Slicer volume

    Args:
      fileName (str): the full path of the file to be converted
      outputVolumeNode (vtkMRMLScalarVolumeNode): selected volume node
      inFormat (str): '.aim' or '.isq'

    Returns:
      dict: metadata of image
    '''
    #Conversion scripts from https://github.com/ManskeLab/Manskelab/blob/master/scripts/fileConverter.py

    print("Converting", fileName, "to Volume")

    if inFormat == '.aim':
      #read image from file
      ImageType = itk.Image[itk.ctype('signed short'), 3]
      reader = itk.ImageFileReader[ImageType].New()
      imageio = itk.ScancoImageIO.New()
      reader.SetImageIO(imageio)
      reader.SetFileName(fileName)
      reader.Update()

      outputImage = sitk_itk.itk2sitk(reader.GetOutput())

    elif inFormat == '.isq':
      #read image from file
      ImageType = itk.Image[itk.ctype('signed short'), 3]
      reader = itk.ImageFileReader[ImageType].New()
      imageio = itk.ScancoImageIO.New()
      reader.SetImageIO(imageio)
      reader.SetFileName(fileName)
      reader.Update()

      #convert to sitk image
      outputImage = sitk_itk.itk2sitk(reader.GetOutput())

    #get metadata
    metadata = dict(reader.GetOutput()) 

    #set intensity metadata
    outputImage.SetMetaData('intensityUnit', 'HU')

    #push to slicer and display
    sitkUtils.PushVolumeToSlicer(outputImage, targetNode=outputVolumeNode)
    slicer.util.setSliceViewerLayers(background=outputVolumeNode, fit=True)
    return metadata

  def convertMultiple(self, filenames, outputFolder=None):
    '''
    Convert multiple files to .mha

    Args:
      filenames (list): list of filenames
      outputFolder (str): default=None, folder to write files to

    Returns:
      None

    '''

    import os

    #convert each file
    for file in filenames:
      print("Converting " + file + " to .mha file")

      #split path and extension
      filepath = os.path.splitext(file)[0]
      name = os.path.split(filepath)[1]

      #read image with itk
      ImageType = itk.Image[itk.ctype('signed short'), 3]
      reader = itk.ImageFileReader[ImageType].New()
      imageio = itk.ScancoImageIO.New()
      reader.SetImageIO(imageio)
      reader.SetFileName(file)
      reader.Update()

      #convert to sitk image
      outputImage = sitk_itk.itk2sitk(reader.GetOutput())

      #add metadata tag for intensity unit
      outputImage.SetMetaData('IntensityUnit', 'HU')
      if outputFolder:
        sitk.WriteImage(outputImage, outputFolder + '/' + name + '.mha')
      else:
        sitk.WriteImage(outputImage, filepath + '.mha')


  def getThreshold(self, mu_water, mu_scaling):
    lower = self.roundNearest(1000 * (3000 / mu_scaling / mu_water - 1), 10)
    upper = self.roundNearest(1000 * (10000 / mu_scaling / mu_water - 1), 100)
    return (lower, upper)

  #rounding function for thesholds
  def roundNearest(self, num, roundTo):
    return int(num - num % roundTo + round(num % roundTo / roundTo) * roundTo)


  