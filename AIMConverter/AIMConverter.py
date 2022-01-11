
import os
import unittest
from __main__ import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
from Resources.sitk_itk import itk2sitk
import SimpleITK as sitk
import sitkUtils
import itk

#
# AIMConverter
#

class AIMConverter(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "AIM File Converter" # TODO make this more human readable by adding spaces
    self.parent.categories = ["Bone"]
    self.parent.dependencies = []
    self.parent.contributors = ["Ryan Yan, Michael Kuczynski"] # replace with "Firstname Lastname (Organization)"
    self.parent.helpText = """
    Updated 2022-01-07. Converts an AIM file to a viewable slicer volume node. 
    IMPORTANT: Requires ITK package installed in Slicer. 
    Follow instructions at https://github.com/ManskeLab/3DSlicer_Erosion_Analysis/wiki/AIM-File-Converter-Module to install.
    """
    self.parent.acknowledgementText = """
    Placeholder Text
""" # replace with organization, grant and thanks.

#
# AIMConverterWidget
#

class AIMConverterWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)
    # Instantiate and connect widgets ...

    #
    # Parameters Area
    #
    parametersCollapsibleButton = ctk.ctkCollapsibleButton()
    parametersCollapsibleButton.text = "Parameters"
    self.layout.addWidget(parametersCollapsibleButton)

    # Layout within the dummy collapsible button
    parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)

    #
    # File Selector
    #
    self.inputFileSelect = qt.QFileDialog()
    self.inputFileSelect.setFileMode(qt.QFileDialog.ExistingFile)
    self.inputFileSelect.setNameFilter("*.AIM, *.aim")

    self.fileButton = qt.QPushButton("Browse")

    self.fileTextList = qt.QTextEdit("None Selected")
    self.fileTextList.setReadOnly(True)
    self.fileTextList.setFixedHeight(45)

    self.fileSelect = qt.QGridLayout()
    self.fileSelect.addWidget(self.fileButton)
    self.fileSelect.addWidget(self.fileTextList)
    parametersFormLayout.addRow("Select AIM File: ", self.fileSelect)

    #
    # Output Format Selector
    # not implemented yet, not sure if neccesary
    self.mhaButton = qt.QRadioButton(".mha")
    self.mhaButton.setChecked(True)

    self.nrrdButton = qt.QRadioButton(".nrrd")
    self.nrrdButton.setChecked(False)

    self.formatSelect = qt.QGridLayout()
    self.formatSelect.addWidget(self.mhaButton, 0, 0)
    self.formatSelect.addWidget(self.nrrdButton, 0, 1)

    # ct type button frame
    self.formatSelectFrame = qt.QFrame()
    self.formatSelectFrame.setLayout(self.formatSelect)
    #parametersFormLayout.addRow("Output File Type: ", self.formatSelectFrame)

    # Preprocessed output selector
    self.outputVolumeSelector = slicer.qMRMLNodeComboBox()
    self.outputVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.outputVolumeSelector.selectNodeUponCreation = True
    self.outputVolumeSelector.addEnabled = True
    self.outputVolumeSelector.renameEnabled = True
    self.outputVolumeSelector.removeEnabled = True
    self.outputVolumeSelector.noneEnabled = False
    self.outputVolumeSelector.showHidden = False
    self.outputVolumeSelector.showChildNodeTypes = False
    self.outputVolumeSelector.setMRMLScene(slicer.mrmlScene)
    self.outputVolumeSelector.setToolTip( "Select the node to converted image in" )
    self.outputVolumeSelector.baseName = "_CONVERTED"
    parametersFormLayout.addRow("Output Volume: ", self.outputVolumeSelector)

    #
    # Apply Button
    #
    executeGridLayout = qt.QGridLayout()
    executeGridLayout.setRowMinimumHeight(0,20)
    executeGridLayout.setRowMinimumHeight(1,20)

    self.applyButton = qt.QPushButton("Convert")
    self.applyButton.toolTip = "Convert AIM File."
    self.applyButton.enabled = False
    executeGridLayout.addWidget(self.applyButton, 1, 0)

    parametersFormLayout.addRow(executeGridLayout)

    #
    # Output Calibrations
    # Update to output recommended thresholds once we figure out calculations
    self.calibrationOutput = qt.QTextEdit()
    self.calibrationOutput.setReadOnly(True)
    self.calibrationOutput.setFixedHeight(90)
    parametersFormLayout.addRow("Calibrations: ", self.calibrationOutput)

    # connections
    self.fileButton.clicked.connect(self.onFileSelect)
    self.applyButton.connect('clicked(bool)', self.onApplyButton)
    self.outputVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onNodeSelect)

    # Add vertical spacer
    self.layout.addStretch(1)

  def cleanup(self):
    pass
  
  #Open file explorer and update file
  def onFileSelect(self):
    if self.inputFileSelect.exec_():
      self.filename = self.inputFileSelect.selectedFiles()[0]
      self.fileTextList.setText(self.filename)
      self.outputVolumeSelector.baseName = (self.filename[self.filename.rfind('/') + 1:self.filename.rfind('.')] +"_CONVERTED")

  def onNodeSelect(self):
    self.applyButton.enabled = (self.outputVolumeSelector.currentNode())
  
  #
  #Conversion Button Pressed
  #
  def onApplyButton(self):
    logic = AIMConverterLogic()
    print("Run the algorithm")
    if self.mhaButton.isChecked():
      outFormat = ".mha"
    elif self.nrrdButton.isChecked():
      outFormat = ".nrrd"
    else:
      outFormat = ".mha"
    print(self.outputVolumeSelector.currentNodeID)
    meta = logic.convert(self.filename, self.outputVolumeSelector.currentNode())

    #find recommended thresholds in HU (3000/10000 in native units)
    mu_water = meta["MuWater"]
    mu_scaling = meta["MuScaling"]
    thresholds = logic.getThreshold(mu_water, mu_scaling)

    #formula: HU = 1000 * (native / mu_scaling - mu_water) / mu_water
    line1 = "Recommended lower threshold: " + str(thresholds[0])
    line2 = "Recommended upper threshold: " + str(thresholds[1])
    self.calibrationOutput.setText(line1 + "\n" + line2)


