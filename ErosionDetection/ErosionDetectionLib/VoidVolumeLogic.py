#-----------------------------------------------------
# VoidVolumeLogic.py
#
# Created by:  Mingjie Zhao
# Created on:  16-10-2020
#
# Description: This module identifies cortical interruptions and 
#              erosions on the input image. 
#              First, the input image is binarized with a global threshold. 
#              Next, a distance transformation and morphological opening operations
#              (i.e. erode, connectivity, dilate) are applied 
#              to select the large void volumes. 
#              Then, the above steps are repeated with more aggressive parameters. 
#              Lastly, the two void volumes obtained are combined to yield the final output. 
#              There are 12 steps, numbered from 1 to 12. 
#
#-----------------------------------------------------
# Usage:       This module is plugged into 3D Slicer, but can
#              run on its own. When run on its own:
#              python VoidVolume.py arg1 arg2 arg3
#
# Where:       arg1 = The input greyscale image to be segmented
#              arg2 = The contour of the input greyscale image
#              arg3 = The output image to store the erosions
#
#-----------------------------------------------------
import SimpleITK as sitk

class VoidVolumeLogic:
    def __init__(self, model_img=None, contour_img=None, lower_thresh=3000, upper_thresh=10000, seeds=None,
    minimalRadius=3, dilationErosionRadius=5):
        self.model_img = model_img            # 3d bone model
        self.contour_img = contour_img        # outer contour, periosteal boundary
        self.small_distance_map = None        # distance transformation map of the cropped ROI
        self.ero1_img = None                  # voids using conservative parameters
        self.ero2_img = None                  # voids using aggressive parameters
        self.output_img = None
        self.lower_threshold = lower_thresh
        self.upper_threshold = upper_thresh
        self.ero1_distance = minimalRadius # erosions with radius >= 3 voxels (>= 0.183 mm)
        self.ero1_radius = dilationErosionRadius # morphological opening with radius = 5 voxels (= 0.305 mm)
        self.ero2_distance = 1
        self.ero2_radius = 2
        self.seeds = seeds         # seed points indicate the locations of erosion
        self.stepNum = 12          # number of steps in the algorithm
        self._step = 0
    
    def threshold(self, img, lower, upper):
        """
        Binarize the bone with a global threshold filter. 
        Voxels within the intensity range will be labeled with the value 1.

        Args:
            img (Image)
            lower (int)
            upper (int)

        Returns:
            Image
        """
        thresh_filter = sitk.BinaryThresholdImageFilter()
        thresh_filter.SetInsideValue(1)
        thresh_filter.SetOutsideValue(0)
        thresh_filter.SetLowerThreshold(lower)
        thresh_filter.SetUpperThreshold(upper)
        thresh_img = thresh_filter.Execute(img)

        return thresh_img

    def maskVoidVolume(self, thresh_img):
        """
        Dilate seed points by 63 voxels to get ROI, and mask ROI onto the bone. 

        Args:
            thresh_img (Image)

        Returns:
            Image: All void volumes inside ROI are marked with the value 0, 
                   and all other regions are marked with 1. 
                   Small bone particals less than 420 voxels in size are removed. 
        """
        void_volume_img = sitk.Image(self.contour_img.GetSize(), sitk.sitkUInt8)
        void_volume_img.CopyInformation(self.contour_img)
        for seed in self.seeds:
            void_volume_img[seed] = 1
        
        # dilate breaks by 63 voxels to get ROI
        print("Applying dilate filter")
        dilate_filter = sitk.BinaryDilateImageFilter()
        dilate_filter.SetForegroundValue(1)
        dilate_filter.SetKernelRadius([63,63,63])
        dilate_img = dilate_filter.Execute(void_volume_img)

        # apply trabecular mask to ROI to remove region outside periosteal boundary
        roi_mask = dilate_img * self.contour_img
        void_volume_img = roi_mask * thresh_img

        # invert to select background
        invert_filter = sitk.InvertIntensityImageFilter()
        invert_filter.SetMaximum(1)
        background_img = invert_filter.Execute(roi_mask)

        # mark void volumes inside ROI 0 and all other regions 1
        background_img = void_volume_img + background_img
        
        # remove bone particles less than 420 voxels in size
        connected_filter = sitk.ConnectedComponentImageFilter()
        connect_img = connected_filter.Execute(background_img)
        label_img = sitk.RelabelComponent(connect_img, minimumObjectSize=420)
        background_img = self.threshold(label_img, 1, 100000)

        return background_img

    def distanceVoidVolume(self, background_img, radius):
        """
        Selects void volumes with diameter two times the radius voxels or more. 

        Args:
            background_img (Image)
            radius (int): minimum radius of the erosions

        Returns:
            Image
        """
        # invert to select void volumes
        invert_filter = sitk.InvertIntensityImageFilter()
        invert_filter.SetMaximum(1)
        void_volume_img = invert_filter.Execute(background_img)

        # get the bounding box of ROI
        label_stats_filter = sitk.LabelStatisticsImageFilter()
        label_stats_filter.Execute(void_volume_img, void_volume_img)
        boundingbox = label_stats_filter.GetBoundingBox(1)

        # crop void_volume_img into small_img so that code works more efficiently
        small_img = background_img[boundingbox[0]:boundingbox[1]+1, 
                                  boundingbox[2]:boundingbox[3]+1,
                                  boundingbox[4]:boundingbox[5]+1]

        if self.small_distance_map is None:
            print("Applying distance map filter")
            # apply distance transformation to void volumes
            self.small_distance_map = sitk.DanielssonDistanceMap(small_img)

        # binary threshold to select seed points in the middle of the void volumes
        # that are >= [radius] away from the bone structure
        seed_img = self.threshold(self.small_distance_map, radius, 100000)

        print("Applying distance map filter")
        # apply distance transformation to the background
        distance_map = sitk.DanielssonDistanceMap(seed_img)

        # binary threshold to select background voxels that are <= [radius] away from
        # the seed points
        small_img = self.threshold(distance_map, 0, radius)

        # paste small_img back to the original image
        destination_index = [boundingbox[0], boundingbox[2], boundingbox[4]]
        source_size = small_img.GetSize()
        paste_filter = sitk.PasteImageFilter()
        paste_filter.SetDestinationIndex(destination_index)
        paste_filter.SetSourceSize(source_size)
        void_volume_img = paste_filter.Execute(void_volume_img, small_img)
        return void_volume_img

    def erodeVoidVolume(self, void_volume_img, radius):
        """
        Erode void volumes to lose connections and
        prevent leaking into the trabecular voids.

        Args:
            void_volume_img (Image)
            radius (int): erode steps, in voxels
        
        Returns:
            Image
        """
        print("Applying erode filter")
        erode_filter = sitk.BinaryErodeImageFilter()
        erode_filter.SetForegroundValue(1)
        erode_filter.SetKernelRadius([radius,radius,radius])
        erode_img = erode_filter.Execute(void_volume_img)

        return erode_img

    def connectVoidVolume(self, erode_img):
        """
        Label void volumes attached to seed points with the value 1.

        Args:
            erode_img (Image)

        Returns:
            Image
        """
        # connected threshold filter to select regions connected to seed points
        connected_thr_filter = sitk.ConnectedThresholdImageFilter()
        connected_thr_filter.SetLower(1)
        connected_thr_filter.SetUpper(1)
        connected_thr_filter.SetSeedList(self.seeds)
        connected_thr_filter.SetReplaceValue(1)
        connected_thr_img = connected_thr_filter.Execute(erode_img)

        return connected_thr_img

    def dilateVoidVolume(self, connect_img, radius):
        """
        Dilate void volumes back to original size.

        Args:
            connect_img (Image)
            radius (Image): dilate steps, in voxels

        Returns:
            Image
        """
        # dilate void volumes by 3 voxels to original size
        print("Applying dilate filter")
        dilate_filter = sitk.BinaryDilateImageFilter()
        dilate_filter.SetForegroundValue(1)
        dilate_filter.SetKernelRadius([radius,radius,radius])
        dilate_img = dilate_filter.Execute(connect_img)

        # apply mask to dilated void volumes to get volumes only in the 
        # trabecular region
        void_volume_img = dilate_img * self.contour_img

        return void_volume_img
    
    def combineVoidVolume(self, ero1_img, ero2_img, radius):
        """
        Combines two erosion labels by dilating the first one and masking it onto the second one.

        Args:
            ero1_img (Image)
            ero2_img (Image): should occupy the same physical space as ero1_img
            radius (Int): dilate steps, in voxels

        Returns:
            Image
        """
        dilate_img = self.dilateVoidVolume(ero1_img, radius)
        output1_img = dilate_img * ero2_img
        output1_img = self.connectVoidVolume(output1_img)

        dilate_img = self.dilateVoidVolume(output1_img, radius)
        output2_img = dilate_img * ero2_img
        
        output2_img = output2_img - output1_img
        subtract_img = self.contour_img - output2_img

        # connectivity filter to select void volumes connecting to periosteal boundary
        connected_filter = sitk.ConnectedThresholdImageFilter()
        connected_filter.SetLower(0)
        connected_filter.SetUpper(0)
        connected_filter.SetReplaceValue(1)
        connected_filter.SetSeedList([(0,0,0)])
        subtract_img = connected_filter.Execute(subtract_img)
        output2_img = subtract_img * self.contour_img

        output_img = output1_img + output2_img

        return output_img

    def labelVoidVolume(self, void_volume_img):
        """
        Label separate objects with different labels. Small objects are removed. 

        Args:
            void_volume_img (Image)
        
        Returns:
            Image
        """
        # connected component filter and relabel filter
        connected_cmp_filter = sitk.ConnectedComponentImageFilter()
        connected_cmp_img = connected_cmp_filter.Execute(void_volume_img)
        label_img = sitk.RelabelComponent(connected_cmp_img, minimumObjectSize=927)
        return label_img

    def execute(self):
        """
        Executes the next step in the algorithm.

        Returns:
            bool: False if reached the end of the algorithm, True otherwise. 
        """
        self._step += 1
        try:
            if self._step == 1:
                self._cleanup()
                self.model_img = self.threshold(self.model_img, self.lower_threshold, self.upper_threshold)
            elif self._step == 2:
                self.model_img = self.maskVoidVolume(self.model_img)
            elif self._step == 3:
                self.ero1_img = self.distanceVoidVolume(self.model_img, self.ero1_distance)
            elif self._step == 4:
                self.ero1_img = self.erodeVoidVolume(self.ero1_img, self.ero1_radius)
            elif self._step == 5:
                self.ero1_img = self.connectVoidVolume(self.ero1_img)
            elif self._step == 6:
                self.ero1_img = self.dilateVoidVolume(self.ero1_img, self.ero1_radius)
                # ero1_img completed, it contains voids obtained using conservative parameters
            elif self._step == 7:
                self.ero2_img = self.distanceVoidVolume(self.model_img, self.ero2_distance)
            elif self._step == 8:
                self.ero2_img = self.erodeVoidVolume(self.ero2_img, self.ero2_radius)
            elif self._step == 9:
                self.ero2_img = self.connectVoidVolume(self.ero2_img)
            elif self._step == 10:
                self.ero2_img = self.dilateVoidVolume(self.ero2_img, self.ero2_radius)
                # ero2_img completed, it contains voids obtained using aggressive parameters
            elif self._step == 11:
                radius = 3 if self.ero1_radius > 5 else 5
                self.output_img = self.combineVoidVolume(self.ero1_img, self.ero2_img, radius)
            elif self._step == 12:
                self.output_img = self.labelVoidVolume(self.output_img)
            else: # the end of the algorithm
                self._step = 0
                return False
            return True
        except:
            self._step = 0
            raise   

    def setModelImage(self, img):
        """
        Args:
            img (Image)
        """
        self.model_img = img
    
    def setContourImage(self, contour_img):
        """
        Args:
            contour_img (Image)
        """
        # threshhold to binarize contour
        thresh_img = self.threshold(contour_img, 1, 10000)
        self.contour_img = thresh_img

    def setThresholds(self, lower_threshold, upper_threshold):
        """
        Args:
            lower_threshold (int)
            upper_threshold (int)
        """
        self.lower_threshold = lower_threshold
        self.upper_threshold = upper_threshold

    def setSeeds(self, seeds):
        """
        Args:
            seeds (list of list/tuple of int)
        """
        self.seeds = seeds

    def setRadii(self, minimalRadius, dilationErosionRadius):
        """
        Args:
            minimalRadius (int): used in the distance map filter
            dilationErosionRadius (int): used in the dilate/erode filters
        """
        self.ero1_distance = minimalRadius
        self.ero1_radius = dilationErosionRadius
    
    def _cleanup(self):
        """
        Reset internal parameters.
        """
        self.small_distance_map = None # clean-up distance map

    def getOutput(self):
        return self.output_img


if __name__ == "__main__":
    # execute the algorithm
    import sys

    if len(sys.argv) < 4:
        # invalid arguments, print usage
        print("Usage: VoidVolume.py [input filename] [contour filename] [output filename]")

    else:
        input_dir = sys.argv[1]
        contour_dir = sys.argv[2]
        output_dir = sys.argv[3]

        # read images
        img = sitk.ReadImage(input_dir)
        contour_img = sitk.ReadImage(contour_dir)

        # get lower and upper thresholds
        lower_threshold = int(input("Lower threshold: "))
        upper_threshold = int(input("Upper threshold: "))        

        # get seed point
        seed_x = int(input("Seed point x coordinate: "))
        seed_y = int(input("Seed point y coordinate: "))
        seed_z = int(input("Seed point z coordinate: "))
        seed = [(seed_x, seed_y, seed_z)]

        # create erosion object
        erosion = VoidVolumeLogic(img, contour_img, lower_threshold, upper_threshold, seed)

        # identify erosions
        while (erosion.execute()):
            pass
        erosion_img = erosion.getOutput()

        # store erosions
        print("Storing image in {}".format(output_dir))
        sitk.WriteImage(erosion_img, output_dir)
