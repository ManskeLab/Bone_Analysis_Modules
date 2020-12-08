# This program identifies cortical interruptions and erosion
# There are ten steps, numbered from 1 to 10.

import SimpleITK as sitk

class Erosion:
    def __init__(self, img=None, contour_img=None, lower=2900, upper=10000, seed=None):
        self.model = img                      # 3d model
        self.contour_img = contour_img        # outer contour, periosteal boundary
        self.inner_contour_img = None         # inner contour, endosteal boundary
        self.cortical_mask = None             # outer contour minus inner contour
        self.background_img = None            # region outside of outer contour
        self.output_img = None
        self.lower_threshold = lower
        self.upper_threshold = upper
        self.seed = seed                      # seed point indicates which bone 
                                              # structure to be segmented
        self.step = 0
    
    def threshold(self, img, lower, upper): # step 1 & helper function
        """Applies binary threshold to the image"""
        thresh_filter = sitk.BinaryThresholdImageFilter()
        thresh_filter.SetInsideValue(1)
        thresh_filter.SetOutsideValue(0)
        thresh_filter.SetLowerThreshold(lower)
        thresh_filter.SetUpperThreshold(upper)
        thresh_img = thresh_filter.Execute(img)

        return thresh_img

    def maskBreaks(self, thresh_img): # step 2
        """
        Creates and stores inner_contour_img, cortical_mask, and background_img;
        applies cortical_mask to 3d model to get cortical shell
        """
        # erode by 5 voxels to get endosteal boundary, 
        # so that it is 5 voxels away from the outer contour
        print("Applying erode filter")
        erode_filter = sitk.BinaryErodeImageFilter()
        erode_filter.SetForegroundValue(1)
        erode_filter.SetKernelRadius([5,5,0])
        self.inner_contour_img = erode_filter.Execute(contour_img)

        # subtract inner contour from contour to get cortical mask
        self.cortical_mask = self.contour_img - self.inner_contour_img

        # invert to get the background
        invert_filter = sitk.InvertIntensityImageFilter()
        invert_filter.SetMaximum(1)
        self.background_img = invert_filter.Execute(self.contour_img)

        # apply cortical_mask to thresh_img
        print("Applying cortical mask")
        breaks_img = thresh_img * self.cortical_mask

        return breaks_img

    def erodeBreaks(self, breaks_img): # step 3
        """Erode cortical breaks by 1 voxel to remove small gaps"""
        # erode breaks by 1 voxel to remove small gaps
        print("Applying dilate filter")
        dilate_filter = sitk.BinaryDilateImageFilter()
        dilate_filter.SetForegroundValue(1)
        dilate_filter.SetKernelRadius([1,1,1])
        breaks_img = dilate_filter.Execute(breaks_img)

        # apply cortical_mask to breaks
        breaks_img = breaks_img * self.cortical_mask

        return breaks_img

    def connectBreaks(self, breaks_img): # step 4
        """
        Removes cortical breaks not attached to periosteal or endosteal boundaries
        """
        # invert to select breaks, background, and trabecular region
        invert_filter = sitk.InvertIntensityImageFilter()
        invert_filter.SetMaximum(1)
        invert_img = invert_filter.Execute(breaks_img)

        # get breaks together with background
        breaks_background = invert_img - self.inner_contour_img

        # connectivity filter to select background and breaks connected to background
        background_seed = [0,0,0]
        connected_thr_filter = sitk.ConnectedThresholdImageFilter()
        connected_thr_filter.SetLower(1)
        connected_thr_filter.SetUpper(1)
        connected_thr_filter.SetSeedList([background_seed])
        connected_thr_filter.SetReplaceValue(1)
        breaks_background = connected_thr_filter.Execute(breaks_background)
        
        # get breaks together with trabecular region
        breaks_trabecular = breaks_background - self.background_img + self.inner_contour_img
        
        # connectivity filter to select trabecular region marked by the seed point
        connected_thr_filter.SetSeedList([self.seed])
        breaks_trabecular = connected_thr_filter.Execute(breaks_trabecular)

        # subtract to get breaks only
        breaks_img = breaks_trabecular - self.inner_contour_img

        return breaks_img

    def dilateBreaks(self, breaks_img): # step 5
        """
        dilates cortical breaks by 1 voxel to original size,
        and filters out breaks less than 48 voxels in size
        """
        # dilate breaks by 1 voxel to original size
        print("Applying dilate filter")
        dilate_filter = sitk.BinaryDilateImageFilter()
        dilate_filter.SetForegroundValue(1)
        dilate_filter.SetKernelRadius([1,1,1])
        breaks_img = dilate_filter.Execute(breaks_img)

        # apply cortical_mask to breaks
        breaks_img = breaks_img * self.cortical_mask

        # remove breaks less than 48 voxels
        print("Removing tiny breaks")
        breaks_label = sitk.ConnectedComponent(breaks_img)
        breaks_label = sitk.RelabelComponent(breaks_label, minimumObjectSize=48)
        breaks_img = self.threshold(breaks_label, 1, 10000)
        return breaks_img

    def maskVoidVolume(self, thresh_img, breaks_img): # step 6
        """
        Dilates cortical breaks by 48 voxels to get ROI,
        and applies ROI to 3d model
        """
        # dilate breaks by 48 voxels to get ROI
        print("Applying dilate filter")
        dilate_filter = sitk.BinaryDilateImageFilter()
        dilate_filter.SetForegroundValue(1)
        dilate_filter.SetKernelRadius([48,48,48])
        dilate_img = dilate_filter.Execute(breaks_img)

        # apply trabecular mask to ROI to remove region outside periosteal boundary
        roi_mask = dilate_img * self.contour_img
        void_volume_img = roi_mask * thresh_img

        # invert to select background
        invert_filter = sitk.InvertIntensityImageFilter()
        invert_filter.SetMaximum(1)
        background_img = invert_filter.Execute(roi_mask)

        # mark void volumes inside ROI 0 and all other regions 1
        void_volume_img = void_volume_img + background_img
        
        return void_volume_img

    def distanceVoidVolume(self, void_volume_img): # step 7
        """
        Selects void volumes with diameter 12 voxels or more
        """
        # get the bounding box of ROI
        label_stats_filter = sitk.LabelStatisticsImageFilter()
        label_stats_filter.Execute(void_volume_img, void_volume_img)
        boundingbox = label_stats_filter.GetBoundingBox(1)

        # crop void_volume_img to small_img so that code works more efficiently
        small_img = void_volume_img[boundingbox[0]:boundingbox[1]+1, 
                                    boundingbox[2]:boundingbox[3]+1,
                                    boundingbox[4]:boundingbox[5]+1]

        # apply distance transformation to void volumes
        distance_filter = sitk.DanielssonDistanceMapImageFilter()
        distance_map = distance_filter.Execute(small_img)

        # binary threshold to select seed points in the middle of the void volumes
        # that are at least 12 voxels away from the bone structure
        seed_img = self.threshold(distance_map, 6, 100000)

        # apply distance transformation to the background
        distance_map = distance_filter.Execute(seed_img)

        # binary threshold to select background voxels that are <= 6 voxels from
        # the seed points
        void_volume_img = self.threshold(distance_map, 0, 6)

        # paste small_img back to the original image
        destination_index = [boundingbox[0], boundingbox[2], boundingbox[4]]
        source_size = small_img.GetSize()
        paste_filter = sitk.PasteImageFilter()
        paste_filter.SetDestinationIndex(destination_index)
        paste_filter.SetSourceSize(source_size)
        paste_filter.SetSourceIndex([0,0,0])
        large_img = paste_filter.Execute(void_volume_img, small_img)

        return large_img

    def erodeVoidVolume(self, void_volume_img, breaks_img): # step 8
        """
        Erode void volumes by 3 voxels to lose connections and
        prevent leaking from the trabecular structure,
        and concatenates them to cortical breaks
        """
        # erode void volumes by 3 voxels to lose connections and
        # prevent leaking from the trabecular structure
        print("Applying erode filter")
        erode_filter = sitk.BinaryErodeImageFilter()
        erode_filter.SetForegroundValue(1)
        erode_filter.SetKernelRadius([6,6,6])
        erode_img = erode_filter.Execute(void_volume_img)

        # pixel-wise OR operator to concatenate void volumes to breaks
        erosion_img = erode_img | breaks_img

        return erosion_img

    def connectVoidVolume(self, erosion_img): # step 9
        """
        Removes void volumes not attached to cortical breaks, 
        periosteal or endosteal boundaries
        """
        # erosion_background consists of (void volumes + breaks + background)
        erosion_background = erosion_img + self.background_img

        # connectivity filter
        connected_filter = sitk.ConnectedComponentImageFilter()
        connected_img = connected_filter.Execute(erosion_background)

        # relabel objects from large to small
        connected_img = sitk.RelabelComponent(connected_img)

        # select the largest object, which consists of erosion and background
        erosion_background = self.threshold(connected_img, 1, 1)

        # apply mask to (void volumes + breaks + background)
        # to get void volumes
        void_volume_img = erosion_background * self.inner_contour_img

        return void_volume_img

    def dilateVoidVolume(self, void_volume_img, breaks_img): # step 10
        """
        Dilates void volumes by 3 voxels to original size,
        and concatenates them to cortical breaks to get final erosion image
        """
        # dilate void volumes by 3 voxels to original size
        print("Applying dilate filter")
        dilate_filter = sitk.BinaryDilateImageFilter()
        dilate_filter.SetForegroundValue(1)
        dilate_filter.SetKernelRadius([6,6,6])
        void_volume_img = dilate_filter.Execute(void_volume_img)

        # apply mask to dilated void volumes to get volumes only in the 
        # trabecular region
        void_volume_img = void_volume_img * self.inner_contour_img

        # add breaks to void_volume
        erosion_img = void_volume_img + breaks_img

        return erosion_img

    def execute(self):
        """
        Executes the next step in the algorithm, 
        returns false if reached the end of the algorithm, 
        returns true otherwise
        """
        self.step += 1
        if self.step == 1:
            self.model = self.threshold(self.model, self.lower_threshold, self.upper_threshold)
        elif self.step == 2:
            self.output_img = self.maskBreaks(self.model)
        elif self.step == 3:
            self.output_img = self.erodeBreaks(self.output_img)
        elif self.step == 4:
            self.output_img = self.connectBreaks(self.output_img)
        elif self.step == 5:
            self.output_img = self.dilateBreaks(self.output_img)
            # so far, output_img contains cortical breaks
        elif self.step == 6:
            self.model = self.maskVoidVolume(self.model, self.output_img)
        elif self.step == 7:
            self.model = self.distanceVoidVolume(self.model)
        elif self.step == 8:
            self.model = self.erodeVoidVolume(self.model, self.output_img)
        elif self.step == 9:
            self.model = self.connectVoidVolume(self.model)
        elif self.step == 10:
            self.output_img = self.dilateVoidVolume(self.model, self.output_img)
            # output_img contains cortical breaks and void volumes
        else:
            self.step = 0
            return False
        return True

    def setModel(self, img):
        self.model = img
    
    def setContourImage(self, contour_img):
        self.contour_img = contour_img

    def setThreshold(self, lower_threshold, upper_threshold):
        self.lower_threshold = lower_threshold
        self.upper_threshold = upper_threshold

    def setSeed(self, x, y, z):
        self.seed = [x, y, z]

    def getOutput(self):
        return self.output_img


if __name__ == "__main__":
    # execute the algorithm
    import sys

    if len(sys.argv) <= 2:
        # incorrect argument, print usage
        print("Usage: erosion.py [images filename] [contour filename]")

    else:
        # read original image
        img = sitk.ReadImage(sys.argv[1])
        contour_img = sitk.ReadImage(sys.argv[2])

        # get lower and upper thresholds
        lower_threshold = int(input("Lower threshold: "))
        upper_threshold = int(input("Upper threshold: "))        

        # get seed point
        seed_x = int(input("Seed point x coordinate: "))
        seed_y = int(input("Seed point y coordinate: "))
        seed_z = int(input("Seed point z coordinate: "))
        seed = [seed_x, seed_y, seed_z]

        # create erosion object
        erosion = Erosion(img, contour_img, lower_threshold, upper_threshold, seed)

        # identify erosion
        while (erosion.execute()):
            pass
        erosion_img = erosion.getOutput()

        # store erosion_img in 'RAMHA_breaks.mha'
        print("Storing image in 'RAMHA_breaks.mha'")
        sitk.WriteImage(erosion_img, 'RAMHA_breaks.mha')
