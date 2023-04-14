#-----------------------------------------------------
# Training.py
#
# Created by:  Yousif Al-Khoury
# Created on:  12-12-2022
#
# Description: This module sets up the interface for the Erosion Volume 3D Slicer extension.
#
#-----------------------------------------------------
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
from TrainingLib.ErosionVolumeLogic import ErosionVolumeLogic
from TrainingLib.MarkupsTable import MarkupsTable
import os

import SimpleITK as sitk
import sitkUtils

#
# ErosionVolume
#
class Training(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Training" # TODO make this more human readable by adding spaces
    self.parent.categories = ["Bone Analysis Module (BAM)"]
    self.parent.dependencies = []
    self.parent.contributors = ["Yousif Al-Khoury"] # replace with "Firstname Lastname (Organization)"
    self.parent.helpText = """ 
TODO
"""
    self.parent.helpText += "<br>For more information see the <a href=https://github.com/ManskeLab/3DSlicer_Erosion_Analysis/wiki/Erosion-Volume-Module>online documentation</a>."
    self.parent.helpText += "<br><td><img src=\"" + self.getLogo('bam') + "\" height=80> "
    self.parent.helpText += "<img src=\"" + self.getLogo('manske') + "\" height=80></td>"
    self.parent.acknowledgementText = """
    
Updated on December 12, 2022.<br>
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
# ErosionVolumeWidget
#
class TrainingWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """
  def __init__(self, parent):
    # Initialize logics object
    self._logic = ErosionVolumeLogic()
    # initialize call back object for updating progrss bar
    self._logic.progressCallBack = self.setProgress

    self.images_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'TrainingSet')
    self.seed_points_dir = os.path.join(self.images_dir, 'CorrectSeeds')
    self.reference_erosions_dir = os.path.join(self.images_dir, 'ErosionSegs')
    self.images_dir = os.path.join(self.images_dir, 'TestFiles')

    ScriptedLoadableModuleWidget.__init__(self, parent)

  def setup(self):
    # Buttons for testing
    ScriptedLoadableModuleWidget.setup(self)

    self.warning = qt.QLabel(
      """WARNING: This module clears all current nodes in the current slicer scene, <br>
      including those worked on inside other modules. Please save your work <br>
      before pressing the 'Proceed' button below.""")
    self.layout.addWidget(self.warning)
    self.proceedButton = qt.QPushButton("Proceed")
    self.proceedButton.toolTip = "Warning before proceeding with the training module."
    self.proceedButton.setFixedSize(80, 25)
    self.layout.addWidget(self.proceedButton)
    self.proceedButton.clicked.connect(self.proceed)
    self.layout.addStretch(0)

    # slicer.mrmlScene.Clear(True)

  def proceed(self):
    self.proceedButton.deleteLater()
    self.warning.deleteLater()
    # Collapsible buttons
    self.erosionsCollapsibleButton = ctk.ctkCollapsibleButton()

    slicer.mrmlScene.Clear(False)

    for image in os.listdir(self.images_dir):
      if not ('nii.gz' in image):
        continue
      image_name = os.path.splitext(image)[0]
      image = os.path.join(self.images_dir, image)
      image = sitk.ReadImage(image)
      volume_node = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLScalarVolumeNode', image_name)
      sitkUtils.PushVolumeToSlicer(image, volume_node)

    # Set up widgets inside the collapsible buttons
    self.setupErosions()

    # Add vertical spacer
    self.layout.addStretch(1)

    # Update buttons
    self.checkErosionsButton()
    self.onSelectInputVolume()

  def setupErosions(self):
    """Set up widgets in step 4 erosions"""
    # Set text on collapsible button, and add collapsible button to layout
    self.erosionsCollapsibleButton.text = "Training"
    self.layout.addWidget(self.erosionsCollapsibleButton)

    # Layout within the collapsible button
    erosionsLayout = qt.QFormLayout(self.erosionsCollapsibleButton)
    erosionsLayout.setVerticalSpacing(5)

    # input volume selector
    self.inputVolumeSelector = slicer.qMRMLNodeComboBox()
    self.inputVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.inputVolumeSelector.selectNodeUponCreation = False
    self.inputVolumeSelector.addEnabled = False
    self.inputVolumeSelector.renameEnabled = True
    self.inputVolumeSelector.removeEnabled = True
    self.inputVolumeSelector.noneEnabled = False
    self.inputVolumeSelector.showHidden = False
    self.inputVolumeSelector.showChildNodeTypes = False
    self.inputVolumeSelector.setMRMLScene(slicer.mrmlScene)
    self.inputVolumeSelector.setToolTip( "Pick the greyscale scan" )
    self.inputVolumeSelector.setCurrentNode(None)
    erosionsLayout.addRow("Input Volume: ", self.inputVolumeSelector)

    # input mask selector
    self.inputMaskSelector = slicer.qMRMLNodeComboBox()
    self.inputMaskSelector.nodeTypes = ["vtkMRMLScalarVolumeNode","vtkMRMLLabelMapVolumeNode"]
    self.inputMaskSelector.selectNodeUponCreation = False
    self.inputMaskSelector.addEnabled = False
    self.inputMaskSelector.renameEnabled = True
    self.inputMaskSelector.removeEnabled = True
    self.inputMaskSelector.noneEnabled = False
    self.inputMaskSelector.showHidden = False
    self.inputMaskSelector.showChildNodeTypes = False
    self.inputMaskSelector.setMRMLScene(slicer.mrmlScene)
    self.inputMaskSelector.setToolTip( "Pick the mask label map" )
    self.inputMaskSelector.setCurrentNode(None)
    erosionsLayout.addRow("Input Mask: ", self.inputMaskSelector)

    # output volume selector
    self.outputErosionSelector = slicer.qMRMLNodeComboBox()
    self.outputErosionSelector.nodeTypes = ["vtkMRMLSegmentationNode"]
    self.outputErosionSelector.selectNodeUponCreation = True
    self.outputErosionSelector.addEnabled = True
    self.outputErosionSelector.removeEnabled = True
    self.outputErosionSelector.renameEnabled = True
    self.outputErosionSelector.noneEnabled = False
    self.outputErosionSelector.showHidden = False
    self.outputErosionSelector.showChildNodeTypes = False
    self.outputErosionSelector.setMRMLScene(slicer.mrmlScene)
    self.outputErosionSelector.baseName = "ER"
    self.outputErosionSelector.setToolTip( "Pick the output segmentation to store the erosions in" )
    self.outputErosionSelector.setCurrentNode(None)
    erosionsLayout.addRow("Output Erosions: ", self.outputErosionSelector)

    # threshold spin boxes (default unit is HU)
    self.lowerThresholdText = qt.QSpinBox()
    self.lowerThresholdText.setMinimum(-9999)
    self.lowerThresholdText.setMaximum(999999)
    self.lowerThresholdText.setSingleStep(10)
    self.lowerThresholdText.value = 850
    erosionsLayout.addRow("Lower Threshold: ", self.lowerThresholdText)
    self.upperThresholdText = qt.QSpinBox()
    self.upperThresholdText.setMinimum(-9999)
    self.upperThresholdText.setMaximum(999999)
    self.upperThresholdText.setSingleStep(10)
    self.upperThresholdText.value = 9999
    erosionsLayout.addRow("Upper Threshold: ", self.upperThresholdText)

    # gaussian sigma spin box
    self.sigmaText = qt.QDoubleSpinBox()
    self.sigmaText.setMinimum(0.0001)
    self.sigmaText.setDecimals(4)
    self.sigmaText.value = 1
    self.sigmaText.setToolTip("Standard deviation in the Gaussian smoothing filter")
    erosionsLayout.addRow("Gaussian Sigma: ", self.sigmaText)

    # seed point table
    self.markupsTableWidget = MarkupsTable(self.erosionsCollapsibleButton)
    self.markupsTableWidget.setMRMLScene(slicer.mrmlScene)
    self.markupsTableWidget.setNodeSelectorVisible(True) # use the above selector instead
    self.markupsTableWidget.setButtonsVisible(False)
    self.markupsTableWidget.setPlaceButtonVisible(True)
    self.markupsTableWidget.setDeleteAllButtonVisible(True)
    self.markupsTableWidget.setJumpToSliceEnabled(True)

    # horizontal white space
    erosionsLayout.addRow(qt.QLabel(""))

    # check box for Large erosions
    self.LargeErosionsCheckBox = qt.QCheckBox('Large Erosions')
    self.LargeErosionsCheckBox.checked = False
    self.LargeErosionsCheckBox.setToolTip('Set internal parameters for segmenting large erosions')
    erosionsLayout.addRow(self.LargeErosionsCheckBox)

    # check box for CBCT scans
    self.SmallErosionsCheckBox = qt.QCheckBox('Small Erosions')
    self.SmallErosionsCheckBox.checked = False
    self.SmallErosionsCheckBox.setToolTip('Set internal parameters for segmenting small erosions')
    erosionsLayout.addRow(self.SmallErosionsCheckBox)

    # glyph size 
    self.glyphSizeBox = qt.QDoubleSpinBox()
    self.glyphSizeBox.setMinimum(0.5)
    self.glyphSizeBox.setMaximum(25)
    self.glyphSizeBox.setSingleStep(0.5)
    self.glyphSizeBox.setSuffix(' %')
    self.glyphSizeBox.value = 1.0
    erosionsLayout.addRow("Seed Point Size ", self.glyphSizeBox)

    # advanced parameter spin boxes
    self.minimalRadiusText = 3
    self.dilateErodeDistanceText = 4

    # Execution layout
    executeGridLayout = qt.QGridLayout()
    executeGridLayout.setRowMinimumHeight(0,15)
    executeGridLayout.setRowMinimumHeight(1,15)

    # Progress Bar
    self.progressBar = qt.QProgressBar()
    self.progressBar.hide()
    executeGridLayout.addWidget(self.progressBar, 0, 0)

    # Get Erosion Button
    self.getErosionsButton = qt.QPushButton("Get Erosions")
    self.getErosionsButton.toolTip = "Get erosions stored in a label map"
    self.getErosionsButton.enabled = False
    executeGridLayout.addWidget(self.getErosionsButton, 1, 0)

    # Reveal Correct Seed Points Button
    self.revealSeedPointsButton = qt.QPushButton("Reveal Correct Seed Points")
    self.revealSeedPointsButton.toolTip = "Display expected seed points that identify erosions for this scan"
    self.revealSeedPointsButton.enabled = False
    executeGridLayout.addWidget(self.revealSeedPointsButton, 2, 0)

    # Execution frame with progress bar and get button
    erosionButtonFrame = qt.QFrame()
    erosionButtonFrame.setLayout(executeGridLayout)
    erosionsLayout.addRow(erosionButtonFrame)
    
    # connections
    self.inputVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.checkErosionsButton)
    self.inputVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelectInputVolume)
    self.inputMaskSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelectInputMask)
    self.inputMaskSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.checkErosionsButton)
    self.outputErosionSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.checkErosionsButton)
    self.outputErosionSelector.connect("nodeAddedByUser(vtkMRMLNode*)", lambda node: self.onAddOutputErosion(node))
    self.markupsTableWidget.getMarkupsSelector().connect("currentNodeChanged(vtkMRMLNode*)", self.checkErosionsButton)
    self.markupsTableWidget.getMarkupsSelector().connect("currentNodeChanged(vtkMRMLNode*)", self.onSelectSeed)
    self.LargeErosionsCheckBox.connect("clicked(bool)", self.onLargeErosionsChecked)
    self.SmallErosionsCheckBox.connect("clicked(bool)", self.onSmallErosionsChecked)
    self.glyphSizeBox.valueChanged.connect(self.onGlyphSizeChanged)
    self.getErosionsButton.connect("clicked(bool)", self.onGetErosionsButton)
    self.revealSeedPointsButton.connect("clicked(bool)", self.onRevealSeedPointsButton)

    # logger
    self.logger = logging.getLogger("erosion_volume")

  def checkErosionsButton(self):
    self.getErosionsButton.enabled = (self.inputVolumeSelector.currentNode() and 
                                     self.inputMaskSelector.currentNode() and
                                     self.outputErosionSelector.currentNode() and
                                     self.markupsTableWidget.getCurrentNode())
    self.revealSeedPointsButton.enabled = (self.inputVolumeSelector.currentNode() and 
                                          self.inputMaskSelector.currentNode())

  def onSelect4(self):
    """Update the state of the get erosions button whenever the selectors in step 4 change"""
    self.getErosionsButton.enabled = (self.inputVolumeSelector.currentNode() and 
                                     self.inputMaskSelector.currentNode() and
                                     self.outputErosionSelector.currentNode() and
                                     self.markupsTableWidget.getCurrentNode())

  def onSelectInputVolume(self):
    """Run this whenever the input volume selector in step 4 changes"""
    inputVolumeNode = self.inputVolumeSelector.currentNode()
    inputMaskNode = self.inputMaskSelector.currentNode()

    if inputVolumeNode:
      # Update the default save directory
      self._logic.setDefaultDirectory(inputVolumeNode)

      # Update the spacing scale in the seed point table
      ras2ijk = vtk.vtkMatrix4x4()
      ijk2ras = vtk.vtkMatrix4x4()
      inputVolumeNode.GetRASToIJKMatrix(ras2ijk)
      inputVolumeNode.GetIJKToRASMatrix(ijk2ras)
      self.markupsTableWidget.setCoordsMatrices(ras2ijk, ijk2ras)
      # update the viewer windows
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
      if check:
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
      except:
        filename = 'share/' + inputVolumeNode.GetName() + '.'
      logHandler = logging.FileHandler(filename)
      
      self.logger.addHandler(logHandler)
      self.logger.info("Using Erosion Volume Module with " + inputVolumeNode.GetName() + "\n")
      

  def onSelectInputMask(self):
    """Run this whenever the input mask selector in step 4 changes"""
    inputMaskNode = self.inputMaskSelector.currentNode()
    if inputMaskNode:
      # update the default output erosion base name, which matches the mask name
      erosion_baseName = inputMaskNode.GetName()+"_ER"
      self.outputErosionSelector.baseName = erosion_baseName
      seed_baseName = inputMaskNode.GetName()+"_SEEDS"
      # self.fiducialSelector.baseName = seed_baseName
      # self.outputTableSelector.baseName = inputMaskNode.GetName()+"_TABLE"
      

  def onAddOutputErosion(self, node):
    """Run this whenever a new erosion segmentation is created from the selector in step 4"""
    # force the output erosion base name to have the post fix '_' plus an index
    #  i.e. baseName_1, baseName_2, ...
    baseName = node.GetName()
    index_str = baseName.split('_')[-1]
    if not index_str.isdigit(): # not postfixed with '_' plus an index
      node.SetName(slicer.mrmlScene.GenerateUniqueName(baseName))

  def onSelectSeed(self):
    """Run this whenever the seed point selector in step 4 changes"""
    self.markupsTableWidget.onMarkupsNodeChanged()
    markupsDisplayNode = self.markupsTableWidget.getCurrentNode().GetMarkupsDisplayNode()
    markupsDisplayNode.SetGlyphScale(self.glyphSizeBox.value)

  def onLargeErosionsChecked(self):
    """Run this whenever the check box for Large Erosions in step 4 changes"""
    if self.LargeErosionsCheckBox.checked:
      self.minimalRadiusText = 6
      self.dilateErodeDistanceText = 6
      self.SmallErosionsCheckBox.checked = False
    else:
      self.minimalRadiusText = 3
      self.dilateErodeDistanceText = 4

  def onSmallErosionsChecked(self):
    """Run this whenever the check box for Small Erosions in step 4 changes"""
    if self.SmallErosionsCheckBox.checked:
      self.minimalRadiusText = 2
      self.dilateErodeDistanceText = 3
      self.LargeErosionsCheckBox.checked = False
    else:
      self.minimalRadiusText = 3
      self.dilateErodeDistanceText = 4
  
  def onGlyphSizeChanged(self):
    markupsDisplayNode = self.markupsTableWidget.getCurrentNode().GetMarkupsDisplayNode()
    markupsDisplayNode.SetGlyphScale(self.glyphSizeBox.value)

  def onGetErosionsButton(self):
    """Run this whenever the get erosions button in step 4 is clicked"""
    # update widgets
    self.disableErosionsWidgets()
    # self.markupsTableWidget.updateLabels()

    inputVolumeNode = self.inputVolumeSelector.currentNode()
    inputMaskNode = self.inputMaskSelector.currentNode()
    outputVolumeNode = self.outputErosionSelector.currentNode()
    markupsNode = self.markupsTableWidget.getCurrentNode()

    self.logger.info("Erosion Volume initialized with parameters:")
    self.logger.info("Input Volume: " + inputVolumeNode.GetName())
    self.logger.info("Input Mask: " + inputMaskNode.GetName())
    self.logger.info("Output Volume: " + outputVolumeNode.GetName())
    
    self.logger.info("Lower Theshold: " + str(self.lowerThresholdText.value))
    self.logger.info("Upper Theshold: " + str(self.upperThresholdText.value))
    self.logger.info("Gaussian Sigma: " + str(self.sigmaText.value))
    
    ready = self._logic.setErosionParameters(inputVolumeNode, 
                                          inputMaskNode, 
                                          self.sigmaText.value,
                                          # fiducialNode,
                                          markupsNode,
                                          self.minimalRadiusText,
                                          self.dilateErodeDistanceText,
                                          lower=self.lowerThresholdText.value,
                                          upper=self.upperThresholdText.value)
    if ready:
      success = self._logic.getErosions(inputVolumeNode, inputMaskNode, outputVolumeNode)
      error_message = ""
      error_flag = None

      # update widgets
      erosion_id = outputVolumeNode.GetName()[0]
      reference_path = None

      for reference in os.listdir(self.reference_erosions_dir):
        if(erosion_id == reference[0]):
          reference_path = os.path.join(self.reference_erosions_dir, reference)

      if(reference_path):
        num_control_points = markupsNode.GetNumberOfControlPoints()
        num_erosions = 0
        vol_map = {}
        ref_vol_map = {}

        labels = []

        erosion_reference = sitk.ReadImage(reference_path)

        labelShape = sitk.LabelShapeStatisticsImageFilter()

        labelShape.Execute(erosion_reference)
        ref_num_erosions = labelShape.GetNumberOfLabels()
        labels_ref = labelShape.GetLabels()
        
        for i in labels_ref:
          ref_vol_map[i] = labelShape.GetNumberOfPixels(i)

        spacing = erosion_reference.GetSpacing()
        origin = erosion_reference.GetOrigin()

        if success:
          volumeNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLabelMapVolumeNode')
          self._logic.exportErosionsToLabelmap(outputVolumeNode, volumeNode) 
          erosion = sitkUtils.PullVolumeFromSlicer(volumeNode)
          # sitk.WriteImage(erosion, reference_path)

          labelShape.Execute(erosion)
          num_erosions = labelShape.GetNumberOfLabels()
          labels = labelShape.GetLabels()
          
          for i in labels:
            vol_map[i] = labelShape.GetNumberOfPixels(i)  

        # label map to tell if labeled erosion volume is too small or too big. (False, True)
        size_map = {}

        # mapper
        mapped_labels = {}
        print(ref_vol_map)
        print(vol_map)

        for i in range(num_control_points):

          id = int(markupsNode.GetNthControlPointID(i))
          seed_pos = [round(ax) for ax in self.markupsTableWidget.getNthControlPointIJKCoords(i)]

          # for ax in range(3):
          #   x = float(control_point_vector[ax]-origin[ax])
          #   print(x)
          #   print(x/float(spacing[ax]))
          #   seed_pos[ax] = int(abs(round(float(control_point_vector[ax]+origin[ax])/float(spacing[ax]))))
          #   print(seed_pos[ax])

          print(seed_pos)
          mapped_labels[id] = None
          
          voxel_val = erosion_reference.GetPixel(seed_pos)
          comp_voxel_val = erosion.GetPixel(seed_pos)
          print(voxel_val)

          if voxel_val > 0:
            if voxel_val in mapped_labels.values():
              # duplicate
              mapped_labels[id] = False
              continue

            mapped_labels[id] = voxel_val
            if comp_voxel_val != 0:
              if vol_map[id] > ref_vol_map[voxel_val]:
                size_map[id] = True
              else:
                size_map[id] = False
        
        feedback = ""
        error_flag = num_control_points > num_erosions or num_control_points != ref_num_erosions
        sim_flag = False

        filter = sitk.SimilarityIndexImageFilter()
        if success:
          erosion = sitk.Cast(erosion, sitk.sitkFloat32)
          erosion_reference = sitk.Cast(erosion_reference, sitk.sitkFloat32)

          resampler = sitk.ResampleImageFilter()
          resampler.SetReferenceImage(erosion_reference)
          resampler.SetInterpolator(sitk.sitkLinear)
          resampler.SetDefaultPixelValue(0)
          resampler.SetTransform(sitk.Transform())
          erosion = resampler.Execute(erosion)

        for i in range(num_control_points):
          label = int(markupsNode.GetNthControlPointID(i))

          feedback += "\nFeedback for Seed #{}:\n".format(i+1)

          if(mapped_labels[label] is None):
            sim_flag = True
            error_flag = True
            feedback += "No erosion should exist at this location. Please remove/relocate this seed point.\n"
          elif(not mapped_labels[label]):
            sim_flag = True
            feedback += "Seedpoint identifies the same erosion identified by another erosion."
          elif(label not in labels):
            error_flag = True
            feedback += "No erosion was detected at this location. But an erosion location was correctly identified."
            feedback += "- Reposition seed point to be located deeper into the erosion.\n"
            feedback += "- Make sure the seed point is located within the mask.\n"
            feedback += "- Enable the small erosions check box.\n"
            feedback += "- Increase the lower threshold in increments of 50.\n"
            feedback += "Please attempt the 3rd and 4th suggestion individually at first.\n"
            feedback += "This means trying to enable the small erosions check box then if that\n"
            feedback += "doesnt work, then try to increase the lower threshold in 50 increments.\n"
            feedback += "When increasing the threshold. Note if your, similarity indexes are increasing or not.\n"
            feedback += "If they are, then you are on the right path."
          else:
            bin_erosion = erosion == label
            bin_erosion_ref = erosion_reference == mapped_labels[label]

            filter.Execute(bin_erosion, bin_erosion_ref)
            similarity_index = filter.GetSimilarityIndex()

            feedback += "Similarity index to refence: {0:.3f}%\n".format(similarity_index*100)
            if similarity_index > 0.9:
              feedback += "Correctly identified erosion!\n"
            else:
              error_flag = True
              sim_flag = True
              
              feedback += "Erosions exists at this location but further actions needed to improve results:\n"
              feedback += "- Reposition seed point to be located deeper within the erosion.\n"
              if size_map[label]:
                feedback += "- Computed erosion is too big:\n"
                if not self.SmallErosionsCheckBox.checked:
                  feedback += "   - Enable large erosions check box.\n"
                else:
                  feedback += "   - Disable small erosions check box.\n"
                feedback += "   - Decrease lower threshold in 50 decrements.\n"
                feedback += "Please attempt the suggestions individually at first.\n"
                feedback += "This means trying to enable the large erosions check box then if that\n"
                feedback += "doesnt work, then try to decrease the lower threshold in 50 increments.\n"
                feedback += "When decreasing the threshold. Note if your, similarity indexes are increasing or not.\n"
                feedback += "If they are, then you are on the right path."
              else:
                feedback += "- Computed erosion is too small:\n"
                if not self.LargeErosionsCheckBox.checked:
                  feedback += "   - Enable small erosions check box.\n"
                else:
                  feedback += "   - Disable large erosions check box.\n"
                feedback += "   - Increase lower threshold in 50 increments.\n"
                feedback += "Please attempt the 3rd and 4th suggestion individually at first.\n"
                feedback += "This means trying to enable the small erosions check box then if that\n"
                feedback += "doesnt work, then try to increase the lower threshold in 50 increments.\n"
                feedback += "When increasing the threshold. Note if your, similarity indexes are increasing or not.\n"
                feedback += "If they are, then you are on the right path."

          feedback += "\n"

        if error_flag:
          error_message += "Error!\n\n"
          
          if(num_erosions == 0):
            error_message += "No erosions detected at any placed seed point/s.\n"

          elif(num_control_points > num_erosions):
            error_message += "Erosions were not detected at all placed seed point/s.\n"

          if(num_control_points == ref_num_erosions):
            if(sim_flag):
              error_message += "Correct number of seed points placed, but the locations are incorrect. See below for feedback on each placed seed point.\n" 
            else:
              error_message += "Correct number of seed points placed. See below for feedback on each placed seed point.\n"

          if(num_control_points > ref_num_erosions):
            error_message += "Too many seed points were placed. Only {} point/s needed. Delete {} point/s.\n".format(ref_num_erosions, num_control_points-ref_num_erosions)
          
          if(num_control_points < ref_num_erosions):
            error_message += "Less seed points were placed than the number of erosions that exist in the reference. Please place {} more seed point/s.\n".format(ref_num_erosions - num_control_points)
        else:
          error_message += "Success!\n"

        error_message += "\n"

        error_message += feedback

      self.outputErosionSelector.setCurrentNodeID("") # reset the output volume selector

      if(error_flag):
        slicer.util.errorDisplay(error_message, 'Incorrect Erosion Analysis')
      else:
        slicer.util.infoDisplay(error_message, 'Seed Point Feedback')
            
    # store thresholds 
    inputVolumeNode.__dict__["Lower"] = self.lowerThresholdText.value
    inputVolumeNode.__dict__["Upper"] = self.upperThresholdText.value

    # update widgets
    self.enableErosionsWidgets()

    self.logger.info("Finished\n")

  def onRevealSeedPointsButton(self):
    image_id = self.inputVolumeSelector.currentNode().GetName()[0]

    for markup in os.listdir(self.seed_points_dir):
      if not (image_id == markup[0]):
        continue
      markup = os.path.join(self.seed_points_dir, markup)
      markupsNode = slicer.util.loadMarkups(markup)
      self.markupsTableWidget.getMarkupsSelector().setCurrentNode(markupsNode)

  def enableErosionsWidgets(self):
    """Enable widgets in the erosions layout in step 4"""
    self.checkErosionsButton()
    self.progressBar.hide()

  def disableErosionsWidgets(self):
    """Disable widgets in the erosions layout in step 4"""
    self.getErosionsButton.enabled = False
    self.progressBar.show()

  def setProgress(self, value):
    """Update the progress bar"""
    self.progressBar.setValue(value)
