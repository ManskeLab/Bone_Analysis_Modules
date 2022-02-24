#-----------------------------------------------------
# ErosionVolumeTestLogic.py
#
# Created by:  Ryan Yan
# Created on:  20-01-2022
#
# Description: This module contains testing logic for the ErosionVolume module.
#              Includes functions for reading in files and verifying output images.
#              Converts images to numpy arrays for numerical analysis.
#
#-----------------------------------------------------

import SimpleITK as sitk
import sitkUtils, os, slicer
import numpy as np

class ErosionVolumeTestLogic:

    def __init__(self):
        pass

    def getFilePath(self, filename):
        '''
        Find the full filepath of a file in the samme folder

        Args: 
            filename (str): name of file (requires \'\\\\' before the name)

        Returns:
            str: full file path
        '''
        root = self.getParent(self.getParent(self.getParent(os.path.realpath(__file__))))

        #Windows
        if root.contains('\\'):
            return root + '\\TestFiles\\' + filename
        
        #MacOS/Linux
        else:
            return root + '/TestFiles/' + filename

    def getParent(self, path):
        return os.path.split(path)[0]

    def volumeFromFile(self, filepath, volume, display=True):
        '''
        Import an image file into a Slicer volume

        Args:
            filepath (str): full path to the file
            volume (vtkVolumeNode): Slicer volume
            display (bool): option to display the volume in Slicer

        Returns:
            None
        '''
        #modify filepath
        fullpath = self.getFilePath(filepath)
        print('Reading in ' + fullpath)

        reader = sitk.ImageFileReader()
        reader.SetFileName(fullpath)

        outputImage = reader.Execute()

        sitkUtils.PushVolumeToSlicer(outputImage, targetNode=volume)
        if display:
            slicer.util.setSliceViewerLayers(background=volume, fit=True)

    def newNode(self, scene, filename='new', name='node', type='scalar', display=True):
        '''
        Create a new node for a Slicer volume

        Args:
            scene (mrmlScene): current Slicer scene
            filename (str)
            name (str): name of the node to be created
            type (str): type of volume created (use \'scalar\' or \'labelmap\')
            display (bool): option to display the volume in Slicer
        
        Returns:
            vtkMRMLVolumeNode
        '''
        if type == 'scalar':
            volume = slicer.vtkMRMLScalarVolumeNode()
        elif type == 'labelmap':
            volume = slicer.vtkMRMLLabelMapVolumeNode()
        elif type == 'segmentation':
            volume = slicer.vtkMRMLSegmentationNode()
        elif type == 'fiducial':
            volume = slicer.vtkMRMLMarkupsFiducialNode()
        elif type == 'table':
            volume = slicer.vtkMRMLTableNode()
        volume.SetScene(scene)
        volume.SetName(name)
        scene.AddNode(volume)
        if not filename == 'new':
            if type == 'fiducial':
                volume = slicer.util.loadMarkups(self.getFilePath(filename))
            elif type == 'seg':
                volume = slicer.util.loadSegmentation(self.getFilePath(filename))
            else:
                self.volumeFromFile(filename, volume, display)
        return volume

    def padArray(self, arr1, arr2):
        '''
        Reformats two arrays to both be the same size

        Args:
            arr1 (NDarray): first array
            arr2 (NDarray): second array

        Returns:
            (NDarray, NDarray): tuple of padded arrays 
        '''
        #find differences in array size
        padDiff = np.subtract(np.shape(arr1), np.shape(arr2))
        negDiff = np.negative(padDiff)

        #remove negative values
        padDiff = np.clip(padDiff, 0, None)
        negDiff = np.clip(negDiff, 0, None)

        #reshape for the pad function
        pad1 = []
        pad2 = []
        for i in range(3):
            pad1.append([negDiff[i], 0])
            pad2.append([padDiff[i], 0])

        #add padding based on array edge values
        arr1 = np.pad(arr1, pad1, 'edge')
        arr2 = np.pad(arr2, pad2, 'edge')
        
        return (arr1, arr2)

    def verifyErosion(self, erosionNode, testNum):
        '''
        Check output erosion segmentation against a comparsion file

        Args:
            erosionNode (vtkMRMLSegmentationNode): The output erosion segmentation
            testNum (int): Test number

        Returns:
            bool: True if erosion is correct, False if not
        '''
        
        #load comparison segmentation
        compareNode = slicer.util.loadSegmentation(self.getFilePath('SAMPLE_ER' + str(testNum) + '.seg.nrrd'))
        #set mask to invisible
        maskId = compareNode.GetSegmentation().GetNthSegmentID(0)
        compareNode.GetDisplayNode().SetSegmentVisibility(maskId, False)

        #iterate through segments using list of IDs
        segment = erosionNode.GetSegmentation()

        #check that number of segmentations is the same
        if segment.GetNumberOfSegments() > compareNode.GetSegmentation().GetNumberOfSegments():
            print("Test Failed: Too many segments in output")
        elif segment.GetNumberOfSegments() < compareNode.GetSegmentation().GetNumberOfSegments():
            print("Test Failed: Missing segments in output")

        for i in range(1, segment.GetNumberOfSegments()):
            id = segment.GetNthSegmentID(i)

            #get array from segment by id
            erosionArr = slicer.util.arrayFromSegmentBinaryLabelmap(erosionNode, id)
            compareArr = slicer.util.arrayFromSegmentBinaryLabelmap(compareNode, id)

            #adjust array sizes if not matching
            if np.shape(erosionArr) != np.shape(compareArr):
                [erosionArr, compareArr] = self.padArray(erosionArr, compareArr)

            #check difference between values in array
            diff = np.subtract(erosionArr, compareArr)
            ratio = np.count_nonzero(diff) / diff.size * 100
            print('The difference between the test and comparison image is ' + str.format('{:.6f}', ratio) + '%')
            if ratio > 0.5:
                print("Test Failed: Difference is too large")
                return False
        print("Test Passed")
        return True

    def verifyTale(self, tableNode, testNum):
        '''
        Check output statistics table against a comparsion file

        Args:
            tableNode (vtkMRMLTableNode): The output statistics table
            testNum (int): Test number

        Returns:
            bool: True if table is correct, False if not
        '''
        #get table data
        table = tableNode.GetTable()

        #load comparison data
        compareTableNode = slicer.util.loadTable(self.getFilePath('SAMPLE_TABLE' + str(testNum) + '.csv'))
        compareTable = compareTableNode.GetTable()

        ratio1 = abs(table.GetValueByName(0, 'Volume [mm3]').ToFloat() / compareTable.GetValueByName(0, 'Volume [mm3]').ToFloat() - 1)
        print('The difference in Volume is ' + str.format('{:.6f}', ratio1) + '%' )
        if ratio1 > 0.01:
            print('Test Failed: Volume difference is too large')
            return False

        ratio2 = abs(table.GetValueByName(0, 'Surface area [mm2]').ToFloat() / compareTable.GetValueByName(0, 'Surface area [mm2]').ToFloat() - 1)
        print('The difference in Surface area is ' + str.format('{:.6f}', ratio2) + '%' )
        if ratio2 > 0.01:
            print('Test Failed: Surface area difference is too large')
            return False
        
        print("Test Passed")
        return True
        
        