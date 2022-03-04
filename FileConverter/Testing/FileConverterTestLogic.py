#-----------------------------------------------------
# FileConverterTestLogic.py
#
# Created by:  Ryan Yan
# Created on:  02-03-2022
#
# Description: This module contains testing logic for the FileConverter module.
#              Includes functions for reading in files and verifying output images.
#              Converts images to numpy arrays for numerical analysis.
#
#-----------------------------------------------------

import slicer, os
import SimpleITK as sitk
import numpy as np

class FileConverterTestLogic:

    def __init__(self) -> None:
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

    def compareImage(self, convertedVolume, comparisonFile) -> bool:

        # create numpy arrays
        convertArr = slicer.util.arrayFromVolume(convertedVolume)

        reader = sitk.ImageFileReader()
        reader.SetFileName(comparisonFile)
        compareArr = sitk.GetArrayFromImage(reader.Execute())

        # check if images exactly equal and return result
        return compareArr.all() == convertArr.all()