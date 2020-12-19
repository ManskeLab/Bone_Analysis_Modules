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
#              Morphological closing operations (i.e. dilate, connectivity, and erode)
#              are applied to each bone separately to close the inner voids. 
#              There are 8 steps. Each bone has to run Steps 4-8 separately.
#
#-----------------------------------------------------
# Usage:       This module is plugged into 3D Slicer, but can
#              run on its own. When run on its own:
#              python Contour.py arg1 arg2
#
# Param:       arg1 = The input greyscale image to be contoured
#              arg2 = The output image to store the contour
#
#-----------------------------------------------------
import SimpleITK as sitk

class FastContourLogic:
    """This class provides methods for automatic contouring"""

    def __init__(self, img=None, lower=3000, upper=10000, boneNum=1):
        self.img = img                     # bone model, will be reused
        self.output_img = None             # output image
        self.label_img = None              # image with each connected bone structures relabeled
        self.separate_map = None           # rough manual separation map
        self.lower_threshold = lower
        self.upper_threshold = upper
        self.boneNum = boneNum             # number of bone structures to be segmented
        self._step = 0                     # number of steps done
        self._stepNum = 5 * self.boneNum + 3 # total number of steps in the algorithm
        self._dilateErodeRadius = 36       # dilate/erode radius
        self._margin = self._dilateErodeRadius + 2
        self._stats_filter = sitk.LabelStatisticsImageFilter()
        self._boundingbox = ()              # bounding box of extracted image, will be reused
    
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
    
    def binarize(self, img, lower, upper):
        thresh_img = sitk.BinaryThreshold(img,
                                          lowerThreshold=lower,
                                          upperThreshold=upper,
                                          insideValue=1)

        return thresh_img

    def denoise(self, img, sigma):
        """
        De-noise the image with a Gaussian filter.

        Args:
            img (Image)
            sigma (double): will be internally scaled by spacing. 
                            SimpleITK Gaussian filters take sigma with respect to spacing.
        
        Returns:
            Image
        """
        sigma_over_spacing = sigma * img.GetSpacing()[0]
        inside_value = 250
        max_inside_value = 255

        thresh_img = sitk.BinaryThreshold(img, 
                                          lowerThreshold=1, 
                                          upperThreshold=1, 
                                          insideValue=inside_value)

        # gaussian smoothing filter
        print("Applying Gaussian filter")
        gaussian_filter = sitk.SmoothingRecursiveGaussianImageFilter()
        gaussian_filter.SetSigma(sigma_over_spacing)
        gaussian_img = gaussian_filter.Execute(thresh_img)
        
        thresh_img = sitk.BinaryThreshold(gaussian_img,
                                          lowerThreshold=inside_value/2,
                                          upperThreshold=max_inside_value,
                                          insideValue=1)

        return thresh_img

    def relabelWithMap(self, thresh_img, smooth_img, separate_map):
        """
        Relabel each bone with the input manual bone separation map.
        
        Args:
            img (Image)
            labelMap (Image): rough mask that indicates how the bones are separated 
                              from one another. 
                              The labels should go from 1, 2,..., to N, without any skips.
        
        Returns:
            Image
        """
        label_img = thresh_img * separate_map
        label_img = label_img * smooth_img

        self._stats_filter.Execute(smooth_img, label_img)
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

    def inflate(self, img, radius, foreground):
        """
        Inflate the objects in the image.

        Args:
            img (Image)
            radius (Int): Inflate steps, in voxels
            foreground (int): Only voxels with the foreground value are inflated.

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

    def deflate(self, img, radius, foreground):
        """
        Deflate the objects in the image back to their original size. 
        
        Args:
            img (Image)
            radius (Int): deflate steps, in voxels
            foreground (int): Only voxels with the foreground value are deflated.
        
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
                self.img = self.connect(self.img, self.boneNum)
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
        contour = FastContourLogic(img)

        # create contour
        while (contour.execute()):
            pass
        contour_img = contour.getOutput()

        # store contour
        print("Storing image in {}".format(output_dir))
        sitk.WriteImage(contour_img, output_dir)
