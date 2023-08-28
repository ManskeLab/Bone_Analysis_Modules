#-----------------------------------------------------
# SegmentEditor.py
#
# Created by:  Mingjie Zhao
# Created on:  04-11-2020
#
# Description: This module contains a customized 3D Slicer built-in segmention editor
#              to contain only the paint, draw and erase effects. 
#              The segmentation editor will be added to the given qt layout
#
#-----------------------------------------------------
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *

#
# SegmentEditor
#
class SegmentEditor:
  def __init__(self, parent=None):
    # Members
    self.parent = parent
    self.parameterSetNode = None
    self.editor = None

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
    # Segment editor widget
    import qSlicerSegmentationsModuleWidgetsPythonQt
    self.editor = qSlicerSegmentationsModuleWidgetsPythonQt.qMRMLSegmentEditorWidget()
    self.editor.setMaximumNumberOfUndoStates(10)
    self.editor.setEffectNameOrder(('Paint', 'Draw', 'Erase', 'Level tracing', 'Threshold', 'Margin', 
                                    'Grow from seeds', 'Fill between slices', 'Smoothing', 'Islands',
                                    'Logical operators'))
    self.editor.unorderedEffectsVisible = False
    self.editor.switchToSegmentationsButtonVisible = False
    self.editor.segmentationNodeSelectorVisible = True
    self.editor.masterVolumeNodeSelectorVisible = True

    # connections
    self.editor.connect('segmentationNodeChanged(vtkMRMLSegmentationNode *)', self.onSegmentationNodeChanged)
    self.editor.connect('masterVolumeNodeChanged (vtkMRMLVolumeNode *)', self.onMasterVolumeNodeChanged)
    self.editor.connect('currentSegmentIDChanged(const QString &)', 
                         lambda segmentId: self.onCurrentSegmentIDChanged(segmentId))

    # Set parameter node first so that the automatic selections made when the scene is set are saved
    self.selectParameterNode()
    self.editor.setMRMLScene(slicer.mrmlScene)
    self.layout.addWidget(self.editor)

    eraseGridLayout = qt.QGridLayout()
    eraseGridLayout.setContentsMargins(0, 5, 0, 5)

    # Erase between slices button
    self.eraseBetweenSlicesButton = qt.QPushButton("Erase Between Slices")
    self.eraseBetweenSlicesButton.toolTip = "Interpolates between segments between slices and erases those segments"
    self.eraseBetweenSlicesButton.enabled = False
    eraseGridLayout.addWidget(self.eraseBetweenSlicesButton, 0, 0)

    # Apply erase button
    self.applyEraseBetweenSlicesButton = qt.QPushButton("Apply Erase")
    self.applyEraseBetweenSlicesButton.toolTip = "Applies erase between slices"
    self.applyEraseBetweenSlicesButton.enabled = False
    eraseGridLayout.addWidget(self.applyEraseBetweenSlicesButton, 0, 1)

    eraseFrame = qt.QFrame()
    eraseFrame.setLayout(eraseGridLayout)

    self.layout.addWidget(eraseFrame)

    self.eraseBetweenSlicesButton.connect('clicked(bool)', self.onEraseBetweenSlicesButton)
    self.applyEraseBetweenSlicesButton.connect('clicked(bool)', self.onApplyEraseBetweenSlicesButton)

    # Observe editor effect registrations to make sure that any effects that are registered
    # later will show up in the segment editor widget. For example, if Segment Editor is set
    # as startup module, additional effects are registered after the segment editor widget is created.
    import qSlicerSegmentationsEditorEffectsPythonQt
    #TODO: For some reason the instance() function cannot be called as a class function although it's static
    factory = qSlicerSegmentationsEditorEffectsPythonQt.qSlicerSegmentEditorEffectFactory()
    self.effectFactorySingleton = factory.instance()
    self.effectFactorySingleton.connect('effectRegistered(QString)', self.editorEffectRegistered)

  def editorEffectRegistered(self):
    self.editor.updateEffectList()

  def selectParameterNode(self):
    # Select parameter set node if one is found in the scene, and create one otherwise
    segmentEditorSingletonTag = "SegmentEditor"
    segmentEditorNode = slicer.mrmlScene.GetSingletonNode(segmentEditorSingletonTag, "vtkMRMLSegmentEditorNode")
    if segmentEditorNode is None:
      segmentEditorNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLSegmentEditorNode")
      segmentEditorNode.UnRegister(None)
      segmentEditorNode.SetSingletonTag(segmentEditorSingletonTag)
      segmentEditorNode = slicer.mrmlScene.AddNode(segmentEditorNode)
    if self.parameterSetNode == segmentEditorNode:
      # nothing changed
      return
    self.parameterSetNode = segmentEditorNode
    self.editor.setMRMLSegmentEditorNode(self.parameterSetNode)

  def setSegmentationNode(self, segmentationNode):
    currSegmentationNode = self.editor.segmentationNode()
    if (currSegmentationNode == segmentationNode): # the same segmentation node has been selected
      # clear selection, and reselect the same segmentation node
      self.editor.setSegmentationNode(None)
    self.editor.setSegmentationNode(segmentationNode)
    self.onSegmentationNodeChanged()

  def getEditor(self):
    return self.editor

  def setMasterVolumeNode(self, masterVolumeNode):
    self.editor.setMasterVolumeNode(masterVolumeNode)
    self.onMasterVolumeNodeChanged()

  def setMasterVolumeIntensityMask(self, isIntensityMask, lower=0, upper=3600):
    """
    Set the segmentation editor mask intensity range. 
    Only area with intensity that falls in the range is editable.
    """
    if isIntensityMask:
      self.parameterSetNode.SetMasterVolumeIntensityMask(True)
      self.parameterSetNode.SetMasterVolumeIntensityMaskRange(lower, upper)
    else:
      self.parameterSetNode.SetMasterVolumeIntensityMask(False)

  def setMaskMode(self, mode, segId=""):
    """
    Set the segmentation editor mask mode. 
    Mode options are:
      - EditAllowedEverywhere 
      - EditAllowedInsideAllSegments
      - EditAllowedInsideVisibleSegments
      - EditAllowedOutsideAllSegments
      - EditAllowedOutsideVisibleSegments 
      - EditAllowedInsideSingleSegment

    Args:
      mode (slicer.vtkMRMLSegmentEditorNode Enum): eg. slicer.vtkMRMLSegmentEditorNode.EditAllowedEverywhere
      segId (Str): must be provided if and only if mode is EditAllowedInsideSingleSegment
    """
    insideSingleSegment = self.editor.segmentationNode().EditAllowedInsideSingleSegment
    if mode == insideSingleSegment:
      if segId == "":
        # self.parameterSetNode.SetMaskMode(insideSingleSegment)
        return
      self.parameterSetNode.SetMaskSegmentID(segId)
      self.parameterSetNode.SetMaskMode(insideSingleSegment)
    else:
      self.parameterSetNode.SetMaskMode(mode)

  def setOverWriteMode(self, mode):
    """
    Set the segmentation editor overwrite mode.
    Mode options are:
      - OverwriteAllSegments
      - OverwriteVisibleSegments
      - OverwriteNone

    Args:
      mode (slicer.vtkMRMLSegmentEditorNode Enum): eg. slicer.vtkMRMLSegmentEditorNode.OverwriteNone
    """
    self.parameterSetNode.SetOverwriteMode(mode)

  def onSegmentationNodeChanged(self):
    """
    Run this whenever a different segmentation node is selected.
    """
    segmentationNode = self.editor.segmentationNode()

    if segmentationNode:
      # display selected segmentation node only
      allSegmentNodes = slicer.util.getNodesByClass("vtkMRMLSegmentationNode")
      for segmentNode in allSegmentNodes:
        segDisplay = segmentNode.GetDisplayNode()
        if segDisplay:
          segDisplay.SetVisibility(0)
      currSegDisplay = segmentationNode.GetDisplayNode()
      currSegDisplay.SetVisibility(1)

      # set editable area to be inside the mask
      segmentation = segmentationNode.GetSegmentation()
      if (segmentation.GetNumberOfSegments()):
        maskSegment = segmentation.GetNthSegment(0)   # the first segment will be the mask
        if ('mask' in maskSegment.GetName().lower()): # the first segment is the mask
          insideSingleSegment = segmentationNode.EditAllowedInsideSingleSegment
          self.setMaskMode(insideSingleSegment, segmentation.GetNthSegmentID(0))
      
    self.checkEraseButtons()

  def onMasterVolumeNodeChanged(self):
    """
    Run this whenever a different master volume is selected.
    """
    masterVolumeNode = self.editor.masterVolumeNode()
    
    if masterVolumeNode:
      # display master volume
      slicer.util.setSliceViewerLayers(background=masterVolumeNode, label=None)

    self.checkEraseButtons()

  def onCurrentSegmentIDChanged(self, segmentId):
    """
    Run this whenever a different segment is selected.

    Args:
      segmentId (Str)
    """
    if segmentId == '':
      return
    centroid = self.editor.segmentationNode().GetSegmentCenter(segmentId)
    if centroid:
      markupsLogic = slicer.modules.markups.logic()
      markupsLogic.JumpSlicesToLocation(centroid[0], centroid[1], centroid[2], False)

  def checkEraseButtons(self):
    # print(self.editor.masterVolumeNode() and self.editor.segmentationNode())
    self.eraseBetweenSlicesButton.enabled = self.editor.masterVolumeNode() and self.editor.segmentationNode()

  def onEraseBetweenSlicesButton(self):
    
    segmentationNode = self.editor.segmentationNode()
    self.segmentIdToErase = self.editor.currentSegmentID()

    eraseNodeID = segmentationNode.GetSegmentation().AddEmptySegment("Delete")
    segmentationNode.GetSegmentation().RemoveSegment(eraseNodeID)
    eraseNodeID = segmentationNode.GetSegmentation().AddEmptySegment("Delete")
    self.editor.setCurrentSegmentID(eraseNodeID)
    self.editor.setActiveEffectByName("Paint")

    self.applyEraseBetweenSlicesButton.enabled = True

    #TODO make slicer wait until you have atleast 2 slices with segments before enabling apply button

  def onApplyEraseBetweenSlicesButton(self):

    volumeNode = self.editor.masterVolumeNode()
    segmentationNode = self.editor.segmentationNode()
    eraseId = segmentationNode.GetSegmentation().GetSegmentIdBySegmentName("Delete")
    self.editor.setCurrentSegmentID(eraseId)

    selectedSegmentIds = vtk.vtkStringArray()

    if(segmentationNode):
        segmentationNode.GetSegmentation().GetSegmentIDs(selectedSegmentIds)

    segmentArrays = []
    segments = []
    segmentIds = []

    # remove all segments
    for idx in range(selectedSegmentIds.GetNumberOfValues()):
      segmentId = selectedSegmentIds.GetValue(idx)
      if segmentId == "Delete":
        continue

      # Get mask segment as numpy array
      segmentArray = slicer.util.arrayFromSegmentBinaryLabelmap(segmentationNode, segmentId, volumeNode)

      segmentArrays.append(segmentArray)
      segments.append(segmentationNode.GetSegmentation().GetSegment(segmentId))
      segmentIds.append(segmentId)
      segmentationNode.GetSegmentation().RemoveSegment(segmentId)

    maskMode = segmentationNode.EditAllowedEverywhere
    self.setMaskMode(maskMode, "")

    self.editor.setActiveEffectByName("Fill between slices")
    effect = self.editor.activeEffect()
    effect.self().onPreview()
    effect.self().onApply()

    # Get erase mask segment as numpy array
    eraseArray = slicer.util.arrayFromSegmentBinaryLabelmap(segmentationNode, eraseId, volumeNode)

    slices = eraseArray.shape[0]
    row = eraseArray.shape[1]
    col = eraseArray.shape[2]

    # Add all segments back but after erasing
    idx = 0
    for segmentArray in segmentArrays:
      segmentationNode.GetSegmentation().AddSegment(segments[idx], segmentIds[idx])

      if segmentIds[idx] == self.segmentIdToErase:
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
    maskSegmentId = segmentationNode.GetSegmentation().GetNthSegmentID(0)

    maskMode = segmentationNode.EditAllowedInsideSingleSegment
    self.setMaskMode(maskMode, maskSegmentId)

    segmentationNode.GetDisplayNode().SetSegmentVisibility(maskSegmentId, False)
    self.editor.setCurrentSegmentID(self.segmentIdToErase)
    # print(maskSegmentId)

  def enter(self):
    """
    Runs this whenever the module is reopened.
    """
    if self.editor.turnOffLightboxes():
      slicer.util.warningDisplay('This toolkit is not compatible with slice viewers in light box mode.'
        'Views are being reset.', windowTitle='Automatic Contour')

    # Allow switching between effects and selected segment using keyboard shortcuts
    self.editor.installKeyboardShortcuts()

    # Set parameter set node if absent
    self.selectParameterNode()
    self.parameterSetNode.SetMaskMode(0)
    self.editor.updateWidgetFromMRML()

  def exit(self):
    """
    Run this whenever the module is closed.
    """
    self.editor.setActiveEffect(None)
    self.editor.uninstallKeyboardShortcuts()
    self.editor.removeViewObservations()

  def cleanup(self):
    """
    Remove the segmentation editor keyboard shortcuts.
    """
    self.effectFactorySingleton.disconnect('effectRegistered(QString)', self.editorEffectRegistered)
