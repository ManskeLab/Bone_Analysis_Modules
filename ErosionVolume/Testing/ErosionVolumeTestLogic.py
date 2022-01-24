import SimpleITK as sitk
import sitkUtils, os, slicer

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
        return root + '\\TestFiles' + filename

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
        print(fullpath)

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

    def verifyErosion(self, erosionNode):
        import numpy as np

        compareNode = slicer.util.loadSegmentation(self.getFilePath('\\SAMPLE_ER.seg.nrrd'))
        compareSegment = compareNode.GetSegmentation

        #compare each segmentation
        segment = erosionNode.GetSegmentation()
        for i in range(1, segment.GetNumberOfSegments()):
            id = segment.GetNthSegmentID(i)
            erosionArr = slicer.util.arrayFromSegmentBinaryLabelmap(erosionNode, id)
            try:
                compareArr = slicer.util.arrayFromSegmentBinaryLabelmap(compareNode, id)
            except:
                print('Segment ' + id + ' not found')
                return False
            print(np.shape(erosionArr), np.shape(compareArr))
            if (np.shape(compareArr) > np.shape(erosionArr)):
                padDiff = np.subtract(np.shape(compareArr), np.shape(erosionArr))
                padDiff = np.reshape(np.append(padDiff, (0, 0, 0)), (3, 2))
                erosionArr = np.pad(erosionArr, padDiff, 'mean')
            else:
                padDiff = np.subtract(np.shape(erosionArr), np.shape(compareArr))
                padDiff = np.reshape(np.append(padDiff, (0, 0, 0)), (3, 2))
                erosionArr = np.pad(compareArr, padDiff, 'mean')
            diff = np.divide(np.abs(np.subtract(erosionArr, compareArr)), 255)
            ratio = np.sum(diff) / np.sum(np.abs(compareArr))
            print(ratio)
            if not ratio < 0.005:
                return False
        return True

        
        
        