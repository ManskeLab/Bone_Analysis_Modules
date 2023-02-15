#-----------------------------------------------------
# VoidVolumeLogic.py
#
# Created by:  Mingjie Zhao
# Created on:  16-10-2020
#
# Description: This module segments erosions given a greyscale image, the mask 
#              and the seed points. 
#              First, the greyscale image is binarized with a global threshold and 
#              a Gaussian filter. Next, distance transformation and morphological 
#              opening operations (i.e. erode, connectivity, dilate) are applied 
#              to select the void volumes connected. 
#              Then, a level set region growing filter is applied to the void volumes
#              to obtain the final erosion segmentation. 
#              Lastly, each erosion is relabeled with the value that matches 
#              the seed point name. 
#              There are 8 steps.
#
#-----------------------------------------------------
# Usage:       This module is plugged into 3D Slicer.
#
# Param:       inputImage: The input scan file path
#              inputMask: The input mask file path
#              outputImage: The output image file path
#              seeds: The seed points csv file path
#              lowerThreshold
#              upperThreshold
#              sigma: Standard deviation for the Gaussian smoothing filter
#              minimumRadius: Minimum erosion radius in voxels, default=3
#              dilateErodeDistance: Morphological kernel radius in voxels, default=5
#
#-----------------------------------------------------
import SimpleITK as sitk

