#-----------------------------------------------------
# ErosionComparisonLogic.py
#
# Created by:  Ryan Yan
# Created on:  12-04-2022
#
# Description: This module contains the logics class 
#              for the 3D Slicer Erosion Comparison module.
#
#-----------------------------------------------------
import slicer
from slicer.ScriptedLoadableModule import *
import vtk
import SimpleITK as sitk
import sitkUtils
import logging, os
import numpy as np
import SegmentStatistics

class ErosionComparisonLogic(ScriptedLoadableModuleLogic):
    def __init__(self):
        self.progressCallBack = None
        self.segNode1 = None
        self.segNode2 = None
        self.image = None

    def setMasterImage(self, imageNode) -> None:
        '''Set the master image (baseline is ideal, but can use follow-up)'''
        self.image = sitkUtils.PullVolumeFromSlicer(imageNode)
    
    def setSegments(self, segNode1, segNode2) -> None:
        '''Set the segmentations to compare'''
        self.segNode1 = segNode1
        self.segNode2 = segNode2

    def compareSegments(self, outputNode) -> None:
        '''Create a comparison mask from 2 segmentations'''
        print("Comparing Segmentations")

        #create base array
        arr = np.zeros(self.image.GetSize()[::-1])

        #loop through all segments
        for i in range(1, self.segNode2.GetSegmentation().GetNumberOfSegments()):
            #get segment IDs
            try:
                id1 = self.segNode1.GetSegmentation().GetNthSegmentID(i)
            except:
                break
            id2 = self.segNode2.GetSegmentation().GetNthSegmentID(i)

            #get segnments as arrays
            segment1 = slicer.util.arrayFromSegmentBinaryLabelmap(self.segNode1, id1)
            segment2 = slicer.util.arrayFromSegmentBinaryLabelmap(self.segNode2, id2)

            #get image representation for location data
            seg_img1 = self.segNode1.GetBinaryLabelmapInternalRepresentation(id1)
            seg_img2 = self.segNode2.GetBinaryLabelmapInternalRepresentation(id2)

            #get origins
            img_origin = [int(x) for x in np.round(np.divide(self.image.GetOrigin(), self.image.GetSpacing()[0]))]
            seg_origin1 = [int(abs(x)) for x in np.round(np.divide(seg_img1.GetOrigin(), seg_img1.GetSpacing()[0]))]
            seg_origin2 = [int(abs(x)) for x in np.round(np.divide(seg_img2.GetOrigin(), seg_img2.GetSpacing()[0]))]

            print("Origin:", img_origin, seg_origin1, seg_origin2)

            #get shift locations (extent + difference between origins)
            shift1 = [seg_img1.GetExtent()[x] for x in [4, 2, 0]]
            shift1 = [shift1[x] - img_origin[2-x] + seg_origin1[2-x] for x in range(3)]
            shift2 = [seg_img2.GetExtent()[x] for x in [4, 2, 0]]
            shift2 = [shift2[x] - img_origin[2-x] + seg_origin2[2-x] for x in range(3)]

            print("Shift:", shift1, shift2)

            #get coordinates of segment
            coord1 = np.nonzero(segment1)
            coord2 = np.nonzero(segment2)

            #shift coordinates
            for i in range(len(coord1[0])):
                coord1[0][i] += shift1[0]
                coord1[1][i] += shift1[1]
                coord1[2][i] += shift1[2]
            arr[coord1] -= 1

            for i in range(len(coord2[0])):
                coord2[0][i] += shift2[0]
                coord2[1][i] += shift2[1]
                coord2[2][i] += shift2[2]
            arr[coord2] += 1

        print("Generating ouput segmentation")
        #create output image
        outimg = sitk.GetImageFromArray(arr)
        outimg.CopyInformation(self.image)

        #push to slicer
        x = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode")
        sitkUtils.PushVolumeToSlicer(outimg, x)
        outputNode.GetSegmentation().RemoveAllSegments()
        slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(x, outputNode)
        slicer.mrmlScene.RemoveNode(x)
        
        #slicer.util.setSliceViewerLayers(label=outputNode, labelOpacity=0.5)

    #INCOMPLETE
    def compareImages(self, imageNode1, imageNode2, outNode, lower:int, upper:int) -> None:
        image1 = sitkUtils.PullVolumeFromSlicer(imageNode1)
        image2 = sitkUtils.PullVolumeFromSlicer(imageNode2)
        image2.CopyInformation(image1)

        spacing = image1.GetSpacing()[0]
        return
    
    def dilate(self, img:sitk.Image, dist:int) -> sitk.Image:
        '''
        Dilate a mask by a set distance
        '''
        #dilate with distance map
        distance_map = sitk.SignedMaurerDistanceMap(img)
        dilated_img = (distance_map <= dist)
        return dilated_img
    
    def erode(self, img:sitk.Image, dist:int) -> sitk.Image:
        '''
        Erode a mask by a set distance
        '''
        #erode with distance map
        distance_map = sitk.SignedMaurerDistanceMap(img)
        eroded_img = (distance_map <= -dist)
        return eroded_img
    
    def getStatistics(self, segNode, tableNode) -> None:
        '''Return the change in volume of the erosions'''
        print("Calculating statistics")
        
        #create columns for new table
        tableNode.RemoveAllColumns()
        
        col_id = tableNode.AddColumn()
        col_id.SetName("Segment ID")
        col_vol = tableNode.AddColumn()
        col_vol.SetName("Change in Volume (mm3)")
        col_vox = tableNode.AddColumn()
        col_vox.SetName("Change in Voxels")

        #get statistics
        segStats = SegmentStatistics.SegmentStatisticsLogic()
        segStats.getParameterNode().SetParameter("Segmentation", segNode.GetID())
        segStats.computeStatistics()
        
        #iterate through segments
        segment = segNode.GetSegmentation()
        for i in range(segment.GetNumberOfSegments() - 1):
            #create row of data
            tableNode.AddEmptyRow()
            seg_id = segment.GetNthSegmentID(i + 1)
            tableNode.SetCellText(i, 0, "Segment_" + str(i + 1))
            tableNode.SetCellText(i, 1, str.format('{:.6f}', segStats.getStatistics()[(seg_id, 'LabelmapSegmentStatisticsPlugin.volume_mm3')]))
            tableNode.SetCellText(i, 2, str(segStats.getStatistics()[(seg_id, 'LabelmapSegmentStatisticsPlugin.voxel_count')]))
        
        segStats.showTable(tableNode)
        