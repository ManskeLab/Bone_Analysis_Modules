import os
import vtk, qt, ctk, slicer

CONTROL_POINT_LABEL_COLUMN = 0
CONTROL_POINT_X_COLUMN = 1
CONTROL_POINT_Y_COLUMN = 2
CONTROL_POINT_Z_COLUMN = 3
CONTROL_POINT_COLUMNS = 4

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
    self._spacing_scale = 1.0

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
    # seed point selector
    self.markupsSelector = slicer.qMRMLNodeComboBox()
    self.markupsSelector.nodeTypes = ['vtkMRMLMarkupsFiducialNode']
    self.markupsSelector.selectNodeUponCreation = True
    self.markupsSelector.addEnabled = True
    self.markupsSelector.removeEnabled = True
    self.markupsSelector.renameEnabled = True
    self.markupsSelector.noneEnabled = False
    self.markupsSelector.showHidden = False
    self.markupsSelector.showChildNodeTypes = False
    self.markupsSelector.setMRMLScene(slicer.mrmlScene)
    self.markupsSelector.baseName = 'Seed'
    self.markupsSelector.setToolTip('Pick the seed points')
    self.layout.addWidget(self.markupsSelector)

    # buttons layout
    buttonsGridLayout = qt.QGridLayout()
    buttonsGridLayout.setContentsMargins(0, 0, 0, 0)

    self.markupsPlaceWidget = slicer.qSlicerMarkupsPlaceWidget()
    self.markupsPlaceWidget.setMRMLScene(slicer.mrmlScene)
    self.setButtonsVisible(False) # hide all buttons
    self.setPlaceButtonVisible(True)   # show only the place button
    buttonsGridLayout.addWidget(self.markupsPlaceWidget, 0, 0)

    self.deleteAllButton = qt.QPushButton(' Delete All')
    self.deleteAllButton.setIcon(qt.QIcon(':/Icons/MarkupsDeleteAllRows.png'))
    self.deleteAllButton.setToolTip('Delete all seed points in the selected node')
    self.deleteAllButton.enabled = False
    buttonsGridLayout.addWidget(self.deleteAllButton, 0, 1)

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
    self.layout.addWidget(self.markupsControlPointsTableWidget)

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
    self.markupsControlPointsTableWidget.setHorizontalHeaderLabels(['Label','X','Y','Z'])
    self.markupsControlPointsTableWidget.horizontalHeader().setSectionResizeMode(0, qt.QHeaderView.Stretch)

  def onDeleteAllButton(self):
    """Run this whenver the delete all button is clicked"""
    markupsNum = self._currentNode.GetNumberOfFiducials()
    currentNodeName = self._currentNode.GetName()
    if slicer.util.confirmOkCancelDisplay(
      'Delete all {} seed points in \'{}\'?'.format(markupsNum, currentNodeName)):
      self._currentNode.RemoveAllMarkups()

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
      ITKCoord = self._logic.rasToITKCoord(currentControlPointPosition, self._spacing_scale)
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
      currentControlPointPosition = self._logic.ITKToRasCoord(ITKCoord, self._spacing_scale)
      self._currentNode.SetNthControlPointPositionFromArray(row, currentControlPointPosition)

  def onMarkupsControlPointSelected(self, row, column):
    """Run this whenever a markup control point in the table is selected"""
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
      self._currentNode.EndModify(wasModifying)
    
    if (selectedAction == upAction and currentControlPoint > 0):
      self._currentNode.SwapControlPoints(currentControlPoint, currentControlPoint-1)

    if (selectedAction == downAction and 
        currentControlPoint < self._currentNode.GetNumberOfControlPoints()-1):
        self._currentNode.SwapControlPoints(currentControlPoint, currentControlPoint+1)

    if (selectedAction == jumpAction):
      self._logic.jumpSlicesToNthPointInMarkup(self._mrmlScene, self._currentNode.GetID(), 
                                               currentControlPoint, False, self.viewGroup)

  def onMarkupsNodeChanged(self):
    """Run this whenever the markup node selector changes"""
    self.setCurrentNode(self.markupsSelector.currentNode())

  def onPointAdded(self, caller=None, event=None):
    """Run this whenever a new markup control point is added to the markup node"""
    self.updateWidget()
    self.markupsControlPointsTableWidget.scrollToBottom()

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
        slicer.vtkMRMLMarkupsNode.PointRemovedEvent, self.updateWidget))
      self._currentNodeObservers.append(currentNode.AddObserver(
        slicer.vtkMRMLMarkupsNode.PointModifiedEvent, self.updateWidget))

    self._currentNode = currentNode
    self.updateWidget()
  
  def getCurrentNode(self):
    return self._currentNode

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

  def setSpacingScale(self, spacingScale):
    self._spacing_scale = spacingScale
    self.updateWidget()

  def updateWidget(self, caller=None, event=None):
    """Update the markup control point table widget"""
    currentNode = self._currentNode

    if (not currentNode):
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
    if (self.markupsControlPointsTableWidget.rowCount == controlPointsNum):
      # don't recreate the table if the number of items is not changed to preserve selection state
      controlPointPosition = [0,0,0]
      for i in range(controlPointsNum):
        controlPointLabel = currentNode.GetNthControlPointLabel(i)
        currentNode.GetNthControlPointPosition(i, controlPointPosition)
        ITKCoord = self._logic.rasToITKCoord(controlPointPosition, self._spacing_scale)
        self.markupsControlPointsTableWidget.item(i, CONTROL_POINT_LABEL_COLUMN).setText(controlPointLabel)
        self.markupsControlPointsTableWidget.item(i, CONTROL_POINT_X_COLUMN).setText('%.3f' % (ITKCoord[0]))
        self.markupsControlPointsTableWidget.item(i, CONTROL_POINT_Y_COLUMN).setText('%.3f' % (ITKCoord[1]))
        self.markupsControlPointsTableWidget.item(i, CONTROL_POINT_Z_COLUMN).setText('%.3f' % (ITKCoord[2]))
    else:
      self.markupsControlPointsTableWidget.clear()
      self.markupsControlPointsTableWidget.setRowCount(controlPointsNum)
      self.markupsControlPointsTableWidget.setColumnCount(CONTROL_POINT_COLUMNS)
      self.markupsControlPointsTableWidget.setHorizontalHeaderLabels(['Label', 'X', 'Y', 'Z'])
      self.markupsControlPointsTableWidget.horizontalHeader().setSectionResizeMode(0, qt.QHeaderView.Stretch)

      controlPointPosition = [0,0,0]
      for i in range(controlPointsNum):
        controlPointLabel = currentNode.GetNthControlPointLabel(i)
        currentNode.GetNthControlPointPosition(i, controlPointPosition)
        ITKCoord = self._logic.rasToITKCoord(controlPointPosition, self._spacing_scale)
        labelItem = qt.QTableWidgetItem(controlPointLabel)
        xItem = qt.QTableWidgetItem('%.3f' % (ITKCoord[0]))
        yItem = qt.QTableWidgetItem('%.3f' % (ITKCoord[1]))
        zItem = qt.QTableWidgetItem('%.3f' % (ITKCoord[2]))
        self.markupsControlPointsTableWidget.setItem(i, CONTROL_POINT_LABEL_COLUMN, labelItem)
        self.markupsControlPointsTableWidget.setItem(i, CONTROL_POINT_X_COLUMN, xItem)
        self.markupsControlPointsTableWidget.setItem(i, CONTROL_POINT_Y_COLUMN, yItem)
        self.markupsControlPointsTableWidget.setItem(i, CONTROL_POINT_Z_COLUMN, zItem)
    self.markupsControlPointsTableWidget.blockSignals(wasBlockedTableWidget)


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

  def rasToITKCoord(self, ras_coord, spacing_scale):
    return [-ras_coord[0] / spacing_scale, 
            -ras_coord[1] / spacing_scale, 
            ras_coord[2] / spacing_scale]

  def ITKToRasCoord(self, ras_coord, spacing_scale):
    return [-ras_coord[0] * spacing_scale, 
            -ras_coord[1] * spacing_scale, 
            ras_coord[2] * spacing_scale]
