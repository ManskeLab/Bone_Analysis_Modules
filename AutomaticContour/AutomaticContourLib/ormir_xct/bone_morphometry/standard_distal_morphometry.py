"""
Written by Nathan Neeteson on 2022/11/2.
Last modified: 2022/11/15.
Module containing high-level logic for standard distal morphometric analysis.
Structure thickness logic imported from `ormir_xct.util.hildebrand_thickness`
Bone thresholding logic imported from `ormir_xct.segmentation.ipl_seg`
"""

from __future__ import annotations

import numpy as np
from warnings import warn

from ormir_xct.util.hildebrand_thickness import calc_structure_thickness_statistics
from ormir_xct.segmentation.ipl_seg import ipl_seg
from SimpleITK import (
    GetImageFromArray,
    GetArrayFromImage,
    BinaryThinning,
    ConnectedComponentImageFilter,
    BinaryDilate,
    sitkCross,
)


def get_bone_mask(
    image: np.ndarray, mask: np.ndarray, bone_thresh: float, sigma: float = 0.8
) -> np.ndarray:
    """

    Parameters
    ----------
    image
    mask
    bone_thresh
    sigma

    Returns
    -------

    """
    bone_mask = (
        GetArrayFromImage(
            ipl_seg(
                GetImageFromArray(image),
                bone_thresh,
                1e10,  # crazy high number because there's no upper thresh
                voxel_size=1,
                sigma=sigma,
            )
        )
        == 127
    )
    return (mask * bone_mask).astype(int)


def calculate_bone_mineral_density(image: np.ndarray, mask: np.ndarray) -> float:
    """
    Function for calculating the volumetric bone mineral density from a masked image.

    Parameters
    ----------
    image : np.ndarray
        The image, in units of density.

    mask : np.ndarray
        A binary mask defining the region to calculate the average density over.

    Returns
    -------
    float
    """
    return float(image[mask].mean())


def calculate_mask_thickness(
    mask: np.ndarray, voxel_width: float, min_th: float
) -> float:
    """

    Parameters
    ----------
    mask
    voxel_width
    min_th

    Returns
    -------

    """
    return calc_structure_thickness_statistics(mask, voxel_width, min_th)[0]


def calculate_bone_thickness(
    image: np.ndarray,
    mask: np.ndarray,
    bone_thresh: float,
    voxel_width: float,
    min_th: float,
) -> float:
    """

    Parameters
    ----------
    image
    mask
    bone_thresh
    voxel_width
    min_th

    Returns
    -------

    """
    bone_mask = get_bone_mask(image, mask, bone_thresh)
    return calculate_mask_thickness(bone_mask, voxel_width, min_th)


def calculate_bone_spacing(
    image: np.ndarray,
    mask: np.ndarray,
    bone_thresh: float,
    voxel_width: float,
    min_th: float,
) -> float:
    """

    Parameters
    ----------
    image
    mask
    bone_thresh
    voxel_width
    min_th

    Returns
    -------

    """
    bone_mask = get_bone_mask(image, mask, bone_thresh)
    space_mask = (1 - bone_mask) & mask
    return calculate_mask_thickness(space_mask, voxel_width, min_th)


