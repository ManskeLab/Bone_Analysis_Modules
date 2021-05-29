#-----------------------------------------------------
# Erosion.py
#
# Created by:  Mingjie Zhao
# Created on:  26-05-2021
#
# Description: This script implements the automatic erosion detection script
#              by Michael Peters. It denoises the scan first, labels all the
#              cortical breaks, then labels all the underlying trabecular
#              voids connected to those cortical breaks, and lastly combine
#              the cortical breaks and the trabecular voids. Only those cortical
#              breaks attached to both the periosteal and endosteal boundaries
#              are labeled. Morphological operations are used to separate 
#              trabecular bone loss from trabecular space.
#              There are 11 steps. Measurements are for XtremeCT II.
#
#-----------------------------------------------------
# Usage:       python Erosion.py inputImage inputContour outputImage 
#                                lowerThreshold upperThreshold
#                                [minimalRadius] [morphologicalRadius]
#
# Param:       inputImage: The input image file path
#              inputContour: The input contour file path
#              outputImage: The output image file path
#              lowerThreshold
#              upperThreshold
#              boneNum: Minimal erosion radius in voxels, default=3
#              roughMask: Morphological kernel radius in voxels, default=5
#
#-----------------------------------------------------

import SimpleITK as sitk

class Erosion:
    def __init__(self, img=None, contour_img=None, lower=2900, upper=10000, 
                 minimalRadius=3, morphologicalRadius=5):
        self.model_img = img                   # greyscale scan
        self.peri_contour = None               # periosteal boundary
        self._boneNum = 1                      # number of separate bone structures, default=1
        if ((self.model_img is not None) and (contour_img is not None)):
            self.setContour(contour_img)
        self.endo_contour = None              # endosteal boundary
        self.cortical_mask = None             # outer contour minus inner contour
        self.background_img = None            # region outside of outer contour
        self.breaks_img = None                # cortical breaks
        self.output_img = None
        self.lower_threshold = lower
        self.upper_threshold = upper
        self.minimalRadius = minimalRadius               # for distance transformation
        self.morphologicalRadius = morphologicalRadius   # for morphological operations
        self._corticalThickness = morphologicalRadius    # thickness cortical shell
        self._step = 0
    
    def smoothen(self, img, lower, upper):
        """
        Binarize the bone with global thresholds, denoise with a Gaussian filter, 
        and remove small bone particles less than 420 voxels (0.094 mm3). 

        Args:
            img (Image)
            lower (int)
            upper (int)

        Returns:
            Image: bone is labeled with 1, and background is labeled with 0.
        """
        sigma_over_spacing = img.GetSpacing()[0]

        # gaussian smoothing filter
        print("Applying Gaussian filter")
        gaussian_filter = sitk.SmoothingRecursiveGaussianImageFilter()
        gaussian_filter.SetSigma(sigma_over_spacing)
        gaussian_img = gaussian_filter.Execute(img)

        thresh_img = sitk.BinaryThreshold(gaussian_img, 
                                          lowerThreshold=lower,
                                          upperThreshold=upper,
                                          insideValue=1)

        # remove bone particles less than 420 voxels in size
        connected_filter = sitk.ConnectedComponentImageFilter()
        connect_img = connected_filter.Execute(thresh_img)
        label_img = sitk.RelabelComponent(connect_img, minimumObjectSize=420)
        thresh_img = sitk.BinaryThreshold(label_img,
                                          lowerThreshold=1,
                                          upperThreshold=10000)
        return thresh_img

    def maskBreaks(self, thresh_img): # step 2
        """
        Creates endo_contour, cortical_mask, and background_img,
        applies cortical_mask to the bone to get cortical shell.

        Args:
            thresh_img (Image)

        Returns:
            Image
        """
        # erode by [5] voxels to get endosteal boundary, 
        #  so that it is [5] voxels away from the periosteal boundary/mask
        #  default thickness is 5
        print("Applying erode filter")
        erode_filter = sitk.BinaryErodeImageFilter()
        erode_filter.SetForegroundValue(1)
        erode_filter.SetKernelRadius([self._corticalThickness,self._corticalThickness,0])
        self.endo_contour = erode_filter.Execute(self.peri_contour)

        # subtract inner contour from contour to get cortical mask
        self.cortical_mask = self.peri_contour - self.endo_contour

        # invert to get the background
        invert_filter = sitk.InvertIntensityImageFilter()
        invert_filter.SetMaximum(1)
        self.background_img = invert_filter.Execute(self.peri_contour)

        # apply cortical_mask to thresh_img
        breaks_img = thresh_img * self.cortical_mask

        return breaks_img

    def erodeBreaks(self, breaks_img): # step 3
        """
        Erode cortical breaks by 1 voxel (0.061mm) to remove small gaps.

        Args:
            breaks_img (Image)

        Returns:
            Image
        """
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

        # connectivity filter to select background and breaks connected to background
        background_seed = [0,0,0]
        connected_thr_filter = sitk.ConnectedThresholdImageFilter()
        connected_thr_filter.SetLower(1)
        connected_thr_filter.SetUpper(1)
        connected_thr_filter.SetSeedList([background_seed])
        connected_thr_filter.SetReplaceValue(1)
        breaks_background = connected_thr_filter.Execute(breaks_background)
        
        # label breaks and trabecular region only
        breaks_trabecular = sitk.Mask(breaks_background, self.background_img, outsideValue=0, maskingValue=1)
        breaks_trabecular = sitk.Mask(breaks_trabecular, self.endo_contour, outsideValue=1, maskingValue=1)

        # connectivity filter to select trabecular region and breaks connected to trabecular region
        connected_filter = sitk.ConnectedComponentImageFilter()
        breaks_trabecular = connected_filter.Execute(breaks_trabecular)
        breaks_trabecular = sitk.RelabelComponent(breaks_trabecular)
        breaks_trabecular = sitk.BinaryThreshold(breaks_trabecular, 
                                                 lowerThreshold=1, upperThreshold=self.boneNum)

        # label cortical breaks only
        breaks_img = breaks_trabecular - self.endo_contour

        return breaks_img

    def dilateBreaks(self, breaks_img): # step 5
        """
        Dilates cortical breaks by 1 voxel to their original size,
        and filters out breaks less than 48 voxels in size.

        Args:
            breaks_img (Image)

        Returns:
            Image
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
        breaks_label = sitk.ConnectedComponent(breaks_img)
        breaks_label = sitk.RelabelComponent(breaks_label, minimumObjectSize=48)
        breaks_img = sitk.BinaryThreshold(breaks_label, lowerThreshold=1)
        return breaks_img

    def createROI(self, thresh_img): # step 6
        """
        Label voids in the bone and background as ROI.

        Args:
            thresh_img (Image)

        Returns:
            Image: All voids inside ROI are marked with the value 1, 
                   and all other regions are marked with 0. 
        """
        # invert to select background and voids in the bone
        invert_filter = sitk.InvertIntensityImageFilter()
        invert_filter.SetMaximum(1)
        void_volume_img = invert_filter.Execute(thresh_img)

        void_volume_img = self.peri_contour * void_volume_img

        return void_volume_img

    def distanceVoidVolume(self, void_volume_img, radius):
        """
        Select voids of large diameter. 

        Args:
            void_volume_img (Image)
            radius (int): minimum radius of the erosions to be selected, in voxels

        Returns:
            Image
        """
        print("Applying distance map")
        distance_filter = sitk.SignedMaurerDistanceMapImageFilter()
        distance_filter.SetSquaredDistance(False)
        distance_filter.SetBackgroundValue(1)
        inner_img = distance_filter.Execute(void_volume_img)

        inner_img = sitk.BinaryThreshold(inner_img,
                                        lowerThreshold=1,
                                        upperThreshold=radius,
                                        insideValue=1)
        inner_img = void_volume_img - inner_img

        distance_filter.SetBackgroundValue(0)
        outer_img = distance_filter.Execute(inner_img)

        outer_img = sitk.BinaryThreshold(outer_img,
                                         lowerThreshold=1,
                                         upperThreshold=radius,
                                         insideValue=1)
        distance_img = outer_img + inner_img

        return distance_img

    def erodeVoidVolume(self, void_volume_img, radius):
        """
        Morphologically erode voids to remove connections and to
        prevent erosions from leaking into the trabecular space.

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

    def connectVoidVolume(self, erode_img, breaks_img): # step 9
        """
        Removes voids not attached to cortical breaks, 
        and those not attached to periosteal boundaries

        Args:
            erode_img (Image)
            breaks_img (Image)

        Returns:
            Image
        """
        # erosion_background consists of (voids + cortical breaks + background)
        erosion_background = sitk.Mask(erode_img, breaks_img, outsideValue=1, maskingValue=1)
        erosion_background += self.background_img

        # connectivity filter
        connected_filter = sitk.ConnectedComponentImageFilter()
        connect_img = connected_filter.Execute(erosion_background)

        # relabel objects from large to small
        relabeled_img = sitk.RelabelComponent(connect_img)

        # select the largest object, which consists of erosion and background
        erosion_background = sitk.BinaryThreshold(relabeled_img, lowerThreshold=1, upperThreshold=1)

        # apply mask to (void volumes + breaks + background)
        # to get void volumes
        connect_img = erosion_background * self.endo_contour

        return connect_img

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
        void_volume_img = dilate_img * self.peri_contour

        return void_volume_img

    def combineVoidVolume(self, void_volume_img, breaks_img, thresh_img, radius):
        """
        Combine dilated voids and cortical breaks, dilate the result,
        and mask ROI with it in order to capture small erosions;
        the three images should occupy the same physical space

        Args:
            void_volume_img (Image): voids inside the endosteal boundary
            breaks_img (Image): cortical breaks
            thresh_img (Image): bone
            radius (int): dilate steps, in voxels

        Returns:
            Image
        """
        # combine dilated voids and cortical breaks
        erosion_img = sitk.Mask(void_volume_img, breaks_img, outsideValue=1, maskingValue=1)

        return erosion_img

    def execute(self):
        """
        Executes the next step in the algorithm, 
        returns false if reached the end of the algorithm, 
        returns true otherwise
        """
        self._step += 1
        if self._step == 1:
            self.model_img = self.smoothen(self.model_img, self.lower_threshold, self.upper_threshold)
        elif self._step == 2:
            self.breaks_img = self.maskBreaks(self.model_img)
        elif self._step == 3:
            self.breaks_img = self.erodeBreaks(self.breaks_img)
        elif self._step == 4:
            self.breaks_img = self.connectBreaks(self.breaks_img)
        elif self._step == 5:
            self.breaks_img = self.dilateBreaks(self.breaks_img)
            # so far, breaks_img contains cortical breaks only
        elif self._step == 6:
            self.output_img = self.createROI(self.model_img)
        elif self._step == 7:
            self.output_img = self.distanceVoidVolume(self.output_img, self.minimalRadius)
        elif self._step == 8:
            self.output_img = self.erodeVoidVolume(self.output_img, self.morphologicalRadius)
        elif self._step == 9:
            self.output_img = self.connectVoidVolume(self.output_img, self.breaks_img)
        elif self._step == 10:
            self.output_img = self.dilateVoidVolume(self.output_img, self.morphologicalRadius)
        elif self._step == 11:
            radius = 2
            self.output_img = self.combineVoidVolume(self.output_img, self.breaks_img, 
                                                     self.model_img, radius)
            # output_img contains cortical breaks and voids
        else:
            self._step = 0
            return False
        return True

    def setModelImg(self, img):
        """
        Args:
            img (Image)
        """
        self.model_img = img
    
    def setContour(self, contour):
        """
        Sets periosteal contour and the number of separate bones in the scan

        Args:
            contour_img (Image)
        """
        # threshhold to binarize mask
        thresh_img = sitk.BinaryThreshold(contour,
                                          lowerThreshold=1,
                                          insideValue=1)
        
        # paste mask to a blank image that matches the size of the scan
        #  this step is to make sure mask lies in the same physical space as the scan
        img_width = self.model_img.GetWidth()
        img_height = self.model_img.GetHeight()
        img_depth = self.model_img.GetDepth()
        img_spacing = self.model_img.GetSpacing()[0]
        self.peri_contour = sitk.Image(img_width, img_height, img_depth, sitk.sitkUInt8)
        self.peri_contour.CopyInformation(self.model_img)
        destination_index = (int(thresh_img.GetOrigin()[0]/img_spacing),
                             int(thresh_img.GetOrigin()[1]/img_spacing),
                             int(thresh_img.GetOrigin()[2]/img_spacing))
        source_size = thresh_img.GetSize()
        paste_filter = sitk.PasteImageFilter()
        paste_filter.SetDestinationIndex(destination_index)
        paste_filter.SetSourceSize(source_size)
        self.peri_contour = paste_filter.Execute(self.peri_contour, thresh_img)

        # update boneNum
        label_img = sitk.ConnectedComponent(contour)
        label_stat_filter = sitk.LabelStatisticsImageFilter()
        label_stat_filter.Execute(contour, label_img)
        self.boneNum = label_stat_filter.GetNumberOfLabels()

    def setThreshold(self, lower_threshold, upper_threshold):
        """
        Args:
            lower_threshold (int)
            upper_threshold (int)
        """
        self.lower_threshold = lower_threshold
        self.upper_threshold = upper_threshold

    def setRadii(self, minimalRadius, morphologicalRadius):
        """
        Args:
            minimalRadius (int): minimum erosion radius, used in the distance map filter
            morphologicalRadius (int): kernel radius for dilate/erode filters
        """
        self.minimalRadius = minimalRadius
        self.morphologicalRadius = morphologicalRadius

    def getOutput(self):
        return self.output_img


