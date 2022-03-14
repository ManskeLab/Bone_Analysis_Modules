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
    self.parent.categories = ["Bone Analysis Module (BAM)"]
    self.parent.dependencies = []
    self.parent.contributors = ["Ryan Yan"] # replace with "Firstname Lastname (Organization)"
    self.parent.helpText = """
    Updated 2022-01-07. Converts an AIM or ISQ file to a viewable slicer volume node. 
    IMPORTANT: Requires ITK package installed in Slicer. 
    Follow instructions on the <a href="https://github.com/ManskeLab/3DSlicer_Erosion_Analysis/wiki/AIM-File-Converter-Module">Github Page</a> to install.
    """
    self.parent.helpText += "<br>For more information see the <a href=https://github.com/ManskeLab/3DSlicer_Erosion_Analysis/wiki/File-Converter-Module>online documentation</a>."
    self.parent.helpText += "<br><td><img src=\"" + self.getLogo('bam') + "\" height=80> "
    self.parent.helpText += "<img src=\"" + self.getLogo('manske') + "\" height=80></td>"
    self.parent.acknowledgementText = """
    Updated on February 28, 2022<br>
    Manske Lab<br>
    McCaig Institue for Bone and Joint Health<br>
    University of Calgary
""" # replace with organization, grant and thanks.

  def getLogo(self, logo_type):
    #get directory
    directory = os.path.split(os.path.split(os.path.realpath(__file__))[0])[0]

    #set file name
    if logo_type == 'bam':
      name = 'BAM_Logo.png'
    elif logo_type == 'manske':
      name = 'Manske_Lab_Logo.png'

    #
    if '\\' in directory:
      return directory + '\\Logos\\' + name
    else:
      return directory + '/Logos/' + name


#
# FileConverterWidget
#

class FileConverterWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """
  def __init__(self, parent):
    ScriptedLoadableModuleWidget.__init__(self, parent)

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)
    # Instantiate and connect widgets ...

    #check if itk installed to slicer
    try:
      import itk
    except:
      text = """This module requires ITK, which is not installed by default in 3D Slicer. 
