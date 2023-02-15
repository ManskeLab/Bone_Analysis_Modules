"""
three_stack_reg.py

Created by: Michael Kuczynski
Created on: July 18, 2022

Description: Perform stack registration of 3 XCT images with a 25% overlap between stacks.
             Overlap is assumed to be in the axial direction and is fixed to 42 slices.
             Each stack is 168 axial slices, and the overlap between stacks is always 42
              slices, even if the image was cropped to be less than 168 axial slices.
             First, an initial alignment of images is obtained by matching geometric centres. 
             Final image alignment is obtained by optimizing the mutual information.

Usage: 
  python three_stack_reg.py topStack midStack bottomStack
"""

import os
import sys
import argparse
import SimpleITK as sitk


def command_iteration(method):
    """
    Funtion to print out registration data to terminal.

    Parameters
    ----------
    method
      SimpleITK registration object
    """
    print(
        "{0:3} = {1:10.5f} : {2}".format(
            method.GetOptimizerIteration(),
            method.GetMetricValue(),
            method.GetOptimizerPosition(),
        )
    )


def crop_image(image, roi_size, roi_start):
    """
    Crops an image given the size of the ROI to crop and where the ROI starts.

    Parameters
    ----------
    image : SimpleITK.Image

    roi_size : list

    roi_start : list

    Returns
    -------
    crop : SimpleITK.Image
    """
    crop = sitk.RegionOfInterest(image, roi_size, roi_start)
    return crop


def crop_initialize_reg(fixed_image, moving_image):
    """
    Aligns the fixed and moving images using the geometric centre of each image.
    The initial transform and resampled moving image are returned as outputs.

    Parameters
    ----------
    fixed_image : SimpleITK.Image

    moving_image : SimpleITK.Image

    Returns
    -------
    list
      A List containing the initialization transformation matrix and the
      resampled moving image.
    """
    initial_tfm = sitk.CenteredTransformInitializer(
        fixed_image,
        moving_image,
        sitk.Euler3DTransform(),
        sitk.CenteredTransformInitializerFilter.GEOMETRY,
    )

    moving_image_resampled = sitk.Resample(
        moving_image,
        fixed_image,
        initial_tfm,
        sitk.sitkBSpline,
        0.0,
        moving_image.GetPixelID(),
    )

    return initial_tfm, moving_image_resampled


def register_stacks(fixed_image, moving_image, initial_tfm):
    """
    Perform intensity-based image registration between two images.

    Parameters
    ----------
    fixed_image : SimpleITK.Image

    moving_image : SimpleITK.Image

    initial_tfm : SimpleITK.Transform

    Returns
    -------
    final_ftm : SimpleITK.Transform
    """
    reg = sitk.ImageRegistrationMethod()

    # Similarity metric settings
    # Use a fixed seed point for random image sampling for reproducible results
    reg.SetMetricAsMattesMutualInformation(numberOfHistogramBins=50)
    reg.SetMetricSamplingStrategy(reg.RANDOM)
    # reg.SetMetricSamplingPercentage(0.01, 0)
    reg.SetMetricSamplingPercentagePerLevel([0.5, 0.1, 0.01], 0)

    reg.SetInterpolator(sitk.sitkBSpline)

    # Optimizer settings
    reg.SetOptimizerAsGradientDescent(
        learningRate=5.0,
        numberOfIterations=500,
        convergenceMinimumValue=1e-12,
        convergenceWindowSize=500,
    )
    reg.SetOptimizerScalesFromPhysicalShift()

    # Setup for the multi-resolution framework
    reg.SetShrinkFactorsPerLevel(shrinkFactors=[4, 2, 1])
    reg.SetSmoothingSigmasPerLevel(smoothingSigmas=[2, 1, 0])
    reg.SmoothingSigmasAreSpecifiedInPhysicalUnitsOn()

    reg.SetInitialTransform(initial_tfm, inPlace=False)

    reg.AddCommand(sitk.sitkIterationEvent, lambda: command_iteration(reg))

    final_ftm = reg.Execute(fixed_image, moving_image)

    print("Final metric value: {0}".format(reg.GetMetricValue()))
    print(
        "Optimizer's stopping condition, {0}".format(
            reg.GetOptimizerStopConditionDescription()
        )
    )

    return final_ftm