#
# AIMConverterLogic
#

class AIMConverterLogic(ScriptedLoadableModuleLogic):
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

  def convert(self, fileName, outputVolumeNode):
    #Conversion script from https://github.com/ManskeLab/Manskelab/blob/master/scripts/fileConverter.py

    print("Converting", fileName, "to Volume")
    ImageType = itk.Image[itk.ctype('signed short'), 3]
    reader = itk.ImageFileReader[ImageType].New()
    imageio = itk.ScancoImageIO.New()
    reader.SetImageIO(imageio)
    reader.SetFileName(fileName)
    reader.Update()

    outputImage = itk2sitk(reader.GetOutput())

    #get metadata
    metadata = dict(reader.GetOutput()) 

    #push to slicer and display
    sitkUtils.PushVolumeToSlicer(outputImage, targetNode=outputVolumeNode)
    slicer.util.setSliceViewerLayers(background=outputVolumeNode, fit=True)
    return metadata

  def getThreshold(self, mu_water, mu_scaling):
    lower = self.roundNearest(1000 * (3000 / mu_scaling / mu_water - 1), 10)
    upper = self.roundNearest(1000 * (10000 / mu_scaling / mu_water - 1), 100)
    return (lower, upper)

  #rounding function for thesholds
  def roundNearest(self, num, roundTo):
    return int(num - num % roundTo + round(num % roundTo / roundTo) * roundTo)

class AIMConverterTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_AIMConverter1()

  def test_AIMConverter1(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests sould exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

    self.delayDisplay("Starting the test")
    #
    # first, get some data
    #
    import urllib
    downloads = (
        ('http://slicer.kitware.com/midas3/download?items=5767', 'FA.nrrd', slicer.util.loadVolume),
        )

    for url,name,loader in downloads:
      filePath = slicer.app.temporaryPath + '/' + name
      if not os.path.exists(filePath) or os.stat(filePath).st_size == 0:
        print('Requesting download %s from %s...\n' % (name, url))
        urllib.urlretrieve(url, filePath)
      if loader:
        print('Loading %s...\n' % (name,))
        loader(filePath)
    self.delayDisplay('Finished with download and loading\n')

    volumeNode = slicer.util.getNode(pattern="FA")
    logic = AIMConverterLogic()
    self.assertTrue( logic.hasImageData(volumeNode) )
    self.delayDisplay('Test passed!')