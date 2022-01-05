#-----------------------------------------------------
# CBCTCorticalBreakDetectionLogic.py
#
# Created by:  Mingjie Zhao
# Created on:  21-08-2021
#
# Description: This script implements the CBCT version of the automatic cortical 
#              break detection script by Michael Peters et al. It identifies all 
#              the cortical breaks that connect to both the periosteal and the 
#              endosteal boundaries. The method for segmentation of underlying
#              trabecular bone loss is modified to accomodate the lower resolution.
#
#-----------------------------------------------------
# Usage:       python CBCTCorticalBreakDetectionLogic.py inputImage inputContour outputImage 
#                                               voxelSize lowerThreshold upperThreshold
#                                               [corticalThickness] [dilateErodeDistance]
#
# Param:       inputImage: The input image file path
#              inputContour: The input contour file path
#              outputImage: The output image file path
#              voxelSize: Isotropic voxel size in millimetres
#              lowerThreshold
#              upperThreshold
#              sigma: Standard deviation for the Gaussian smoothing filter.
#              corticaThickness: Distance from the periosteal boundary 
#                                to the endosteal boundary, only erosions connected
#                                to both the periosteal and the endosteal boundaries
#                                are labeled, default=4
#              dilateErodeDistance: kernel radius for morphological dilation and 
#                                   erosion, default=1
#
#-----------------------------------------------------
import SimpleITK as sitk