def resample_full_extent(image, tmat):
    """
    Resamples an input image while keeping the image's original extent.

    Parameters
    ----------
    image : SimpleITK.Image

    tmat : SimpleITK.Transform

    Returns
    -------
    resampled_image : SimpleITK.Image
    """
    # First get the extent of the original image
    extreme_points = [
        image.TransformIndexToPhysicalPoint((0, 0, 0)),
        image.TransformIndexToPhysicalPoint((image.GetWidth(), 0, 0)),
        image.TransformIndexToPhysicalPoint((0, image.GetHeight(), 0)),
        image.TransformIndexToPhysicalPoint((0, 0, image.GetDepth())),
        image.TransformIndexToPhysicalPoint((image.GetWidth(), image.GetHeight(), 0)),
        image.TransformIndexToPhysicalPoint((image.GetWidth(), 0, image.GetDepth())),
        image.TransformIndexToPhysicalPoint(
            (image.GetWidth(), image.GetHeight(), image.GetDepth())
        ),
        image.TransformIndexToPhysicalPoint((0, image.GetHeight(), image.GetDepth())),
    ]

    # Use the inverse transform to get the bounds of the resampling grid
    tmat_inverse = tmat.GetInverse()
    extreme_points_transf = [tmat_inverse.TransformPoint(pnt) for pnt in extreme_points]

    min_x = min(extreme_points_transf)[0]
    min_y = min(extreme_points_transf, key=lambda p: p[1])[1]
    min_z = min(extreme_points_transf, key=lambda p: p[2])[2]
    max_x = max(extreme_points_transf)[0]
    max_y = max(extreme_points_transf, key=lambda p: p[1])[1]
    max_z = max(extreme_points_transf, key=lambda p: p[2])[2]

    output_spacing = image.GetSpacing()
    output_direction = image.GetDirection()
    output_origin = [min_x, min_y, min_z]

    # Compute grid size based on the physical size and spacing
    output_size = [
        int((max_x - min_x) / output_spacing[0]),
        int((max_y - min_y) / output_spacing[1]),
        int((max_z - min_z) / output_spacing[2]),
    ]

    # Transform the image keeping the original extent
    resampled_image = sitk.Resample(
        image,
        output_size,
        tmat,
        sitk.sitkBSpline,
        output_origin,
        output_spacing,
        output_direction,
    )

    return resampled_image


