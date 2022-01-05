#-----------------------------------------------------
# PetersCorticalBreakDetectionLogic.py
#
# Created by:  Mingjie Zhao
# Created on:  26-05-2021
#
# Description: This script implements the automatic cortical break detection script
#              by Michael Peters et al. It identifies all the cortical breaks
#              that connect to both the periosteal and the endosteal boundaries
#              as well as underlying trabecular bone loss.
#
# Updated 2021-09-30 Sarah Manske to run from command line, beginning at step 1 
#               i.e., generate the seg/preprocessed file within the script
#-----------------------------------------------------
# Usage:       python PetersCorticalBreakDetectionLogicCommandLine.py inputImage [--inputContour] [--outputImage]
#                                                 [--voxelSize] [--lowerThreshold] [--upperThreshold]
#                                                 [--corticalThickness] [--dilateErodeDistance]
#
# Param:       inputImage: The input image file path
#              inputContour: The input contour file path, default=[inputImage]_MASK
#              outputImage: The output image file path, default=[inputImage]_BREAKS
#              outputSeeds: The output seeds csv file path, default=[inputImage]_SEEDS
#              voxelSize: Isotropic voxel size in micrometres, default=82
#              lowerThreshold: default=3000
#              upperThreshold: default=10000
#              sigma: Standard deviation for the Gaussian smoothing filter, default=0.8
#              corticaThickness: Distance from the periosteal boundary
#                                to the endosteal boundary, only erosions connected
#                                to both the periosteal and the endosteal boundaries
#                                are labeled, default=4
#              dilateErodeDistance: kernel radius for morphological dilation and
#                                   erosion, default=1
#
#-----------------------------------------------------
import SimpleITK as sitk
import pdb
import csv

