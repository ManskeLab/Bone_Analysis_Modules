#-----------------------------------------------------
# AutoMask.py
#
# Created by:  Mingjie Zhao
# Created on:  20-10-2020
#
# Description: This module sets up the Automatic Mask 3D Slicer extension.
#
#-----------------------------------------------------
from sre_constants import SUCCESS
import vtk, qt, ctk, slicer
import SimpleITK as sitk
import sitkUtils
import sys

import numpy as np
np.set_printoptions(threshold=sys.maxsize)

from slicer.ScriptedLoadableModule import *
import logging
from AutoMaskLib.AutoMaskLogic import AutoMaskLogic
from AutoMaskLib.SegmentEditor import SegmentEditor
from AutoMaskLib.DeleteQtDialog import DeleteQtDialog
import os
from time import sleep

#
# AutoMask
#
class AutoMask(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Automatic Mask" # TODO make this more human readable by adding spaces
    self.parent.categories = ["Bone Analysis Module (BAM)"]
    self.parent.dependencies = []
    self.parent.contributors = ["Mingjie Zhao"] # replace with "Firstname Lastname (Organization)"
    self.parent.helpText = """
This module contains steps 1-3 of erosion analysis. <br>
Step 1: Manually separate the bones by covering each bone with a different label. <br>
Step 2: Perform automatic masking on the greyscale image and generate a
label map volume of the mask. <br>
Step 3: Manually correct the mask. <br>
If a mask already exists and needs to be corrected, load it to slicer as a label map volume
and skip to Step 3.
"""
    self.parent.helpText += "<br>For more information see the <a href=https://github.com/ManskeLab/3DSlicer_Erosion_Analysis/wiki/Automatic-mask-Module>online documentation</a>."
    self.parent.helpText += "<br><td><img src=\"" + self.getLogo('bam') + "\" height=80> "
    self.parent.helpText += "<img src=\"" + self.getLogo('manske') + "\" height=80></td>"
    self.parent.acknowledgementText = """
    Updated on January 27, 2022.<br>
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
# AutoMaskWidget
#
class AutoMaskWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    # Initialize logics object
    self._logic = AutoMaskLogic()
    self._logic.progressCallBack = self.setProgress

    self.loadMasksPath = os.path.join(os.path.split(os.path.dirname(os.path.abspath(__file__)))[0], 'LOAD_MASKS')

    self.applyPressed = False

    ScriptedLoadableModuleWidget.__init__(self, parent)

  def setup(self):
    # Buttons for testing
    ScriptedLoadableModuleWidget.setup(self)

    # Collapsible buttons
    self.boneSeparationCollapsibleButton = ctk.ctkCollapsibleButton()
    self.autoMaskCollapsibleButton = ctk.ctkCollapsibleButton()
    self.manualCorrectionCollapsibleButton = ctk.ctkCollapsibleButton()

    # Set up widgets inside the collapsible buttons
    self.setupBoneSeparation()
    self.setupAutoMask()
    self.setupManualCorrection()

    # Add vertical spacer
    self.layout.addStretch(1)

    # Update buttons
    self.onSelect1()
    self.onSelect2()
    self.onSelect3()
    self.onSelectInputVolume()

  def setupBoneSeparation(self):
    """Set up widgets in step 1 bone separation"""
    # set text on collapsible button, and add collapsible button to layout
    self.boneSeparationCollapsibleButton.text = "Step 1 - Rough Mask"
    self.boneSeparationCollapsibleButton.collapsed = True
    self.layout.addWidget(self.boneSeparationCollapsibleButton)

    # layout within the collapsible button
    boneSeparationLayout = qt.QVBoxLayout(self.boneSeparationCollapsibleButton)

    # instructions
    boneSeparationLayout.addWidget(qt.QLabel("This step is only necessary if the bones are close to each other."))
    boneSeparationLayout.addWidget(qt.QLabel("Create a rough mask for each bone to assist masking."))
    boneSeparationLayout.addWidget(qt.QLabel("")) # horizontal space

    # layout for input and output selectors
    selectorFormLayout = qt.QFormLayout()
    selectorFormLayout.setContentsMargins(0, 0, 0, 0)

    # master volume selector
    self.separateInputSelector = slicer.qMRMLNodeComboBox()
    self.separateInputSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.separateInputSelector.selectNodeUponCreation = False
    self.separateInputSelector.addEnabled = False
    self.separateInputSelector.removeEnabled = False
    self.separateInputSelector.noneEnabled = False
    self.separateInputSelector.showHidden = False
    self.separateInputSelector.showChildNodeTypes = False
    self.separateInputSelector.setMRMLScene(slicer.mrmlScene)
    self.separateInputSelector.setToolTip("Select the input scan")
    selectorFormLayout.addRow("Input Volume: ", self.separateInputSelector)

    self.separateRoughMaskSelector = slicer.qMRMLNodeComboBox()
    self.separateRoughMaskSelector.nodeTypes = ["vtkMRMLLabelMapVolumeNode"]
    self.separateRoughMaskSelector.selectNodeUponCreation = False
    self.separateRoughMaskSelector.addEnabled = False
    self.separateRoughMaskSelector.removeEnabled = False
    self.separateRoughMaskSelector.noneEnabled = True
    self.separateRoughMaskSelector.showHidden = False
    self.separateRoughMaskSelector.showChildNodeTypes = False
    self.separateRoughMaskSelector.setMRMLScene(slicer.mrmlScene)
    self.separateRoughMaskSelector.setToolTip("Select the rough mask segment")
    selectorFormLayout.addRow("Rough Mask: ", self.separateRoughMaskSelector)

    # frame with selectors
    selectorFrame = qt.QFrame()
    selectorFrame.setLayout(selectorFormLayout)
    boneSeparationLayout.addWidget(selectorFrame)

    # layout for initialize and apply buttons
    initApplyGridLayout = qt.QGridLayout()
    initApplyGridLayout.setContentsMargins(0, 5, 0, 5)

    # initialize button
    self.initButton1 = qt.QPushButton("Initialize")
    self.initButton1.toolTip = "Initialize the parameters in segmentation editor for manual correction"
    self.initButton1.enabled = False
    initApplyGridLayout.addWidget(self.initButton1, 0, 0)

    # cancel button
    self.cancelButton1 = qt.QPushButton("Cancel")
    self.cancelButton1.toolTip = "Discard the manual correction"
    self.cancelButton1.enabled = False
    initApplyGridLayout.addWidget(self.cancelButton1, 0, 1)

    # apply button
    self.applyButton1 = qt.QPushButton("Apply")
    self.applyButton1.toolTip = "Apply the manual correction to the mask"
    self.applyButton1.enabled = False
    initApplyGridLayout.addWidget(self.applyButton1, 0, 2)

    # delete button
    self.deleteButton1 = qt.QPushButton("Delete Masks")
    self.deleteButton1.toolTip = "Delete all masks in all slices"
    self.deleteButton1.enabled = False
    initApplyGridLayout.addWidget(self.deleteButton1, 1, 0)

    # Erase between slices button
    self.eraseBetweenSlicesButton1 = qt.QPushButton("Erase Between Slices")
    self.eraseBetweenSlicesButton1.toolTip = "Interpolates between segments between slices and erases those segments"
    self.eraseBetweenSlicesButton1.enabled = False
    initApplyGridLayout.addWidget(self.eraseBetweenSlicesButton1, 1, 1)

    # Apply erase button
    self.applyEraseBetweenSlicesButton1 = qt.QPushButton("Apply Erase")
    self.applyEraseBetweenSlicesButton1.toolTip = "Applies erase between slices"
    self.applyEraseBetweenSlicesButton1.enabled = False
    initApplyGridLayout.addWidget(self.applyEraseBetweenSlicesButton1, 1, 2)

    # Hide rough mask checkbox
    self.hideButton = qt.QCheckBox()
    self.hideButton.checked = False
    initApplyGridLayout.addWidget(qt.QLabel("Hide Rough Mask"), 0, 3)
    initApplyGridLayout.addWidget(self.hideButton, 0, 4)

    # frame with initialize and apply buttons
    initApplyFrame = qt.QFrame()
    initApplyFrame.setLayout(initApplyGridLayout)
    boneSeparationLayout.addWidget(initApplyFrame)

    # segmentation editor
    self.segmentEditor = SegmentEditor(boneSeparationLayout)

    self.boneSeparationCollapsibleButton.connect('contentsCollapsed(bool)', self.onCollapsed1)
    self.initButton1.connect('clicked(bool)', self.onInitButton1)
    self.cancelButton1.connect('clicked(bool)', self.onCancelButton1)
    self.applyButton1.connect('clicked(bool)', self.onApplyButton1)
    self.deleteButton1.connect('clicked(bool)', self.onDeleteButton)
    self.eraseBetweenSlicesButton1.connect('clicked(bool)', self.onEraseBetweenSlicesButton1)
    self.applyEraseBetweenSlicesButton1.connect('clicked(bool)', self.onApplyEraseBetweenSlicesButton)
    self.separateInputSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect1)
    self.separateRoughMaskSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelectRoughMask)
    self.hideButton.clicked.connect(self.onHideRoughMask)

  def setupAutoMask(self):
    """Set up widgets in step 2 automatic mask"""
    # set text on collapsible button, and add collapsible button to layout
    self.autoMaskCollapsibleButton.text = "Step 2 - Automatic Mask"
    self.layout.addWidget(self.autoMaskCollapsibleButton)

    # layout within the collapsible button
    autoMaskLayout = qt.QFormLayout(self.autoMaskCollapsibleButton)
    autoMaskLayout.setVerticalSpacing(5)

    # input volume selector
    self.inputVolumeSelector = slicer.qMRMLNodeComboBox()
    self.inputVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.inputVolumeSelector.selectNodeUponCreation = False
    self.inputVolumeSelector.addEnabled = False
    self.inputVolumeSelector.removeEnabled = True
    self.inputVolumeSelector.renameEnabled = True
    self.inputVolumeSelector.noneEnabled = False
    self.inputVolumeSelector.showHidden = False
    self.inputVolumeSelector.showChildNodeTypes = False
    self.inputVolumeSelector.setMRMLScene( slicer.mrmlScene )
    self.inputVolumeSelector.setToolTip("Select the input volume to get the mask from")
    self.inputVolumeSelector.setCurrentNode(None)
    autoMaskLayout.addRow("Input Volume: ", self.inputVolumeSelector)

    # output volume selector
    self.outputVolumeSelector = slicer.qMRMLNodeComboBox()
    self.outputVolumeSelector.nodeTypes = ["vtkMRMLLabelMapVolumeNode"]
    self.outputVolumeSelector.selectNodeUponCreation = True
    self.outputVolumeSelector.addEnabled = True
    self.outputVolumeSelector.removeEnabled = True
    self.outputVolumeSelector.renameEnabled = True
    self.outputVolumeSelector.noneEnabled = False
    self.outputVolumeSelector.showHidden = False
    self.outputVolumeSelector.showChildNodeTypes = False
    self.outputVolumeSelector.setMRMLScene( slicer.mrmlScene )
    self.outputVolumeSelector.baseName = "MASK"
    self.outputVolumeSelector.setToolTip( "Select the output volume to store the mask" )
    self.outputVolumeSelector.setCurrentNode(None)
    autoMaskLayout.addRow("Output Mask: ", self.outputVolumeSelector)

    #auto threshold dropdown and button
    self.threshButton = qt.QCheckBox()
    self.threshButton.checked = True
    autoMaskLayout.addRow("Use Automatic Thresholding", self.threshButton)

    self.threshSelector = qt.QComboBox()
    self.threshSelector.addItems(['Otsu', 'Huang', 'Max Entropy', 'Moments', 'Yen'])
    #self.threshSelector.setCurrentIndex(2)
    autoMaskLayout.addRow("Thresholding Method", self.threshSelector)

    # Help button for thresholding methods
    self.helpButton = qt.QPushButton("Help")
    self.helpButton.toolTip = "Tips for selecting a thresholding method"
    self.helpButton.setFixedSize(50, 20)
    autoMaskLayout.addRow("", self.helpButton)

    # threshold spin boxes (default unit is HU)
    self.lowerThresholdText = qt.QSpinBox()
    self.lowerThresholdText.setMinimum(-9999)
    self.lowerThresholdText.setMaximum(999999)
    self.lowerThresholdText.setSingleStep(10)
    self.lowerThresholdText.value = 900
    autoMaskLayout.addRow("Lower Threshold: ", self.lowerThresholdText)
    self.upperThresholdText = qt.QSpinBox()
    self.upperThresholdText.setMinimum(-9999)
    self.upperThresholdText.setMaximum(999999)
    self.upperThresholdText.setSingleStep(10)
    self.upperThresholdText.value = 4000
    autoMaskLayout.addRow("Upper Threshold: ", self.upperThresholdText)

    # gaussian sigma spin box
    self.sigmaText = qt.QDoubleSpinBox()
    self.sigmaText.setMinimum(0.0001)
    self.sigmaText.setDecimals(4)
    self.sigmaText.value = 2
    self.sigmaText.setToolTip("Standard deviation in the Gaussian smoothing filter")
    autoMaskLayout.addRow("Gaussian Sigma: ", self.sigmaText)

    # bone number spin box
    self.boneNumSpinBox = qt.QSpinBox()
    self.boneNumSpinBox.setMinimum(1)
    self.boneNumSpinBox.setMaximum(9)
    self.boneNumSpinBox.setSingleStep(1)
    self.boneNumSpinBox.value = 1
    self.boneNumSpinBox.setToolTip("Enter the number of separate bone structures in the scan")
    autoMaskLayout.addRow("Number of Bones: ", self.boneNumSpinBox)

    #dilate/erode spin box
    self.dilateErodeRadiusText = qt.QSpinBox()
    self.dilateErodeRadiusText.setMinimum(1)
    self.dilateErodeRadiusText.setMaximum(9999)
    self.dilateErodeRadiusText.setSingleStep(1)
    self.dilateErodeRadiusText.value = 38
    self.dilateErodeRadiusText.setToolTip("Enter the dilate/erode kernel radius")
    autoMaskLayout.addRow("Dilate/Erode Radius [voxels]: ", self.dilateErodeRadiusText)

    # rough mask selector
    self.separateMapSelector = slicer.qMRMLNodeComboBox()
    self.separateMapSelector.nodeTypes = ["vtkMRMLLabelMapVolumeNode"]
    self.separateMapSelector.selectNodeUponCreation = False
    self.separateMapSelector.addEnabled = False
    self.separateMapSelector.removeEnabled = False
    self.separateMapSelector.renameEnabled = False
    self.separateMapSelector.noneEnabled = True
    self.separateMapSelector.showHidden = False
    self.separateMapSelector.showChildNodeTypes = False
    self.separateMapSelector.setMRMLScene( slicer.mrmlScene )
    self.separateMapSelector.setToolTip( "Select the rough mask from Step 1" )
    autoMaskLayout.addRow("Rough Mask(Optional): ", self.separateMapSelector)

    self.algorithmSelector = qt.QComboBox()
    self.algorithmSelector.addItems(['Ormir', 'Dual Threshold'])
    self.algorithmSelector.setCurrentIndex(0)
    autoMaskLayout.addRow("Masking Algorithm", self.algorithmSelector)

    # Execution layout
    executeGridLayout = qt.QGridLayout()
    executeGridLayout.setRowMinimumHeight(0,20)
    executeGridLayout.setRowMinimumHeight(1,20)

    # Progress Bar
    self.progressBar = qt.QProgressBar()
    self.progressBar.hide()
    executeGridLayout.addWidget(self.progressBar, 0, 0)

    # Get Button
    self.getMaskButton = qt.QPushButton("Get Mask")
    self.getMaskButton.toolTip = "Get mask as a label map"
    self.getMaskButton.enabled = False
    executeGridLayout.addWidget(self.getMaskButton, 1, 0)

    # Execution frame with progress bar and get button
    executeFrame = qt.QFrame()
    executeFrame.setLayout(executeGridLayout)
    autoMaskLayout.addRow(executeFrame)

    # connections
    self.autoMaskCollapsibleButton.connect('contentsCollapsed(bool)', self.onCollapsed2)
    self.inputVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelectInputVolume)
    self.getMaskButton.connect('clicked(bool)', self.onGetMask)
    self.inputVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect2)
    self.outputVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect2)
    self.threshButton.clicked.connect(self.onAutoThresh)
    self.helpButton.clicked.connect(self.onHelpButton)

    self.onAutoThresh()

  def setupManualCorrection(self):
    """Set up widgets in step 3 manual correction"""
    # Set text on collapsible button, and add collapsible button to layout
    self.manualCorrectionCollapsibleButton.text = 'Step 3 - Manual Correction'
    self.manualCorrectionCollapsibleButton.collapsed = True
    self.layout.addWidget(self.manualCorrectionCollapsibleButton)

    # Layout within the collapsible button
    manualCorrectionLayout = qt.QVBoxLayout(self.manualCorrectionCollapsibleButton)

    # layout for input and output selectors
    selectorFormLayout = qt.QFormLayout()
    selectorFormLayout.setContentsMargins(0, 0, 0, 0)

    selectorFormLayout.addRow(qt.QLabel("Load masks from directory <BAM directory>/LOAD_MASKS:"))

    self.loadMasks = qt.QPushButton("Load")
    self.loadMasks.toolTip = "Load masks from the directory <BAM directory>/LOAD_MASKS"
    self.loadMasks.enabled = True
    selectorFormLayout.addRow(self.loadMasks)

    # mask selector
    self.maskVolumeSelector = slicer.qMRMLNodeComboBox()
    self.maskVolumeSelector.nodeTypes = ["vtkMRMLLabelMapVolumeNode"]
    self.maskVolumeSelector.selectNodeUponCreation = False
    self.maskVolumeSelector.addEnabled = False
    self.maskVolumeSelector.removeEnabled = False
    self.maskVolumeSelector.renameEnabled = False
    self.maskVolumeSelector.noneEnabled = True
    self.maskVolumeSelector.showHidden = False
    self.maskVolumeSelector.showChildNodeTypes = False
    self.maskVolumeSelector.setMRMLScene( slicer.mrmlScene )
    self.maskVolumeSelector.setToolTip( "Select the mask to be corrected" )
    selectorFormLayout.addRow("Mask to be Corrected: ", self.maskVolumeSelector)

    selectorFormLayout.addRow(qt.QLabel(""))

    # master volume selector
    self.masterVolumeSelector = slicer.qMRMLNodeComboBox()
    self.masterVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.masterVolumeSelector.selectNodeUponCreation = False
    self.masterVolumeSelector.addEnabled = False
    self.masterVolumeSelector.removeEnabled = False
    self.masterVolumeSelector.noneEnabled = False
    self.masterVolumeSelector.showHidden = False
    self.masterVolumeSelector.showChildNodeTypes = False
    self.masterVolumeSelector.setMRMLScene( slicer.mrmlScene )
    self.masterVolumeSelector.setToolTip("Select the scan associated with the mask")
    selectorFormLayout.addRow("Master Volume: ", self.masterVolumeSelector)

    # frame with selectors
    selectorFrame = qt.QFrame()
    selectorFrame.setLayout(selectorFormLayout)
    manualCorrectionLayout.addWidget(selectorFrame)

    # layout for initialize and apply buttons
    initApplyGridLayout = qt.QGridLayout()
    initApplyGridLayout.setContentsMargins(0, 5, 0, 5)

    # initialize button
    self.initButton3 = qt.QPushButton("Initialize")
    self.initButton3.toolTip = "Initialize the parameters in segmentation editor for manual correction"
    self.initButton3.enabled = False
    initApplyGridLayout.addWidget(self.initButton3, 0, 0)

    # cancel button
    self.cancelButton3 = qt.QPushButton("Cancel")
    self.cancelButton3.toolTip = "Discard the manual correction"
    self.cancelButton3.enabled = False
    initApplyGridLayout.addWidget(self.cancelButton3, 0, 1)

    # apply button
    self.applyButton3 = qt.QPushButton("Apply")
    self.applyButton3.toolTip = "Apply the manual correction to the mask"
    self.applyButton3.enabled = False
    initApplyGridLayout.addWidget(self.applyButton3, 0, 2)

    # delete button
    self.deleteButton3 = qt.QPushButton("Delete Masks")
    self.deleteButton3.toolTip = "Delete all masks in all slices"
    self.deleteButton3.enabled = False
    initApplyGridLayout.addWidget(self.deleteButton3, 1, 0)

    # Erase between slices button
    self.eraseBetweenSlicesButton3 = qt.QPushButton("Erase Between Slices")
    self.eraseBetweenSlicesButton3.toolTip = "Interpolates between segments between slices and erases those segments"
    self.eraseBetweenSlicesButton3.enabled = False
    initApplyGridLayout.addWidget(self.eraseBetweenSlicesButton3, 1, 1)

    # Apply erase button
    self.applyEraseBetweenSlicesButton3 = qt.QPushButton("Apply Erase")
    self.applyEraseBetweenSlicesButton3.toolTip = "Applies erase between slices"
    self.applyEraseBetweenSlicesButton3.enabled = False
    initApplyGridLayout.addWidget(self.applyEraseBetweenSlicesButton3, 1, 2)

    # frame with initialize and apply buttons
    initApplyFrame = qt.QFrame()
    initApplyFrame.setLayout(initApplyGridLayout)
    manualCorrectionLayout.addWidget(initApplyFrame)

    # segmentation editor
    self.segmentEditor3 = SegmentEditor(manualCorrectionLayout)

    # connections
    self.manualCorrectionCollapsibleButton.connect('contentsCollapsed(bool)', self.onCollapsed3)
    self.initButton3.connect('clicked(bool)', self.onInitButton3)
    self.applyButton3.connect('clicked(bool)', self.onApplyButton3)
    self.cancelButton3.connect('clicked(bool)', self.onCancelButton3)
    self.deleteButton3.connect('clicked(bool)', self.onDeleteButton)
    self.eraseBetweenSlicesButton3.connect('clicked(bool)', self.onEraseBetweenSlicesButton3)
    self.applyEraseBetweenSlicesButton3.connect('clicked(bool)', self.onApplyEraseBetweenSlicesButton)
    self.loadMasks.connect('clicked(bool)', self.onLoadMasks)
    self.maskVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelectInternalMask)
    self.masterVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect3)

    #logger
    self.logger = logging.getLogger("AutoMask")

  def onCollapsed1(self):
    if not self.boneSeparationCollapsibleButton.collapsed:
      self.autoMaskCollapsibleButton.collapsed = True
      self.manualCorrectionCollapsibleButton.collapsed = True

  def onCollapsed2(self):
    if not self.autoMaskCollapsibleButton.collapsed:
      self.boneSeparationCollapsibleButton.collapsed = True
      self.manualCorrectionCollapsibleButton.collapsed = True

  def onCollapsed3(self):
    if not self.manualCorrectionCollapsibleButton.collapsed:
      self.boneSeparationCollapsibleButton.collapsed = True
      self.autoMaskCollapsibleButton.collapsed = True

  def enter(self):
    """Run this whenever the module is reopened"""
    success = self._logic.enterSegmentEditor(self.segmentEditor)

    if not success: # if enter segmentation editor is not successful, some nodes are missing
      self.disableBoneSeparationWidgets()
      self.disableManualCorrectionWidgets()

  def exit(self):
    """Run this whenever the module is closed"""
    self._logic.exitSegmentEditor(self.segmentEditor)

  def onSelect1(self):
    """Update the state of the initialize button whenever the selector in step 1 change"""
    self.initButton1.enabled = self.separateInputSelector.currentNode()

    slicer.util.setSliceViewerLayers(background=self.separateInputSelector.currentNode())
    slicer.util.resetSliceViews()

  def onSelectRoughMask(self):
    if self.applyPressed:
      self.applyPressed = False
      return

    displayMask = self.separateRoughMaskSelector.currentNode()

    #  Remove current SegmentationNode and create a new node from the rough mask
    if displayMask:
      self._logic.changeRoughMask(displayMask, self.separateInputSelector.currentNode(), self.segmentEditor)

      # add temperory node and delete to prevent duplicate colors
      tempNode = self._logic.getSegmentNode().GetSegmentation().AddEmptySegment("temp")
      self._logic.getSegmentNode().GetSegmentation().RemoveSegment(tempNode)

  def onSelect2(self):
    """Update the state of the get mask button whenever the selectors in step 2 change"""
    self.getMaskButton.enabled = (self.inputVolumeSelector.currentNode() and
                                     self.outputVolumeSelector.currentNode())

  def onLoadMasks(self):
    for image in os.listdir(self.loadMasksPath):
      image_lower = image.lower()
      image_dir = os.path.join(self.loadMasksPath, image)

      binaryThresh = sitk.BinaryThresholdImageFilter()
      binaryThresh.SetLowerThreshold(1)
      binaryThresh.SetUpperThreshold(255)
      binaryThresh.SetInsideValue(1)

      segmentor = sitk.ConnectedComponentImageFilter()
      relabeler = sitk.RelabelComponentImageFilter()
      relabeler.SetMinimumObjectSize(2)

      if ('nrrd' in image_lower) or ('nii' in image_lower) or ('mha' in image_lower) or ('aim' in image_lower):
        outBasename, outExtension = os.path.splitext(image)
        out_dir = os.path.join(self.loadMasksPath, outBasename+'.nrrd')
        temp = sitk.ReadImage(image_dir, sitk.sitkInt32)

        out = binaryThresh.Execute(temp)
        out = segmentor.Execute(out)
        out = relabeler.Execute(out)

        sizes = relabeler.GetSizeOfObjectsInPhysicalUnits()
        print(sizes)
        labeled_out = out[0]
        for i in range(len(sizes) - 1):
          if sizes[i+1] > 1:
            print(i)
            labeled_out += out[i+1]
        sitk.WriteImage(out, out_dir)
        node = slicer.util.loadLabelVolume(out_dir)

  def onSelectInternalMask(self):
    self.segmentEditor3.setSegmentationNode(self.maskVolumeSelector.currentNode())
    self.onSelect3()

  def onSelect3(self):
    """Update the state of the initialize button whenever the selectors in step 3 change"""
    self.initButton3.enabled = (self.maskVolumeSelector.currentNode() and
                               self.masterVolumeSelector.currentNode())

    self.segmentEditor3.setMasterVolumeNode(self.masterVolumeSelector.currentNode())

  def onInitButton1(self):
    """Run this whenever the initialize button in step 1 is clicked"""
    separateInputNode = self.separateInputSelector.currentNode()

    success = self._logic.initRoughMask(self.segmentEditor, separateInputNode)

    if success:
      # update widgets
      self.enableBoneSeparationWidgets()

  def onCancelButton1(self):
    """Run this whenever the cancel button in step 1 is clicked"""
    if slicer.util.confirmOkCancelDisplay('Do you want to discard the segmentation?'):
      separateInputNode = self.separateInputSelector.currentNode()

      self._logic.cancelRoughMask(separateInputNode)

      # update widgets
      self.disableBoneSeparationWidgets()

  def onApplyButton1(self):
    """Run this whenever the apply button in step 1 is clicked"""
    # get the current nodes in the toolkit
    separateInputNode = self.separateInputSelector.currentNode()
    separateOutputName = slicer.mrmlScene.GenerateUniqueName(separateInputNode.GetName()+"_separated")
    separateOutputNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", separateOutputName)

    self._logic.applyRoughMask(separateInputNode, separateOutputNode)

    # update widgets
    if separateOutputNode:
      self.inputVolumeSelector.setCurrentNodeID(separateInputNode.GetID())
      self.separateMapSelector.setCurrentNodeID(separateOutputNode.GetID())
      self.separateRoughMaskSelector.setCurrentNodeID(separateOutputNode.GetID())
    self.disableBoneSeparationWidgets()

    self.hideButton.checked = False
    self.onSelectRoughMask()

    segmentLabelMapNode = self._logic.getSegmentNode()

    dir = os.path.split(separateInputNode.GetStorageNode().GetFullNameFromFileName())
    storageNode = segmentLabelMapNode.CreateDefaultStorageNode()
    storageNode.SetFileName(dir[0]+'/'+os.path.splitext(dir[1])[0]+"_RoughMask.sig.nrrd")

    storageNode.WriteData(segmentLabelMapNode)

  def onDeleteButton(self):
    """Run this whenever the delete button in step 1 is clicked"""
    # user prompt to get start and end slices for delete
    DeleteDialog = DeleteQtDialog()
    DeleteDialog.exec()
    maskRange = DeleteDialog.getNums()

    #background Image
    volumeNode = self.separateInputSelector.currentNode()

    self._logic.applyDeleteMask(maskRange[0], maskRange[1], volumeNode, self.segmentEditor)

    self.applyButton1.enabled = True

    self.onHideRoughMask()

  def onEraseBetweenSlicesButton1(self):
    self.applyEraseBetweenSlicesButton1.enabled = True
    self.onEraseBetweenSlices()

  def onEraseBetweenSlicesButton3(self):
    self.applyEraseBetweenSlicesButton3.enabled = True

    segmentationNode = self.segmentEditor3.getEditor().segmentationNode()

    eraseNodeID = segmentationNode.GetSegmentation().AddEmptySegment("Delete")
    segmentationNode.GetSegmentation().RemoveSegment(eraseNodeID)
    eraseNodeID = segmentationNode.GetSegmentation().AddEmptySegment("Delete")
    self.segmentEditor3.getEditor().setCurrentSegmentID(eraseNodeID)
    self.segmentEditor3.getEditor().setActiveEffectByName("Paint")

  def onEraseBetweenSlices(self):
    
    segmentationNode = self._logic.getSegmentNode()

    eraseNodeID = segmentationNode.GetSegmentation().AddEmptySegment("Delete")
    self.segmentEditor.getEditor().setCurrentSegmentID(eraseNodeID)
    self.segmentEditor.getEditor().setActiveEffectByName("Paint")

    #TODO make slicer wait until you have atleast 2 slices with segments before enabling apply button

  def onApplyEraseBetweenSlicesButton(self):

    volumeNode = self.separateInputSelector.currentNode()
    segmentationNode = self._logic.getSegmentNode()
    eraseId = segmentationNode.GetSegmentation().GetSegmentIdBySegmentName("Delete")
    self.segmentEditor.getEditor().setCurrentSegmentID(eraseId)

    selectedSegmentIds = vtk.vtkStringArray()

    if(segmentationNode):
        segmentationNode.GetSegmentation().GetSegmentIDs(selectedSegmentIds)

    segmentArrays = []
    segments = []
    segmentIds = []

    for idx in range(selectedSegmentIds.GetNumberOfValues()):
      segmentName = selectedSegmentIds.GetValue(idx)
      if segmentName == "Delete":
        continue

      segmentId = segmentationNode.GetSegmentation().GetSegmentIdBySegmentName(segmentName)

      # Get mask segment as numpy array
      segmentArray = slicer.util.arrayFromSegmentBinaryLabelmap(segmentationNode, segmentId, volumeNode)

      segmentArrays.append(segmentArray)
      segments.append(segmentationNode.GetSegmentation().GetSegment(segmentId))
      segmentIds.append(segmentId)
      segmentationNode.GetSegmentation().RemoveSegment(segmentId)

    self.segmentEditor.getEditor().setActiveEffectByName("Fill between slices")
    effect = self.segmentEditor.getEditor().activeEffect()
    effect.self().onPreview()
    effect.self().onApply()

    # Get erase mask segment as numpy array
    eraseArray = slicer.util.arrayFromSegmentBinaryLabelmap(segmentationNode, eraseId, volumeNode)

    # # startOfEraseMask = 0
    # # endOfEraseMask = startOfEraseMask
    slices = eraseArray.shape[0]
    row = eraseArray.shape[1]
    col = eraseArray.shape[2]

    idx = 0
    for segmentArray in segmentArrays:
      segmentationNode.GetSegmentation().AddSegment(segments[idx], segmentIds[idx])

      # Iterate through voxels
      for i in range(slices):
        for j in range(row):
          for k in range(col):
            if(eraseArray[i, j, k]):
              segmentArray[i, j, k] = 0

      # Convert back to label map array
      slicer.util.updateSegmentBinaryLabelmapFromArray(segmentArray, segmentationNode, segmentIds[idx], volumeNode)
      idx = idx + 1

    segmentationNode.GetSegmentation().RemoveSegment(eraseId)

  def onHideRoughMask(self):
    checked = self.hideButton.checked
    if checked:
      displayMask = None
    else:
      displayMask = self.separateRoughMaskSelector.currentNode()

    if self._logic.getSegmentNode():
      self._logic.getSegmentNode().SetDisplayVisibility(not checked)

    slicer.util.setSliceViewerLayers(background=self.separateInputSelector.currentNode(),
                                      label= displayMask,
                                      labelOpacity=0.5)
    slicer.util.resetSliceViews()

  def onSelectInputVolume(self):
    """Run this whenever the input volume selector in step 2 changes"""
    inputVolumeNode = self.inputVolumeSelector.currentNode()

    if inputVolumeNode:
      # update the default output base name
      self.outputVolumeSelector.baseName = (inputVolumeNode.GetName()+"_MASK")
      # Update the default save directory
      self._logic.setDefaultDirectory(inputVolumeNode)
      # update viewer windows
      slicer.util.setSliceViewerLayers(background=inputVolumeNode)
      slicer.util.resetSliceViews() # centre the volume in the viewer windows

      #check if preset intensity units exist
      check = True
      if "Lower" in inputVolumeNode.__dict__.keys():
        self.lowerThresholdText.setValue(inputVolumeNode.__dict__["Lower"])
        check = False
      if "Upper" in inputVolumeNode.__dict__.keys():
        self.upperThresholdText.setValue(inputVolumeNode.__dict__["Upper"])
        check = False

      #check intensity units and display warning if not in HU
      if check and not self.threshButton.checked:
        if not self._logic.intensityCheck(inputVolumeNode):
          text = """The selected image likely does not use HU for intensity units.
Default thresholds are set in HU and will not generate an accurate result.
Change the lower and upper thresholds before initializing."""
          slicer.util.warningDisplay(text, windowTitle='Intensity Unit Warning')

      #remove existing loggers
      if self.logger.hasHandlers():
        for handler in self.logger.handlers:
          self.logger.removeHandler(handler)

      #initialize logger with filename
      try:
        filename = inputVolumeNode.GetStorageNode().GetFullNameFromFileName()
        filename = os.path.split(filename)[0] + '/LOG_' + os.path.split(filename)[1]
        filename = os.path.splitext(filename)[0] + '.log'
        print(filename)
      except:
        filename = 'share/' + inputVolumeNode.GetName() + '.'
      logHandler = logging.FileHandler(filename)

      self.logger.addHandler(logHandler)
      self.logger.info("Using Automatic Mask Module with " + inputVolumeNode.GetName() + "\n")

    else:
      self.outputVolumeSelector.baseName = "MASK"

  def onAutoThresh(self):
    '''Auto-threshold checkbox is cliked'''
    use_auto = self.threshButton.checked
    self.lowerThresholdText.setEnabled(not use_auto)
    self.upperThresholdText.setEnabled(not use_auto)
    self.threshSelector.setEnabled(use_auto)
    if not use_auto:
      self.onSelectInputVolume()

  def onHelpButton(self) -> None:
    '''Help button is pressed'''
    txt = """Thresholding Methods\n
For images that only contain bone and soft tissue (no completely dark regions), use the 'Otsu', 'Huang', or 'Moments' Thresholds. \n
For images with completely dark regions, use the 'Max Entropy' or 'Yen' Thresholds.
          """
    slicer.util.infoDisplay(txt, 'Help: Similarity Metrics')

  def onGetMask(self):
    """Run this whenever the get mask button in step 2 is clicked"""
    print("hello")
    # update widgets
    self.disableAutoMaskWidgets()

    inputVolumeNode = self.inputVolumeSelector.currentNode()
    outputVolumeNode = self.outputVolumeSelector.currentNode()
    separateMapNode = self.separateMapSelector.currentNode()

    # log info
    self.logger.info("Automatic Mask initialized with parameters:")
    self.logger.info("Input Volume: " + inputVolumeNode.GetName())
    self.logger.info("Output Volume: " + outputVolumeNode.GetName())
    if separateMapNode:
      self.logger.info("Rough Mask: " + separateMapNode.GetName())
    if self.threshButton.checked:
      self.logger.info("Automatic Threshold Method: " + self.threshSelector.currentText)
    else:
      self.logger.info("Lower Theshold: " + str(self.lowerThresholdText.value))
      self.logger.info("Upper Theshold: " + str(self.upperThresholdText.value))
    self.logger.info("Gaussian Sigma: " + str(self.sigmaText.value))
    self.logger.info("Number of Bones: " + str(self.boneNumSpinBox.value))
    self.logger.info("Dilate/Erode Radius: " + str(self.dilateErodeRadiusText.value))

    if self.threshButton.checked:
      ready = self._logic.setParameters(inputVolumeNode,
                                     outputVolumeNode,
                                     self.sigmaText.value,
                                     self.boneNumSpinBox.value,
                                     self.dilateErodeRadiusText.value,
                                     separateMapNode,
                                     method=self.threshSelector.currentIndex,)
    else:
      ready = self._logic.setParameters(inputVolumeNode,
                                     outputVolumeNode,
                                     self.sigmaText.value,
                                     self.boneNumSpinBox.value,
                                     self.dilateErodeRadiusText.value,
                                     separateMapNode,
                                     lower=self.lowerThresholdText.value,
                                     upper=self.upperThresholdText.value)
    if ready:
      # run the algorithm
      success = self._logic.getMask(inputVolumeNode, outputVolumeNode, self.algorithmSelector.currentIndex)
      if success:
        # update widgets
        self.maskVolumeSelector.setCurrentNodeID(self.outputVolumeSelector.currentNodeID)
        print(outputVolumeNode.GetDisplayNode().GetName())
        self.masterVolumeSelector.setCurrentNodeID(self.inputVolumeSelector.currentNodeID)
        self.outputVolumeSelector.setCurrentNodeID("") # reset the output volume selector
    # update widgets
    self.enableAutoMaskWidgets()

    # store thresholds
    inputVolumeNode.__dict__["Lower"] = self.lowerThresholdText.value
    inputVolumeNode.__dict__["Upper"] = self.upperThresholdText.value
    self.logger.info("Finished\n")

  def onInitButton3(self):
    """Run this whenever the initialize button in step 3 is clicked"""
    maskVolumeNode = self.maskVolumeSelector.currentNode()
    masterVolumeNode = self.masterVolumeSelector.currentNode()

    if(self.maskVolumeSelector.enabled):

      print(maskVolumeNode.GetNumberOfDisplayNodes())  
      success = self._logic.initManualCorrection(self.segmentEditor3,
                                              None,
                                              maskVolumeNode,
                                              masterVolumeNode)

    if success:
      self.enableManualCorrectionWidgets()

  def onCancelButton3(self):
    """Run this whenever the cancel button in step 3 is clicked"""
    if slicer.util.confirmOkCancelDisplay('Do you want to discard the manual correction?'):
      maskVolumeNode = self.maskVolumeSelector.currentNode()
      masterVolumeNode = self.masterVolumeSelector.currentNode()

      self._logic.cancelManualCorrection(maskVolumeNode, masterVolumeNode)

      self.disableManualCorrectionWidgets()

  def onApplyButton3(self):
    """Run this whenever the apply button in step 3 is clicked"""
    maskVolumeNode = self.maskVolumeSelector.currentNode()
    masterVolumeNode = self.masterVolumeSelector.currentNode()

    self._logic.applyManualCorrection(maskVolumeNode, masterVolumeNode)

    self.disableManualCorrectionWidgets()

  def enableBoneSeparationWidgets(self):
    """Enable widgets in the bone separation layout in step 1"""
    self.initButton1.enabled = False
    self.cancelButton1.enabled = True
    self.applyButton1.enabled = True
    self.deleteButton1.enabled = True
    self.eraseBetweenSlicesButton1.enabled = True
    self.applyEraseBetweenSlicesButton1.enabled = False
    self.separateInputSelector.enabled = False
    self.initButton3.enabled = False
    self.maskVolumeSelector.enabled = False
    self.masterVolumeSelector.enabled = False

  def disableBoneSeparationWidgets(self):
    """Disable widgets in the bone separation layout in step 1"""
    self.onSelect1()
    self.cancelButton1.enabled = False
    self.applyButton1.enabled = False
    self.deleteButton1.enabled = False
    self.eraseBetweenSlicesButton1.enabled = False
    self.applyEraseBetweenSlicesButton1.enabled = False
    self.separateInputSelector.enabled = True
    self.onSelect3()
    self.maskVolumeSelector.enabled = True
    self.masterVolumeSelector.enabled = True

  def enableAutoMaskWidgets(self):
    """Enable widgets in the automatic masking layout in step 2"""
    self.onSelect2()
    self.progressBar.hide()

  def disableAutoMaskWidgets(self):
    """Disable widgets in the automatic masking layout in step 2"""
    self.getMaskButton.enabled = False
    self.progressBar.show()

  def enableManualCorrectionWidgets(self):
    """Enable widgets in the manual correction layout in step 3"""
    self.initButton1.enabled = False
    self.separateInputSelector.enabled = False
    self.initButton3.enabled = False
    self.cancelButton3.enabled = True
    self.applyButton3.enabled = True
    self.deleteButton3.enabled = True
    self.eraseBetweenSlicesButton3.enabled = True
    self.maskVolumeSelector.enabled = False
    self.masterVolumeSelector.enabled = False

  def disableManualCorrectionWidgets(self):
    """Disable widgets in the manual correction layout in step 3"""
    self.onSelect1()
    self.separateInputSelector.enabled = True
    self.onSelect3()
    self.cancelButton3.enabled = False
    self.applyButton3.enabled = False
    self.deleteButton1.enabled = False
    self.eraseBetweenSlicesButton1.enabled = False
    self.maskVolumeSelector.enabled = True
    self.masterVolumeSelector.enabled = True

  def setProgress(self, value):
    """Update the progress bar"""
    self.progressBar.setValue(value)

class AutoMaskTest(ScriptedLoadableModuleTest):
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
    self.test_AutoMask()
    #self.test_AutoMaskFailure()

  def test_AutoMask(self):
    '''
    Automatic Mask Tests: Runs the mask function on 3 sample images and compares the results to masks generated in IPL

    Test Requires:

      mha files: 'SAMPLE_MHA1.mha', 'SAMPLE_MHA2.mha', 'SAMPLE_MHA3.mha'
      comparison masks: 'SAMPLE_MASK1.mha', 'SAMPLE_MASK2.mha', 'SAMPLE_MASK3.mha'

    Success Conditions:
      1. Mask mask is successfully generated
      2. Output mask mask differs by less than 2% from the comparison mask
    '''
    from Testing.AutoMaskTestLogic import AutoMaskTestLogic
    from AutoMaskLib.AutoMaskLogic import AutoMaskLogic

    self.delayDisplay("Starting the test")
    #
    # first, get some data
    #

    # get test file

    # setup logic
    logic = AutoMaskLogic()
    testLogic = AutoMaskTestLogic()

    scene = slicer.mrmlScene

    # run 3 tests
    passed = True
    for i in range(1, 4):
      index = str(i)
      print('\n*----------------------Test ' + index + '----------------------*')

      # setup input volume
      inputVolume = testLogic.newNode(scene, filename='SAMPLE_MHA' + index + '.mha', name='testInputVolume' + index)

      # generate mask with default settings
      outputVolume = testLogic.newNode(scene, name='testOutputVolume' + index, type='labelmap')
      logic.setParameters(inputVolume, outputVolume, 2, 1, 38, None, lower=686, upper=4000)
      self.assertTrue(logic.getMask(inputVolume, outputVolume, noProgress=True), "Mask operation failed")

      # verify mask with comparison
      if not testLogic.verifyMask(outputVolume, i):
        self.delayDisplay('Output mask is incorrect', msec = 300)
        passed = False
        continue

      self.delayDisplay('Test ' + index + ' complete')

    # failure message
    self.assertTrue(passed, 'Incorrect results, check testing log')

    return SUCCESS

  def test_AutoMaskFailure(self):
    from Testing.AutoMaskTestLogic import AutoMaskTestLogic
    from AutoMaskLib.AutoMaskLogic import AutoMaskLogic

    slicer.util.infoDisplay('Several errors will display during this test.\nFollow the test log to determine test success.')

    #setup scene
    logic = AutoMaskLogic()
    testLogic = AutoMaskTestLogic()

    #setup nodes
    scene = slicer.mrmlScene
    a = testLogic.newNode(scene, filename='FAIL_MHA.mha', name='node1')
    b = testLogic.newNode(scene, type = 'labelmap', name = 'node4')

    #attempt to set invalid parameters
    self.assertFalse(logic.setParameters(a, b, 6860, 4000, 0.8, 1, 48, None), 'Masking does not check if lower threshold is greater than upper threshold')
    self.assertFalse(logic.setParameters(a, a, 686, 4000, 0.8, 1, 48, None), 'Masking does not check if output volume is the same as segment volume')

    #get breaks with image which will fail
    self.assertFalse(logic.getMask(a, b, noProgress=True), 'Masking does not fail when no inputs are set')

    logic.setParameters(a, b, 686, 4000, 0.8, 1, 48, None)
    self.assertTrue(logic.getMask(a, b, noProgress=True), 'Masking should not fail despite no results being generated')


    self.delayDisplay('Test passed')