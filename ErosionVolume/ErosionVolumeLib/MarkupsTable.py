import os
import vtk, qt, ctk, slicer

CONTROL_POINT_LABEL_COLUMN = 0
CONTROL_POINT_BONE = 1
CONTROL_POINT_CORTICAL_INTERRUPION = 2
# for later iterations
CONTROL_POINT_LARGE_EROSION =  4
CONTROL_POINT_MINIMUM_RADIUS = 4
CONTROL_POINT_ERODE_DISTANCE = 5
CONTROL_POINT_X_COLUMN = 3
CONTROL_POINT_Y_COLUMN = 4
CONTROL_POINT_Z_COLUMN = 5
CONTROL_POINT_COLUMNS = 6

#
# MarkupsTableWidget
#
class MarkupsTable:
  def __init__(self, parent=None):
    """
    Called when the user opens the module the first time and the widget is initialized.
    """
    self.jumpToSliceEnabled = False
    self.viewGroup = -1
    self._mrmlScene = None
    self._currentNode = None
    self._currentNodeObservers = []
    self._logic = MarkupsTableLogic()
    self._ras2ijk = vtk.vtkMatrix4x4()
    self._ijk2ras = vtk.vtkMatrix4x4()
    self.advanced = False
    self.data_cache = {}

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
    """
    Called when the user opens the module the first time and the widget is initialized.
    """

    # buttons layout
    buttonsGridLayout = qt.QGridLayout()
    buttonsGridLayout.setContentsMargins(0, 0, 0, 0)

    # seed point selector
    self.markupsSelector = slicer.qMRMLNodeComboBox()
    self.markupsSelector.nodeTypes = ['vtkMRMLMarkupsFiducialNode']
    self.markupsSelector.selectNodeUponCreation = True
    self.markupsSelector.addEnabled = True
    self.markupsSelector.removeEnabled = True
    self.markupsSelector.renameEnabled = True
    self.markupsSelector.noneEnabled = True
    self.markupsSelector.showHidden = False
    self.markupsSelector.showChildNodeTypes = False
    self.markupsSelector.setMRMLScene(slicer.mrmlScene)
    self.markupsSelector.baseName = 'SEEDS'
    self.markupsSelector.setToolTip('Pick the seed points')
    self.layout.addRow("Seed Points: ", self.markupsSelector)

    self.markupsPlaceWidget = slicer.qSlicerMarkupsPlaceWidget()
    self.markupsPlaceWidget.setMRMLScene(slicer.mrmlScene)
    self.setButtonsVisible(False) # hide all buttons
    self.setPlaceButtonVisible(True)   # show only the place button
    buttonsGridLayout.addWidget(self.markupsPlaceWidget, 1, 0)

    self.deleteAllButton = qt.QPushButton(' Delete All')
    self.deleteAllButton.setIcon(qt.QIcon(':/Icons/MarkupsDeleteAllRows.png'))
    self.deleteAllButton.setToolTip('Delete all seed points in the selected node')
    self.deleteAllButton.enabled = False
    buttonsGridLayout.addWidget(self.deleteAllButton, 1, 1)

    # buttons frame
    buttonsFrame = qt.QFrame()
    buttonsFrame.setLayout(buttonsGridLayout)
    self.layout.addWidget(buttonsFrame)

    self.markupsControlPointsTableWidget = qt.QTableWidget()
    self.setupMarkupsControlPointsTableWidget()
    # Reduce row height to minimum necessary
    self.markupsControlPointsTableWidget.setWordWrap(True)
    self.markupsControlPointsTableWidget.verticalHeader().setSectionResizeMode(qt.QHeaderView.ResizeToContents)
    self.markupsControlPointsTableWidget.setContextMenuPolicy(qt.Qt.CustomContextMenu)
    self.markupsControlPointsTableWidget.setSelectionBehavior(qt.QAbstractItemView.SelectRows)
    self.layout.addRow(self.markupsControlPointsTableWidget)
    self.markupsControlPointsTableWidget.setMinimumHeight(200)

    # connections
    self.markupsSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.onMarkupsNodeChanged)
    self.deleteAllButton.connect('clicked(bool)', self.onDeleteAllButton)
    self.markupsControlPointsTableWidget.connect('customContextMenuRequested(const QPoint&)', self.onMarkupsControlPointsTableContextMenu)
    self.markupsControlPointsTableWidget.connect('cellChanged(int,int)', self.onMarkupsControlPointEdited)
    self.markupsControlPointsTableWidget.connect('cellClicked(int,int)', self.onMarkupsControlPointSelected)

    self.updateWidget()

  def setupMarkupsControlPointsTableWidget(self):
    """Reset the appearence of the markups control points table widget"""
    self.markupsControlPointsTableWidget.setColumnCount(CONTROL_POINT_COLUMNS)
    self.markupsControlPointsTableWidget.setRowCount(0)
    self.markupsControlPointsTableWidget.setHorizontalHeaderLabels(['Label', 'Bone', 'Cortical Interruption', 'X', 'Y', 'Z'])
    # self.markupsControlPointsTableWidget.horizontalHeader().setSectionResizeMode(0, qt.QHeaderView.Stretch)

  def onDeleteAllButton(self):
    """Run this whenever the delete all button is clicked"""
    markupsNum = self._currentNode.GetNumberOfFiducials()
    currentNodeName = self._currentNode.GetName()
    if slicer.util.confirmOkCancelDisplay(
      'Delete all {} seed points in \'{}\'?'.format(markupsNum, currentNodeName)):
      self._currentNode.RemoveAllMarkups()
    self.parent.checkErosionsButton()

  def onMarkupsControlPointEdited(self, row, column):
    """Run this whenever the markups control point table is edited"""
    if (not self._currentNode):
      return
    
    qItem = self.markupsControlPointsTableWidget.item(row, column)
    qText = qItem.text()

    if (column == CONTROL_POINT_LABEL_COLUMN):
      self._currentNode.SetNthControlPointLabel(row, qText)
    else:
      currentControlPointPosition = [0,0,0]
      self._currentNode.GetNthControlPointPosition(row, currentControlPointPosition)
      ITKCoord = self._logic.RASToIJKCoords(currentControlPointPosition, self._ras2ijk)
      newControlPointPosition = 0.000
      try:
        newControlPointPosition = float(qText)
      except ValueError:
        pass
      qItem.setText('%.3f' % newControlPointPosition)
      if (column == CONTROL_POINT_X_COLUMN):
        ITKCoord[0] = newControlPointPosition
      elif (column == CONTROL_POINT_Y_COLUMN):
        ITKCoord[1] = newControlPointPosition
      elif (column == CONTROL_POINT_Z_COLUMN):
        ITKCoord[2] = newControlPointPosition
      currentControlPointPosition = self._logic.IJKToRASCoords(ITKCoord, self._ijk2ras)
      self._currentNode.SetNthControlPointPositionFromArray(row, currentControlPointPosition)

  def onMarkupsControlPointSelected(self, row, column):
    """Run this whenever a markup control point in the table is selected"""
    for i in range(self.markupsControlPointsTableWidget.rowCount):
      controlPointPosition = [0, 0, 0]
      self._currentNode.GetNthControlPointPosition(i, controlPointPosition)
      print(i)
      print(controlPointPosition)
      print("*****")
    if (self.jumpToSliceEnabled and self._currentNode):
      self._logic.jumpSlicesToNthPointInMarkup(self._mrmlScene, self._currentNode.GetID(), row, False, self.viewGroup)
  
  def onMarkupsControlPointsTableContextMenu(self, position):
    """
    Run this whenever a context menu is requested by right clicking a markup control point in the table
    """
    if (not self._currentNode):
      return
    globalPosition = self.markupsControlPointsTableWidget.viewport().mapToGlobal(position)
    controlPointsMenu = qt.QMenu(self.markupsControlPointsTableWidget)
    deleteAction = qt.QAction('Delete highlighted control points', controlPointsMenu)
    upAction = qt.QAction('Move current control point up', controlPointsMenu)
    downAction = qt.QAction('Move current control point down', controlPointsMenu)
    jumpAction = qt.QAction('Jump slices to control point', controlPointsMenu)

    controlPointsMenu.addAction(deleteAction)
    controlPointsMenu.addAction(upAction)
    controlPointsMenu.addAction(downAction)
    controlPointsMenu.addAction(jumpAction)

    selectedAction = controlPointsMenu.exec(globalPosition)

    currentControlPoint = self.markupsControlPointsTableWidget.currentRow()

    if (selectedAction == deleteAction):
      selectionModel = self.markupsControlPointsTableWidget.selectionModel()
      deleteControlPoints = []
      # Need to find selected before removing because removing automatically refreshes the table
      for i in range(self.markupsControlPointsTableWidget.rowCount):
        if (selectionModel.rowIntersectsSelection(i, self.markupsControlPointsTableWidget.rootIndex())):
          deleteControlPoints.append(i)
      # Do this in batch mode
      wasModifying = self._currentNode.StartModify()
      for i in range(len(deleteControlPoints)-1, -1, -1):
        # remove the point at that row
        self._currentNode.RemoveNthControlPoint(deleteControlPoints[i])

        print(deleteControlPoints[i])
        self.markupsControlPointsTableWidget.removeRow(deleteControlPoints[i])
      self._currentNode.EndModify(wasModifying)
    
    if (selectedAction == upAction and currentControlPoint > 0):
      self._currentNode.SwapControlPoints(currentControlPoint, currentControlPoint-1)

    if (selectedAction == downAction and 
        currentControlPoint < self._currentNode.GetNumberOfControlPoints()-1):
        self._currentNode.SwapControlPoints(currentControlPoint, currentControlPoint+1)

    if (selectedAction == jumpAction):
      self._logic.jumpSlicesToNthPointInMarkup(self._mrmlScene, self._currentNode.GetID(), 
                                               currentControlPoint, False, self.viewGroup)

  def getCurrentMarkupsData(self):
    data = []
    currentNode = self._currentNode

    controlPointsNum = currentNode.GetNumberOfControlPoints()
    for i in range(controlPointsNum):
      data_row = []
      data_row.append(str(self.markupsControlPointsTableWidget.item(i, CONTROL_POINT_LABEL_COLUMN).text()))
      data_row.append(self.markupsControlPointsTableWidget.cellWidget(i, CONTROL_POINT_BONE).currentIndex)
      data_row.append(self.markupsControlPointsTableWidget.cellWidget(i, CONTROL_POINT_CORTICAL_INTERRUPION).currentIndex)
      data.append(data_row)

    return data    

  def onMarkupsNodeChanged(self):
    """Run this whenever the markup node selector changes"""
    if(self._currentNode):
      self._currentNode.SetDisplayVisibility(False)
      data = self.getCurrentMarkupsData()
      # add current state to data cache
      self.data_cache[self._currentNode.GetID()] = data
    self.markupsControlPointsTableWidget.clear()
    self.setupMarkupsControlPointsTableWidget()
    self.setCurrentNode(self.markupsSelector.currentNode())

    self._currentNode.SetDisplayVisibility(True)
    self.updateWidget()
    
    if self._currentNode.GetID() in self.data_cache:
      controlPointsNum = self._currentNode.GetNumberOfControlPoints()

      data = self.data_cache[self._currentNode.GetID()]
      for i in range(controlPointsNum):
        self.markupsControlPointsTableWidget.cellWidget(i, CONTROL_POINT_BONE).setCurrentIndex(data[i][0])
        self.markupsControlPointsTableWidget.cellWidget(i, CONTROL_POINT_CORTICAL_INTERRUPION).setCurrentIndex(data[i][1])

    self.markupsControlPointsTableWidget.scrollToBottom()

  def onPointAdded(self, caller=None, event=None):
    """Run this whenever a new markup control point is added to the markup node"""
    self.updateWidget()
    self.markupsControlPointsTableWidget.scrollToBottom()

  def onPointDeleted(self, caller, event=None):
    """Run this whenever a new markup control point is added to the markup node"""
    # self.markupsControlPointsTableWidget.deleteRow()
    # print(caller.GetDisplayNode().GetActiveControlPoint())
    # self.updateWidget()

  def onPointModified(self, caller=None, event=None):
    """Run this whenever a new markup control point is added to the markup node"""
    self.updateWidget()

  def setCurrentNode(self, currentNode):
    if (currentNode == self._currentNode):
      # not changed
      return

    if (self._currentNode and self._currentNodeObservers):
      # remove old observers
      for observer in self._currentNodeObservers:
        self._currentNode.RemoveObserver(observer)
      self._currentNodeObservers = []
    if currentNode:
      wasBlocked = self.markupsSelector.blockSignals(True)
      self.markupsSelector.setCurrentNodeID(currentNode.GetID())
      self.markupsSelector.blockSignals(wasBlocked)
      self.markupsPlaceWidget.setCurrentNode(currentNode)
      # add new observers
      self._currentNodeObservers.append(currentNode.AddObserver(
        slicer.vtkMRMLMarkupsNode.PointAddedEvent, self.onPointAdded))
      self._currentNodeObservers.append(currentNode.AddObserver(
        slicer.vtkMRMLMarkupsNode.PointAboutToBeRemovedEvent, self.onPointDeleted))
      self._currentNodeObservers.append(currentNode.AddObserver(
        slicer.vtkMRMLMarkupsNode.PointModifiedEvent, self.onPointModified))

    self._currentNode = currentNode
    self.updateWidget()
  
  def getCurrentNode(self):
    return self._currentNode

  def getCurrentNodeMinimalRadii(self):
    currentNode = self._currentNode
    minimalRadius = []

    for i in range(currentNode.GetNumberOfControlPoints()):
      if self.advanced:
        minimalRadius.append(self.markupsControlPointsTableWidget.cellWidget(i, CONTROL_POINT_MINIMUM_RADIUS).value)

      else:
        if(self.markupsControlPointsTableWidget.cellWidget(i, CONTROL_POINT_LARGE_EROSION).checked):
          minimalRadius.append(6)
        else:
          minimalRadius.append(3)

    return minimalRadius

  def getCurrentNodeDilateErodeDistances(self):
    currentNode = self._currentNode
    
    dilateErodeDistance = []

    for i in range(currentNode.GetNumberOfControlPoints()):
      if self.advanced:
        dilateErodeDistance.append(self.markupsControlPointsTableWidget.cellWidget(i, CONTROL_POINT_ERODE_DISTANCE).value)

      else:
        if(self.markupsControlPointsTableWidget.cellWidget(i, CONTROL_POINT_LARGE_EROSION).checked):
          dilateErodeDistance.append(6)
        else:
          dilateErodeDistance.append(4)

    return dilateErodeDistance


  def getMarkupsSelector(self):
    return self.markupsSelector

  def setJumpToSliceEnabled(self, enable):
    self.jumpToSliceEnabled = enable
  
  def getJumpToSliceEnabled(self):
    return self.jumpToSliceEnabled

  def setMRMLScene(self, mrmlScene):
    self._mrmlScene = mrmlScene
    self.markupsPlaceWidget.setMRMLScene(mrmlScene)
    self.updateWidget()

  def setButtonsVisible(self, visible):
    self.markupsPlaceWidget.buttonsVisible = visible

  def getButtonsVisible(self, visible):
    return self.markupsPlaceWidget.buttonsVisible

  def setDeleteAllButtonVisible(self, visible):
    self.deleteAllButton.visible = visible
  
  def getDeleteAllButtonVisible(self):
    return self.deleteAllButton.visible

  def setPlaceButtonVisible(self, visible):
    self.markupsPlaceWidget.placeButton().visible = visible

  def getPlaceButtonVisible(self, visible):
    return self.markupsPlaceWidget.placeButton().visible
    
  def setNodeSelectorVisible(self, visible):
    self.markupsSelector.visible = visible
  
  def getNodeSelectorVisible(self):
    return self.markupsSelector.visible

  def setViewGroup(self, newViewGroup):
    self.viewGroup = newViewGroup
  
  def getViewGroup(self):
    return self.viewGroup

  def setCoordsMatrices(self, ras2ijk, ijk2ras):
    self._ras2ijk = ras2ijk
    self._ijk2ras = ijk2ras

  def advancedMarkupsControlPointsTableView(self):
    """Change the table view to show and allow edits of Minimum Erosion Radius and Dilate/Erode Distance parameters"""
    global CONTROL_POINT_X_COLUMN
    global CONTROL_POINT_Y_COLUMN
    global CONTROL_POINT_Z_COLUMN

    self.advanced = True
    CONTROL_POINT_X_COLUMN += 1
    CONTROL_POINT_Y_COLUMN += 1
    CONTROL_POINT_Z_COLUMN += 1
    self.markupsControlPointsTableWidget.setColumnCount(CONTROL_POINT_COLUMNS+1)
    self.markupsControlPointsTableWidget.setHorizontalHeaderLabels(['Label', 'Bone', 'Type', 'Erosion in FOV', 'Min Erosion Radius', 'Erode Distance', 'X', 'Y', 'Z'])
    currentNode = self._currentNode

    for i in range(currentNode.GetNumberOfControlPoints()):
      minimalRadiusText = qt.QSpinBox()
      minimalRadiusText.setMinimum(1)
      minimalRadiusText.setMaximum(99)
      minimalRadiusText.setSingleStep(1)
      minimalRadiusText.setSuffix(' voxels')
      minimalRadiusText.value = 3
      self.markupsControlPointsTableWidget.setCellWidget(i, CONTROL_POINT_MINIMUM_RADIUS, minimalRadiusText)

      dilateErodeDistanceText = qt.QSpinBox()
      dilateErodeDistanceText.setMinimum(0)
      dilateErodeDistanceText.setMaximum(99)
      dilateErodeDistanceText.setSingleStep(1)
      dilateErodeDistanceText.setSuffix(' voxels')
      dilateErodeDistanceText.value = 4
      self.markupsControlPointsTableWidget.setCellWidget(i, CONTROL_POINT_ERODE_DISTANCE, dilateErodeDistanceText)

      controlPointPosition = [0, 0, 0]
      currentNode.GetNthControlPointPosition(i, controlPointPosition)
      ITKCoord = self._logic.RASToIJKCoords(controlPointPosition, self._ras2ijk)

      xItem = qt.QTableWidgetItem('%.3f' % (ITKCoord[0]))
      yItem = qt.QTableWidgetItem('%.3f' % (ITKCoord[1]))
      zItem = qt.QTableWidgetItem('%.3f' % (ITKCoord[2]))
      self.markupsControlPointsTableWidget.setItem(i, CONTROL_POINT_X_COLUMN, xItem)
      self.markupsControlPointsTableWidget.setItem(i, CONTROL_POINT_Y_COLUMN, yItem)
      self.markupsControlPointsTableWidget.setItem(i, CONTROL_POINT_Z_COLUMN, zItem)

    self.updateWidget()
      

  def normalMarkupsControlPointsTableView(self):
    """Change the table view to show and allow edits of Minimum Erosion Radius and Dilate/Erode Distance parameters"""
    global CONTROL_POINT_X_COLUMN
    global CONTROL_POINT_Y_COLUMN
    global CONTROL_POINT_Z_COLUMN

    self.advanced = False
    CONTROL_POINT_X_COLUMN -= 1
    CONTROL_POINT_Y_COLUMN -= 1
    CONTROL_POINT_Z_COLUMN -= 1
    self.markupsControlPointsTableWidget.setColumnCount(CONTROL_POINT_COLUMNS)
    self.markupsControlPointsTableWidget.setHorizontalHeaderLabels(['Label', 'Bone', 'Type', 'Erosion in FOV', 'Large Erosion', 'X', 'Y', 'Z'])
    currentNode = self._currentNode

    for i in range(currentNode.GetNumberOfControlPoints()):
      largeErosionCheckBox = qt.QCheckBox()
      largeErosionCheckBox.checked = False
      largeErosionCheckBox.setToolTip('Set internal parameters for segmenting large erosions')
      self.markupsControlPointsTableWidget.setCellWidget(i, CONTROL_POINT_LARGE_EROSION, largeErosionCheckBox)

      controlPointPosition = [0, 0, 0]
      currentNode.GetNthControlPointPosition(i, controlPointPosition)
      ITKCoord = self._logic.RASToIJKCoords(controlPointPosition, self._ras2ijk)

      xItem = qt.QTableWidgetItem('%.3f' % (ITKCoord[0]))
      yItem = qt.QTableWidgetItem('%.3f' % (ITKCoord[1]))
      zItem = qt.QTableWidgetItem('%.3f' % (ITKCoord[2]))
      self.markupsControlPointsTableWidget.removeCellWidget(i, CONTROL_POINT_X_COLUMN)
      self.markupsControlPointsTableWidget.setItem(i, CONTROL_POINT_X_COLUMN, xItem)
      self.markupsControlPointsTableWidget.setItem(i, CONTROL_POINT_Y_COLUMN, yItem)
      self.markupsControlPointsTableWidget.setItem(i, CONTROL_POINT_Z_COLUMN, zItem)

    self.updateWidget()

  def updateLabels(self):
    currentNode = self._currentNode

    controlPointsNum = currentNode.GetNumberOfControlPoints()
    print(controlPointsNum)
    for i in range(controlPointsNum):
      if self.markupsControlPointsTableWidget.item(i, CONTROL_POINT_LABEL_COLUMN):
        controlPointLabel = currentNode.GetNthControlPointLabel(i)
        bone = self.markupsControlPointsTableWidget.cellWidget(i, CONTROL_POINT_BONE)
        self.markupsControlPointsTableWidget.item(i, CONTROL_POINT_LABEL_COLUMN).setText(bone.currentText+'_'+controlPointLabel)

  def updateWidget(self, caller=None, event=None):
    """Update the markup control point table widget"""
    currentNode = self._currentNode

    if(not currentNode):
      self.markupsControlPointsTableWidget.clear()
      self.setupMarkupsControlPointsTableWidget()
      self.markupsPlaceWidget.setEnabled(False)
      self.deleteAllButton.enabled = False
      return
    
    self.markupsPlaceWidget.setEnabled(True)
    self.deleteAllButton.enabled = True

    # Update the control points table
    wasBlockedTableWidget = self.markupsControlPointsTableWidget.blockSignals(True)
    controlPointsNum = currentNode.GetNumberOfControlPoints()

    if(self.markupsControlPointsTableWidget.rowCount == controlPointsNum):
      # don't recreate the table if the number of items is not changed to preserve selection state
      controlPointPosition = [0,0,0]
      for i in range(controlPointsNum):
        controlPointLabel = currentNode.GetNthControlPointLabel(i)
        currentNode.GetNthControlPointPosition(i, controlPointPosition)
        ITKCoord = self._logic.RASToIJKCoords(controlPointPosition, self._ras2ijk)
        self.markupsControlPointsTableWidget.item(i, CONTROL_POINT_LABEL_COLUMN).setText(controlPointLabel)
        self.markupsControlPointsTableWidget.item(i, CONTROL_POINT_X_COLUMN).setText('%.3f' % (ITKCoord[0]))
        self.markupsControlPointsTableWidget.item(i, CONTROL_POINT_Y_COLUMN).setText('%.3f' % (ITKCoord[1]))
        self.markupsControlPointsTableWidget.item(i, CONTROL_POINT_Z_COLUMN).setText('%.3f' % (ITKCoord[2]))
    else:
      if(not self.markupsControlPointsTableWidget.rowCount):
        for i in range(controlPointsNum):
          self.markupsControlPointsTableWidget.insertRow(i)
          self.insertPoint(i, controlPointsNum)

      elif(controlPointsNum > self.markupsControlPointsTableWidget.rowCount):
        self.markupsControlPointsTableWidget.insertRow(controlPointsNum-1)
        self.insertPoint(controlPointsNum-1, controlPointsNum)
    self.markupsControlPointsTableWidget.blockSignals(wasBlockedTableWidget)


  def insertPoint(self, i, controlPointsNum):
    currentNode = self._currentNode
    controlPointPosition = [0,0,0]
    
    controlPointLabel = currentNode.GetNthControlPointLabel(i)
    currentNode.GetNthControlPointPosition(i, controlPointPosition)
    ITKCoord = self._logic.RASToIJKCoords(controlPointPosition, self._ras2ijk)
    labelItem = qt.QTableWidgetItem(controlPointLabel)
    boneNumItem = qt.QComboBox()
    boneNumItem.addItems(['N/A', 'Metacarpal', 'Phalanx'])
    self.markupsControlPointsTableWidget.setCellWidget(i, CONTROL_POINT_BONE, boneNumItem)

    erosionTypeCombo = qt.QComboBox()
    erosionTypeCombo.addItems(['Erosion', 'Cyst', 'Unreadable', 'None'])
    self.markupsControlPointsTableWidget.setCellWidget(i, CONTROL_POINT_CORTICAL_INTERRUPION, erosionTypeCombo)

    # if(self.advanced):
    #   minimalRadiusText = qt.QSpinBox()
    #   minimalRadiusText.setMinimum(1)
    #   minimalRadiusText.setMaximum(99)
    #   minimalRadiusText.setSingleStep(1)
    #   minimalRadiusText.setSuffix(' voxels')
    #   minimalRadiusText.value = 3
    #   self.markupsControlPointsTableWidget.setCellWidget(i, CONTROL_POINT_MINIMUM_RADIUS, minimalRadiusText)

    #   dilateErodeDistanceText = qt.QSpinBox()
    #   dilateErodeDistanceText.setMinimum(0)
    #   dilateErodeDistanceText.setMaximum(99)
    #   dilateErodeDistanceText.setSingleStep(1)
    #   dilateErodeDistanceText.setSuffix(' voxels')
    #   dilateErodeDistanceText.value = 4
    #   self.markupsControlPointsTableWidget.setCellWidget(i, CONTROL_POINT_ERODE_DISTANCE, dilateErodeDistanceText)

    # else:
    #   largeErosionCheckBox = qt.QCheckBox()
    #   largeErosionCheckBox.checked = False
    #   largeErosionCheckBox.setToolTip('Set internal parameters for segmenting large erosions')
    #   self.markupsControlPointsTableWidget.setCellWidget(i, CONTROL_POINT_LARGE_EROSION, largeErosionCheckBox)
      
    xItem = qt.QTableWidgetItem('%.3f' % (ITKCoord[0]))
    yItem = qt.QTableWidgetItem('%.3f' % (ITKCoord[1]))
    zItem = qt.QTableWidgetItem('%.3f' % (ITKCoord[2]))
    self.markupsControlPointsTableWidget.setItem(i, CONTROL_POINT_LABEL_COLUMN, labelItem)
    
    self.markupsControlPointsTableWidget.setItem(i, CONTROL_POINT_X_COLUMN, xItem)
    self.markupsControlPointsTableWidget.setItem(i, CONTROL_POINT_Y_COLUMN, yItem)
    self.markupsControlPointsTableWidget.setItem(i, CONTROL_POINT_Z_COLUMN, zItem)