def three_stack_reg(top_stack, mid_stack, bottom_stack, output_dir):
    """
    Run the full stack registration workflow.

    Parameters
    ----------
    top_stack : SimpleITK.Image

    mid_stack : SimpleITK.Image

    bottom_stack : SimpleITK.Image

    output_dir : string
    """
    # -------------------------------------------------------------------#
    #   STEP 1: Create the output paths
    # -------------------------------------------------------------------#
    # Cropped overlap images
    top_overlap_path = os.path.join(output_dir, "TOP_MID_OVERLAP.nii")
    midTop_overlap_path = os.path.join(output_dir, "MID_TOP_OVERLAP.nii")
    midBottom_overlap_path = os.path.join(output_dir, "MID_BTM_OVERLAP.nii")
    bottom_overlap_path = os.path.join(output_dir, "BTM_MID_OVERLAP.nii")

    # Transformation matrix outputs
    top2Mid_initial_tfm_path = os.path.join(output_dir, "TOP_TO_MID_INITAL_REG.tfm")
    bottom2Mid_initial_tfm_path = os.path.join(output_dir, "BTM_TO_MID_INITAL_REG.tfm")
    top2Mid_final_tfm_path = os.path.join(output_dir, "TOP_TO_MID_FINAL_REG.tfm")
    bottom2Mid_final_tfm_path = os.path.join(output_dir, "BTM_TO_MID_FINAL_REG.tfm")

    # Image masks
    top_reg_mask_path = os.path.join(output_dir, "TOP_REG_MASK.nii")
    bottom_mask_path = os.path.join(output_dir, "BOTTOM_REG_MASK.nii")
    mid_mask_path = os.path.join(output_dir, "MID_MASK.nii")

    # Registered output images
    top2Mid_reg_path = os.path.join(output_dir, "TOP_TO_MID_REG.nii")
    bottom2Mid_reg_path = os.path.join(output_dir, "BTM_TO_MID_REG.nii")

    full_image_path = os.path.join(output_dir, "FULL_IMAGE.nii")

    # -------------------------------------------------------------------#
    #   STEP 2: Create the fixed and moving images
    # -------------------------------------------------------------------#
    # Crop overlap regions
    # Registration #1: Top to Middle
    # Set the middle image as fixed, and the top as moving
    fixed_image1 = crop_image(
        mid_stack,
        [mid_stack.GetWidth(), mid_stack.GetHeight(), 42],
        [0, 0, mid_stack.GetDepth() - 42],
    )
    moving_image1 = crop_image(
        top_stack, [top_stack.GetWidth(), top_stack.GetHeight(), 42], [0, 0, 0]
    )

    sitk.WriteImage(fixed_image1, midTop_overlap_path)
    sitk.WriteImage(moving_image1, top_overlap_path)

    top2Mid_initial_tfm, moving_image_resampled1 = crop_initialize_reg(
        fixed_image1, moving_image1
    )
    sitk.WriteTransform(top2Mid_initial_tfm, top2Mid_initial_tfm_path)
    sitk.WriteImage(moving_image_resampled1, top2Mid_reg_path)

    # Registration #2: Bottom to Middle
    # Set the middle image as fixed, and the bottom as moving
    fixed_image2 = crop_image(
        mid_stack, [mid_stack.GetWidth(), mid_stack.GetHeight(), 42], [0, 0, 0]
    )
    moving_image2 = crop_image(
        bottom_stack,
        [bottom_stack.GetWidth(), bottom_stack.GetHeight(), 42],
        [0, 0, bottom_stack.GetDepth() - 42],
    )

    sitk.WriteImage(fixed_image2, midBottom_overlap_path)
    sitk.WriteImage(moving_image2, bottom_overlap_path)

    bottom2Mid_initial_tfm, moving_image_resampled2 = crop_initialize_reg(
        fixed_image2, moving_image2
    )
    sitk.WriteTransform(bottom2Mid_initial_tfm, bottom2Mid_initial_tfm_path)
    sitk.WriteImage(moving_image_resampled2, bottom2Mid_reg_path)

    # -------------------------------------------------------------------#
    #   STEP 3: Register top stack to bottom stack
    # -------------------------------------------------------------------#
    # Run the registration
    # Registration #1: Top to Middle
    top2Mid_final_tfm = register_stacks(
        fixed_image1, moving_image1, top2Mid_initial_tfm, "top"
    )
    sitk.WriteTransform(top2Mid_final_tfm, top2Mid_final_tfm_path)

    # Registration #2: Bottom to Middle
    bottom2Mid_final_tfm = register_stacks(
        fixed_image2, moving_image2, bottom2Mid_initial_tfm, "bottom"
    )
    sitk.WriteTransform(bottom2Mid_final_tfm, bottom2Mid_final_tfm_path)

    # -------------------------------------------------------------------#
    #   STEP 4: Transform and resample the moving images
    # -------------------------------------------------------------------#
    # Make sure we keep the full extent of the transformed images

    # Registration #1: Top Image
    reg_top_image = resample_full_extent(top_stack, top2Mid_final_tfm)
    sitk.WriteImage(reg_top_image, top2Mid_reg_path)

    # Registration #2: Bottom Image
    reg_bottom_image = resample_full_extent(bottom_stack, bottom2Mid_final_tfm)
    sitk.WriteImage(reg_bottom_image, bottom2Mid_reg_path)

    # -------------------------------------------------------------------#
    #   STEP 5: Create an empty image and paste in the bottom stack
    # -------------------------------------------------------------------#
    width = (
        max(
            mid_stack.GetSize()[0],
            reg_top_image.GetSize()[0],
            reg_bottom_image.GetSize()[0],
        )
        + 50
    )
    height = (
        max(
            mid_stack.GetSize()[1],
            reg_top_image.GetSize()[1],
            reg_bottom_image.GetSize()[1],
        )
        + 50
    )
    depth = (
        mid_stack.GetSize()[2]
        + reg_top_image.GetSize()[2]
        + reg_bottom_image.GetSize()[2]
        - 42
        - 42
    )

    origin_x = min(
        reg_top_image.GetOrigin()[0],
        mid_stack.GetOrigin()[0],
        reg_bottom_image.GetOrigin()[0],
    )
    origin_y = min(
        reg_top_image.GetOrigin()[1],
        mid_stack.GetOrigin()[1],
        reg_bottom_image.GetOrigin()[1],
    )
    origin_z = min(
        reg_top_image.GetOrigin()[2],
        mid_stack.GetOrigin()[2],
        reg_bottom_image.GetOrigin()[2],
    )

    final_image_origin = [origin_x, origin_y, origin_z]
    final_image_dim = [width, height, depth]

    final_image = sitk.Image(final_image_dim, sitk.sitkFloat32)
    final_image.SetOrigin(final_image_origin)
    final_image.SetSpacing(mid_stack.GetSpacing())
    final_image.SetDirection(mid_stack.GetDirection())

    # Get the index where our mid stack image will be pasted
    # This needs to be in  image index coordinates, not physical image coordinates (i.e., mm or um)
    dest_index_x = abs(
        final_image.TransformPhysicalPointToIndex(final_image_origin)[0]
        - final_image.TransformPhysicalPointToIndex(mid_stack.GetOrigin())[0]
    )
    dest_index_y = abs(
        final_image.TransformPhysicalPointToIndex(final_image_origin)[1]
        - final_image.TransformPhysicalPointToIndex(mid_stack.GetOrigin())[1]
    )
    dest_index_z = abs(
        final_image.TransformPhysicalPointToIndex(final_image_origin)[2]
        - final_image.TransformPhysicalPointToIndex(mid_stack.GetOrigin())[2]
    )
    mid_dest_index = [dest_index_x, dest_index_y, dest_index_z]

    pasted_image = sitk.Paste(
        final_image, mid_stack, mid_stack.GetSize(), destinationIndex=mid_dest_index
    )

    # -------------------------------------------------------------------#
    #   STEP 6: Create a mask of each bone
    # -------------------------------------------------------------------#
    # Get the mask of each bone (assuming background is 0)
    # Use morphological closing to account for voxels in the bone that equal 0
    top_mask = sitk.Cast(reg_top_image, sitk.sitkInt8) != 0
    top_mask = sitk.BinaryMorphologicalClosing(top_mask, (3, 3, 1))

    mid_mask = sitk.Cast(pasted_image, sitk.sitkInt8) != 0
    mid_mask = sitk.BinaryMorphologicalClosing(mid_mask, (3, 3, 1))

    bottom_mask = sitk.Cast(reg_bottom_image, sitk.sitkInt8) != 0
    bottom_mask = sitk.BinaryMorphologicalClosing(bottom_mask, (3, 3, 1))

    # Resample the top and bottom masks so they has the same dimensions as the mid mask
    top_mask = sitk.Resample(
        top_mask, pasted_image, interpolator=sitk.sitkNearestNeighbor
    )
    bottom_mask = sitk.Resample(
        bottom_mask, pasted_image, interpolator=sitk.sitkNearestNeighbor
    )

    # Create a mask for the top and bottom images that does not include the overlap
    # with the mid image
    top_combined_mask = top_mask - (top_mask & mid_mask)
    bottom_combined_mask = bottom_mask - (bottom_mask & mid_mask)

    sitk.WriteImage(top_mask, top_reg_mask_path)
    sitk.WriteImage(mid_mask, mid_mask_path)
    sitk.WriteImage(bottom_mask, bottom_mask_path)

    # -------------------------------------------------------------------#
    #   STEP 7: Add images together
    # -------------------------------------------------------------------#
    # Resample the transformed top stack image to have the same dimensions
    # as the bottom stack image so we can do a simple addition
    reg_top_image = sitk.Resample(
        reg_top_image, pasted_image, interpolator=sitk.sitkBSpline
    )
    reg_bottom_image = sitk.Resample(
        reg_bottom_image, pasted_image, interpolator=sitk.sitkBSpline
    )

    # Mask out the top and bottom stack images (without the overlap)
    masked_reg_top = sitk.Mask(reg_top_image, top_combined_mask, 0, 0)
    masked_reg_bottom = sitk.Mask(reg_bottom_image, bottom_combined_mask, 0, 0)

    pasted_image = pasted_image + masked_reg_top + masked_reg_bottom

    sitk.WriteImage(pasted_image, full_image_path)