class VoidVolumeLogic:
    def __init__(self, img=None, mask=None, lower=530, upper=15000, sigma=1,
                 seeds=None, minimalRadius=3, dilateErodeDistance=4):
        self.model_img = img                  # greyscale scan
        self.contour_img = mask               # mask, periosteal boundary
        self.output_img = None
        self.lower_threshold = lower
        self.upper_threshold = upper
        self.sigma = sigma                    # Gaussian sigma
        self.minimalRadius = minimalRadius               # for distance transformation, default=3
        self.dilateErodeDistance = dilateErodeDistance   # for morphological operations, default=4
        self.seeds = seeds         # list of seed point coordinates (x,y,z)
        self.erosionIds = []       # erosion ids decide which value each erosion is labeled with
        if seeds is not None:      #  default = [1, 2, ..., len(seeds)+1]
            self.erosionIds = list(range(1, len(seeds)+1))
        self.stepNum = 8           # number of steps in the algorithm
        self._step = 0             # number of steps done
        self.method = None
        self.auto_thresh = False
    
    def denoise(self, img, sigma):
        """
        Denoise the bone model with a Gaussian filter.

        Args:
            img (Image)
            sigma (float)

        Returns:
            Image
        """
        sigma_over_spacing = sigma * img.GetSpacing()[0]

        # gaussian smoothing filter
        print("Applying Gaussian filter")
        gaussian_filter = sitk.SmoothingRecursiveGaussianImageFilter()
        gaussian_filter.SetSigma(sigma_over_spacing)
        gaussian_img = gaussian_filter.Execute(img)

        return gaussian_img

    def createROI(self, gaussian_img):
        """
        Threshold. Label void volume in the bone and background as ROI.

        Args:
            gaussian_img (Image)
            auto_thresh (bool)

        Returns:
            Image: All voids inside ROI are marked with the value 1, 
                   and all other regions are marked with 0.  
        """
        # binarize the bone
        if self.auto_thresh:
            index = self.method
            if index == 0:
                thresh = sitk.OtsuThresholdImageFilter()
            elif index == 1:
                thresh = sitk.HuangThresholdImageFilter()
            elif index == 2:
                thresh = sitk.MaximumEntropyThresholdImageFilter()
            elif index == 3:
                thresh = sitk.MomentsThresholdImageFilter()
            elif index == 4:
                thresh = sitk.YenThresholdImageFilter()
            thresh.SetOutsideValue(1)
            thresh.SetInsideValue(0)
            thresh_img = thresh.Execute(gaussian_img)
        else:
            thresh_img = sitk.BinaryThreshold(gaussian_img, 
                                          lowerThreshold=self.lower_threshold,
                                          upperThreshold=self.upper_threshold,
                                          insideValue=1)

        # invert to select background and voids in the bone
        invert_filter = sitk.InvertIntensityImageFilter()
        invert_filter.SetMaximum(1)
        void_volume_img = invert_filter.Execute(thresh_img)

        void_volume_img = self.contour_img * void_volume_img

        return void_volume_img

    def distanceVoidVolume(self, void_volume_img, radius):
        """
        Label voids in the bone that are larger than the specified value in separation. 

        Args:
            void_volume_img (Image)
            radius (int): minimum radius of the erosions to be selected, in voxels

        Returns:
            Image
        """

        distance_filter = sitk.SignedMaurerDistanceMapImageFilter()
        distance_filter.SetSquaredDistance(False)
        distance_filter.SetBackgroundValue(1)
        inner_img = distance_filter.Execute(void_volume_img)

        image_viewer = sitk.ImageViewer()
        image_viewer.SetCommand("Z:\Programs\ImageJ\ImageJ.exe")

        inner_img = sitk.BinaryThreshold(inner_img,
                                        lowerThreshold=1,
                                        upperThreshold=radius,
                                        insideValue=1)
        image_viewer.SetTitle('innerimg using ImageViewer class')
        image_viewer.Execute(inner_img)

        image_viewer.SetTitle('volume using ImageViewer class')
        image_viewer.Execute(void_volume_img)

        inner_img = void_volume_img - inner_img

        image_viewer.SetTitle('grid using ImageViewer class')
        image_viewer.Execute(inner_img)

        distance_filter.SetBackgroundValue(0)
        outer_img = distance_filter.Execute(inner_img)

        outer_img = sitk.BinaryThreshold(outer_img,
                                         lowerThreshold=1,
                                         upperThreshold=radius,
                                         insideValue=1)

        image_viewer.SetTitle('out using ImageViewer class')
        image_viewer.Execute(outer_img)

        distance_img = outer_img + inner_img

        image_viewer.SetTitle('dist using ImageViewer class')
        image_viewer.Execute(distance_img)

        return distance_img

    def erodeVoidVolume(self, void_volume_img, radius):
        """
        Morphologically erode voids to remove connections and to
        prevent erosions from leaking into the trabecular region.

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
        Label voids that are connected to seed points.

        Args:
            erode_img (Image)
            
        Returns:
            Image
        """
        seeds_img = sitk.Image(self.contour_img.GetSize(), sitk.sitkUInt8)
        seeds_img.CopyInformation(self.contour_img)
        for seed in self._seeds_crop:
            seeds_img[seed] = 1

        # apply distance transformation to the seed points
        print("Applying distance map filter")
        distance_filter = sitk.SignedMaurerDistanceMapImageFilter()
        distance_filter.SetSquaredDistance(False)
        distance_filter.SetBackgroundValue(0)
        distance_img = distance_filter.Execute(seeds_img)

        # inflate seed points
        upper = self.dilateErodeDistance if self.dilateErodeDistance != 0 else 1
        seeds_img = sitk.BinaryThreshold(distance_img, 
                                         lowerThreshold=0, 
                                         upperThreshold=self.dilateErodeDistance, 
                                         insideValue=1)

        # combine inflated seed points and voids in the bone
        void_seeds_img = seeds_img | erode_img

        # connected threshold filter to select voids connected to seed points
        connected_filter = sitk.ConnectedThresholdImageFilter()
        connected_filter.SetLower(1)
        connected_filter.SetUpper(1)
        connected_filter.SetSeedList(self._seeds_crop)
        connected_filter.SetReplaceValue(1)
        connected_img = connected_filter.Execute(void_seeds_img)
        
        # remove inflated seed points from the voids
        connected_img = erode_img * connected_img

        return connected_img

    def dilateVoidVolume(self, connect_img, radius):
        """
        Morphologically dilate voids back to their original size.

        Args:
            connect_img (Image)
            radius (Image): dilate steps, in voxels

        Returns:
            Image
        """
        print("Applying dilate filter")
        dilate_filter = sitk.BinaryDilateImageFilter()
        dilate_filter.SetForegroundValue(1)
        dilate_filter.SetKernelRadius([radius,radius,radius])
        dilate_img = dilate_filter.Execute(connect_img)

        # apply mask to dilated voids to get volumes only inside the 
        #  endosteal boundary
        void_volume_img = dilate_img * self.contour_img

        return void_volume_img

    def growVoidVolume(self, ero1_img, iterations):
        """
        Apply level set region growing filter to the erosion segmentation.

        Args:
            ero1_img (Image)
            iterations (int): number of level set iterations, which determines
                              how much the region will expand

        Returns:
            Image
        """
        # distance map for level set filter
        print("Applying distance map filter")
        distance_filter = sitk.SignedMaurerDistanceMapImageFilter()
        distance_filter.SetInsideIsPositive(True)
        distance_filter.SetUseImageSpacing(False)
        distance_filter.SetBackgroundValue(0)
        distance_img = distance_filter.Execute(ero1_img)
        
        # level set requires spacing of [1,1,1] and float voxel type
        distance_img.SetSpacing([1,1,1])
        feature_img = sitk.Cast(self.model_img, sitk.sitkFloat32)
        feature_img.SetSpacing([1,1,1])

        # level set region growing
        print("Applying level set filter")
        ls_filter = sitk.ThresholdSegmentationLevelSetImageFilter()
        ls_filter.SetLowerThreshold(-999999)
        ls_filter.SetUpperThreshold(self.lower_threshold)
        ls_filter.SetMaximumRMSError(0.02)
        ls_filter.SetNumberOfIterations(iterations)
        ls_filter.SetCurvatureScaling(1)
        ls_filter.SetPropagationScaling(1)
        ls_filter.SetReverseExpansionDirection(True)
        ls_img = ls_filter.Execute(distance_img, feature_img)

        # restore spacing
        ls_img.SetSpacing(ero1_img.GetSpacing())

        # mask the level set output with periosteal mask
        output_img = sitk.BinaryThreshold(ls_img, lowerThreshold=1, insideValue=1)
        output_img = (output_img * self.contour_img) | ero1_img

        return output_img

    def labelVoidVolume(self, void_volume_img):
        """
        Label erosions with values that match the corresponding seed point numbers.

        Args:
            void_volume_img (Image)
        
        Returns:
            Image
        """
        # connected component filter to relabel erosions
        connected_filter = sitk.ConnectedComponentImageFilter()
        connected_filter.SetFullyConnected(True)
        relabeled_img = connected_filter.Execute(void_volume_img)

        relabel_map = {}
        for seed, erosionId in zip(self._seeds_crop, self.erosionIds):
            key = relabeled_img[seed]
            if key > 0:
                relabel_map[key] = erosionId
        
        relabel_filter = sitk.ChangeLabelImageFilter()

        relabel_filter.SetChangeMap(relabel_map)
        relabeled_img = relabel_filter.Execute(relabeled_img)

        return relabeled_img

    def execute(self, step):
        """
        Executes the specified step in the algorithm, 
        returns false if reached the end of the algorithm, 
        returns true otherwise.

        Args:
            step(int): 1 <= step <= self.stepNum
        """
        if step == 1:
            self._initializeParams()
            self.model_img = self.denoise(self.model_img, self.sigma)
        elif step == 2:
            self.ero1_img = self.createROI(self.model_img)
        elif step == 3:
            self.ero1_img = self.distanceVoidVolume(self.ero1_img, self.minimalRadius)
        elif step == 4:
            self.ero1_img = self.erodeVoidVolume(self.ero1_img, self.dilateErodeDistance)
        elif step == 5:
            self.ero1_img = self.connectVoidVolume(self.ero1_img)
        elif step == 6:
            self.ero1_img = self.dilateVoidVolume(self.ero1_img, self.dilateErodeDistance)
        elif step == 7:
            iterations = 100
            self.output_img = self.growVoidVolume(self.ero1_img, iterations)
        elif step == 8:
            self.output_img = self.labelVoidVolume(self.output_img)
        else: # the end of the algorithm
            return False
        return True

    def setModelImage(self, img):
        """
        Args:
            img (Image)
        """
        self.model_img = img
    
    def setContourImage(self, contour_img):
        """
        Args:
            contour_img (Image): Bounding box cut will be applied to it.
        """
        # threshhold to binarize mask
        thresh_img = sitk.BinaryThreshold(contour_img, lowerThreshold=1, insideValue=1)

        # bounding box cut
        lss_filter = sitk.LabelStatisticsImageFilter()
        lss_filter.Execute(thresh_img, thresh_img)
        bounds = lss_filter.GetBoundingBox(1)
        xmin_crop, xmax, ymin_crop, ymax, zmin_crop, zmax = bounds
        xmin_crop = round(xmin_crop) 
        ymin_crop = round(ymin_crop) 
        zmin_crop = round(zmin_crop) 
        xmax_crop = contour_img.GetWidth() - xmax 
        ymax_crop = contour_img.GetHeight() - ymax
        zmax_crop = contour_img.GetDepth() - zmax
        self.contour_img = sitk.Crop(thresh_img, 
                                     [xmin_crop, ymin_crop, zmin_crop],
                                     [xmax_crop, ymax_crop, zmax_crop])

    def _initializeParams(self):
        """
        Crop the bone model so that it occupies the same physcial space as the mask.
        Update the seed point coordinates based on the cropped bone model, 
        and remove seed points that are outside the periosteal mask.
        """
        width = self.contour_img.GetWidth()
        height = self.contour_img.GetHeight()
        depth = self.contour_img.GetDepth()
        spacing = self.model_img.GetSpacing()[0]
        contour_origin = self.contour_img.GetOrigin()
        model_origin = self.model_img.GetOrigin()
        model_size = self.model_img.GetSize()
        direction = self.model_img.GetDirection()

        # crop bone model
        model_img = sitk.Image(width, height, depth, self.model_img.GetPixelID())
        model_img.CopyInformation(self.contour_img)
        destination_x = round((model_origin[0] - contour_origin[0]) / spacing)
        destination_y = round((model_origin[1] - contour_origin[1]) / spacing)
        destination_z = round((model_origin[2] - contour_origin[2]) / spacing)

        r = sitk.VersorTransform()
        r.SetMatrix(direction)
        destination_index = r.TransformPoint((destination_x, destination_y, destination_z))
        destination_index = (round(destination_index[0]), round(destination_index[1]), round(destination_index[2]))
        paste_filter = sitk.PasteImageFilter()
        paste_filter.SetDestinationIndex(destination_index)
        paste_filter.SetSourceSize(model_size)
        self.model_img = paste_filter.Execute(model_img, self.model_img)
        
        # update seed points
        destination_x *= int(direction[0])
        destination_y *= int(direction[4])
        destination_z *= int(direction[8])
        self._seeds_crop = [(seed[0]+destination_x, seed[1]+destination_y, seed[2]+destination_z)
                            for seed in self.seeds]
        for i, seed in reversed(list(enumerate(self._seeds_crop))):
            is_in_range = ((0 <= seed[0] < width) and 
                           (0 <= seed[1] < height) and 
                           (0 <= seed[2] < depth))
            if not is_in_range:
                self._removeNthSeed(i)

    def setThresholds(self, lower_threshold, upper_threshold):
        """
        Args:
            lower_threshold (int)
            upper_threshold (int)
        """
        self.auto_thresh = False
        self.lower_threshold = lower_threshold
        self.upper_threshold = upper_threshold

    def setSigma(self, sigma):
        """
        Args:
            sigma (Double): Standard deviation in the Gaussian smoothing filter,
                            not normalized by image spacing.
        
        """
        self.sigma = sigma

    def setSeeds(self, seeds):
        """
        Args:
            seeds (list of list/tuple of int)
        """
        self.seeds = seeds
        self.erosionIds = list(range(1, len(seeds)+1))

    def setRadii(self, minimalRadius, dilateErodeDistance):
        """
        Args:
            minimalRadius (int[]): minimum erosion radius, used in the distance map filter
            dilateErodeDistance (int[]): kernel radius for dilate/erode filters
        """
        self.minimalRadius = minimalRadius
        self.dilateErodeDistance = dilateErodeDistance
    
    def setErosionIds(self, erosion_ids):
        """
        Args:
            erosionIds (list of int): list of seed point ids extracted from the seed point names, 
                                      the nth int in the list is the nth seed point id. This 
                                      decides which value the erosion corresponding with that seed
                                      point gets labeled.
        """
        if len(erosion_ids) == len(self.seeds):
            self.erosionIds = erosion_ids

    def _removeNthSeed(self, n):
        """
        Remove the nth seed from the seeds list.

        Args:
            n (int)
        """
        self._seeds_crop.pop(n)
        self.seeds.pop(n)
        self.erosionIds.pop(n)
        # self.minimalRadius.pop(n)
        # self.dilateErodeDistance.pop(n)

    def _cleanup(self):
        """
        Reset internal parameters.
        """
        pass

    def getOutput(self):
        return self.output_img

    def setThreshMethod(self, method):
        '''Set automatic thresholding method'''
        self.auto_thresh = True
        self.method = method