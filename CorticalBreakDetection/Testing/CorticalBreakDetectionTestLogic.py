#-----------------------------------------------------
# CorticalBreakDetectionTestLogic.py
#
# Created by:  Ryan Yan
# Created on:  20-01-2022
#
# Description: This module contains testing logic for the Cortical Break Detection module.
#              Includes functions for reading in files and verifying output images.
#              Converts images to numpy arrays for numerical analysis.
#
#-----------------------------------------------------

import SimpleITK as sitk
import sitkUtils, os, slicer
import numpy as np

class CorticalBreakDetectionTestLogic:

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
        elif type == 'fiducial':
            volume = slicer.vtkMRMLMarkupsFiducialNode()
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

    def verifyBreaks(self, breaksNode, testNum):
        '''
        Check output cortical break mask against a comparsion file

        Args:
            breaksNode (vtkMRMLScalarVolumeNode): The output cortical break mask
            testNum (int): Test number

        Returns:
            bool: True if mask is correct, False if not
        '''

        #convert breaks image to array
        breaksArr = slicer.util.arrayFromVolume(breaksNode)
        compareImage = sitk.ReadImage(self.getFilePath('SAMPLE_BREAKS' + str(testNum) + '.nrrd'))
        compareArr = sitk.GetArrayFromImage(compareImage)

        #pad array if sizes different
        if np.shape(breaksArr) != np.shape(compareArr):
            (breaksArr, compareArr) = self.padArray(breaksArr, compareArr)

        #calculate difference in arrays
        diff = np.subtract(breaksArr, compareArr)

        #find total percentage difference
        ratio = np.count_nonzero(diff) / diff.size * 100
        print('The difference between the test and comparison image is ' + str.format('{:.6f}', ratio) + '%')
        if ratio > 0.5:
            print("Test Failed: Difference is too large")
            return False
        else:
            print("Test Passed")
            return True


    def verifySeeds(self, seedsNode, testNum):
        '''
        Checks output list of seed points against a comparison list

        Args:
            seedsNode (vtkMRMLFidualsNode): Fiducial node with output seeds
            testNume (int): Test number

        Returns:
            bool: True if mask is correct, False if not
        '''

        #get list of seeds from node
        seedsList = []
        for i in range(seedsNode.GetNumberOfFiducials()):
            seedsList.append([0, 0, 0])
            seedsNode.GetNthFiducialPosition(i, seedsList[i])

        #get list of seeds from file
        compareList = []
        fileSeeds = slicer.util.loadMarkups(self.getFilePath('SAMPLE_SEEDS' + str(testNum) + '.json'))
        for i in range(fileSeeds.GetNumberOfFiducials()):
            compareList.append([0, 0, 0])
            fileSeeds.GetNthFiducialPosition(i, compareList[i])
        
        #calculate difference in length between lists
        lendiff = len(seedsList) - len(compareList)

        #fail test if too many points or any point is missing
        if lendiff > 9:
            print("Too many seed points placed\nTest Failed")
            return False
        elif lendiff < 0:
            print("Missing seed point\nTest Failed")
            return False

        #test 3 has larger erosion -> larger error threshold
        if testNum == 3:
            threshold = 1.5
        else:
            threshold = 0.5

        #match each point in the lists to comparison list
        for seed in seedsList:
            found = False
            for compSeed in compareList:
                if all(abs(seed[x] - compSeed[x]) < threshold for x in range(3)):
                    found = True
                    break
            if not found:
                #allow for mismatchs for extra seeds
                print('No match found for seed at', seed)
                lendiff -= 1
                if lendiff < 0:
                    print('Missing a correct erosion seed')
                    return False
        print('Test passed')
        return True
        
    