class CBCTCorticalBreakDetectionLogic:
    def __init__(self, img=None, contour_img=None, voxelSize=250, lower=600, upper=10000, 
                 sigma=0.01, corticaThickness=1, dilateErodeDistance=0):
        self.img = img                         # original greyscale scan
        self.model_img = img                   # cropped greyscale scan
        self.peri_contour = None               # cropped periosteal boundary
        self.seg_img = None                    # bone segmentation
        self._boneNum = 1                      # number of separate bone structures, will be modified
        if ((self.model_img is not None) and (contour_img is not None)):
            self.setContour(contour_img)
        self.endo_contour = None              # endosteal boundary
        self.cortical_mask = None             # region between periosteal and endosteal boundaries
        self.background_img = None            # region outside of periosteal boundary
        self.breaks_img = None                # cortical breaks
        self.output_img = None
        self.voxelSize = voxelSize            # isotropic voxel size in millimetres
        self.lower_threshold = lower
        self.upper_threshold = upper
        self.sigma = sigma                    # Gaussian sigma
        self.corticalThickness = corticaThickness       # thickness of cortical shell in voxels
        self.dilateErodeDistance = dilateErodeDistance  # morphological kernel radius in voxels
        self.seeds = []                       # seed point inside each cortical break, will modified
        self.stepNum = 7
    
    def smoothen(self, img, sigma, lower, upper): # step 1
        """
        Denoise with a Gaussian filter and binarize the image with a threshold filter.

        Args:
            img (Image)
            sigma (Float)
            lower (int)
            upper (int)

        Returns:
            Image: bone is labeled with 1, and background is labeled with 0.
        """
        sigma_over_spacing = sigma * img.GetSpacing()[0]

        # gaussian smoothing filter
        print("Applying Gaussian filter")
        gaussian_filter = sitk.SmoothingRecursiveGaussianImageFilter()
        gaussian_filter.SetSigma(sigma_over_spacing)
        gaussian_img = gaussian_filter.Execute(img)

        thresh_img = sitk.BinaryThreshold(gaussian_img, 
                                          lowerThreshold=lower, 
                                          upperThreshold=upper, 
                                          insideValue=1)

        return thresh_img

    def deflate(self, img, radius, foreground):
        """
        Deflate the object in the image using distance transformation. 
        
        Args:
            img (Image)
            radius (Int): Deflate steps, in voxels
            foreground (int): Only voxels with the foreground value are considered.
        
        Returns:
            Image
        """
        # deflate with Maurer distance map filter
        print("Applying distance map filter")
        distance_filter = sitk.SignedMaurerDistanceMapImageFilter()
        distance_filter.SetSquaredDistance(False)
        distance_filter.SetInsideIsPositive(True)
        distance_img = distance_filter.Execute(img)

        deflate_img = sitk.BinaryThreshold(distance_img, 
                                           lowerThreshold=radius,
                                           insideValue=foreground)

        return deflate_img

    def createMasks(self): # step 2
        """
        Creates endo_contour, cortical_mask, and background_img.
        Endo_contour marks the space inside the endosteal boundary. For simplocity,
        the endosteal boundary is a constant distance away from the periosteal boundary,
        and that distance is specified by corticalThickness.
        Cortical_mask marks the space between the periosteal and endosteal boundaries.
        Background_img marks the space outside the periosteal boundary.
        """
        # erode peri_contour by [6] voxels to get the endosteal boundary, 
        #  which is [6] voxels away from the periosteal boundary/mask
        #  default thickness is 6 (6 * 0.061mm = 0.366mm)
        print("Applying erode filter")
        #erode_filter = sitk.BinaryErodeImageFilter()
        #erode_filter.SetForegroundValue(1)
        #erode_filter.SetKernelRadius(self._corticalThickness)
        #self.endo_contour = erode_filter.Execute(self.peri_contour)
        self.endo_contour = self.deflate(self.peri_contour, self.corticalThickness, 1)

        # subtract inner contour from contour to get cortical mask
        self.cortical_mask = self.peri_contour - self.endo_contour

        # invert to get the background
        invert_filter = sitk.InvertIntensityImageFilter()
        invert_filter.SetMaximum(1)
        self.background_img = invert_filter.Execute(self.peri_contour)

    def erodeBreaks(self, thresh_img, radius): # step 3
        """
        Morphologically erode cortical breaks to remove small gaps. 
        The erode distance will be specified by dilateErodeDistance.

        Args:
            breaks_img (Image)
            radius (Int): erode distance in voxels

        Returns:
            Image
        """
        # dilate bone by [1] voxel to remove small gaps
        #  default kernel radius is 1 (1 * 0.061mm = 0.061mm)
        print("Applying dilate filter")
        dilate_filter = sitk.BinaryDilateImageFilter()
        dilate_filter.SetForegroundValue(1)
        dilate_filter.SetKernelRadius(radius)
        breaks_img = dilate_filter.Execute(thresh_img)

        # apply cortical_mask to bone
        breaks_img = breaks_img * self.cortical_mask

        return breaks_img

    def connectBreaks(self, breaks_img): # step 4
        """
        Removes cortical breaks not attached to periosteal or endosteal boundaries.

        Args:
            breaks_img (Image)

        Returns:
            Image
        """
        # invert to select breaks, background, and trabecular region
        invert_filter = sitk.InvertIntensityImageFilter()
        invert_filter.SetMaximum(1)
        invert_img = invert_filter.Execute(breaks_img)

        # label breaks and background only
        breaks_background = sitk.Mask(invert_img, self.endo_contour, outsideValue=0, maskingValue=1)

        # connectivity filter to select background and breaks connected to periosteal surface
        background_seed = [0,0,0]
        connected_thr_filter = sitk.ConnectedThresholdImageFilter()
        connected_thr_filter.SetLower(1)
        connected_thr_filter.SetUpper(1)
        connected_thr_filter.SetSeedList([background_seed])
        connected_thr_filter.SetReplaceValue(1)
        breaks_background = connected_thr_filter.Execute(breaks_background)
        
        # label breaks and trabecular region only
        breaks_trabecular = (breaks_background * self.peri_contour) | self.endo_contour

        # connectivity filter to select trabecular region and breaks connected to trabecular region
        connected_filter = sitk.ConnectedComponentImageFilter()
        breaks_trabecular = connected_filter.Execute(breaks_trabecular)
        breaks_trabecular = sitk.RelabelComponent(breaks_trabecular)
        breaks_trabecular = sitk.BinaryThreshold(breaks_trabecular, 
                                                 lowerThreshold=1, upperThreshold=self._boneNum)

        # label cortical breaks only
        breaks_img = breaks_trabecular - self.endo_contour

        return breaks_img

    def dilateBreaks(self, breaks_img, radius): # step 5
        """
        Morphologically dilates cortical breaks back to their original size,
        and filters out tiny breaks. The erode distance will be specified by 
        dilateErodeDistance.

        Args:
            breaks_img (Image)
            radius (Int): dilate distance in voxels

        Returns:
            Image
        """
        # dilate cortical breaks by [1] voxel to original size
        #  default kernel radius is 1 (1 * 0.061mm = 0.061mm)
        #  kernel radius should be the same as the one in step 3
        print("Applying dilate filter")
        dilate_filter = sitk.BinaryDilateImageFilter()
        dilate_filter.SetForegroundValue(1)
        dilate_filter.SetKernelRadius(radius)
        breaks_img = dilate_filter.Execute(breaks_img)

        # apply cortical_mask to breaks
        breaks_img = breaks_img * self.cortical_mask

        # remove breaks less than 20*0.061^3 mm3 in size
        scale = 0.082 / self.voxelSize
        breaks_label = sitk.ConnectedComponent(breaks_img)
        minimumObjectSize_voxel = 20
        minimumObjectSize = round(minimumObjectSize_voxel * scale**3)
        breaks_label = sitk.RelabelComponent(breaks_label, minimumObjectSize=minimumObjectSize)
        breaks_img = sitk.BinaryThreshold(breaks_label, lowerThreshold=1)
        return breaks_img

    def growBreaks(self, breaks_img, iterations): # step 6
        """
        Apply level set region growing filter to the cortical breaks.
        This will attempt to capture the underlying trabecular bone loss.
        This step does not follow the original algorithm by Peters et al.
        
        Args:
            breaks_img (Image)
            iterations (int)
        
        Returns:
            Image
        """
        # dilate cortical breaks by 1 voxel for the level set filter
        print("Applying dilate filter")
        dilate_filter = sitk.BinaryDilateImageFilter()
        dilate_filter.SetForegroundValue(1)
        dilate_filter.SetKernelRadius(1)
        breaks_img = dilate_filter.Execute(breaks_img)

        # distance map for level set filter
        print("Applying distance map filter")
        distance_filter = sitk.SignedMaurerDistanceMapImageFilter()
        distance_filter.SetInsideIsPositive(True)
        distance_filter.SetUseImageSpacing(False)
        distance_filter.SetBackgroundValue(0)
        distance_img = distance_filter.Execute(breaks_img)

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
        ls_img.SetSpacing(breaks_img.GetSpacing())

        # mask the level set output with periosteal mask
        output_img = sitk.BinaryThreshold(ls_img, lowerThreshold=0, insideValue=1)
        output_img = output_img * self.peri_contour

        return output_img
    
    def maskToSeeds(self, breaks_img):
        """
        Convert cortical break mask to seed points.

        Args:
            breaks_img (Image)
        """
        # label each cortical break with a different label
        label_img = sitk.ConnectedComponent(breaks_img)
        label_img = sitk.RelabelComponent(label_img)

        stats_filter = sitk.LabelIntensityStatisticsImageFilter()
        stats_filter.Execute(label_img, self.model_img)
        labelNum = stats_filter.GetNumberOfLabels()

        for i in range(labelNum):
            seed = stats_filter.GetCentroid(i+1)
            seed = self.img.TransformPhysicalPointToIndex(seed)
            self.seeds.append(seed)

    def execute(self, step):
        """
        Executes the specified step in the algorithm, 
        returns false if reached the end of the algorithm, 
        returns true otherwise.

        Args:
            step(int): 1 <= step <= self.stepNum

        Returns:
            bool: False if reached the end of the algorithm, True otherwise.
        """
        if step == 1:
            self.seg_img = self.smoothen(self.model_img, self.sigma, self.lower_threshold, self.upper_threshold)
        elif step == 2:
            self._initializeParams()
            self.createMasks()
        elif step == 3:
            self.breaks_img = self.erodeBreaks(self.seg_img, self.dilateErodeDistance)
        elif step == 4:
            self.breaks_img = self.connectBreaks(self.breaks_img)
        elif step == 5:
            self.breaks_img = self.dilateBreaks(self.breaks_img, self.dilateErodeDistance)
            # breaks_img contains cortical breaks only and no trabecular bone loss
        elif step == 6:
            iterations = 50
            self.output_img = self.growBreaks(self.breaks_img, iterations)
            # output_img contains cortical breaks and trabecular bone loss
        elif step == 7:
            self.maskToSeeds(self.breaks_img)
            print(self.seeds)
        else:
            return False
        return True

    def _boundingBoxCut(self, img):
        """
        Crop the image so that it occupies the same physcial space as the mask.

        Args:
            img (Image)

        Returns:
            Image
        """
        # image info
        width = self.peri_contour.GetWidth()
        height = self.peri_contour.GetHeight()
        depth = self.peri_contour.GetDepth()
        spacing = img.GetSpacing()[0]
        contour_origin = self.peri_contour.GetOrigin()
        model_origin = img.GetOrigin()
        model_size = img.GetSize()
        direction = img.GetDirection()

        # crop image
        cropped_img = sitk.Image(width, height, depth, img.GetPixelID())
        cropped_img.CopyInformation(self.peri_contour)
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
        cropped_img = paste_filter.Execute(cropped_img, img)

        return cropped_img

    def _initializeParams(self):
        """
        Crop the preprocessed bone segmentation and the greyscale scan so that 
        they occupy the same physcial space as the mask.
        """
        # crop preprocessed bone segmentation to the same size as the mask
        self.seg_img = self._boundingBoxCut(self.seg_img)
        
        # crop greyscale scan to the same size as the mask
        self.model_img = self._boundingBoxCut(self.model_img)
        
    def setModel(self, img):
        """
        Args:
            img (Image)
        """
        self.img = img
        self.model_img = img
    
    def getSeg(self):
        return self.seg_img

    def setSeg(self, seg_img):
        """
        Args: 
            seg_img (Image): Preprocessed segmentation of the bone.
        """
        self.seg_img = seg_img

    def setContour(self, contour_img):
        """
        Sets periosteal surface and the number of separate bones in the scan.

        Args:
            contour_img (Image): Bounding box cut will be applied to it.
        """
        # threshhold to binarize mask
        thresh_img = sitk.BinaryThreshold(contour_img,
                                          lowerThreshold=1,
                                          insideValue=1)
        
        # bounding box cut
        margin = 2
        lss_filter = sitk.LabelStatisticsImageFilter()
        lss_filter.Execute(thresh_img, thresh_img)
        bounds = lss_filter.GetBoundingBox(1)
        xmin_crop, xmax, ymin_crop, ymax, zmin_crop, zmax = bounds
        xmin_crop = max(round(xmin_crop-margin), 0)
        ymin_crop = max(round(ymin_crop-margin), 0)
        zmin_crop = max(round(zmin_crop), 0)
        xmax_crop = max(contour_img.GetWidth() - xmax - margin, 0)
        ymax_crop = max(contour_img.GetHeight() - ymax - margin, 0)
        zmax_crop = max(contour_img.GetDepth() - zmax, 0)
        self.peri_contour = sitk.Crop(thresh_img, 
                                     [xmin_crop, ymin_crop, zmin_crop],
                                     [xmax_crop, ymax_crop, zmax_crop])

        # update _boneNum, which is the number of separate bones in the scan
        label_stat_filter = sitk.LabelStatisticsImageFilter()
        label_img = sitk.ConnectedComponent(contour_img)
        label_stat_filter.Execute(contour_img, label_img)
        self._boneNum = label_stat_filter.GetNumberOfLabels()

    def setThresholds(self, lower_threshold, upper_threshold):
        """
        Args:
            lower_threshold (int)
            upper_threshold (int)
        """
        self.lower_threshold = lower_threshold
        self.upper_threshold = upper_threshold

    def setVoxelSize(self, voxelSize):
        """
        Args:
            voxelSize (Float)
        """
        self.voxelSize = voxelSize

    def setSigma(self, sigma):
        """
        Args:
            sigma (Double): Standard deviation in the Gaussian smoothing filter,
                           not normalized by image spacing.
        
        """
        self.sigma = sigma
    
    def setCorticalThickness(self, corticalThickness):
        """
        Args:
            corticalThickness (Int): Define the distance from the periosteal boundary 
                                     to the endosteal boundary, only erosions connected
                                     to both the periosteal and the endosteal boundaries
                                     are labeled.
        """
        self.corticalThickness = corticalThickness

    def setDilateErodeDistance(self, dilateErodeDistance):
        """
        Args:
            dilateErodeDistance (Int): Distance for morphological dilation and erosion 
                                       in voxels.
        """
        self.dilateErodeDistance = dilateErodeDistance

    def getOutput(self):
        return self.output_img

    def getSeeds(self):
        return self.seeds