class PetersCorticalBreakDetectionLogic:
    def __init__(self, img=None, contour_img=None, voxelSize=82, lower=3000, upper=10000,
                 sigma=0.8, corticaThickness=4, dilateErodeDistance=1):
        self.model_img = img                   # greyscale scan
        self.peri_contour = None               # periosteal boundary
        self.seg_img = None                    # bone segmentation
        self._boneNum = 1                      # number of separate bone structures, will be modified
        if contour_img is not None:
            self.setContour(contour_img)
        self.endo_contour = None              # endosteal boundary
        self.cortical_mask = None             # region between periosteal and endosteal boundaries
        self.background_img = None            # region outside of periosteal boundary
        self.breaks_img = None                # cortical breaks
        self.output_img = None
        self.voxelSize = voxelSize            # isotropic voxel size in micrometres
        self.lower_threshold = lower
        self.upper_threshold = upper
        self.sigma = sigma                    # Gaussian sigma
        self.corticalThickness = corticaThickness       # thickness of cortical shell in voxels
        self.dilateErodeDistance = dilateErodeDistance  # morphological kernel radius in voxels
        self.seeds = []                       # seed point inside each cortical break, will modified
        self.stepNum = 12

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
        distance_filter = sitk.SignedDanielssonDistanceMapImageFilter()
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
        scale = 82 / self.voxelSize
        breaks_label = sitk.ConnectedComponent(breaks_img)
        minimumObjectSize_voxel = 20
        minimumObjectSize = round(minimumObjectSize_voxel * scale**3)
        breaks_label = sitk.RelabelComponent(breaks_label, minimumObjectSize=minimumObjectSize)
        breaks_img = sitk.BinaryThreshold(breaks_label, lowerThreshold=1)
        return breaks_img

    def createROI(self, thresh_img): # step 6
        """
        Label voids inside the periosteal surface as ROI.

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

        # apply periosteal mask to the inverted image
        void_volume_img = self.peri_contour * void_volume_img

        return void_volume_img

    def distanceVoidVolume(self, void_volume_img, radius): # step 7
        """
        Select voids of large radius/diameter.
        That radius will be the same as corticalThickness.

        Args:
            void_volume_img (Image)
            radius (int): minimum radius of the erosions to be labeled, in voxels

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

    def erodeVoidVolume(self, void_volume_img, radius): # step 8
        """
        Morphologically erode voids to remove connections and to
        prevent erosions from leaking into the trabecular space.
        The erode distance will be the same as corticalThickness.

        Args:
            void_volume_img (Image)
            radius (int): erode distance in voxels

        Returns:
            Image
        """
        print("Applying erode filter")
        erode_filter = sitk.BinaryErodeImageFilter()
        erode_filter.SetForegroundValue(1)
        erode_filter.SetKernelRadius([radius,radius,radius])
        erode_img = erode_filter.Execute(void_volume_img)

        return erode_img

    def connectVoidVolume(self, erode_img, breaks_img, distance): # step 9
        """
        Removes trabecular voids farther than the specified distance away from the cortical breaks.
        That distance will be the same as corticalThickness.
        In the original method by Peters el at., any morphologically eroded voids that are
        not attached to the cortical breaks are removed. But here an epsilon distance is considered.

        Args:
            erode_img (Image)
            breaks_img (Image)
            distance (int)

        Returns:
            Image
        """
        dilate_filter = sitk.BinaryDilateImageFilter()
        dilate_filter.SetForegroundValue(1)
        dilate_filter.SetKernelRadius(distance)
        dilated_breaks = dilate_filter.Execute(breaks_img)
        dilated_breaks = sitk.Mask(dilated_breaks, self.seg_img, outsideValue=0, maskingValue=1)

        # erosion_background consists of (voids + dilated cortical breaks + background)
        erosion_background = erode_img | dilated_breaks | self.background_img

        # connectivity filter
        connected_filter = sitk.ConnectedComponentImageFilter()
        connect_img = connected_filter.Execute(erosion_background)

        # relabel objects from large to small
        relabeled_img = sitk.RelabelComponent(connect_img)

        # select the largest object, which consists of erosion and background
        erosion_background = sitk.BinaryThreshold(relabeled_img, lowerThreshold=1, upperThreshold=1)

        # extract voids from (voids + dilated cortical breaks + background)
        connect_img = erosion_background * erode_img

        return connect_img

    def dilateVoidVolume(self, connect_img, radius): # step 10
        """
        Morphologically dilate voids back to their original size.
        The dilate distance will be the same as corticalThickness.

        Args:
            connect_img (Image)
            radius (int): dilate distance in voxels

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

    def combineVoidVolume(self, void_volume_img, breaks_img): # step 11
        """
        Combine cortical breaks and underlying trabecular voids.

        Args:
            void_volume_img (Image): trabecular voids inside the endosteal boundary
            breaks_img (Image): cortical breaks

        Returns:
            Image
        """
        # combine dilated voids and cortical breaks
        erosion_img = sitk.Mask(void_volume_img, breaks_img, outsideValue=1, maskingValue=1)

        return erosion_img

    def maskToSeeds(self, breaks_img): # step 12
        """
        Convert cortical break mask to seed points.

        Args:
            breaks_img (Image)
        """
        # label each cortical break with a different label
        label_img = sitk.ConnectedComponent(breaks_img)
        label_img = sitk.RelabelComponent(label_img)

        stats_filter = sitk.LabelIntensityStatisticsImageFilter()
        stats_filter.Execute(label_img, self.seg_img)
        labelNum = stats_filter.GetNumberOfLabels()

        for i in range(labelNum):
            seed = stats_filter.GetCentroid(i+1)
            seed = self.model_img.TransformPhysicalPointToIndex(seed)
            self.seeds.append(seed)

    def execute(self, step):
        """
        Executes the specified step in the algorithm.

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
            self.output_img = self.createROI(self.seg_img)
        elif step == 7:
            self.output_img = self.distanceVoidVolume(self.output_img, self.corticalThickness)
        elif step == 8:
            self.output_img = self.erodeVoidVolume(self.output_img, self.corticalThickness)
        elif step == 9:
            self.output_img = self.connectVoidVolume(self.output_img, self.breaks_img, self.corticalThickness)
        elif step == 10:
            self.output_img = self.dilateVoidVolume(self.output_img, self.corticalThickness)
        elif step == 11:
            self.output_img = self.combineVoidVolume(self.output_img, self.breaks_img)
            # output_img contains cortical breaks and trabecular bone loss
        elif step == 12:
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

    def setModel(self, img):
        """
        Args:
            img (Image)
        """
        self.model_img = img

    def getModel(self):
        return self.model_img

    def setSeg(self, seg_img):
        """
        Args:
            seg_img (Image): Preprocessed segmentation of the bone.
        """
        self.seg_img = sitk.BinaryThreshold(seg_img, lowerThreshold=1, insideValue=1)

    def getSeg(self):
        return self.seg_img

    def setContour(self, contour_img):
        """
        Sets periosteal surface and the number of separate bones in the scan.

        Args:
            contour_img (Image): Bounding box cut will be applied to it.
        """
        # threshhold to binarize mask
        thresh_img = sitk.BinaryThreshold(contour_img, lowerThreshold=1, insideValue=1)

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
            voxelSize (Float): in millimetres
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
            corticalThickness (Int): The distance from the periosteal boundary
                                     to the endosteal boundary, only erosions connected
                                     to both the periosteal and the endosteal boundaries
                                     are labeled.
        """
        self.corticalThickness = corticalThickness

    def setDilateErodeDistance(self, dilateErodeDistance):
        """
        Args:
            dilateErodeDistance (Int): Distance for morphological dilation and erosion
                                       of cortical breaks in voxels.
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
    parser.add_argument('-ic', '--inputContour', help='The input contour file path, default=[inputImage]_MASK', default="_MASK.mha", metavar='')
    parser.add_argument('-oi', '--outputImage', help='The output image file path, default=[inputImage]_BREAKS', default="_BREAKS.nrrd", metavar='')
    parser.add_argument('-os', '--outputSeeds', help='The output seeds csv file path, default=[inputImage]_SEEDS', default="_SEEDS.csv", metavar='')
    parser.add_argument('-vs', '--voxelSize', type=float, help='Isotropic voxel size in micrometres, default=82', default=82, metavar='')
    parser.add_argument('-lt', '--lowerThreshold', help='default=3000', type=int, default=3000, metavar='')
    parser.add_argument('-ut', '--upperThreshold', help='default=10000', type=int, default=10000, metavar='')
    parser.add_argument('-sg', '--sigma', type=float, help='Standard deviation for the Gaussian smoothing filter, default=0.8', default=0.8, metavar='')
    parser.add_argument('-ct', '--corticalThickness', type=int, default=4,
                        help='Distance from the periosteal boundary to the endosteal boundary, only erosions connected to both the periosteal and the endosteal boundaries are labeled, default=4', metavar='')
    parser.add_argument('-ded', '--dilateErodeDistance', type=int, default=1,
                        help='kernel radius for morphological dilation and erosion, default=1', metavar='')
    args = parser.parse_args()

    input_dir = args.inputImage
    contour_dir = args.inputContour
    output_dir = args.outputImage
    seeds_dir = args.outputSeeds
    voxelSize = args.voxelSize
    lower = args.lowerThreshold
    upper = args.upperThreshold
    sigma = args.sigma
    corticalThickness = args.corticalThickness
    dilateErodeDistance = args.dilateErodeDistance

    #correct file directiories (default or incorrect file extension)
    if contour_dir == "_MASK.mha":
        contour_dir = input_dir[:input_dir.index('.')] + contour_dir
    if output_dir == "_BREAKS.nrrd":
        output_dir = input_dir[:input_dir.index('.')] + output_dir
    elif output_dir.find('.') == -1:
        output_dir += ".nrrd"
    if seeds_dir == "_SEEDS.csv":
        seeds_dir = input_dir[:input_dir.index('.')] + seeds_dir
    elif seeds_dir[-4] != ".csv":
        seeds_dir += ".csv"

    # read images
    img = sitk.ReadImage(input_dir)
    contour = sitk.ReadImage(contour_dir)

    # create erosion logic object
    erosion = PetersCorticalBreakDetectionLogic(img, contour, voxelSize, lower, upper,
                                       sigma, corticalThickness, dilateErodeDistance)

    # identify erosions
    step = 1
    print("Running automatic erosion detection script")
    while (erosion.execute(step)):
        step += 1
    erosion_img = erosion.getOutput()
    seeds_list = erosion.getSeeds()

    # store erosion_img in output_dir
    print("Storing image in "+output_dir)
    sitk.WriteImage(erosion_img, output_dir)

    #store erosion seeds
    print("Storing seeds in "+seeds_dir)
    with open(seeds_dir, 'w', newline='') as f:
        writer = csv.writer(f)
        for i in range(len(seeds_list)):
            writer.writerow([i] + list(seeds_list[i]))
