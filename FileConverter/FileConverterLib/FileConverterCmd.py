#-----------------------------------------------------
# FileConverterLogic.py
#
# Created by:  Ryan Yan
# Created on:  17-01-2020
#
# Description: This module implements FileConverterLogic for command line
#
#-----------------------------------------------------
# Usage:       Type the following command:
#              python FileConverterLogic.py mode filepath [filepath ...] [outformat] [outputPath]
#
# Param:       mode: input format -> 'd' for directory, 'f' for files
#              filepath: name of folder/files to be converted (supports multiple arguments)
#              outputPath: destination folder for converted files, default is location of input file/folder
#              
#
#-----------------------------------------------------

import itk
import SimpleITK as sitk
import sitk_itk

class FileConverterLogic():

  def convertMultiple(self, filenames:list, outFormat:str, outputFolder:str=None, noProgress=False) -> None:
    import itk
    import sitk_itk
    '''
    Convert multiple files to .mha

    Args:
      filenames (list): list of filenames
      outputFolder (str): default=None, folder to write files to

    Returns:
      None
    '''
    import os
    progress = 0

    #convert each file
    for file in filenames:
      print("Converting " + file + " to " + outFormat +  " file")

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

      #write image
      if outputFolder:
        sitk.WriteImage(outputImage, outputFolder + '/' + name + outFormat)
      else:
        sitk.WriteImage(outputImage, filepath + outFormat)
      
      #update progress
      progress += 100 / len(filenames)
      if not noProgress:
        self.progressCallBack(int(progress))

class FileConverterCmd():

  def __init__(self) -> None:
    pass

# execute this script on command line
if __name__ == "__main__":
  import argparse
  import os

  # Read the input arguments
  parser = argparse.ArgumentParser()
  parser.add_argument('mode', help='input format -> \'d\' for directory, \'f\' for files')
  parser.add_argument('filepath', help='name of folder/files to be converted (supports multiple arguments)', nargs='+')
  parser.add_argument('-of', '--outputFormat', help='file format to convert to (.mha or .nii)', default='.mha', metavar='')
  parser.add_argument('-op', '--outputPath', help='destination folder for converted files, default is location of input file/folder', default=None, metavar='')
  args = parser.parse_args()

  mode = args.mode
  filepath = args.filepath
  outputFormat = args.outputFormat
  outputPath = args.outputPath

  #check conversion mode
  if 'd' in mode.lower():
    #get list of files from directory
    filenames = []
    exts = ['.aim', '.AIM', '.isq', '.ISQ']
    for file in os.listdir(filepath[0]):
      print(file)
      if os.path.splitext(file)[1] in exts:
        filenames.append(filepath[0] + '/' + file)
  elif 'f' in mode.lower():
    #get filelist
    filenames = filepath
  
  #check output format
  accepted = ['.mha', '.nii']
  if not outputFormat in accepted:
    outputFormat = '.mha'

  converter = FileConverterLogic()
  if outputPath:
    converter.convertMultiple(filenames, outputFormat, outputFolder=outputPath, noProgress=True)
  else:
    converter.convertMultiple(filenames, outputFormat, noProgress=True)