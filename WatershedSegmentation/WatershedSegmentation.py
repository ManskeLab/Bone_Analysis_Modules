#-----------------------------------------------------
# WatershedSegmentation.py
#
# Created by:  Ryan Yan
# Created on:  18-04-2022
#
# Description: This module sets up the interface for the Watershed Segmentation 3D Slicer extension.
#              Currently also contains logic, should be moved to a separate class upon release
#
#-----------------------------------------------------

import os
import unittest
from __main__ import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import sitkUtils
from WatershedSegmentationLib.MarkupsTable import MarkupsTable

import SimpleITK as sitk

class WatershedSegmentation(ScriptedLoadableModule):

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Watershed Segmentation" # TODO make this more human readable by adding spaces
    self.parent.categories = ["Bone Analysis Module (BAM)"]
    self.parent.dependencies = []
    self.parent.contributors = ["Ryan Yan"] # replace with "Firstname Lastname (Organization)"
    self.parent.helpText = """
    """
    self.parent.acknowledgementText = """
""" # replace with organization, grant and thanks.


class WatershedSegmentationWidget(ScriptedLoadableModuleWidget):
  """
  """
  def __init__(self, parent):

    ScriptedLoadableModuleWidget.__init__(self, parent)

  def setup(self) -> None:
    '''Setup Registration widget'''
    ScriptedLoadableModuleWidget.setup(self)
    # Instantiate and connect widgets ...

    
    self.collapsibleButton = ctk.ctkCollapsibleButton()
    self.collapsibleButton.text = "Watershed"
    formLayout = qt.QFormLayout(self.collapsibleButton)
    formLayout.setVerticalSpacing(5)
    self.layout.addWidget(self.collapsibleButton)

    # Help button
    self.helpButton = qt.QPushButton("Help")
    self.helpButton.toolTip = "Generate the watershed image"
    formLayout.addRow("", self.helpButton)
    self.helpButton.clicked.connect(self.help)

    # First input volume selector
    self.inputSelector1 = slicer.qMRMLNodeComboBox()
    self.inputSelector1.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.inputSelector1.selectNodeUponCreation = True
    self.inputSelector1.addEnabled = False
    self.inputSelector1.removeEnabled = False
    self.inputSelector1.noneEnabled = False
    self.inputSelector1.showHidden = False
    self.inputSelector1.showChildNodeTypes = False
    self.inputSelector1.setMRMLScene( slicer.mrmlScene )
    self.inputSelector1.setToolTip( "Select the baseline image" )
    self.inputSelector1.setCurrentNode(None)
    formLayout.addRow("Input", self.inputSelector1)


    # Output volume selector for gradient image
    self.outputSelector = slicer.qMRMLNodeComboBox()
    self.outputSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.outputSelector.selectNodeUponCreation = True
    self.outputSelector.addEnabled = True
    self.outputSelector.renameEnabled = True
    self.outputSelector.removeEnabled = True
    self.outputSelector.noneEnabled = False
    self.outputSelector.showHidden = False
    self.outputSelector.showChildNodeTypes = False
    self.outputSelector.baseName = 'GRADIENT'
    self.outputSelector.setMRMLScene( slicer.mrmlScene )
    self.outputSelector.setToolTip( "Select the output gradient image" )
    self.outputSelector.setCurrentNode(None)
    formLayout.addRow("Gradient", self.outputSelector)

    # Output volume selector for watershed
    self.outputSelector2 = slicer.qMRMLNodeComboBox()
    self.outputSelector2.nodeTypes = ["vtkMRMLLabelMapVolumeNode"]
    self.outputSelector2.selectNodeUponCreation = True
    self.outputSelector2.addEnabled = True
    self.outputSelector2.renameEnabled = True
    self.outputSelector2.removeEnabled = True
    self.outputSelector2.noneEnabled = True
    self.outputSelector2.showHidden = False
    self.outputSelector2.showChildNodeTypes = False
    self.outputSelector2.baseName = 'WATERSHED'
    self.outputSelector2.setMRMLScene( slicer.mrmlScene )
    self.outputSelector2.setToolTip( "Select the output watershed image" )
    self.outputSelector2.setCurrentNode(None)
    formLayout.addRow("Watershed", self.outputSelector2)


    # gaussian sigma spin box
    self.basinsText = qt.QSpinBox()
    self.basinsText.setMaximum(10000)
    self.basinsText.value = 300
    self.basinsText.setToolTip("Number of basins used in the watershed filter")
    formLayout.addRow("Basins: ", self.basinsText)

    # gaussian sigma spin box
    self.sigmaText = qt.QDoubleSpinBox()
    self.sigmaText.setDecimals(1)
    self.sigmaText.setMaximum(10)
    self.sigmaText.value = 5
    self.sigmaText.setToolTip("Standard deviation in the Gaussian smoothing filter")
    formLayout.addRow("Gaussian Sigma: ", self.sigmaText)

    # Generate watershed button
    self.watershedButton = qt.QPushButton("Create Watershed")
    self.watershedButton.toolTip = "Generate the watershed image"
    formLayout.addRow("", self.watershedButton)
    self.watershedButton.clicked.connect(self.watershed)

    formLayout.addRow(qt.QLabel(""))

    # seed point table
    self.markupsTableWidget = MarkupsTable(self.collapsibleButton)
    self.markupsTableWidget.setMRMLScene(slicer.mrmlScene)
    self.markupsTableWidget.setNodeSelectorVisible(True) 
    self.markupsTableWidget.setButtonsVisible(False)
    self.markupsTableWidget.setPlaceButtonVisible(True)
    self.markupsTableWidget.setDeleteAllButtonVisible(True)
    self.markupsTableWidget.setJumpToSliceEnabled(True)

    # Output volume selector for final mask
    self.outputSelector3 = slicer.qMRMLNodeComboBox()
    self.outputSelector3.nodeTypes = ["vtkMRMLLabelMapVolumeNode"]
    self.outputSelector3.selectNodeUponCreation = True
    self.outputSelector3.addEnabled = True
    self.outputSelector3.renameEnabled = True
    self.outputSelector3.removeEnabled = True
    self.outputSelector3.noneEnabled = True
    self.outputSelector3.showHidden = False
    self.outputSelector3.showChildNodeTypes = False
    self.outputSelector3.baseName = 'MASK'
    self.outputSelector3.setMRMLScene( slicer.mrmlScene )
    self.outputSelector3.setToolTip( "Select the image for the final mask" )
    self.outputSelector3.setCurrentNode(None)
    formLayout.addRow("Final Mask", self.outputSelector3)

    # Dilate erode radius value
    self.radiusText = qt.QSpinBox()
    self.radiusText.setMinimum(1)
    self.radiusText.setMaximum(10)
    self.radiusText.value = 2
    self.radiusText.setToolTip("Radius to dilate and erode the image")
    formLayout.addRow("Dilate/Erode Radius: ", self.radiusText)

    # Help button for similarity metrics
    self.maskButton = qt.QPushButton("Create Mask")
    self.maskButton.toolTip = "Description of each image similarity metric"
    formLayout.addRow("", self.maskButton)
    self.maskButton.clicked.connect(self.create_mask)

    self.layout.addStretch(1)

  def help(self):
    text = """Watershed Segmentation Instructions\n
1. Generate a watershed of the grayscale image. Adjust settings if needed. Note that increasing the basins will decrease the number of regions in the watershed.\n
2. Place seed points in regions that are to be excluded from the final mask.\n
3. Generate the contour mask using the watershed and seed points."""
    slicer.util.infoDisplay(text)

  def watershed(self):
    #get image
    img = sitkUtils.PullVolumeFromSlicer(self.inputSelector1.currentNode())
    spacing = img.GetSpacing()

    print("Generating Watershed Image")
    
    #get gaussian gradient of image
    gauss_img = sitk.GradientMagnitudeRecursiveGaussian(img, sigma=spacing[0] * self.sigmaText.value)

    #create watershed and remove background
    ws_img = sitk.MorphologicalWatershed(gauss_img, level=self.basinsText.value, markWatershedLine=True)
    ws_img = sitk.Threshold(ws_img, lower=3, upper=100000)

    
    sitkUtils.PushVolumeToSlicer(gauss_img, self.outputSelector.currentNode())
    sitkUtils.PushVolumeToSlicer(ws_img, self.outputSelector2.currentNode())

    slicer.util.setSliceViewerLayers(label=self.outputSelector2.currentNode(), labelOpacity=0.5)

    print('Finished')

  
  def create_mask(self):
    #get watershed and points
    fid = self.markupsTableWidget.markupsSelector.currentNode()
    img = sitkUtils.PullVolumeFromSlicer(self.inputSelector1.currentNode())
    watershed = sitkUtils.PullVolumeFromSlicer(self.outputSelector2.currentNode())
    spacing = img.GetSpacing()[0]
    origin = img.GetOrigin()

    print('Creating Mask\n')

    #align fiducial values with image
    values = {}
    for i in range(fid.GetNumberOfFiducials()):
      seed = [0, 0, 0]
      fid.GetNthFiducialPosition(i, seed)
      seed_adj = [abs(round((seed[i] + origin[i]) / spacing)) for i in range(3)]
      #determine values to remove
      values[watershed.GetPixel(int(seed_adj[0]), int(seed_adj[1]), int(seed_adj[2]))] = 1
    
    print('Removed values:', values)
   

    #remove regions
    watershed = sitk.ChangeLabel(watershed, values)
    mask_raw = (watershed > 2)

    #dilate and erode image
    rad_num = self.radiusText.value
    rad = (rad_num, rad_num, rad_num)
    mask_raw = sitk.BinaryErode(sitk.BinaryDilate(mask_raw, rad), rad)
    mask_raw = sitk.BinaryFillhole(mask_raw)

    #convert to label map
    con = sitk.BinaryImageToLabelMapFilter()
    mask_img = sitk.Cast(con.Execute(mask_raw), sitk.sitkInt16)

    sitkUtils.PushVolumeToSlicer(mask_img, self.outputSelector3.currentNode())
    slicer.util.setSliceViewerLayers(label=self.outputSelector3.currentNode(), labelOpacity=0.5)

    print('Finished\n')



