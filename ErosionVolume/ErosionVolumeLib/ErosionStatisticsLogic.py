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
import os
import csv

#
# ErosionStatisticsLogic
#
class ErosionStatisticsLogic:
  def __init__(self, segmentationNode=None, masterVolumeNode=None, outputTableNode=None, markupsData=None, voxelSize=0.0607):
    self.segmentationNode = segmentationNode
    self.outputTableNode = outputTableNode
    self.masterVolumeNode = masterVolumeNode
    self.markupsData = markupsData
    self.voxelSize = voxelSize        # voxel size in millimetres
    self.viewGroup = -1               # for erosion visualization
    self._mrmlScene = slicer.mrmlScene
    self._ras2ijk = vtk.vtkMatrix4x4()
    self._ijk2ras = vtk.vtkMatrix4x4()
    self.spacing = 1

    self.output_path = os.path.join(os.path.split(os.path.split(os.path.dirname(os.path.abspath(__file__)))[0])[0], 'EROSIONS_OUTPUT_DATA')

    if masterVolumeNode is not None:
      self.spacing = masterVolumeNode.GetSpacing()[0]
      masterVolumeNode.GetRASToIJKMatrix(self._ras2ijk)
      masterVolumeNode.GetIJKToRASMatrix(self._ijk2ras)
  
  def displayErosionStatistics(self):
    """
    Get statistics from the segmentation and store them in the output table. 
    Supported statistics include volume, surface area, sphericity, and location.
    """
    import SegmentStatistics
    # set parameters in segmentation statistics module
    segStatsLogic = SegmentStatistics.SegmentStatisticsLogic()
    segStatsLogic.getParameterNode().SetParameter("Segmentation", self.segmentationNode.GetID())
    segStatsLogic.getParameterNode().SetParameter("ScalarVolumeSegmentStatisticsPlugin.enabled","False")
    segStatsLogic.getParameterNode().SetParameter("ClosedSurfaceSegmentStatisticsPlugin.enabled","False")
    segStatsLogic.getParameterNode().SetParameter("LabelmapSegmentStatisticsPlugin.voxel_count.enabled","True")
    segStatsLogic.getParameterNode().SetParameter("LabelmapSegmentStatisticsPlugin.volume_mm3.enabled","True")
    segStatsLogic.getParameterNode().SetParameter("LabelmapSegmentStatisticsPlugin.volume_cm3.enabled","False")
    segStatsLogic.getParameterNode().SetParameter("LabelmapSegmentStatisticsPlugin.surface_area_mm2.enabled","True")
    segStatsLogic.getParameterNode().SetParameter("LabelmapSegmentStatisticsPlugin.roundness.enabled","True")
    segStatsLogic.getParameterNode().SetParameter("LabelmapSegmentStatisticsPlugin.centroid_ras.enabled", "True")
    numOfPoints = self.segmentationNode.GetNumberOfDisplayNodes()

    if(numOfPoints>0):
      segStatsLogic.computeStatistics()
      segStatsLogic.exportToTable(self.outputTableNode)
      stats = segStatsLogic.getStatistics()
    else:
      stats = None

    # convert data according to image spacing
    self._convertData(stats)

    # display table
    segStatsLogic.showTable(self.outputTableNode)
  
  def RASToIJKCoords(self, ras_3coords):
    ras_4coords = ras_3coords + [1]
    return tuple((int(i) for i in self._ras2ijk.MultiplyPoint(ras_4coords)[:3]))

  def IJKToRASCoords(self, ijk_3coords):
    ijk_4coords = ijk_3coords + [1]
    return [i for i in self._ijk2ras.MultiplyPoint(ijk_4coords)[:3]]

  def _convertData(self, stats):
    # erosion segment info
    segmentation = self.segmentationNode.GetSegmentation()
    scan_ID = self.masterVolumeNode.GetName()
    segmentation_name = self.segmentationNode.GetName()
    bones_list = ['N/A', 'Metacarpal', 'Phalanx']
    erosion_type_list = ['Erosion', 'Cyst', 'Unreadable', 'None']

    source_tag = vtk.mutable("") # will store erosion segment info
    seed_tag = vtk.mutable("")
    minimal_radius_tag = vtk.mutable("")
    dilate_erode_distance_tag = vtk.mutable("")

    # table info
    voxel_scale = self.voxelSize / self.spacing
    row_num = self.outputTableNode.GetNumberOfRows()

    source = self.outputTableNode.AddColumn()
    source.SetName("Source")
    source_col = self.outputTableNode.GetColumnIndex("Source")

    seeds = self.outputTableNode.AddColumn()
    seeds.SetName("Seeds")
    seeds_col = self.outputTableNode.GetColumnIndex("Seeds")

    bone = self.outputTableNode.AddColumn()
    bone.SetName("Bone")
    bone_col = self.outputTableNode.GetColumnIndex("Bone")

    cortical_interruption = self.outputTableNode.AddColumn()
    cortical_interruption.SetName("Cortical Interruption")
    cortical_interruption_col = self.outputTableNode.GetColumnIndex("Cortical Interruption")

    segment_col = self.outputTableNode.GetColumnIndex("Segment")

    volume_mm3_col = self.outputTableNode.GetColumnIndex("Volume [mm3]")

    surface_area_mm2_col = self.outputTableNode.GetColumnIndex("Surface area [mm2]")

    centroid_col = self.outputTableNode.GetColumnIndex("Centroid")
    self.outputTableNode.SetColumnProperty(centroid_col, "componentNames", "L|P|S")
    self.outputTableNode.SetColumnDescription("Centroid", "Location of the centroid in LPS coordinates")

    minimalRadius = self.outputTableNode.AddColumn()
    minimalRadius.SetName("Minimum Radius [Voxels]")
    minimalRadius_col = self.outputTableNode.GetColumnIndex("Minimum Radius [Voxels]")

    dilateErodeRadius = self.outputTableNode.AddColumn()
    dilateErodeRadius.SetName("Dilate Erode Distance [Voxels]")
    dilateErodeRadius_col = self.outputTableNode.GetColumnIndex("Dilate Erode Distance [Voxels]")

    # Generate csv file
    with open(os.path.join(self.output_path, segmentation_name+'.csv'), 'w', newline='') as f:
      writer = csv.writer(f)
      # csv header
      writer.writerow(['Scan ID', 'Cortical Interruption', 'Bone', 'Label', 'Seed Location', 'Centroid Location', 'Volume (mm3)', 'Surface Area (mm2)', 'Roundness', 'Number of voxels (voxels)'])

      # convert erosion data in table according to image spacing
      for row in range(0, len(self.markupsData)):
        # convert segment name to "Erosion_XXX"
        data = self.markupsData[row]

        old_name = self.outputTableNode.GetCellText(row, segment_col)
        segment_ID = segmentation.GetSegmentIdBySegmentName(old_name)
        new_name = old_name.split(' ')[-1]
        print(new_name)
        self.outputTableNode.SetCellText(row, segment_col, new_name)

        erosion_label = data[0]
        bone_val = bones_list[data[1]]
        cortical_interruption_val = 'None'

        self.outputTableNode.SetCellText(row, bone_col, bone_val)
        self.outputTableNode.SetCellText(row, cortical_interruption_col, cortical_interruption_val)

        volume = 0
        surface_area = 0
        roundness = 0
        voxel_count = 0
        centroid_coord = 'N/A'
        
        if(self.outputTableNode.GetCellText(row, volume_mm3_col) != ''):
          # record erosion source file (which mask it is located in)
          segment = segmentation.GetSegment(segment_ID)

          if segment.GetTag("Source", source_tag):
            self.outputTableNode.SetCellText(row, source_col, source_tag)

          # record seed point for each erosion
          if segment.GetTag("Seed", seed_tag):
            self.outputTableNode.SetCellText(row, seeds_col, seed_tag)

          cortical_interruption_val = erosion_type_list[data[2]]

          # convert volume to mm3
          volume = float(self.outputTableNode.GetCellText(row, volume_mm3_col)) * (voxel_scale**3)
          self.outputTableNode.SetCellText(row, volume_mm3_col, str(volume))

          # convert surface area to mm2
          surface_area = float(self.outputTableNode.GetCellText(row, surface_area_mm2_col)) * (voxel_scale**2)
          self.outputTableNode.SetCellText(row, surface_area_mm2_col, str(surface_area))
          roundness = stats[segment_ID, "LabelmapSegmentStatisticsPlugin.roundness"]
          voxel_count = stats[segment_ID, "LabelmapSegmentStatisticsPlugin.voxel_count"]

          # convert coordinates to ITK coordinates
          ras_coord = [float(num) for num in (self.outputTableNode.GetCellText(row, centroid_col)).split(' ')]
          itk_coord = self.RASToIJKCoords(ras_coord)
          self.outputTableNode.GetTable().GetColumn(centroid_col).SetComponent(row, 0, itk_coord[0])
          self.outputTableNode.GetTable().GetColumn(centroid_col).SetComponent(row, 1, itk_coord[1])
          self.outputTableNode.GetTable().GetColumn(centroid_col).SetComponent(row, 2, itk_coord[2])
          self.outputTableNode.Modified()

          centroid_coord = ', '.join(str(x) for x in itk_coord)

        # # record advanced parameters for each erosion
        # if segment.GetTag("MinimalRadius", minimal_radius_tag):
        #   self.outputTableNode.SetCellText(row, minimalRadius_col, minimal_radius_tag)

        # if segment.GetTag("DilateErodeDistance", dilate_erode_distance_tag):
        #   self.outputTableNode.SetCellText(row, dilateErodeRadius_col, dilate_erode_distance_tag)

        # Write to CSV
        writer.writerow([scan_ID, cortical_interruption_val, bone_val, erosion_label, str(seed_tag), centroid_coord, volume, surface_area, 
            roundness, voxel_count])

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
    seeds_col = self.outputTableNode.GetColumnIndex("Seeds")
    selectedRow = itemSelection.indexes()[0].row()-1 if len(itemSelection.indexes()) else None
    if (selectedRow is not None) and (selectedRow >= 0):
      seedsStr = self.outputTableNode.GetCellText(selectedRow, seeds_col)
      seedStr = seedsStr.split('; ')[0]
      try:
        x, y, z = seedStr[1:-1].split(', ')
        itk_coord = [int(x), int(y), int(z)]
      except ValueError:
        itk_coord = [float(num) for num in (self.outputTableNode.GetCellText(selectedRow, centroid_col)).split(' ')]
      print("Coords: "+str(itk_coord))
      ras_coord = self.IJKToRASCoords(itk_coord)
      self.jumpSlicesToLocation(self._mrmlScene, ras_coord[0], ras_coord[1], ras_coord[2], False, self.viewGroup)
  
  def setViewGroup(self, newViewGroup):
    self.viewGroup = newViewGroup
  
  def getViewGroup(self):
    return self.viewGroup

  def setMRMLScene(self, mrmlScene):
    self._mrmlScene = mrmlScene

  def setSegmentationNode(self, segmentationNode):
    self.segmentationNode = segmentationNode

  def setMasterVolumeNode(self, masterVolumeNode):
    self.masterVolumeNode = masterVolumeNode
    self.spacing = masterVolumeNode.GetSpacing()[0]
    masterVolumeNode.GetRASToIJKMatrix(self._ras2ijk)
    masterVolumeNode.GetIJKToRASMatrix(self._ijk2ras)

  def setMarkupsData(self, markupsData):
    self.markupsData = markupsData

  def setVoxelSize(self, voxelSize):
    self.voxelSize = voxelSize
    
  def setOutputTableNode(self, outputTableNode):
    self.outputTableNode = outputTableNode

  # def setLowerThreshold(self, lower_threshold):
  #   self.lower_threshold = lower_threshold 

  # def setVariance(self, canny_smoothing_variance):
  #   self.canny_smoothing_variance = canny_smoothing_variance 
