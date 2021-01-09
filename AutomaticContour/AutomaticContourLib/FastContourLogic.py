#-----------------------------------------------------
# FastContourLogic.py
#
# Created by:  Mingjie Zhao
# Created on:  15-12-2020
#
# Description: This module draws the contours of the input bones 
#              and saves them in one label mask. Each bone will have a different label. 
#              The bones are first smoothened by a Gaussian filter.
#              Then, they are separated by either a connectivity filter or 
#              a user provided label map.
#              Maurer distance map is used to inflate and deflate each bone. 
#              Holes are filled inside each bone.
#              There are 8 steps. Each bone has to run Steps 4-8 separately.
#
#-----------------------------------------------------
# Usage:       This module is plugged into 3D Slicer, but can
#              run on its own. When run on its own:
#              python FastContourLogic.py arg1 arg2
#
# Param:       arg1 = The input greyscale image to be contoured
#              arg2 = The output image to store the contour
#
#-----------------------------------------------------
import SimpleITK as sitk
from AutomaticContourLib.ContourLogic import ContourLogic

class FastContourLogic(ContourLogic):
    """This class provides methods for automatic contouring"""
    def inflate(self, img, radius, foreground):
        """
        Inflate the bone in the image using Maurer distance map.

        Args:
            img (Image)
            radius (Int): Inflate steps, in voxels
            foreground (int): Only voxels with the foreground value are considered.

        Returns:
            Image
        """
        # inflate with Maurer distance map filter
        print("Applying distance map filter")
        distance_filter = sitk.SignedMaurerDistanceMapImageFilter()
        distance_filter.SetSquaredDistance(False)
        distance_filter.SetBackgroundValue(0)
        distance_img = distance_filter.Execute(img)

        distance_img = sitk.BinaryThreshold(distance_img, 
                                          lowerThreshold=1,
                                          upperThreshold=radius,
                                          insideValue=foreground)
        inflate_img = distance_img + img

        return inflate_img

    def deflate(self, img, radius, foreground):
        """
        Deflate the bone in the image to its original size using Maurer distance map. 
        
        Args:
            img (Image)
            radius (Int): deflate steps, in voxels
            foreground (int): Only voxels with the foreground value are considered.
        
        Returns:
            Image
        """
        # deflate with Maurer distance map filter
        print("Applying distance map filter")
        distance_filter = sitk.SignedMaurerDistanceMapImageFilter()
        distance_filter.SetSquaredDistance(False)
        distance_filter.SetBackgroundValue(foreground)
        distance_img = distance_filter.Execute(img)

        distance_img = sitk.BinaryThreshold(distance_img, 
                                          lowerThreshold=1,
                                          upperThreshold=radius,
                                          insideValue=foreground)

        deflate_img = img - distance_img

        return deflate_img

    def execute(self):
        """
        Execute the next step in the algorithm. 

        Returns:
            bool: False if reached the end of the algorithm, True otherwise. 
        """
        self._step += 1
        try:
            if self._step == 1: # step 1
                self._cleanup()
                self.img = self.binarize(self.img, self.lower_threshold, self.upper_threshold)
            elif self._step == 2: # step 2
                self.label_img = self.denoise(self.img, sigma=2)
            elif self._step == 3: # step 3
                if (self.separate_map is None): # separate bones with connectivity filter
                    self.label_img = self.relabelWithConnect(self.label_img)
                else:                           # separate bones with manual map
                    self.label_img = self.relabelWithMap(self.img, self.label_img, self.separate_map)
            elif self._step == 4: # step 4
                self.img = self.extract(self.label_img, self.boneNum)
            elif self._step == 5: # step 5
                self.img = self.inflate(self.img, radius=self._dilateErodeRadius, foreground=self.boneNum)
            elif self._step == 6: # step 6
                self.img = self.fillHole(self.img, self.boneNum)
            elif self._step == 7: # step 7
                self.img = self.deflate(self.img, radius=self._dilateErodeRadius, foreground=self.boneNum)
            elif self._step == 8: # step 8
                if (self.output_img is None): # store first bone in output_img
                    self.output_img = self.pasteBack(self.img)
                else:                         # concatenate temp_img to output_img
                    temp_img = self.pasteBack(self.img)
                    self.output_img = sitk.Mask(self.output_img, 
                                                temp_img, 
                                                outsideValue=self.boneNum, 
                                                maskingValue=self.boneNum)
                # one bone structure completed
                self.boneNum -= 1
                if (self.boneNum > 0):
                    self._step = 3 # go back to the end of step 3
            else: # end of the algorithm
                self._step = 0
                return False

            return True
        except:
            self._step = 0
            raise

# run this program on its own
if __name__ == "__main__":
    # execute the algorithm
    import sys

    if len(sys.argv) < 3:
        # invalid arguments, print usage
        print("Usage: FastContourLogic.py [input filename] [output filename]")

    else:
        input_dir = sys.argv[1]
        output_dir = sys.argv[2]

        # read image
        img = sitk.ReadImage(input_dir)

        # create contour object
        contour = FastContourLogic(img)

        # create contour
        while (contour.execute()):
            pass
        contour_img = contour.getOutput()

        # store contour
        print("Storing image in {}".format(output_dir))
        sitk.WriteImage(contour_img, output_dir)
