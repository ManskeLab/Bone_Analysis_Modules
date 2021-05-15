#-----------------------------------------------------
# ContourLogic.py
#
# Created by:  Mingjie Zhao
# Created on:  09-10-2020
#
# Description: This module draws the contours of the input bones 
#              and saves them in one labeled mask. Each bone will have a different label. 
#              The bones are first smoothened by a Gaussian filter.
#              Then, they are separated by either a connectivity filter or 
#              a user provided rough mask.
#              Maurer distance map is used to inflate and deflate each bone. 
#              Holes are filled inside each bone.
#              There are 8 steps. Each bone has to run Steps 4-8 separately.
#
#-----------------------------------------------------
# Usage:       This module is plugged into 3D Slicer, but can run on its own. 
#              When running on its own:
#              python ContourLogic.py inputImage outputImage lowerThreshold upperThreshold
#                                     boneNum [roughMask]
#
# Param:       inputImage: The input greyscale image to be contoured
#              outputImage: The output image to store the contour
#              lowerThreshold
#              upperThreshold
#              boneNum: Number of separate bone structures
#              roughMask: The file path of optional rough mask that helps separate bones
#
#-----------------------------------------------------
import SimpleITK as sitk

class ContourLogic:
    """This class provides methods for automatic contouring"""

    def __init__(self, img=None, lower=3000, upper=10000, boneNum=1, roughMask=None):
        self.img = img                     # bone model, will be reused
        self.output_img = None             # output image
        self.label_img = None              # image with each connected bone structures relabeled
        self.roughMask = roughMask         # rough mask
        self.lower_threshold = lower
        self.upper_threshold = upper
        self.boneNum = boneNum             # number of bone structures to be segmented
        self._step = 0                     # number of steps done
        self._stepNum = 5 * self.boneNum + 3 # number of steps in the algorithm
        self._dilateErodeRadius = 38       # dilate/erode radius
        self._margin = self._dilateErodeRadius + 2
        self._stats_filter = sitk.LabelStatisticsImageFilter()
        self._boundingbox = ()              # bounding box of extracted image, will be reused
    
    def binarize(self, img, lower, upper):
        thresh_img = sitk.BinaryThreshold(img,
                                          lowerThreshold=lower,
                                          upperThreshold=upper,
                                          insideValue=1)

        return thresh_img

    def denoise(self, img, sigma, foreground=1):
        """
        De-noise the image with a Gaussian filter.

        Args:
            img (Image)
            sigma (double): will be internally scaled by spacing. 
                            SimpleITK Gaussian filters take sigma with respect to spacing.
            foreground (int)
        
        Returns:
            Image
        """
        sigma_over_spacing = sigma * img.GetSpacing()[0]
        inside_value = 250
        max_inside_value = 255

        opening_filter = sitk.BinaryMorphologicalOpeningImageFilter()
        opening_filter.SetForegroundValue(foreground)
        opening_filter.SetKernelRadius(1)
        opening_img = opening_filter.Execute(img)

        thresh_img = sitk.BinaryThreshold(opening_img,
                                          lowerThreshold=foreground,
                                          upperThreshold=foreground,
                                          insideValue=inside_value)

        # gaussian smoothing filter
        print("Applying Gaussian filter")
        gaussian_filter = sitk.SmoothingRecursiveGaussianImageFilter()
        gaussian_filter.SetSigma(sigma_over_spacing)
        gaussian_img = gaussian_filter.Execute(thresh_img)
        
        thresh_img = sitk.BinaryThreshold(gaussian_img,
                                          lowerThreshold=inside_value/2,
                                          upperThreshold=max_inside_value,
                                          insideValue=foreground)

        return thresh_img

    def relabelWithMap(self, thresh_img, rough_mask):
        """
        Relabel each bone based on the rough mask.
        
        Args:
            thresh_img (Image)
            rough_mask (Image): rough mask that indicates how to separate the bones.
                                The labels should go from 1, 2,..., to N, without any skips.
        
        Returns:
            Image
        """
        label_img = thresh_img * rough_mask

        self._stats_filter.Execute(rough_mask, label_img)
        boneNum = self._stats_filter.GetNumberOfLabels() - 1
        self.setBoneNum(boneNum)

        return label_img

    def relabelWithConnect(self, img):
        """
        Relabel the connected bone structures from biggest to smallest. 
        The labels go from 1 (for the biggest), 2, 3,..., to N (for the smallest). 

        Args:
            img (Image)

        Returns:
            Image
        """
        # connectivity filter to label connected components
        print("Applying connectivity filter")
        connected_filter = sitk.ConnectedComponentImageFilter()
        connected_img = connected_filter.Execute(img)

        label_img = sitk.RelabelComponent(connected_img)
        
        # prepare for getting statisitcs of the labels
        self._stats_filter.Execute(img, label_img)
        boneNum = self._stats_filter.GetNumberOfLabels() - 1
        if boneNum < self.boneNum: # if number of bones are fewer than the provided number
            self.setBoneNum(boneNum)

        return label_img

    def extract(self, img, foreground):
        """
        Extract the bone with the foreground value, 
        and paste it to a larger image with sufficient margin space. 

        Args:
            img (Image)

        Returns:
            Image
        """
        margin = self._margin

        boundingbox = self._stats_filter.GetBoundingBox(foreground)
        self._boundingbox = boundingbox
        
        thresh_img = sitk.BinaryThreshold(img, 
                                          lowerThreshold=foreground, 
                                          upperThreshold=foreground, 
                                          insideValue=foreground)

        # crop img into small_img
        small_img = thresh_img[boundingbox[0]:boundingbox[1]+1, 
                               boundingbox[2]:boundingbox[3]+1,
                               boundingbox[4]:boundingbox[5]+1]

        # paste small_img to extract_img
        extract_width = small_img.GetWidth() + 2 * margin
        extract_height = small_img.GetHeight() + 2 * margin
        extract_depth = small_img.GetDepth() + 2 * margin
        extract_img = sitk.Image(extract_width, extract_height, extract_depth, sitk.sitkUInt8)

        destination_index = (margin, margin, margin)
        source_size = small_img.GetSize()
        paste_filter = sitk.PasteImageFilter()
        paste_filter.SetDestinationIndex(destination_index)
        paste_filter.SetSourceSize(source_size)
        extract_img = paste_filter.Execute(extract_img, small_img)

        return extract_img

    def dilate(self, img, radius, foreground):
        """
        Dilate the objects in the image.
        Args:
            img (Image)
            radius (Int): dilate steps, in voxels
            foreground (int): Only voxels with the foreground value are considered.
        Returns:
            Image
        """
        # dilate
        print("Applying dilate filter")
        dilate_filter = sitk.BinaryDilateImageFilter()
        dilate_filter.SetKernelRadius(radius)
        dilate_filter.SetForegroundValue(foreground)
        dilate_img = dilate_filter.Execute(img)

        return dilate_img

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

    def fillHole(self, img, foreground):
        """
        Fill holes inside the bone. 
        The fill hole filter is applied slice by slice in each of the three directions. 
        
        Args:
            img (Image)
            foreground (int): The output will be a binary image
                              of 0 and the foreground value.

        Returns:
            Image
        """
        # get img info
        width = img.GetWidth()
        height = img.GetHeight()
        depth = img.GetDepth()

        fill_hole_filter = sitk.BinaryFillholeImageFilter()
        fill_hole_filter.SetForegroundValue(foreground)
        
        print("Applying fill hole filter")
        vectorOfImages = sitk.VectorOfImage()
        # apply fill hole filter slice by slice in z direction
        for i in range(depth):
            im = img[:,:,i]
            contour = fill_hole_filter.Execute(im)
            vectorOfImages.push_back(contour)
        fill_hole_img = sitk.JoinSeries(vectorOfImages)
        vectorOfImages.clear()
        fill_hole_img.CopyInformation(img)
        # apply fill hole filter slice by slice in y direction
        for j in range(height):
            im = img[:,j,:]
            contour = fill_hole_filter.Execute(im)
            vectorOfImages.push_back(contour)
        fill_hole_img2 = sitk.JoinSeries(vectorOfImages)
        vectorOfImages.clear()
        fill_hole_img2 = sitk.PermuteAxes(fill_hole_img2, (0,2,1))
        fill_hole_img2.CopyInformation(img)
        # apply fill hole filter slice by slice in x direction
        for k in range(width):
            im = img[k,:,:]
            contour = fill_hole_filter.Execute(im)
            vectorOfImages.push_back(contour)
        fill_hole_img3 = sitk.JoinSeries(vectorOfImages)
        vectorOfImages.clear()
        fill_hole_img3 = sitk.PermuteAxes(fill_hole_img3, (2,0,1))
        fill_hole_img3.CopyInformation(img)

        fill_hole_img = fill_hole_img | fill_hole_img2 | fill_hole_img3

        return fill_hole_img

    def erode(self, img, radius, foreground):
        """
        Erode the objects in the image back to its original size. 
        
        Args:
            img (Image)
            radius (Int): erode steps, in voxels
            foreground (int): Only voxels with the foreground value are considered.
        
        Returns:
            Image
        """
        # erode to original size
        print("Applying erode filter")
        erode_filter = sitk.BinaryErodeImageFilter()
        erode_filter.SetKernelRadius(radius)
        erode_filter.SetForegroundValue(foreground)
        contour_img = erode_filter.Execute(img)

        return contour_img

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

    def pasteBack(self, extract_img):
        """
        Paste the extracted bone back to the original image. Refer to extract().

        Args:
            extract_img (Image)

        Returns:
            Image
        """
        margin = self._margin

        # remove margin and extract the bone from extract_img
        extract_width = extract_img.GetWidth()
        extract_height = extract_img.GetHeight()
        extract_depth = extract_img.GetDepth()
        small_img = extract_img[margin:extract_width-margin,
                                margin:extract_height-margin,
                                margin:extract_depth-margin]
        
        img_size = self.label_img.GetSize()
        img = sitk.Image(img_size, sitk.sitkUInt8)
        img.CopyInformation(self.label_img)

        # paste the bone back to the new image
        boundingbox = self._boundingbox
        destination_index = (boundingbox[0], boundingbox[2], boundingbox[4])
        source_size = small_img.GetSize()
        paste_filter = sitk.PasteImageFilter()
        paste_filter.SetDestinationIndex(destination_index)
        paste_filter.SetSourceSize(source_size)
        img = paste_filter.Execute(img, small_img)

        return img

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
                if (self.roughMask is None):
                    self.img = self.denoise(self.img, sigma=2)
            elif self._step == 3: # step 3
                if (self.roughMask is None): # separate bones with connectivity filter
                    self.label_img = self.relabelWithConnect(self.img)
                else:                        # separate bones with rough mask
                    self.label_img = self.relabelWithMap(self.img, self.roughMask)
            elif self._step == 4: # step 4
                self.img = self.extract(self.label_img, foreground=self.boneNum)
                if (self.roughMask is not None): # denoise the rough mask, may not be neccessary
                    self.img = self.denoise(self.img, sigma=2, foreground=self.boneNum)
            elif self._step == 5: # step 5
                #self.img = self.dilate(self.img, radius=self._dilateErodeRadius, foreground=self.boneNum)
                self.img = self.inflate(self.img, radius=self._dilateErodeRadius, foreground=self.boneNum)
            elif self._step == 6: # step 6
                self.img = self.fillHole(self.img, self.boneNum)
            elif self._step == 7: # step 7
                #self.img = self.erode(self.img, radius=self._dilateErodeRadius, foreground=self.boneNum)
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

    def setImage(self, img):
        """
        Args:
            img (Image)
        """
        self.img = img
    
    def setRoughMask(self, roughMask):
        """
        Args:
            roughMask (Image)
        """
        self.roughMask = roughMask
    
    def setThreshold(self, lower_threshold, upper_threshold):
        """
        Args:
            lower_threshold (int)
            upper_threshold (int)
        """
        self.lower_threshold = lower_threshold
        self.upper_threshold = upper_threshold
    
    def setBoneNum(self, boneNum):
        """
        Args:
            boneNum (int)
        """
        if boneNum < 1:
            self.boneNum = 1
        else:
            self.boneNum = boneNum
        self.stepNum = 5 * boneNum + 3
    
    def _cleanup(self):
        """
        Reset internal parameters.
        """
        self.output_img = None

    def getStepNum(self):
        """
        Returns:
            int: the total number of steps in the algorithm.
        """
        return self.stepNum

    def getOutput(self):
        return self.output_img


# execute this script on command line
if __name__ == "__main__":
    import argparse

    # Read the input arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('inputImage', help='The input image file path')
    parser.add_argument('outputImage', help='The output image file path')
    parser.add_argument('lowerThreshold', type=int)
    parser.add_argument('upperThreshold', type=int)
    parser.add_argument('boneNum', type=int, default=1, help='Number of separate bone structures')
    parser.add_argument('roughMask', nargs='?', default="", 
                         help='The file path of optional rough mask that helps separate bones')
    args = parser.parse_args()

    input_dir = args.inputImage
    output_dir = args.outputImage
    lower = args.lowerThreshold
    upper = args.upperThreshold
    boneNum = args.boneNum
    roughMask_dir = args.roughMask

    # read images
    img = sitk.ReadImage(input_dir)
    roughMask = None
    if (roughMask_dir != ""):
        roughMask = sitk.ReadImage(roughMask_dir)

    # create contour object
    contour = ContourLogic(img, lower, upper, boneNum, roughMask)

    # run contour algorithm
    print("Running contour script")
    while (contour.execute()):
        pass
    contour_img = contour.getOutput()

    # store contour
    print("Storing image in {}".format(output_dir))
    sitk.WriteImage(contour_img, output_dir)
