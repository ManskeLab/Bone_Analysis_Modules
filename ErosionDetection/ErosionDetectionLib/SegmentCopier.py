#-----------------------------------------------------
# SegmentCopier.py
#
# Created by:  Mingjie Zhao
# Created on:  26-06-2021
#
# Description: This module contains a segmentation copier in 3D Slicer
#              that allows for copying segments between segmention nodes.
#              The segmentation copier will be added to the given qt layout.
#
#-----------------------------------------------------
from typing import ValuesView
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *

#
# SegmentEditor
#
class SegmentCopier:
  def __init__(self, parent=None):
    # Members
    self.parent = parent
    self.parameterSetNode = None

    if not parent:
      self.parent = slicer.qMRMLWidget()
      self.parent.setLayout(qt.QVBoxLayout())
      self.parent.setMRMLScene(slicer.mrmlScene)
      self.layout = self.parent.layout()
    else:
      self.parent = parent
      self.layout = parent.layout()
    self.setup()

  def setup(self):
    self.relatedUIElements = {}

    # current segmentation selector
    self.currSegmentationSelector = slicer.qMRMLNodeComboBox()
    self.currSegmentationSelector.nodeTypes = ["vtkMRMLSegmentationNode"]
    self.currSegmentationSelector.selectNodeUponCreation = True
    self.currSegmentationSelector.addEnabled = True
    self.currSegmentationSelector.removeEnabled = True
    self.currSegmentationSelector.renameEnabled = True
    self.currSegmentationSelector.noneEnabled = True
    self.currSegmentationSelector.showHidden = False
    self.currSegmentationSelector.showChildNodeTypes = False
    self.currSegmentationSelector.setMRMLScene(slicer.mrmlScene)
    self.currSegmentationSelector.setToolTip("Pick the segmentation to import from")

    # other segmentation selector
    self.otherSegmentationSelector = slicer.qMRMLNodeComboBox()
    self.otherSegmentationSelector.nodeTypes = ["vtkMRMLSegmentationNode"]
    self.otherSegmentationSelector.selectNodeUponCreation = True
    self.otherSegmentationSelector.addEnabled = True
    self.otherSegmentationSelector.removeEnabled = True
    self.otherSegmentationSelector.renameEnabled = True
    self.otherSegmentationSelector.noneEnabled = True
    self.otherSegmentationSelector.showHidden = False
    self.otherSegmentationSelector.showChildNodeTypes = False
    self.otherSegmentationSelector.setMRMLScene(slicer.mrmlScene)
    self.otherSegmentationSelector.setToolTip("Pick the segmentation to import to")

    # current segmentation and other segmentation table views
    self.currSegmentsTableView = self._createSegmentsTableView()
    self.relatedUIElements[self.currSegmentationSelector] = self.currSegmentsTableView
    self.otherSegmentsTableView = self._createSegmentsTableView()
    self.relatedUIElements[self.otherSegmentationSelector] = self.otherSegmentsTableView
    
    # forward copy button
    self.copyCurrToOtherButton = qt.QPushButton("-+>")
    self.copyCurrToOtherButton.toolTip = "Copy segment"
    self.copyCurrToOtherButton.enabled = False
    
    # backward copy button
    self.copyOtherToCurrButton = qt.QPushButton("<+-")
    self.copyOtherToCurrButton.toolTip = "Copy segment"
    self.copyOtherToCurrButton.enabled = False
    
    # info label
    self.infoLabel = qt.QLabel("")
    blankLabel = qt.QLabel("")
    
    # arrange widgets
    #  selectors in the top row, tables and buttons in the middle row, info label in the bottom row
    self.layout.addWidget(self.currSegmentationSelector, 0, 0)
    self.layout.addWidget(self.otherSegmentationSelector, 0, 2)
    self.layout.addWidget(self.currSegmentsTableView, 1, 0, 2, 1)
    self.layout.addWidget(self.otherSegmentsTableView, 1, 2, 2, 1)
    self.layout.addWidget(self.copyCurrToOtherButton, 1, 1)
    self.layout.addWidget(self.copyOtherToCurrButton, 2, 1)
    self.layout.addWidget(self.infoLabel, 3, 0, 1, 3)
    self.layout.addWidget(blankLabel, 4, 0, 1, 3)

    # connections
    self.currSegmentationSelector.connect('currentNodeChanged(vtkMRMLNode*)',
                                          lambda node: self.onSegmentationSelected(self.currSegmentationSelector,
                                                                                   node,
                                                                                   self.otherSegmentationSelector))
    self.otherSegmentationSelector.connect('currentNodeChanged(vtkMRMLNode*)',
                                           lambda node: self.onSegmentationSelected(self.otherSegmentationSelector,
                                                                                    node,
                                                                                    self.currSegmentationSelector))
    self.currSegmentsTableView.connect('selectionChanged(QItemSelection,QItemSelection)', self.updateView)
    self.otherSegmentsTableView.connect('selectionChanged(QItemSelection,QItemSelection)', self.updateView)
    self.copyCurrToOtherButton.connect("clicked(bool)", lambda: self.copySegmentsBetweenSegmentations(True, False))
    self.copyOtherToCurrButton.connect("clicked(bool)", lambda: self.copySegmentsBetweenSegmentations(False, False))

  def _createSegmentsTableView(self):
    """
    Create a segmentation table widget.
    
    Returns:
      qMRMLSegmentsTableView
    """
    tableView = slicer.qMRMLSegmentsTableView()
    tableView.setHeaderVisible(False)
    tableView.setVisibilityColumnVisible(False)
    tableView.setOpacityColumnVisible(False)
    tableView.setColorColumnVisible(False)
    tableView.setSizePolicy(qt.QSizePolicy.Expanding, qt.QSizePolicy.Expanding)
    tableView.SegmentsTableMessageLabel.hide()
    return tableView

  def updateView(self):
    """
    Update the copy buttons and warning message.
    """
    valid = self.currSegmentationSelector.currentNode() and self.otherSegmentationSelector.currentNode()
    self.copyCurrToOtherButton.enabled = valid and len(self.currSegmentsTableView.selectedSegmentIDs())
    self.copyOtherToCurrButton.enabled = valid and len(self.otherSegmentsTableView.selectedSegmentIDs())
    self.currSegmentsTableView.SegmentsTableMessageLabel.hide()
    self.otherSegmentsTableView.SegmentsTableMessageLabel.hide()

  def onSegmentationSelected(self, selector, node, contrary):
    """
    Run this whenever a different segmentation is selected.

    Args:
      selector (qMRMLNodeComboBox): the selector in which the segmentation node is selected
      node (vtkMRMLSegmentationNode): the selected segmentation node
      contrary (vtkMRMLSegmentationNode): the other segmentation node that is not selected
    """
    tableView = self.relatedUIElements[selector]
    message = ""
    if node and node == contrary.currentNode():
      node = None
      message = "Warning: Cannot have the same segmentation selected on both sides"
    selector.setCurrentNode(node)
    tableView.setSegmentationNode(node)
    tableView.SegmentsTableMessageLabel.hide()
    self.infoLabel.setText(message) 
    self.updateView()
  
  def copySegmentsBetweenSegmentations(self, copyFromCurrentSegmentation, removeFromSource):
    """
    Copy selected segments from one segmentation node to the other.

    Args:
      copyFromCurrentSegmentation (bool): True if to segment from current segmentation 
                                          to other segmentation, False otherwise
      removeFromSource (bool): True if the segments are to be removed after being copied,
                               False if not to be removed
    """
    currSegmentationNode = self.currSegmentationSelector.currentNode()
    otherSegmentationNode = self.otherSegmentationSelector.currentNode()

    if not (currSegmentationNode and otherSegmentationNode):
      return

    if copyFromCurrentSegmentation:
      sourceSegmentation = currSegmentationNode.GetSegmentation()
      targetSegmentation = otherSegmentationNode.GetSegmentation()
      otherSegmentationNode.CreateDefaultDisplayNodes()
      selectedSegmentIds = self.currSegmentsTableView.selectedSegmentIDs()
    else:
      sourceSegmentation = otherSegmentationNode.GetSegmentation()
      targetSegmentation = currSegmentationNode.GetSegmentation()
      currSegmentationNode.CreateDefaultDisplayNodes()
      selectedSegmentIds = self.otherSegmentsTableView.selectedSegmentIDs()
    
    if len(selectedSegmentIds):
      for segmentID in selectedSegmentIds:
        if not targetSegmentation.CopySegmentFromSegmentation(sourceSegmentation, segmentID, removeFromSource):
          raise RuntimeError("Segment %s could not be copied from segmentation %s to %s" %(segmentID,
                                                                                           sourceSegmentation.GetName(),
                                                                                           targetSegmentation.GetName()))

  def setBaseName(self, baseName):
    """
    Set the base name of the Segmentation Copier Selectors.

    Args:
      baseName (Str)
    """
    self.currSegmentationSelector.baseName = baseName
    self.otherSegmentationSelector.baseName = baseName