#
# MarkupsTableLogic
#
class MarkupsTableLogic:
  def jumpSlicesToNthPointInMarkup(self, mrmlScene, id, n, centred, viewGroup):
    if ((not id) or (not mrmlScene)):
      return
    markupNode = mrmlScene.GetNodeByID(id)
    if (not markupNode):
      return
    point = [0,0,0]
    markupNode.GetNthControlPointPositionWorld(n, point)
    self._jumpSlicesToLocation(mrmlScene, point[0], point[1], point[2], centred, viewGroup)
    
  def _jumpSlicesToLocation(self, mrmlScene, x, y, z, centred, viewGroup):
    if (not mrmlScene):
      return
    jumpMode = (slicer.vtkMRMLSliceNode.CenteredJumpSlice if centred
                else slicer.vtkMRMLSliceNode.OffsetJumpSlice)
    slicer.vtkMRMLSliceNode.JumpAllSlices(mrmlScene, x, y, z, jumpMode, viewGroup)

  def RASToIJKCoords(self, ras_3coords, ras2ijk):
    ras_4coords = ras_3coords + [1]
    return [i for i in ras2ijk.MultiplyPoint(ras_4coords)[:3]]

  def IJKToRASCoords(self, ijk_3coords, ijk2ras):
    ijk_4coords = ijk_3coords + [1]
    return [i for i in ijk2ras.MultiplyPoint(ijk_4coords)[:3]]
