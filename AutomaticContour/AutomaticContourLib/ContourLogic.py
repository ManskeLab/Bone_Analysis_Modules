#-----------------------------------------------------
# ContourLogic.py
#
# Created by:  Mingjie Zhao
# Created on:  09-10-2020
#
# Description: This module creates the contour of the input image 
#              and saves it as a binary mask. The bones are first separated
#              by either a connectivity filter or a user provided label map.
#              The input image is then smoothened by a Gaussian filter, 
#              binarized by a global threshold and closed holes by 
#              morphological closing operations (i.e. dilate, connectivity, and erode). 
#              There are 7 steps, numbered from 1 to 7. 
#              Each bone has to run Steps 2-7 separately.
#
#-----------------------------------------------------
# Usage:       This module is plugged into 3D Slicer, but can
#              run on its own. When run on its own:
#              python Contour.py arg1 arg2
#
# Where:       arg1 = The input greyscale image to be contoured
#              arg2 = The output image to store the contour
#
#-----------------------------------------------------
import SimpleITK as sitk

class ContourLogic:
    """This class provides methods for automatic contouring"""

    def __init__(self, img=None, lower=3000, upper=10000, boneNum=1):
        self.img = img                     # bone model, will be reused
        self.output_img = None             # output image
        self.label_img = None              # image with connected bone structures relabeled
        self.separate_map = None           # label map that shows how each bone is separated
        self.lower_threshold = lower
        self.upper_threshold = upper
        self.boneNum = boneNum             # number of bone structures to be segmented
        self._step = 0                     # number of steps done
        self._stepNum = 6 * self.boneNum + 1
        self._dilateErodeRadius = 34       # dilate/erode radius
        self._margin = self._dilateErodeRadius + 2
        self._stats_filter = sitk.LabelStatisticsImageFilter()
        self._boundingbox = ()              # bounding box of extracted image
    
    def setPhysicalSpace(self, img, origin, spacing):
        """
        Set the origin and spacing of the image

        Args:
            img (Image): will be modified
            origin (list/tuple of double)
            spacing (list/tutple of double)
        """
        img.SetOrigin(origin)
        img.SetSpacing(spacing)
        return img

    def threshold(self, img, lower, upper):
        """
        Apply a global threshold to binarize the bone.

        Args:
            img (Image)
            lower (int)
            upper (int)
        
        Returns:
            Image
        """
        thresh_img = sitk.BinaryThreshold(img, lowerThreshold=lower, upperThreshold=upper, insideValue=1)

        return thresh_img

    def relabelWithMap(self, img, labelMap):
        """
        Relabel the bones with the input label map.
        
        Args:
            img (Image)
            labelMap (Image): indicates how the bones are separated from one another. 
                              The labels should go from 1, 2,..., to N, without any skips.
        """
        label_img = img * labelMap

        self._stats_filter.Execute(img, label_img)
        boneNum = self._stats_filter.GetNumberOfLabels() - 1
        self.setBoneNum(boneNum)

        return label_img

    def relabelWithConnect(self, img, lower, upper):
        """
        Relabel the connected bone structures from biggest to smallest. 
        The labels go from 1 (for the biggest), 2, 3,..., to N (for the smallest). 

        Args:
            img (Image)

        Returns:
            Image: Small bone particals less than 927 voxels in size are removed. 
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

    def denoise(self, img, sigma, foreground):
        """
        De-noise the image with a Gaussian filter.

        Args:
            img (Image)
            sigma (double): will be internally scaled by spacing. 
                            SimpleITK Gaussian filters take sigma with respect to spacing.
        
        Returns:
            Image
        """
        denoiseInsideValue = 250
        thresh_img = sitk.BinaryThreshold(img, 
                                          lowerThreshold=foreground, 
                                          upperThreshold=foreground, 
                                          insideValue=denoiseInsideValue)
        sigma_over_spacing = sigma / thresh_img.GetSpacing()[0]

        # gaussian smoothing filter
        print("Applying Gaussian filter")
        gaussian_filter = sitk.SmoothingRecursiveGaussianImageFilter()
        gaussian_filter.SetSigma(sigma_over_spacing)
        gaussian_img = gaussian_filter.Execute(thresh_img)
        
        # threshold filter
        thresh_img = sitk.BinaryThreshold(gaussian_img, 
                                          lowerThreshold=denoiseInsideValue//2, 
                                          upperThreshold=denoiseInsideValue, 
                                          insideValue=foreground)

        return thresh_img

    def dilate(self, img, radius, foreground):
        """
        Dilate the objects in the image.

        Args:
            img (Image)
            radius (Int): dilate steps, in voxels
            foreground (int): Only voxels with the foreground value are dilated.

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

    def connect(self, img, foreground):
        """
        Select the outer contour of the bones that attaches to the background, 
        and ignore the inner trabecular voids.
        
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
        origin = img.GetOrigin()
        spacing = img.GetSpacing()
        seed_list = [(0,0),(width-1,0),(0,height-1),(width-1,height-1)]

        # connectivity filter to select the background
        print("Applying connectivity filter")
        connected_filter = sitk.ConnectedThresholdImageFilter()
        connected_filter.SetSeedList(seed_list)
        connected_filter.SetLower(0)
        connected_filter.SetUpper(0)
        connected_filter.SetReplaceValue(foreground)

        vectorOfImages = sitk.VectorOfImage()
        # apply connectivity slice by slice to select the background
        # not to consider z direction
        for i in range(depth):
            im = img[:,:,i]
            contour = connected_filter.Execute(im)
            vectorOfImages.push_back(contour)
        connected_img = sitk.JoinSeries(vectorOfImages)
        vectorOfImages.clear()

        # invert filter to select the bone structure
        invert_filter = sitk.InvertIntensityImageFilter()
        invert_filter.SetMaximum(foreground)
        invert_img = invert_filter.Execute(connected_img)

        invert_img = self.setPhysicalSpace(invert_img, origin, spacing)
        return invert_img

    def erode(self, img, radius, foreground):
        """
        Erode the objects in the image back to its original size. 
        
        Args:
            img (Image)
            radius (Int): erode steps, in voxels
            foreground (int): Only voxels with the foreground value are eroded.
        
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
                self.img = self.threshold(self.img, self.lower_threshold, self.upper_threshold)
                if (self.separate_map is None): # separate bones automatically
                    self.label_img = self.relabelWithConnect(self.img, self.lower_threshold, self.upper_threshold)
                else: # separate bones with manual map
                    self.label_img = self.relabelWithMap(self.img, self.separate_map)
            elif self._step == 2: # step 2
                self.img = self.extract(self.label_img, self.boneNum)
            elif self._step == 3: # step 3
                self.img = self.denoise(self.img, 2, self.boneNum) # sigma=2
            elif self._step == 4: # step 4
                self.img = self.dilate(self.img, self._dilateErodeRadius, self.boneNum) # radius=34
            elif self._step == 5: # step 5
                self.img = self.connect(self.img, self.boneNum)
            elif self._step == 6: # step 6
                self.img = self.erode(self.img, self._dilateErodeRadius, self.boneNum) # radius=34
            elif self._step == 7: # step 7
                if (self.output_img is None):
                    self.output_img = self.pasteBack(self.img)
                else:
                    temp_img = self.pasteBack(self.img)
                    self.output_img = self.output_img | temp_img
                # one bone structure completed
                self.boneNum -= 1
                if (self.boneNum > 0):
                    self._step = 1 # go back to the end of step 1
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
    
    def setSeparateMap(self, separate_map):
        """
        Args:
            separate_map (Image)
        """
        self.separate_map = separate_map
    
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
        self.boneNum = boneNum
        self.stepNum = 6 * boneNum + 1
    
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


# run this program on its own
if __name__ == "__main__":
    # execute the algorithm
    import sys

    if len(sys.argv) < 3:
        # invalid arguments, print usage
        print("Usage: Contour.py [input filename] [output filename]")

    else:
        input_dir = sys.argv[1]
        output_dir = sys.argv[2]

        # read image
        img = sitk.ReadImage(input_dir)

        # create contour object
        contour = ContourLogic(img)

        # create contour
        while (contour.execute()):
            pass
        contour_img = contour.getOutput()

        # store contour
        print("Storing image in {}".format(output_dir))
        sitk.WriteImage(contour_img, output_dir)