def main():
    # Parse input arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("top_stack", type=str, help="Top stack image (path + filename)")
    parser.add_argument(
        "mid_stack", type=str, help="Middle stack image (path + filename)"
    )
    parser.add_argument(
        "bottom_stack", type=str, help="Bottom stack image (path + filename)"
    )
    args = parser.parse_args()

    top_stack_path = args.top_stack
    mid_stack_path = args.mid_stack
    bottom_stack_path = args.bottom_stack

    # Get the filename from the path
    top_stack_basename = (os.path.basename(top_stack_path)).lower()
    mid_stack_basename = (os.path.basename(mid_stack_path)).lower()
    bottom_stack_basename = (os.path.basename(bottom_stack_path)).lower()

    # Only accept MHA and NII images
    if not (".mha" in top_stack_basename or ".nii" in top_stack_basename):
        sys.exit(
            "Wrong file type for the top stack. Only MHA and NII images will be accepted."
        )
    elif not (".mha" in bottom_stack_basename or ".nii" in bottom_stack_basename):
        sys.exit(
            "Wrong file type for the bottom stack. Only MHA and NII images will be accepted."
        )
    elif not (".mha" in mid_stack_basename or ".nii" in mid_stack_basename):
        sys.exit(
            "Wrong file type for the middle stack. Only MHA and NII images will be accepted."
        )

    # Create a new folder to hold the output images
    image_dir = os.path.dirname(bottom_stack_path)
    output_dir = os.path.join(image_dir, "stackRegistrationOutput")

    # Check if the directory already exists
    if not os.path.isdir(output_dir):
        print("Creating output directory {}".format(output_dir))
        os.mkdir(output_dir)

    # Read in images as floats to increase precision
    top_image = sitk.ReadImage(top_stack_path, sitk.sitkFloat32)
    mid_image = sitk.ReadImage(mid_stack_path, sitk.sitkFloat32)
    bottom_image = sitk.ReadImage(bottom_stack_path, sitk.sitkFloat32)

    three_stack_reg(top_image, mid_image, bottom_image, output_dir)


if __name__ == "__main__":
    main()