def calculate_porosity(
    image: np.ndarray,
    mask: np.ndarray,
    bone_thresh: float,
    max_growing_steps: int = 100,
) -> float:
    """
    Function for calculating cortical porosity.
    Reference: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC2926164/

    Parameters
    ----------
    image
    mask
    bone_thresh
    sigma
    max_growing_steps

    Returns
    -------
    float
    """

    connected_components_filter = ConnectedComponentImageFilter()

    bone_mask = get_bone_mask(image, mask, bone_thresh)

    # (1) Use 2D connectivity filtering to get a mask of pores in the cortex that are not connected to marrow
    # or background. Call this mask `initial_pore_mask`

    initial_pore_mask = np.zeros_like(bone_mask, dtype=int)

    for z in range(bone_mask.shape[2]):

        labelled_slice = GetArrayFromImage(
            connected_components_filter.Execute(
                GetImageFromArray(1 - bone_mask[:, :, z])
            )
        )

        num_objects = connected_components_filter.GetObjectCount()

        if num_objects > 1:

            counts = np.zeros((num_objects,), dtype=int)

            for i in range(num_objects):
                counts[i] = (labelled_slice == i).sum()

            sorted_labels = np.argsort(counts)

            # two largest components will be background and marrow, remove
            labelled_slice[labelled_slice == sorted_labels[-1]] = 0
            labelled_slice[labelled_slice == sorted_labels[-2]] = 0

            initial_pore_mask[:, :, z] = (labelled_slice > 0).astype(int)

    # (2) Use a region growing filter to expand the initial pore mask along the z axis into space where there
    # are voids in the cortical bone.

    # dilate the initial pore estimate mask by 1 voxel, then mask out that mask with the all pores mask.
    # this will spread the initial pores onto the other pores.
    # after each step, check how many pore voxels there are. if the number hasn't changed, stop

    num_pore_voxels_prev = initial_pore_mask.sum()

    grown_pores_mask = initial_pore_mask.copy()

    for i in range(max_growing_steps):

        grown_pores_mask = GetArrayFromImage(
            BinaryDilate(
                GetImageFromArray(grown_pores_mask),
                kernelRadius=[1, 0, 0],
                kernelType=sitkCross,
                backgroundValue=0,
                foregroundValue=1,
            )
        )
        grown_pores_mask = mask * (1 - bone_mask) * grown_pores_mask

        num_pore_voxels = grown_pores_mask.sum()

        if num_pore_voxels == num_pore_voxels_prev:
            break
        else:
            num_pore_voxels_prev = num_pore_voxels

    # (4) Add the mask of all pores found to the cortical bone mask to get a mask of bone with pores filled in.
    # Now apply the 2D connectivity filtering again to find any remaining pores that are not connected to the
    # marrow or the background.

    bone_plus_pores = bone_mask + grown_pores_mask

    extra_pore_mask = np.zeros_like(bone_plus_pores, dtype=int)

    for z in range(bone_plus_pores.shape[2]):

        labelled_slice = GetArrayFromImage(
            connected_components_filter.Execute(
                GetImageFromArray(1 - bone_plus_pores[:, :, z])
            )
        )

        num_objects = connected_components_filter.GetObjectCount()

        if num_objects > 1:

            counts = np.zeros((num_objects,), dtype=int)

            for i in range(num_objects):
                counts[i] = (labelled_slice == i).sum()

            sorted_labels = np.argsort(counts)

            # two largest components will be background and marrow
            labelled_slice[labelled_slice == sorted_labels[-1]] = 0
            labelled_slice[labelled_slice == sorted_labels[-2]] = 0

            extra_pore_mask[:, :, z] = (labelled_slice > 0).astype(int)

    # (5) Add together the two pore masks, then discard any pores with a total size of less than 5 voxels.

    combined_pore_mask = ((grown_pores_mask > 0) | (extra_pore_mask > 0)).astype(int)

    labelled_image = GetArrayFromImage(
        connected_components_filter.Execute(GetImageFromArray(combined_pore_mask))
    )

    num_objects = connected_components_filter.GetObjectCount()

    for i in range(num_objects):
        if (labelled_image == i).sum() < 5:
            labelled_image[labelled_image == i] = 0

    final_pores_mask = (labelled_image > 0).astype(int)

    # return the fraction of pore voxels divided by pore voxels plus bone voxels

    total_pore_voxels = final_pores_mask.sum()
    bone_voxels = bone_mask.sum()

    return total_pore_voxels / (total_pore_voxels + bone_voxels)


def calculate_bone_volume_fraction(
    image: np.ndarray, mask: np.ndarray, bone_thresh: float
) -> float:
    """

    Parameters
    ----------
    image
    mask
    bone_thresh

    Returns
    -------

    """
    bone_mask = get_bone_mask(image, mask, bone_thresh)
    return float(bone_mask.sum() / mask.sum())


def calculate_trabecular_number(
    image: np.ndarray,
    mask: np.ndarray,
    bone_thresh: float,
    voxel_width: float,
    min_th: float,
) -> float:
    """

    Parameters
    ----------
    image
    mask
    bone_thresh
    voxel_width
    min_th

    Returns
    -------

    """
    bone_mask = get_bone_mask(image, mask, bone_thresh)
    inter_medial_axis_space_mask = (
        ~GetArrayFromImage(BinaryThinning(GetImageFromArray(bone_mask.astype(int))))
        & mask
    )
    return 1 / calculate_mask_thickness(
        inter_medial_axis_space_mask, voxel_width, min_th
    )


def calculate_mask_average_axial_area(
    mask: np.ndarray, voxel_width: float, axial_dim: int = 2
) -> float:
    """

    Parameters
    ----------
    mask
    voxel_width
    axial_dim

    Returns
    -------

    """
    voxel_area = voxel_width**2
    return np.asarray(
        [voxel_area * s.sum() for s in np.moveaxis(mask, axial_dim, 0)]
    ).mean()


