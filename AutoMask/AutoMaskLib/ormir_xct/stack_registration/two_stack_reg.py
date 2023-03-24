"""
two_stack_reg.py

Created by: Michael Kuczynski
Created on: July 18, 2022

Description: Perform stack registration of 2 XCT images with a 25% overlap between stacks.
             Overlap is assumed to be in the axial direction and is fixed to 42 slices.
             Each stack is 168 axial slices, and the overlap between stacks is always 42
              slices, even if the image was cropped to be less than 168 axial slices.
             First, an initial alignment of images is obtained by matching geometric centres. 
             Final image alignment is obtained by optimizing the mutual information.

Usage: 
  python two_stack_reg.py top_stack bottom_stack
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


def two_stack_reg(top_stack, bottom_stack, output_dir):
    """
    Run the stack registration on two image stacks.

    Parameters
    ----------
    top_stack : SimpleITK.Image

    bottom_stack : SimpleITK.Image

    output_dir : string
    """
    # -------------------------------------------------------------------#
    #   STEP 1: Create the output paths
    # -------------------------------------------------------------------#
    # Cropped overlap images
    bottom_overlap_path = os.path.join(output_dir, "BOTTOM_OVERLAP.nii")
    top_overlap_path = os.path.join(output_dir, "TOP_OVERLAP.nii")

    # Transformation matrix outputs
    initial_tfm_path = os.path.join(output_dir, "INITIAL_TMAT.tfm")
    final_tfm_path = os.path.join(output_dir, "FINAL_TMAT.tfm")

    # Image masks
    top_reg_mask_path = os.path.join(output_dir, "TOP_REG_MASK.nii")
    bottom_mask_path = os.path.join(output_dir, "BOTTOM_MASK.nii")

    # Registered output images
    overlap_reg_path = os.path.join(output_dir, "OVERLAP_REG.nii")
    full_image_path = os.path.join(output_dir, "FULL_IMAGE.nii")

    # -------------------------------------------------------------------#
    #   STEP 2: Create the fixed and moving images
    # -------------------------------------------------------------------#
    # Crop overlap regions
    # Set the bottom image as fixed, and the top as moving
    fixed_image = sitk.RegionOfInterest(
        bottom_stack,
        [bottom_stack.GetWidth(), bottom_stack.GetHeight(), 42],
        [0, 0, bottom_stack.GetDepth() - 42],
    )
    sitk.WriteImage(fixed_image, bottom_overlap_path)

    moving_image = sitk.RegionOfInterest(
        top_stack, [top_stack.GetWidth(), top_stack.GetHeight(), 42], [0, 0, 0]
    )
    sitk.WriteImage(moving_image, top_overlap_path)

    # Align images by centres
    initial_tfm = sitk.CenteredTransformInitializer(
        fixed_image,
        moving_image,
        sitk.Similarity3DTransform(),
        sitk.CenteredTransformInitializerFilter.GEOMETRY,
    )
    sitk.WriteTransform(initial_tfm, initial_tfm_path)

    moving_image_resampled = sitk.Resample(
        moving_image,
        fixed_image,
        initial_tfm,
        sitk.sitkBSpline,
        0.0,
        moving_image.GetPixelID(),
    )
    sitk.WriteImage(moving_image_resampled, overlap_reg_path)

    # -------------------------------------------------------------------#
    #   STEP 3: Register top stack to bottom stack
    # -------------------------------------------------------------------#
    # Run the registration
    reg = sitk.ImageRegistrationMethod()

    # Similarity metric settings
    # Use a fixed seed point for random image sampling for reproducible results
    reg.SetMetricAsMattesMutualInformation(numberOfHistogramBins=50)
    reg.SetMetricSamplingStrategy(reg.RANDOM)
    reg.SetMetricSamplingPercentage(0.01, 0)
    reg.SetInterpolator(sitk.sitkBSpline)

    # Optimizer settings
    reg.SetOptimizerAsGradientDescent(
        learningRate=2.0,
        numberOfIterations=250,
        convergenceMinimumValue=1e-10,
        convergenceWindowSize=100,
    )
    reg.SetOptimizerScalesFromPhysicalShift()

    # Setup for the multi-resolution framework
    reg.SetShrinkFactorsPerLevel(shrinkFactors=[4, 2, 1])
    reg.SetSmoothingSigmasPerLevel(smoothingSigmas=[2, 1, 0])
    reg.SmoothingSigmasAreSpecifiedInPhysicalUnitsOn()

    reg.SetInitialTransform(initial_tfm, inPlace=False)

    reg.AddCommand(sitk.sitkIterationEvent, lambda: command_iteration(reg))

    final_tfm = reg.Execute(fixed_image, moving_image)
    sitk.WriteTransform(final_tfm, final_tfm_path)

    print("Final metric value: {0}".format(reg.GetMetricValue()))
    print(
        "Optimizer's stopping condition, {0}".format(
            reg.GetOptimizerStopConditionDescription()
        )
    )

    # -------------------------------------------------------------------#
    #   STEP 4: Transform and resample the top image
    # -------------------------------------------------------------------#
    # Make sure we keep the full extent of the transformed image

    # First get the extent of the moving image
    extreme_points = [
        top_stack.TransformIndexToPhysicalPoint((0, 0, 0)),
        top_stack.TransformIndexToPhysicalPoint((top_stack.GetWidth(), 0, 0)),
        top_stack.TransformIndexToPhysicalPoint((0, top_stack.GetHeight(), 0)),
        top_stack.TransformIndexToPhysicalPoint((0, 0, top_stack.GetDepth())),
        top_stack.TransformIndexToPhysicalPoint(
            (top_stack.GetWidth(), top_stack.GetHeight(), 0)
        ),
        top_stack.TransformIndexToPhysicalPoint(
            (top_stack.GetWidth(), 0, top_stack.GetDepth())
        ),
        top_stack.TransformIndexToPhysicalPoint(
            (top_stack.GetWidth(), top_stack.GetHeight(), top_stack.GetDepth())
        ),
        top_stack.TransformIndexToPhysicalPoint(
            (0, top_stack.GetHeight(), top_stack.GetDepth())
        ),
    ]

    # Use the inverse transform to get the bounds of the resampling grid
    final_tfm_inv = final_tfm.GetInverse()
    extreme_points_transf = [
        final_tfm_inv.TransformPoint(pnt) for pnt in extreme_points
    ]

    min_x = min(extreme_points_transf)[0]
    min_y = min(extreme_points_transf, key=lambda p: p[1])[1]
    min_z = min(extreme_points_transf, key=lambda p: p[2])[2]
    max_x = max(extreme_points_transf)[0]
    max_y = max(extreme_points_transf, key=lambda p: p[1])[1]
    max_z = max(extreme_points_transf, key=lambda p: p[2])[2]

    output_spacing = top_stack.GetSpacing()
    output_direction = top_stack.GetDirection()
    output_origin = [min_x, min_y, min_z]

    # Compute grid size based on the physical size and spacing
    output_size = [
        int((max_x - min_x) / output_spacing[0]),
        int((max_y - min_y) / output_spacing[1]),
        int((max_z - min_z) / output_spacing[2]),
    ]

    # Transform the top stack to the bottom stack's image space, keeping the original top stack's extent
    reg_top_image = sitk.Resample(
        top_stack,
        output_size,
        final_tfm,
        sitk.sitkBSpline,
        output_origin,
        output_spacing,
        output_direction,
    )
    sitk.WriteImage(reg_top_image, overlap_reg_path)

    # -------------------------------------------------------------------#
    #   STEP 5: Create an empty image and paste in the bottom stack
    # -------------------------------------------------------------------#
    width = max(reg_top_image.GetSize()[0], bottom_stack.GetSize()[0])
    height = max(reg_top_image.GetSize()[1], bottom_stack.GetSize()[1])
    depth = reg_top_image.GetSize()[2] + bottom_stack.GetSize()[2] - 42

    origin_x = min(reg_top_image.GetOrigin()[0], bottom_stack.GetOrigin()[0])
    origin_y = min(reg_top_image.GetOrigin()[1], bottom_stack.GetOrigin()[1])
    origin_z = min(reg_top_image.GetOrigin()[2], bottom_stack.GetOrigin()[2])

    final_image_origin = [origin_x, origin_y, origin_z]
    final_image_dim = [width, height, depth]

    final_image = sitk.Image(final_image_dim, sitk.sitkFloat32)
    final_image.SetOrigin(final_image_origin)
    final_image.SetSpacing(bottom_stack.GetSpacing())
    final_image.SetDirection(bottom_stack.GetDirection())

    # Get the index where our bottom stack image will be pasted
    # This needs to be in  image index coordinates, not physical image coordinates (i.e., mm or um)
    bottom_dest_index = [
        abs(
            final_image.TransformPhysicalPointToIndex(final_image_origin)[0]
            - final_image.TransformPhysicalPointToIndex(bottom_stack.GetOrigin())[0]
        ),
        abs(
            final_image.TransformPhysicalPointToIndex(final_image_origin)[1]
            - final_image.TransformPhysicalPointToIndex(bottom_stack.GetOrigin())[1]
        ),
        abs(
            final_image.TransformPhysicalPointToIndex(final_image_origin)[2]
            - final_image.TransformPhysicalPointToIndex(bottom_stack.GetOrigin())[2]
        ),
    ]

    pasted_image = sitk.Paste(
        final_image,
        bottom_stack,
        bottom_stack.GetSize(),
        destinationIndex=bottom_dest_index,
    )

    # -------------------------------------------------------------------#
    #   STEP 6: Create a mask of each bone
    # -------------------------------------------------------------------#
    # Get the mask of each bone (assuming background is 0)
    # Use morphological closing to account for voxels in the bone that equal 0
    top_mask = sitk.Cast(reg_top_image, sitk.sitkInt8) != 0
    top_mask = sitk.BinaryMorphologicalClosing(top_mask, (3, 3, 1))

    bottom_mask = sitk.Cast(pasted_image, sitk.sitkInt8) != 0
    bottom_mask = sitk.BinaryMorphologicalClosing(bottom_mask, (3, 3, 1))

    # Resample the top mask so it has the same dimensions as the bottom mask
    top_mask = sitk.Resample(
        top_mask, pasted_image, interpolator=sitk.sitkNearestNeighbor
    )

    # Create a mask for the top image that does not include the overlap
    # with the bottom image
    combined_mask = top_mask - (top_mask & bottom_mask)

    sitk.WriteImage(top_mask, top_reg_mask_path)
    sitk.WriteImage(bottom_mask, bottom_mask_path)

    # -------------------------------------------------------------------#
    #   STEP 7: Add images together
    # -------------------------------------------------------------------#
    # Resample the transformed top stack image to have the same dimensions
    # as the bottom stack image so we can do a simple addition
    reg_top_image = sitk.Resample(
        reg_top_image, pasted_image, interpolator=sitk.sitkBSpline
    )

    # Mask out the top stack image (without the overlap)
    masked_reg_top = sitk.Mask(reg_top_image, combined_mask, 0, 0)

    pasted_image = pasted_image + masked_reg_top

    sitk.WriteImage(pasted_image, full_image_path)


def main():
    # Parse input arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("top_stack", type=str, help="Top stack image (path + filename)")
    parser.add_argument(
        "bottom_stack", type=str, help="Bottom stack image (path + filename)"
    )
    args = parser.parse_args()

    top_stack_path = args.top_stack
    bottom_stack_path = args.bottom_stack

    # Get the filename from the path
    top_stack_basename = (os.path.basename(top_stack_path)).lower()
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

    # Create a new folder to hold the output images
    image_dir = os.path.dirname(bottom_stack_path)
    output_dir = os.path.join(image_dir, "stackRegistrationOutput")

    # Check if the directory already exists
    if not os.path.isdir(output_dir):
        print("Creating output directory {}".format(output_dir))
        os.mkdir(output_dir)

    # Read in images as floats to increase precision
    top_stack = sitk.ReadImage(top_stack_path, sitk.sitkFloat32)
    bottom_stack = sitk.ReadImage(bottom_stack_path, sitk.sitkFloat32)

    two_stack_reg(top_stack, bottom_stack, output_dir)


if __name__ == "__main__":
    main()