if __name__ == "__main__":
    import argparse

    # Read the input arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('inputImage', help='The input scan file path')
    parser.add_argument('inputContour', help='The input contour file path')
    parser.add_argument('outputImage', help='The output image file path')
    parser.add_argument('lowerThreshold', type=int)
    parser.add_argument('upperThreshold', type=int)
    parser.add_argument('minimalRadius', type=int, nargs='?', default=3, 
                        help='Minimal erosion radius in voxels, default=3')
    parser.add_argument('morphologicalRadius', type=int, nargs='?', default=5,
                        help='Morphological kernel radius in voxels, default=5')
    args = parser.parse_args()

    input_dir = args.inputImage
    contour_dir = args.inputContour
    output_dir = args.outputImage
    lower = args.lowerThreshold
    upper = args.upperThreshold
    minimalRadius = args.minimalRadius
    morphologicalRadius = args.morphologicalRadius

    # read images
    img = sitk.ReadImage(input_dir)
    contour = sitk.ReadImage(contour_dir)

    # create erosion logic object
    erosion = Erosion(img, contour, lower, upper, 
                      minimalRadius, morphologicalRadius)

    # identify erosions
    print("Running automatic erosion detection script")
    while (erosion.execute()):
        pass
    erosion_img = erosion.getOutput()

    # store erosion_img in output_dir
    print("Storing image in "+output_dir)
    sitk.WriteImage(erosion_img, output_dir)
