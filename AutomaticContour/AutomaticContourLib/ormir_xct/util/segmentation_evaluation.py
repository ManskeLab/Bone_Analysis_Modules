"""
Created by: Nathan Neeteson
Created on: ??

Description: Utilities for quantitatively comparing 
              predicted and reference segmentations.
              Loosely adapted from: 
https://github.com/InsightSoftwareConsortium/SimpleITK-Notebooks/blob/master/Python/34_Segmentation_Evaluation.ipynb
"""

import SimpleITK as sitk
import numpy as np


def binarize_numpy_array(arr):
    """
    Binarize an input image. Values > 0 are set to 1, values < 0 are set to 0.

    Parameters
    ----------
    arr : numpy.array
        Input image to binarize

    Returns
    -------
    numpy.array
        Binarized image as an array
    """
    return (np.abs(arr) > 0).astype(np.int)


def get_distance_map_and_surface(mask):
    """
    Take in an ITK image mask and return the distance map and surface images.

    Parameters
    ----------
    mask : ITK.Image

    Returns
    -------
    list
        A Python list containing the distance map, surface image, and number of
        pixels in the surface image.
    """
    dist_map = sitk.Abs(
        sitk.SignedMaurerDistanceMap(mask, squaredDistance=False, useImageSpacing=True)
    )
    surface = sitk.LabelContour(mask)
    stats_filter = sitk.StatisticsImageFilter()
    stats_filter.Execute(surface)
    surface_num_pix = int(stats_filter.GetSum())
    return dist_map, surface, surface_num_pix


def get_surface_to_surface_distances_list(surf2surf_dist_map, surface_num_pix):
    """
    Returns a list of the surface to surface distances.

    Parameters
    ----------
    surf2surf_dist_map : SimpleITK.Image

    surface_num_pix : int

    Returns
    -------
    surf2surf_dist_list : list
    """
    surf2surf_dist_array = sitk.GetArrayFromImage(surf2surf_dist_map).flatten()
    surf2surf_dist_list = list(surf2surf_dist_array[surf2surf_dist_array != 0])
    num_nonzero_pix = len(surf2surf_dist_list)
    if num_nonzero_pix < surface_num_pix:
        zeros_list = list(np.zeros(surface_num_pix - num_nonzero_pix))
        surf2surf_distance_list = surf2surf_dist_list + zeros_list

    return surf2surf_dist_list


def calculate_dice_and_jaccard(ref, seg):
    """
    Compute the Sørensen-Dice coefficient and Jaccard index.

    Parameters
    ----------
    ref : numpy.array

    seg : numpy.array

    Returns
    -------
    list
        A list containing the Dice coefficient and Jaccard index
    """
    ref, seg = ref > 0, seg > 0
    ref, seg = ref.flatten(), seg.flatten()
    dice = 2 * (ref & seg).sum() / (ref.sum() + seg.sum())
    jaccard = (ref & seg).sum() / (ref | seg).sum()
    return dice, jaccard


def calculate_surface_distance_measures(ref, seg, spacing):
    """
    Compute the Hausdorff distance.

    Parameters
    ----------
    ref : numpy.array

    seg : numpy.array

    spacing : numpy.array

    Returns
    -------
    ssd_measures : set
        A set containing the mean, median, max, and standard deviation
        of symmetric surface distances.
    """
    # binarize reference and segmentation
    ref, seg = binarize_numpy_array(ref), binarize_numpy_array(seg)

    # convert numpy binary matrices into binary SITK images
    ref = sitk.GetImageFromArray(ref)
    seg = sitk.GetImageFromArray(seg)
    ref.SetSpacing(spacing)
    seg.SetSpacing(spacing)

    # calculate the surface and distance maps for reference and segmentation
    ref_dist_map, ref_surface, ref_surface_num_pix = get_distance_map_and_surface(ref)
    seg_dist_map, seg_surface, seg_surface_num_pix = get_distance_map_and_surface(seg)

    # get the symmetric distances by multiplying the reference distance map by
    # the segmentation surface and vice versa
    seg2ref_dist_map = ref_dist_map * sitk.Cast(seg_surface, sitk.sitkFloat32)
    ref2seg_dist_map = seg_dist_map * sitk.Cast(ref_surface, sitk.sitkFloat32)

    # get lists of the distances (including overlap)
    seg2ref_dist_list = get_surface_to_surface_distances_list(
        seg2ref_dist_map, seg_surface_num_pix
    )
    ref2seg_dist_list = get_surface_to_surface_distances_list(
        ref2seg_dist_map, ref_surface_num_pix
    )
    all_dist_list = seg2ref_dist_list + ref2seg_dist_list

    # calculate max, median, mean, std of symmetric surface distances
    ssd_measures = {}
    ssd_measures["max"] = np.max(all_dist_list)
    ssd_measures["median"] = np.median(all_dist_list)
    ssd_measures["mean"] = np.mean(all_dist_list)
    ssd_measures["std"] = np.std(all_dist_list)

    return ssd_measures
