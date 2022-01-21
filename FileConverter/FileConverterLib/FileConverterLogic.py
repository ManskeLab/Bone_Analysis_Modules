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

  def hasImageData(self,volumeNode):
    """This is a dummy logic method that
    returns true if the passed in volume
    node has valid image data
    """
    if not volumeNode:
      print('no volume node')
      return False
    if volumeNode.GetImageData() == None:
      print('no image data')
      return False
    return True

  def takeScreenshot(self,name,description,type=-1):
    # show the message even if not taking a screen shot
    self.delayDisplay(description)

    if self.enableScreenshots == 0:
      return

    lm = slicer.app.layoutManager()
    # switch on the type to get the requested window
    widget = 0
    if type == slicer.qMRMLScreenShotDialog.FullLayout:
      # full layout
      widget = lm.viewport()
    elif type == slicer.qMRMLScreenShotDialog.ThreeD:
      # just the 3D window
      widget = lm.threeDWidget(0).threeDView()
    elif type == slicer.qMRMLScreenShotDialog.Red:
      # red slice window
      widget = lm.sliceWidget("Red")
    elif type == slicer.qMRMLScreenShotDialog.Yellow:
      # yellow slice window
      widget = lm.sliceWidget("Yellow")
    elif type == slicer.qMRMLScreenShotDialog.Green:
      # green slice window
      widget = lm.sliceWidget("Green")
    else:
      # default to using the full window
      widget = slicer.util.mainWindow()
      # reset the type so that the node is set correctly
      type = slicer.qMRMLScreenShotDialog.FullLayout

    # grab and convert to vtk image data
    qpixMap = qt.QPixmap().grabWidget(widget)
    qimage = qpixMap.toImage()
    imageData = vtk.vtkImageData()
    slicer.qMRMLUtils().qImageToVtkImageData(qimage,imageData)

    annotationLogic = slicer.modules.annotations.logic()
    annotationLogic.CreateSnapShot(name, description, type, self.screenshotScaleFactor, imageData)

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