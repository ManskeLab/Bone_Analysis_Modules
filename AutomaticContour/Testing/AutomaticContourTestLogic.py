#-----------------------------------------------------
# AutmaticContourTestLogic.py
#
# Created by:  Ryan Yan
# Created on:  20-01-2022
#
# Description: This module contains testing logic for the Automatic Contour module.
#              Includes functions for reading in files and verifying output images.
#              Converts images to numpy arrays for numerical analysis.
#
#-----------------------------------------------------

import SimpleITK as sitk
import sitkUtils, os, slicer
import numpy as np

class AutomaticContourTestLogic:

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
        if '\\' in root:
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
        fullpath = self.getFilePath(filepath )
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
        volume.SetScene(scene)
        volume.SetName(name)
        scene.AddNode(volume)
        if not filename == 'new':
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

    def verifyMask(self, maskVolume, testNum):
        '''
        Check output contour mask against a comparsion file

        Args:
            maskVolume (vtkMRMLScalarVolumeNode): The output contour mask
            testNum (int): Test number

        Returns:
            bool: True if mask is correct, False if not
        '''

        #get arrays from output and comparison image
        outArr = slicer.util.arrayFromVolume(maskVolume)
        compareImg = sitk.ReadImage(self.getFilePath('SAMPLE_MASK' + str(testNum) + '.mha'))
        compareArr = sitk.GetArrayFromImage(compareImg)

        #pad array if sizes differemt
        if np.shape(outArr) != np.shape(compareArr):
            (outArr, compareArr) = self.padArray(outArr, compareArr)
        
        #the comparison array uses 0 and 177 instead of 0 and 1 for some reason, convert it to proper binary node
        compareArr[np.nonzero(compareArr)] = 1

        #calculate difference between arrays
        diff = np.subtract(outArr, compareArr)
  
        #check if difference is less than 2%
        ratio = np.count_nonzero(diff) / diff.size * 100
        print('The difference between the test and comparison image is ' + str.format('{:.6f}', ratio) + '%')

        if ratio > 2:
            print("Test Failed: Difference is too large")
            return False
        else:
            print("Test Passed")
            return True
    