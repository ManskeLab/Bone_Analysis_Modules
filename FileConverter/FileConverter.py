from FileConverterLib.FileConverterLogic import FileConverterLogic
import os
from sre_constants import SUCCESS
from __main__ import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import SimpleITK as sitk
import sitkUtils

#
# FileConverter
#

class FileConverter(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "File Converter"
    self.parent.categories = ["Bone"]
    self.parent.dependencies = []
    self.parent.contributors = ["Ryan Yan"] # replace with "Firstname Lastname (Organization)"
    self.parent.helpText = """
    Updated 2022-01-07. Converts an AIM or ISQ file to a viewable slicer volume node. 
    IMPORTANT: Requires ITK package installed in Slicer. 
    Follow instructions at https://github.com/ManskeLab/3DSlicer_Erosion_Analysis/wiki/AIM-File-Converter-Module to install.
    """
    self.parent.acknowledgementText = """
    Placeholder Text
""" # replace with organization, grant and thanks.

#
# FileConverterWidget
#

class FileConverterWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)
    # Instantiate and connect widgets ...

    #
    # Convert to volume option
    #
    self.toVolumeCollapsible = ctk.ctkCollapsibleButton()
    self.toVolumeCollapsible.text = "Convert to Volume"
    self.layout.addWidget(self.toVolumeCollapsible)

    # Layout within the dummy collapsible button
    toVolumeLayout = qt.QFormLayout(self.toVolumeCollapsible)
    toVolumeLayout.setVerticalSpacing(5)

    #Convert to .mha files option
    self.toFilesCollapsible = ctk.ctkCollapsibleButton()
    self.toFilesCollapsible.text = "Convert to Files"
    self.toFilesCollapsible.collapsed = True
    self.layout.addWidget(self.toFilesCollapsible)

    # Layout within the collapsible button
    toFilesLayout = qt.QFormLayout(self.toFilesCollapsible)

    #
    # Output Format Selector ------------------------------------------------------------------------*
    #
    self.aimButton = qt.QRadioButton(".aim")
    self.aimButton.setChecked(True)

    self.isqButton = qt.QRadioButton(".isq")
    self.isqButton.setChecked(False)

    self.formatSelect = qt.QGridLayout()
    self.formatSelect.addWidget(self.aimButton, 0, 0)
    self.formatSelect.addWidget(self.isqButton, 0, 1)

    # ct type button frame
    self.formatSelectFrame = qt.QFrame()
    self.formatSelectFrame.setLayout(self.formatSelect)
    #self.formatSelectFrame.setFixedHeight(30)
    toVolumeLayout.addRow("Input File Type: ", self.formatSelectFrame)

    #
    # File Selector
    #
    self.inputFileSelect = qt.QFileDialog()
    self.inputFileSelect.setFileMode(qt.QFileDialog.ExistingFile)
    self.inputFileSelect.setNameFilter("*.AIM *.aim")

    self.fileButton = qt.QPushButton("Browse")

    self.fileTextList = qt.QTextEdit("None Selected")
    self.fileTextList.setReadOnly(True)
    self.fileTextList.setFixedHeight(45)

    self.fileSelect = qt.QGridLayout()
    self.fileSelect.addWidget(self.fileButton)
    self.fileSelect.addWidget(self.fileTextList)
    toVolumeLayout.addRow("Select File: ", self.fileSelect)

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
    self.outputVolumeSelector.setCurrentNode(None)
    toVolumeLayout.addRow("Output Volume: ", self.outputVolumeSelector)

    #
    # Apply Button
    #
    executeGridLayout = qt.QGridLayout()
    executeGridLayout.setRowMinimumHeight(0,20)
    executeGridLayout.setRowMinimumHeight(1,40)

    self.applyButton = qt.QPushButton("Convert")
    self.applyButton.toolTip = "Convert file to Slicer volume."
    self.applyButton.enabled = False
    executeGridLayout.addWidget(self.applyButton, 1, 0)

    toVolumeLayout.addRow(executeGridLayout)

    #
    # Output Calibrations
    # Update to output recommended thresholds once we figure out calculations
    self.calibrationOutput = qt.QTextEdit()
    self.calibrationOutput.setReadOnly(True)
    self.calibrationOutput.setFixedHeight(90)
    toVolumeLayout.addRow("Calibrations: ", self.calibrationOutput)

    # connections
    self.fileButton.clicked.connect(self.onFileSelect)
    self.applyButton.connect('clicked(bool)', self.onApplyButton)
    self.outputVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onNodeSelect)
    self.aimButton.clicked.connect(self.onFormatSelect)
    self.isqButton.clicked.connect(self.onFormatSelect)

    # Add vertical spacer
    self.layout.addStretch(1)

    #
    # File Selector ---------------------------------------------------------------------------------*
    #
    self.multiFileSelect = qt.QFileDialog()
    self.multiFileSelect.setFileMode(qt.QFileDialog.ExistingFiles)
    self.multiFileSelect.setNameFilter("*.AIM *.aim *.ISQ *.isq")

    self.fileButton2 = qt.QPushButton("Browse")

    self.multiFileText = qt.QTextEdit("None Selected")
    self.multiFileText.setReadOnly(True)
    self.multiFileText.setFixedHeight(90)

    self.fileSelectPanel = qt.QGridLayout()
    self.fileSelectPanel.addWidget(self.fileButton2)
    self.fileSelectPanel.addWidget(self.multiFileText)
    toFilesLayout.addRow("Select File: ", self.fileSelectPanel)

    #optional destination folder
    self.outputFolderSelect = qt.QFileDialog()
    self.outputFolderSelect.setFileMode(qt.QFileDialog.Directory)

    self.folderButton = qt.QPushButton("Browse")

    self.folderText = qt.QTextEdit("None Selected")
    self.folderText.setReadOnly(True)
    self.folderText.setFixedHeight(45)

    self.folderSelectPanel = qt.QGridLayout()
    self.folderSelectPanel.addWidget(self.folderButton)
    self.folderSelectPanel.addWidget(self.folderText)
    toFilesLayout.addRow("Select Output Folder: \n(optional)", self.folderSelectPanel)

    #list of files, folder
    self.filenameList = []
    self.selectedFolder = ''

    #convert button
    executeGridLayout2 = qt.QGridLayout()
    executeGridLayout2.setRowMinimumHeight(0,20)
    executeGridLayout2.setRowMinimumHeight(1,20)

    self.convertButton = qt.QPushButton('Convert')
    self.convertButton.toolTip = "Convert files to .mha format"
    self.convertButton.enabled = False
    executeGridLayout2.addWidget(self.convertButton, 1, 0)

    toFilesLayout.addRow(executeGridLayout2)

    # connections
    self.fileButton2.clicked.connect(self.onFilesSelect)
    self.folderButton.clicked.connect(self.onFolderSelect)
    self.convertButton.clicked.connect(self.onConvertButton)

    self.toVolumeCollapsible.contentsCollapsed.connect(self.onCollapse1)
    self.toFilesCollapsible.contentsCollapsed.connect(self.onCollapse2)


  def cleanup(self):
    pass

  def onFormatSelect(self):
    if self.aimButton.isChecked():
      self.inputFileSelect.setNameFilter("*.AIM *.aim")
    elif self.isqButton.isChecked():
      self.inputFileSelect.setNameFilter("*.ISQ *.isq")

  
  
  def onFileSelect(self):
    #Open file explorer and update file
    if self.inputFileSelect.exec_():
      self.filename = self.inputFileSelect.selectedFiles()[0]
      self.fileTextList.setText(self.filename)
      self.outputVolumeSelector.baseName = (self.filename[self.filename.rfind('/') + 1:self.filename.rfind('.')] +"_CONVERTED")
      if not self.outputVolumeSelector.currentNode():
        self.outputVolumeSelector.addNode()
  
  def onFilesSelect(self):
    #Open file explorer and update files
    if self.multiFileSelect.exec_():
      self.filenameList += self.multiFileSelect.selectedFiles()
      self.multiFileText.clear()
      for file in self.filenameList:
        self.multiFileText.append(file)

    #check to enable convert button
    if len(self.filenameList) > 0:
      self.convertButton.enabled = True

  def onFolderSelect(self):
    #select destination folder
    if self.outputFolderSelect.exec_():
      self.selectedFolder = self.outputFolderSelect.selectedFiles()[0]
      self.folderText.setText(self.selectedFolder)

  def onNodeSelect(self):
    self.applyButton.enabled = self.outputVolumeSelector.currentNode()
  
  #
  #Volume Conversion Button Pressed
  #
  def onApplyButton(self):
    #check if itk installed to slicer
    try:
      import itk
    except:
      slicer.util.errorDisplay("The ITK module is not installed in 3D Slicer. Follow the instructions on the File Converter Wiki page on GitHub to install.", 'ITK Not Installed')
      return

    logic = FileConverterLogic()
    print("Run the algorithm")
    if self.aimButton.isChecked():
      inFormat = '.aim'
    elif self.isqButton.isChecked():
      inFormat = '.isq'
    
    meta = logic.convert(self.filename, self.outputVolumeSelector.currentNode(), inFormat)

    #find recommended thresholds in HU (3000/10000 in native units)
    mu_water = meta["MuWater"]
    mu_scaling = meta["MuScaling"]
    thresholds = logic.getThreshold(mu_water, mu_scaling)

    #formula: HU = 1000 * (native / mu_scaling - mu_water) / mu_water
    line1 = "Recommended lower threshold: " + str(thresholds[0])
    line2 = "Recommended upper threshold: " + str(thresholds[1])
    self.calibrationOutput.setText(line1 + "\n" + line2)
  
  #
  #Files Conversion Button Pressed
  #
  def onConvertButton(self):
    #check if itk installed to slicer
    try:
      import itk
    except:
      slicer.util.errorDisplay("The ITK module is not installed in 3D Slicer. Follow the instructions on the File Converter Wiki page on GitHub to install.", 'ITK Not Installed')
      return

    logic = FileConverterLogic()
    if not self.selectedFolder == '':
      logic.convertMultiple(self.filenameList, self.selectedFolder)
    else:
      logic.convertMultiple(self.filenameList)
    
    #reset files and box
    self.filenameList = []
    self.multiFileText.clear()
  
  def onCollapse1(self):
    if not self.toVolumeCollapsible.collapsed:
      self.toFilesCollapsible.collapsed = True
  
  def onCollapse2(self):
    if not self.toFilesCollapsible.collapsed:
      self.toVolumeCollapsible.collapsed = True
  