def standard_distal_morphometry(
    image: np.ndarray,
    cort_mask: np.ndarray,
    trab_mask: np.ndarray,
    voxel_width: float = 0.0606964,
    cort_thresh: float = 450.0,
    cort_sigma: float = 0.8,
    trab_thresh: float = 320.0,
    trab_sigma: float = 0.8,
    ctth_min_th: float = 0.0,
    tbn_min_th: float = 0.0,
    tbth_min_th: float = 0.0,
    tbsp_min_th: float = 0.0,
    axial_dim: int = 2,
    show_progress: bool = True,
) -> dict:
    """

    Parameters
    ----------
    image : np.ndarray
        The input CT image, with intensities in some kind of density units.

    cort_mask : np.ndarray
        A binary mask of the cortical compartment. Should be either boolean or have positive values for cortex and
        zero values for not-cortex. Should not overlap with trabecular mask.

    trab_mask : np.ndarray
        A binary mask of the trabecular compartment. Should be either boolean or have positive values for trabecular
        and zero values for not-trabecular. Should not overlap with cortical mask.

    voxel_width : float
        The physical width of voxels in the image. For now, only isotropic is supported for consistency with the
        standard HR-pQCT workflow. Default value is 0.0606964 (in um, corresponds to standard HR-pQCT protocol)

    cort_thresh : float
        The lower threshold to use to segment cortical bone. Should be in the same units as the intensity image.
        Default value is 450.0 (in mg HA/ccm, corresponds to standard HR-pQCT protocol)

    cort_sigma : float

    trab_thresh : float
        The lower threshold to use to segment trabecular bone. Should be in the same units as the intensity image.
        Default value is 320.0 (in mg HA/ccm, corresponds to standard HR-pQCT protocol)

    trab_sigma : float

    ctth_min_th : float

    tbn_min_th : float

    tbth_min_th : float

    tbsp_min_th : float

    axial_dim : int
        The axial dimension in the image, this is the dimension to iterate across slice-by-slice to find Tt.Ar, Ct.Ar,
        and Tb.Ar. Must be 0, 1, or 2. Default is 2.

    show_progress : bool
        If `True`, print messages indicating analysis progress.

    Returns
    -------
    dict
        Dictionary with string keys and float values with the estimated morphometric parameters for the given image and
        masks. Contains the following keys: `Tt.BMD`, `Ct.BMD`, `Tb.BMD`, `Ct.Th`, `Ct.Po`, `Tb.BV/TV`, `Tb.N`, `Tb.Th`,
        `Tb.Sp`, `Tt.Ar`, `Ct.Ar`, `Tb.Ar`. Refer to `DOI: 10.1007/s00198-020-05438-5` Tables 2 and 3 for descriptions
        of all parameters.
    """

    # input error checking

    if not isinstance(axial_dim, int) or axial_dim not in [0, 1, 2]:
        raise ValueError(
            "`axial_dim` must be an integer and must be either 0, 1, or 2."
        )

    if (cort_mask & trab_mask).sum() > 0:
        warn(
            "`cort_mask` and `trab_mask` should not overlap or the analysis may be invalid"
        )

    # set up the parameters dictionary
    parameters = {}

    # calculate density measures

    if show_progress:
        print("Calculating total BMD... ", end="")
    parameters["Tt.BMD"] = calculate_bone_mineral_density(image, cort_mask | trab_mask)
    if show_progress:
        print(f"{parameters['Tt.BMD']:0.2f}")

    if show_progress:
        print("Calculating cortical BMD... ", end="")
    parameters["Ct.BMD"] = calculate_bone_mineral_density(image, cort_mask)
    if show_progress:
        print(f"{parameters['Ct.BMD']:0.2f}")

    if show_progress:
        print("Calculating trabecular BMD... ", end="")
    parameters["Tb.BMD"] = calculate_bone_mineral_density(image, trab_mask)
    if show_progress:
        print(f"{parameters['Tb.BMD']:0.2f}")

    # calculate cortical morphometry
    if show_progress:
        print("Calculating cortical thickness... ", end="")
    parameters["Ct.Th"] = calculate_mask_thickness(cort_mask, voxel_width, ctth_min_th)

    if show_progress:
        print("Calculating cortical porosity... ", end="")
    parameters["Ct.Po"] = calculate_porosity(image, cort_mask, cort_thresh)

    # calculate trabecular morphometry
    if show_progress:
        print("Calculating trabecular bone volume fraction... ", end="")
    parameters["Tb.BV/TV"] = calculate_bone_volume_fraction(
        image, trab_mask, trab_thresh
    )

    if show_progress:
        print("Calculating trabecular number... ", end="")
    parameters["Tb.N"] = calculate_trabecular_number(
        image, trab_mask, trab_thresh, voxel_width, tbn_min_th
    )

    if show_progress:
        print("Calculating trabecular thickness... ", end="")
    parameters["Tb.Th"] = calculate_bone_thickness(
        image, trab_mask, trab_thresh, voxel_width, tbth_min_th
    )

    if show_progress:
        print("Calculating trabecular spacing... ", end="")
    parameters["Tb.Sp"] = calculate_bone_spacing(
        image, trab_mask, trab_thresh, voxel_width, tbsp_min_th
    )

    # calculate area measures
    if show_progress:
        print("Calculating total area... ", end="")
    parameters["Tt.Ar"] = calculate_mask_average_axial_area(
        cort_mask | trab_mask, voxel_width
    )

    if show_progress:
        print("Calculating cortical area... ", end="")
    parameters["Ct.Ar"] = calculate_mask_average_axial_area(cort_mask, voxel_width)

    if show_progress:
        print("Calculating trabecular area... ", end="")
    parameters["Tb.Ar"] = calculate_mask_average_axial_area(trab_mask, voxel_width)

    return parameters