# run this script on command line
if __name__ == "__main__":
    import argparse

    # Read the input arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('inputImage', help='The input scan file path')
    parser.add_argument('inputContour', help='The input contour file path')
    parser.add_argument('outputImage', help='The output image file path')
    parser.add_argument('voxelSize', type=float, help='Isotropic voxel size in millimetres')
    parser.add_argument('lowerThreshold', type=int)
    parser.add_argument('upperThreshold', type=int)
    parser.add_argument('sigma', type=float, help='Standard deviation for the Gaussian smoothing filter')
    parser.add_argument('corticalThickness', type=int, nargs='?', default=4, 
                        help='Distance from the periosteal boundary to the endosteal boundary, only erosions connected to both the periosteal and the endosteal boundaries are labeled, default=4')
    parser.add_argument('dilateErodeDistance', type=int, nargs='?', default=1,
                        help='kernel radius for morphological dilation and erosion')
    args = parser.parse_args()

    input_dir = args.inputImage
    contour_dir = args.inputContour
    output_dir = args.outputImage
    voxelSize = args.voxelSize
    lower = args.lowerThreshold
    upper = args.upperThreshold
    sigma = args.sigma
    corticalThickness = args.corticalThickness
    dilateErodeDistance = args.dilateErodeDistance

    # read images
    img = sitk.ReadImage(input_dir)
    contour = sitk.ReadImage(contour_dir)

    # create erosion logic object
    erosion = CBCTCorticalBreakDetectionLogic(img, contour, voxelSize, lower, upper, 
                                     sigma, corticalThickness, dilateErodeDistance)

    # identify erosions
    step = 2
    print("Running automatic erosion detection script")
    while (erosion.execute(step)):
        step += 1
    erosion_img = erosion.getOutput()

    # store erosion_img in output_dir
    print("Storing image in "+output_dir)
    sitk.WriteImage(erosion_img, output_dir)