class FileConverterTest(ScriptedLoadableModuleTest):
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
    self.test_FileConverterQuick()

  def test_FileConverterQuick(self):
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
    
    # get test file
    aimPath = self.getFilePath('\\SAMPLE_AIM.AIM')
    
    # check if file is converted
    logic = FileConverterLogic()
    volume = slicer.vtkMRMLScalarVolumeNode()
    volume.SetScene(slicer.mrmlScene)
    volume.SetName("testVolumeNode")
    slicer.mrmlScene.AddNode(volume)
    logic.convert(aimPath, volume, '.aim')

    # check if output volume correct
    self.assertTrue(self.compareImage(volume, self.getFilePath("\\SAMPLE_AIM_CONVERTED.mha")))

    import numpy as np
    img = sitk.GetImageFromArray(np.multiply(np.random.rand(10, 10, 10), 1000))
    sitkUtils.PushVolumeToSlicer(img, volume)

    self.delayDisplay('Test passed!')
    return SUCCESS
  
  def getFilePath(self, filename):
    '''
    Find the full filepath of a file in the samme folder

    Args: 
        filename (str): name of file (requires \'\\\\' before the name)

    Returns:
        str: full file path
    '''
    root = self.getParent(self.getParent(os.path.realpath(__file__)))
    return root + '\\TestFiles' + filename

  def getParent(self, path):
    return os.path.split(path)[0]

  def compareImage(self, convertedVolume, comparisonFile):
    import numpy as np

    # create numpy arrays
    convertArr = slicer.util.arrayFromVolume(convertedVolume)

    reader = sitk.ImageFileReader()
    reader.SetFileName(comparisonFile)
    compareArr = sitk.GetArrayFromImage(reader.Execute())

    # check if images exactly equal and return result
    return compareArr.all() == convertArr.all()