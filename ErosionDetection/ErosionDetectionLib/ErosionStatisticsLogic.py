#-----------------------------------------------------
# ErosionStatisticsLogic.py
#
# Created by:  Mingjie Zhao
# Created on:  21-05-2021
#
# Description: This module contains the logics class for 
#              the erosion statistics table in the 3D Slicer 
#              Erosion Detection extension.
#
#-----------------------------------------------------
import vtk, qt, ctk, slicer
import SimpleITK as sitk

#
# ErosionStatisticsLogic
#
class ErosionStatisticsLogic:
  def __init__(self, segmentNode=None, inputErosionNode=None, outputTableNode=None, voxelSize=0.0607):
    self.segmentNode = segmentNode
    self.inputErosionNode = inputErosionNode
    self.outputTableNode = outputTableNode
    self.voxelSize = voxelSize        # voxel size in millimetres
    self.viewGroup = -1               # for erosion visualization
    self._mrmlScene = slicer.mrmlScene
    self._ras2ijk = vtk.vtkMatrix4x4()
    self._ijk2ras = vtk.vtkMatrix4x4()
    if inputErosionNode is not None:
      inputErosionNode.GetRASToIJKMatrix(self._ras2ijk)
      inputErosionNode.GetIJKToRASMatrix(self._ijk2ras)
  
  def displayErosionStatistics(self):
    """
    Get statistics from the segmentation and store them in the output table. 
    Supported statistics include volume, surface area, sphericity, and location.
    """
    import SegmentStatistics
    # set parameters in segmentation statistics module
    segStatsLogic = SegmentStatistics.SegmentStatisticsLogic()
    segStatsLogic.getParameterNode().SetParameter("Segmentation", self.segmentNode.GetID())
    segStatsLogic.getParameterNode().SetParameter("ScalarVolumeSegmentStatisticsPlugin.enabled","False")
    segStatsLogic.getParameterNode().SetParameter("ClosedSurfaceSegmentStatisticsPlugin.enabled","False")
    segStatsLogic.getParameterNode().SetParameter("LabelmapSegmentStatisticsPlugin.voxel_count.enabled","True")
    segStatsLogic.getParameterNode().SetParameter("LabelmapSegmentStatisticsPlugin.volume_mm3.enabled","True")
    segStatsLogic.getParameterNode().SetParameter("LabelmapSegmentStatisticsPlugin.volume_cm3.enabled","False")
    segStatsLogic.getParameterNode().SetParameter("LabelmapSegmentStatisticsPlugin.surface_area_mm2.enabled","True")
    segStatsLogic.getParameterNode().SetParameter("LabelmapSegmentStatisticsPlugin.roundness.enabled","True")
    segStatsLogic.getParameterNode().SetParameter("LabelmapSegmentStatisticsPlugin.centroid_ras.enabled", "True")
    segStatsLogic.computeStatistics()
    segStatsLogic.exportToTable(self.outputTableNode)

    # convert data according to image spacing
    self._convertData()

    # display table
    segStatsLogic.showTable(self.outputTableNode)
    # connect signals, centre erosions in viewer windows upon selection
    self.connectErosionSelection()
  
  def RASToIJKCoords(self, ras_3coords, ras2ijk):
    ras_4coords = ras_3coords + [1]
    return tuple((int(i) for i in ras2ijk.MultiplyPoint(ras_4coords)[:3]))

  def IJKToRASCoords(self, ijk_3coords, ijk2ras):
    ijk_4coords = ijk_3coords + [1]
    return [i for i in ijk2ras.MultiplyPoint(ijk_4coords)[:3]]

  def _convertData(self):
    # table info
    voxel_scale = self.voxelSize / self.inputErosionNode.GetSpacing()[0]
    row_num = self.outputTableNode.GetNumberOfRows()
    volume_mm3_col = self.outputTableNode.GetColumnIndex("Volume [mm3]")
    surface_area_mm2_col = self.outputTableNode.GetColumnIndex("Surface area [mm2]")
    centroid_col = self.outputTableNode.GetColumnIndex("Centroid")
    self.outputTableNode.SetColumnProperty(centroid_col, "componentNames", "L|P|S")
    self.outputTableNode.SetColumnDescription("Centroid", "Location of the centroid in LPS coordinates")

    # convert data in table according to image spacing
    for row in range(0, row_num):
      # convert volume to mm3
      volume = float(self.outputTableNode.GetCellText(row, volume_mm3_col)) * (voxel_scale**3)
      self.outputTableNode.SetCellText(row, volume_mm3_col, str(volume))
      # convert surface area to mm2
      surface_area = float(self.outputTableNode.GetCellText(row, surface_area_mm2_col)) * (voxel_scale**2)
      self.outputTableNode.SetCellText(row, surface_area_mm2_col, str(surface_area))
      # convert coordinates to ITK coordinates
      ras_coord = [float(num) for num in (self.outputTableNode.GetCellText(row, centroid_col)).split(' ')]
      itk_coord = self.RASToIJKCoords(ras_coord, self._ras2ijk)
      self.outputTableNode.GetTable().GetColumn(centroid_col).SetComponent(row, 0, itk_coord[0])
      self.outputTableNode.GetTable().GetColumn(centroid_col).SetComponent(row, 1, itk_coord[1])
      self.outputTableNode.GetTable().GetColumn(centroid_col).SetComponent(row, 2, itk_coord[2])
      self.outputTableNode.Modified()

  def jumpSlicesToLocation(self, mrmlScene, x, y, z, centred, viewGroup):
    if (not mrmlScene):
      return
    jumpMode = (slicer.vtkMRMLSliceNode.CenteredJumpSlice if centred
                else slicer.vtkMRMLSliceNode.OffsetJumpSlice)
    slicer.vtkMRMLSliceNode.JumpAllSlices(mrmlScene, x, y, z, jumpMode, viewGroup)

  def connectErosionSelection(self):
    lm = slicer.app.layoutManager()
    for viewIndex in range(lm.tableViewCount):
      lm.tableWidget(viewIndex).tableView().setSelectionBehavior(qt.QTableView.SelectRows)
      lm.tableWidget(viewIndex).tableView().selectionModel().connect('selectionChanged(QItemSelection,QItemSelection)',
                                                                     self.onSelectionChanged)

  def disconnectErosionSelection(self):
    lm = slicer.app.layoutManager()
    for viewIndex in range(lm.tableViewCount):
      lm.tableWidget(viewIndex).tableView().selectionModel().disconnect('selectionChanged(QItemSelection,QItemSelection)',
                                                                        self.onSelectionChanged)
  
  def onSelectionChanged(self, itemSelection):
    centroid_col = self.outputTableNode.GetColumnIndex("Centroid")
    selectedRow = itemSelection.indexes()[0].row()-1 if len(itemSelection.indexes()) else None
    if ((selectedRow is not None) and (selectedRow >= 0)):
      print("Coords: "+self.outputTableNode.GetCellText(selectedRow, centroid_col))
      itk_coord = [int(float(num)) for num in (self.outputTableNode.GetCellText(selectedRow, centroid_col)).split(' ')]
      ras_coord = self.IJKToRASCoords(itk_coord, self._ras2ijk)
      self.jumpSlicesToLocation(self._mrmlScene, ras_coord[0], ras_coord[1], ras_coord[2], False, self.viewGroup)
  
  def setViewGroup(self, newViewGroup):
    self.viewGroup = newViewGroup
  
  def getViewGroup(self):
    return self.viewGroup

  def setMRMLScene(self, mrmlScene):
    self._mrmlScene = mrmlScene

  def setSegmentNode(self, segmentNode):
    self.segmentNode = segmentNode

  def setOutputTableNode(self, outputTableNode):
    self.outputTableNode = outputTableNode

  def setInputErosionNode(self, inputErosionNode):
    self.inputErosionNode = inputErosionNode
    inputErosionNode.GetRASToIJKMatrix(self._ras2ijk)
    inputErosionNode.GetIJKToRASMatrix(self._ijk2ras)
    