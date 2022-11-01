#-----------------------------------------------------
# SegmentEditor.py
#
# Created by:  Mingjie Zhao
# Created on:  04-11-2020
#
# Description: This program simplifies the 3D Slicer built-in segmention editor
#              to contain only the paint, draw and erase effects.
#              It then adds the sementation editor to a given qt layout.
#
#-----------------------------------------------------
import vtk, qt, ctk, slicer

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
    self.editor.setEffectNameOrder(('Paint', 'Draw', 'Erase', 'Threshold',
                                    'Grow from seeds', 'Fill between slices','Scissors'))
    self.editor.unorderedEffectsVisible = False
    self.editor.switchToSegmentationsButtonVisible = False
    self.editor.segmentationNodeSelectorVisible = False
    self.editor.masterVolumeNodeSelectorVisible = False

    # Set parameter node first so that the automatic selections made when the scene is set are saved
    self.selectParameterNode()
    self.editor.setMRMLScene(slicer.mrmlScene)
    self.layout.addWidget(self.editor)

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

  def setSegmentationNode(self, segmentNode):
    self.editor.setSegmentationNode(segmentNode)

  def setMasterVolumeNode(self, masterVolumeNode):
    self.editor.setMasterVolumeNode(masterVolumeNode)

  def setSegmentationGeometry(self, segmentNode, masterVolumeNode, oversamplingFactor):
    segmentationGeometryWidget = slicer.qMRMLSegmentationGeometryWidget()
    segmentationGeometryWidget.setMRMLScene(slicer.mrmlScene)
    segmentationGeometryWidget.setParent(self.editor)
    segmentationGeometryWidget.setEditEnabled(True)
    segmentationGeometryWidget.setSegmentationNode(segmentNode)
    segmentationGeometryWidget.setSourceNode(masterVolumeNode)
    segmentationGeometryWidget.setOversamplingFactor(oversamplingFactor)
    segmentationGeometryWidget.setReferenceImageGeometryForSegmentationNode()
    segmentationGeometryWidget.hide()

  def setMasterVolumeIntensityMask(self, isIntensityMask, lower=0, upper=3600):
    if isIntensityMask:
      self.parameterSetNode.SetMasterVolumeIntensityMask(True)
      self.parameterSetNode.SetMasterVolumeIntensityMaskRange(lower, upper)
    else:
      self.parameterSetNode.SetMasterVolumeIntensityMask(False)

  def setMaskMode(self, mode, segId=""):
    insideSingleSegment = slicer.vtkMRMLSegmentEditorNode.PaintAllowedInsideSingleSegment
    if (mode == insideSingleSegment):
      self.parameterSetNode.SetMaskSegmentID(segId)
      self.parameterSetNode.SetMaskMode(insideSingleSegment)
    else:
      self.parameterSetNode.SetMaskMode(mode)

  def setOverWriteMode(self, mode):
    self.parameterSetNode.SetOverwriteMode(mode)

  def enter(self):
    """Runs whenever the module is reopened
    """
    if self.editor.turnOffLightboxes():
      slicer.util.warningDisplay('This toolkit is not compatible with slice viewers in light box mode.'
        'Views are being reset.', windowTitle='Automatic Contour')

    # Allow switching between effects and selected segment using keyboard shortcuts
    self.editor.installKeyboardShortcuts()

    # Set parameter set node if absent
    self.selectParameterNode()
    self.editor.updateWidgetFromMRML()

  def exit(self):
    self.editor.setActiveEffect(None)
    self.editor.uninstallKeyboardShortcuts()
    self.editor.removeViewObservations()

  def cleanup(self):
    #self.removeObservers()
    self.effectFactorySingleton.disconnect('effectRegistered(QString)', self.editorEffectRegistered)