Follow the instructions on the File Converter Wiki page on GitHub 
(https://github.com/ManskeLab/3DSlicer_Erosion_Analysis/wiki/File-Converter-Module)."""
      slicer.util.errorDisplay(text, 'ITK Not Installed')
      return
    

    #initialize logic
    self.logic = FileConverterLogic()

    # initialize call back object for updating progrss bar
    self.logic.progressCallBack = self.setProgress

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

    # file type button frame
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

    toVolumeLayout.addRow(qt.QLabel(""))

    # Output selector
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

    toVolumeLayout.addRow(qt.QLabel(""))

    # Additional image options
    self.originCheckBox = qt.QCheckBox('Set origin to (0, 0, 0)')
    self.originCheckBox.checked = False
    self.originCheckBox.setToolTip('Sets the offset of the image to 0 in all directions')
    toVolumeLayout.addRow(self.originCheckBox)

    self.spacingCheckBox = qt.QCheckBox('Set spacing to 1')
    self.spacingCheckBox.checked = False
    self.spacingCheckBox.setToolTip('Sets the voxel spacing to be 1 in all directions')
    toVolumeLayout.addRow(self.spacingCheckBox)

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

    # Progress Bar
    self.progressBar = qt.QProgressBar()
    self.progressBar.hide()
    executeGridLayout.addWidget(self.progressBar, 0, 0)

    toVolumeLayout.addRow(executeGridLayout)

    #
    # Output Calibrations
    # Update to output recommended thresholds once we figure out calculations
    self.calibrationOutput = qt.QTextEdit()
    self.calibrationOutput.setReadOnly(True)
    self.calibrationOutput.setFixedHeight(45)
    toVolumeLayout.addRow("Calibrations: ", self.calibrationOutput)

    # connections
    self.fileButton.clicked.connect(self.onFileSelect)
    self.applyButton.connect('clicked(bool)', self.onApplyButton)
    self.outputVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onNodeSelect)
    self.aimButton.clicked.connect(self.onFormatSelect)
    self.isqButton.clicked.connect(self.onFormatSelect)
    self.originCheckBox.clicked.connect(self.onCheckBox)
    self.spacingCheckBox.clicked.connect(self.onCheckBox)

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

    toFilesLayout.addRow(qt.QLabel(""))

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

    toFilesLayout.addRow(qt.QLabel(""))

    # Additional image options
    self.originCheckBox2 = qt.QCheckBox('Set origin to (0, 0, 0)')
    self.originCheckBox2.checked = False
    self.originCheckBox2.setToolTip('Sets the offset of the image to 0 in all directions')
    toFilesLayout.addRow(self.originCheckBox2)

    self.spacingCheckBox2 = qt.QCheckBox('Set spacing to 1')
    self.spacingCheckBox2.checked = False
    self.spacingCheckBox2.setToolTip('Sets the voxel spacing to be 1 in all directions')
    toFilesLayout.addRow(self.spacingCheckBox2)

    # ct type button layout
    fileTypeLayout = qt.QGridLayout()

    # ct type buttons
    self.mhaButton = qt.QRadioButton("MetaImage (.mha)")
    self.mhaButton.setChecked(True)
    self.niftiButton = qt.QRadioButton("NIfTI (.nii)")
    self.niftiButton.setChecked(False)
    fileTypeLayout.addWidget(self.mhaButton, 0, 0)
    fileTypeLayout.addWidget(self.niftiButton, 0, 1)
    # ct type button frame
    fileTypeFrame = qt.QFrame()
    fileTypeFrame.setLayout(fileTypeLayout)
    toFilesLayout.addRow("Output Format: ", fileTypeFrame)

    #convert button
    executeGridLayout2 = qt.QGridLayout()
    executeGridLayout2.setRowMinimumHeight(0,20)
    executeGridLayout2.setRowMinimumHeight(1,20)

    self.convertButton = qt.QPushButton('Convert')
    self.convertButton.toolTip = "Convert files to the selected"
    self.convertButton.enabled = False
    executeGridLayout2.addWidget(self.convertButton, 1, 0)

    # Progress Bar
    self.progressBar2 = qt.QProgressBar()
    self.progressBar2.hide()
    executeGridLayout2.addWidget(self.progressBar2, 0, 0)

    toFilesLayout.addRow(executeGridLayout2)

    # connections
    self.fileButton2.clicked.connect(self.onFilesSelect)
    self.folderButton.clicked.connect(self.onFolderSelect)
    self.convertButton.clicked.connect(self.onConvertButton)
    self.originCheckBox2.clicked.connect(self.onCheckBox)
    self.spacingCheckBox2.clicked.connect(self.onCheckBox)

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
    '''File is selected in Convert to Volume'''
    #Open file explorer and update file
    if self.inputFileSelect.exec_():
      self.filename = self.inputFileSelect.selectedFiles()[0]
      self.fileTextList.setText(self.filename)
      self.outputVolumeSelector.baseName = (self.filename[self.filename.rfind('/') + 1:self.filename.rfind('.')] +"_CONVERTED")
  
  def onFilesSelect(self):
    '''Files are selected in Convert to Files'''
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
    '''Destination folder selected'''
    if self.outputFolderSelect.exec_():
      self.selectedFolder = self.outputFolderSelect.selectedFiles()[0]
      self.folderText.setText(self.selectedFolder)

  def onNodeSelect(self):
    '''Output volume changed'''
    self.applyButton.enabled = self.outputVolumeSelector.currentNode()

  def onCheckBox(self):
    '''Check box option changed'''
    if self.toFilesCollapsible.collapsed:
      self.logic.changeOptions(self.originCheckBox.checked, self.spacingCheckBox.checked)
    else:
      self.logic.changeOptions(self.originCheckBox2.checked, self.spacingCheckBox2.checked)
  
  #
  #Volume Conversion Button Pressed
  #
  def onApplyButton(self):
    '''Convert button in first widget pressed'''

    self.progressBar.show()

    print("Run the algorithm")
    if self.aimButton.isChecked():
      inFormat = '.aim'
    elif self.isqButton.isChecked():
      inFormat = '.isq'
    
    meta = self.logic.convert(self.filename, self.outputVolumeSelector.currentNode(), inFormat)

    self.progressBar.hide()

    #find recommended thresholds in HU (3000/10000 in native units)
    mu_water = meta["MuWater"]
    mu_scaling = meta["MuScaling"]
    thresholds = self.logic.getThreshold(mu_water, mu_scaling)

    #formula: HU = 1000 * (native / mu_scaling - mu_water) / mu_water
    line1 = "Recommended lower threshold: " + str(thresholds[0])
    line2 = "Recommended upper threshold: " + str(thresholds[1])
    self.calibrationOutput.setText(line1 + "\n" + line2)
  
  #
  #Files Conversion Button Pressed
  #
  def onConvertButton(self):
    '''Convert button in second widget pressed'''

    self.progressBar2.show()

    #get output format
    if self.mhaButton.checked:
      outFormat = '.mha'
    elif self.niftiButton.checked:
      outFormat = '.nii'

    #convert files
    if not self.selectedFolder == '':
      self.logic.convertMultiple(self.filenameList, outFormat, self.selectedFolder)
    else:
      self.logic.convertMultiple(self.filenameList, outFormat)
    
    #reset files and box
    self.filenameList = []
    self.multiFileText.clear()

    self.progressBar2.hide()

  #collapsible button pressed
  def onCollapse1(self):
    if not self.toVolumeCollapsible.collapsed:
      self.toFilesCollapsible.collapsed = True
  
  def onCollapse2(self):
    if not self.toFilesCollapsible.collapsed:
      self.toVolumeCollapsible.collapsed = True
  
  #update progress bar
  def setProgress(self, value):
    """Update the progress bar"""
    self.progressBar.setValue(value)
    self.progressBar2.setValue(value)

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
    from Testing.FileConverterTestLogic import FileConverterTestLogic

    self.delayDisplay("Starting the test")
    #
    # first, get some data
    #

    #setup logic
    logic = FileConverterLogic()
    testLogic = FileConverterTestLogic()
    
    # get test file
    aimPath = testLogic.getFilePath('SAMPLE_AIM.AIM')
    
    # check if file is converted
    volume = slicer.vtkMRMLScalarVolumeNode()
    volume.SetScene(slicer.mrmlScene)
    volume.SetName("testVolumeNode")
    slicer.mrmlScene.AddNode(volume)
    logic.convert(aimPath, volume, '.aim', noProgress=True)

    # check if output volume correct
    self.assertTrue(testLogic.compareImage(volume, testLogic.getFilePath("\\SAMPLE_AIM_CONVERTED.mha")))

    self.delayDisplay('Test passed!')
    return SUCCESS
