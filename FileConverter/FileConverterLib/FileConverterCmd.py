import itk
import SimpleITK as sitk
import sitk_itk

class FileConverterCmd():

  def __init__(self) -> None:
    pass

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

# execute this script on command line
if __name__ == "__main__":
  import argparse
  import os

  # Read the input arguments
  parser = argparse.ArgumentParser()
  parser.add_argument('mode', help='input format -> \'d\' for directory, \'f\' for files')
  parser.add_argument('filepath', help='name of folder/files to be converted (supports multiple arguments)', nargs='+')
  parser.add_argument('-o', '--outputPath', help='destination folder for converted files, default is location of input file/folder', default=None, metavar='')
  args = parser.parse_args()

  mode = args.mode
  filepath = args.filepath
  outputPath = args.outputPath

  if mode == "'d'" or mode == 'd':
    filenames = []
    exts = ['.aim', '.AIM', '.isq', '.ISQ']
    for file in os.listdir(filepath[0]):
      print(file)
      if os.path.splitext(file)[1] in exts:
        filenames.append(filepath[0] + '/' + file)
  elif mode == "'f'" or mode == 'f':
    filenames = filepath

  converter = FileConverterCmd()
  if outputPath:
    converter.convertMultiple(filenames, outputPath)
  else:
    converter.convertMultiple(filenames)