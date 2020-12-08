
import os
import unittest
from __main__ import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *

#
# LineIntensityProfile
#

class LineIntensityProfile(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "LineIntensityProfile" # TODO make this more human readable by adding spaces
    self.parent.categories = ["Bone"]
    self.parent.dependencies = []
    self.parent.contributors = ["John Doe (AnyWare Corp.)"] # replace with "Firstname Lastname (Organization)"
    self.parent.helpText = """
    This is an example of scripted loadable module bundled in an extension.
    """
    self.parent.acknowledgementText = """
    This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc.
    and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
""" # replace with organization, grant and thanks.

#
# LineIntensityProfileWidget
#

class LineIntensityProfileWidget(ScriptedLoadableModuleWidget):
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
    # First input volume selector
    #
    self.inputSelector1 = slicer.qMRMLNodeComboBox()
    self.inputSelector1.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.inputSelector1.selectNodeUponCreation = True
    self.inputSelector1.addEnabled = False
    self.inputSelector1.removeEnabled = False
    self.inputSelector1.noneEnabled = False
    self.inputSelector1.showHidden = False
    self.inputSelector1.showChildNodeTypes = False
    self.inputSelector1.setMRMLScene( slicer.mrmlScene )
    self.inputSelector1.setToolTip( "Pick the first input." )
    parametersFormLayout.addRow("First Volume: ", self.inputSelector1)

    #
    # Second input volume selector
    #
    self.inputSelector2 = slicer.qMRMLNodeComboBox()
    self.inputSelector2.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.inputSelector2.selectNodeUponCreation = True
    self.inputSelector2.addEnabled = False
    self.inputSelector2.removeEnabled = False
    self.inputSelector2.noneEnabled = False
    self.inputSelector2.showHidden = False
    self.inputSelector2.showChildNodeTypes = False
    self.inputSelector2.setMRMLScene( slicer.mrmlScene )
    self.inputSelector2.setToolTip( "Pick the first input." )
    parametersFormLayout.addRow("Second Volume: ", self.inputSelector2)

    #
    # Ruler selector
    #
    self.rulerSelector = slicer.qMRMLNodeComboBox()
    self.rulerSelector.nodeTypes = ["vtkMRMLAnnotationRulerNode"]
    self.rulerSelector.selectNodeUponCreation = True
    self.rulerSelector.addEnabled = False
    self.rulerSelector.removeEnabled = False
    self.rulerSelector.noneEnabled = False
    self.rulerSelector.showHidden = False
    self.rulerSelector.showChildNodeTypes = False
    self.rulerSelector.setMRMLScene(slicer.mrmlScene)
    self.rulerSelector.setToolTip( "Pick the ruler to sample along." )
    parametersFormLayout.addRow("Ruler: ", self.rulerSelector)

    #
    # Apply Button
    #
    self.applyButton = qt.QPushButton("Apply")
    self.applyButton.toolTip = "Run the algorithm."
    self.applyButton.enabled = True
    parametersFormLayout.addRow(self.applyButton)

    # connections
    self.applyButton.connect('clicked(bool)', self.onApplyButton)

    # Add vertical spacer
    self.layout.addStretch(1)

  def cleanup(self):
    pass

  def onSelect(self):
    self.applyButton.enabled = self.inputSelector1.currentNode() and self.inputSelector2.currentNode()

  def onApplyButton(self):
    logic = LineIntensityProfileLogic()
    print("Run the algorithm")
    logic.run(self.inputSelector1.currentNode(), self.inputSelector2.currentNode(), 
      self.rulerSelector.currentNode())


#
# LineIntensityProfileLogic
#

class LineIntensityProfileLogic(ScriptedLoadableModuleLogic):
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

  def probeVolume(self, volumeNode, rulerNode):
    # get ruler endpoints coordinates in RAS
    p0ras = rulerNode.GetPolyData().GetPoint(0)+(1,)
    p1ras = rulerNode.GetPolyData().GetPoint(1)+(1,)

    # convert RAS to IJK coordinates of the vtkImageData
    ras2ijk = vtk.vtkMatrix4x4()
    volumeNode.GetRASToIJKMatrix(ras2ijk)
    p0ijk = [int(round(c)) for c in ras2ijk.MultiplyPoint(p0ras)[:3]]
    p1ijk = [int(round(c)) for c in ras2ijk.MultiplyPoint(p1ras)[:3]]

    # create VTK line that will be used for sampling
    line = vtk.vtkLineSource()
    line.SetResolution(100)
    line.SetPoint1(p0ijk[0], p0ijk[1], p0ijk[2])
    line.SetPoint2(p1ijk[0], p1ijk[1], p1ijk[2])

    # create VTK probe filter and sample the image
    probe = vtk.vtkProbeFilter()
    probe.SetInputConnection(line.GetOutputPort())
    probe.SetSourceData(volumeNode.GetImageData())
    probe.Update()

    # return VTK array
    return probe.GetOutput().GetPointData().GetArray('ImageScalars')
  def showChart(self, samples, names):
    print("Logic showing chart")

    # switch to a layout containing a chart viewer
    lm = slicer.app.layoutManager()
    lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpQuantitativeView)

    # initialize double array MRML node for each sample list,
    #  since this is what chart view MRML node needs
    doubleArrays = []
    for sample in samples:
      arrayNode = slicer.mrmlScene.AddNode(slicer.vtkMRMLDoubleArrayNode())
      array = arrayNode.GetArray()
      nDataPoints = sample.GetNumberOfTuples()
      array.SetNumberOfTuples(nDataPoints)
      array.SetNumberOfComponents(3)
      for i in range(nDataPoints):
        array.SetComponent(i, 0, i)
        array.SetComponent(i, 1, sample.GetTuple1(i))
        array.SetComponent(i, 2, 0)
      doubleArrays.append(arrayNode)
    
    #get the chart view MRML node
    cvNodes = slicer.mrmlScene.GetNodesByClass('vtkMRMLChartViewNode')
    cvNodes.SetReferenceCount(cvNodes.GetReferenceCount()-1)
    cvNodes.InitTraversal()
    cvNode = cvNodes.GetNextItemAsObject()

    # create a new chart node
    chartNode = slicer.mrmlScene.AddNode(slicer.vtkMRMLChartNode())
    for pairs in zip(names, doubleArrays):
      chartNode.AddArray(pairs[0], pairs[1].GetID())
    cvNode.SetChartNodeID(chartNode.GetID())

    return

  def run(self,volumeNode1, volumeNode2, rulerNode):
    """
    Run the actual algorithm
    """
    print("LineIntensityProfileLogic run() called")

    """
    1. get the list(s) of intensity samples along the ruler
    2. set up quantitative layout
    3. use the chart view to plot the intensity samples
    """

    """
    1. get the list of samples
    """
    if not rulerNode or (not volumeNode1 and not volumeNode2):
      print("Inputs are not initialized!")
      return
    
    volumeSamples1 = None
    volumeSamples2 = None

    if volumeNode1:
      volumeSamples1 = self.probeVolume(volumeNode1, rulerNode)
    if volumeNode2:
      volumeSamples2 = self.probeVolume(volumeNode2, rulerNode)
    
    print("volumeSamples1 = "+str(volumeSamples1))
    print("volumeSamples2 = "+str(volumeSamples2))

    imageSamples = [volumeSamples1, volumeSamples2]
    legendNames = [volumeNode1.GetName()+' - '+rulerNode.GetName(),
                   volumeNode2.GetName()+' - '+rulerNode.GetName()]
    self.showChart(imageSamples, legendNames)

    return True


class LineIntensityProfileTest(ScriptedLoadableModuleTest):
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
    self.test_LineIntensityProfile1()

  def test_LineIntensityProfile1(self):
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
    logic = LineIntensityProfileLogic()
    self.assertTrue( logic.hasImageData(volumeNode) )
    self.delayDisplay('Test passed!')