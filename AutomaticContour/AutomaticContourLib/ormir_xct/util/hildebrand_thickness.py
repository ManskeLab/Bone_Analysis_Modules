"""
Created by: Nathan Neeteson
Created on: ??

Description: A set of utilities for morphometry on an
                image and/or binary mask.

"""

from __future__ import annotations

import numpy as np
from collections.abc import Iterable
from numba import jit
from SimpleITK import (
    GetImageFromArray,
    GetArrayFromImage,
    SignedMaurerDistanceMap,
)
from typing import Optional, Union
import warnings

EPS = 1e-8


@jit(nopython=True, fastmath=True, error_model="numpy")
def compute_local_thickness_from_sorted_distances(
    local_thickness: np.ndarray,
    sorted_dists: np.ndarray,
    sorted_dists_indices: np.ndarray,
    voxel_width: np.ndarray,
) -> np.ndarray:
    """
    Use Hildebrand's sphere-fitting method to compute the local thickness field for a
    binary image, given an array to fill in and the sorted distance map of the binary image.

    Since the distances are sorted by distance values in ascending order, we can iterate through and assign each voxel's
    distance value to all voxels within that distance. Voxels corresponding to larger spheres will be processed
    later and overwrite values assigned by smaller spheres, and so each voxel will eventually be assigned the
    diameter of the largest sphere that it lies within.

    Finally, we do not check every voxel in the image for whether it lies within a sphere. We only check voxels that
    lie within the cube with side length equal to the sphere diameter around the center voxel. This saves a lot of
    computational effort.

    Parameters
    ----------
    local_thickness : np.ndarray
        A numpy array that is initialized as zeros.

    sorted_dists : np.ndarray
        A numpy array that is the sorted distance ridge of a mask, but the distances only. Each element is a float
        that corresponds to a distance value on the distance ridge, in ascending order.

    sorted_dists_indices : np.ndarray
        A numpy array that is the integer indices of the location of the distance. Each row in this array corresponds to
        the distance at the same position in the `dist_ridge` parameter, and then the three elements in each row are
        the i, j, k indices of the location of that voxel of the distance ridge in the binary image.

    voxel_width : np.ndarray
        A numpy array with shape (3,) that gives the width of voxels in each dimension.

    Returns
    -------
    np.ndarray
        The local thickness field.
    """

    for (rd, (ri, rj, rk)) in zip(sorted_dists, sorted_dists_indices):
        rd_sqrt = np.sqrt(rd)
        rd_sqrt_vox_0 = rd_sqrt / voxel_width[0]
        rd_sqrt_vox_1 = rd_sqrt / voxel_width[1]
        rd_sqrt_vox_2 = rd_sqrt / voxel_width[2]
        for di in range(
            np.maximum(np.floor(ri - rd_sqrt_vox_0) - 1, 0),
            np.minimum(np.ceil(ri + rd_sqrt_vox_0) + 2, local_thickness.shape[0]),
        ):
            for dj in range(
                np.maximum(np.floor(rj - rd_sqrt_vox_1) - 1, 0),
                np.minimum(np.ceil(rj + rd_sqrt_vox_1) + 2, local_thickness.shape[1]),
            ):
                for dk in range(
                    np.maximum(np.floor(rk - rd_sqrt_vox_2) - 1, 0),
                    np.minimum(
                        np.ceil(rk + rd_sqrt_vox_2) + 2, local_thickness.shape[2]
                    ),
                ):
                    if (
                        (voxel_width[0] * (di - ri)) ** 2
                        + (voxel_width[1] * (dj - rj)) ** 2
                        + (voxel_width[2] * (dk - rk)) ** 2
                    ) < rd:
                        local_thickness[di, dj, dk] = 2 * rd_sqrt
    return local_thickness


def compute_local_thickness_from_mask(
    mask: np.ndarray, voxel_width: Union[Iterable[float], float]
) -> np.ndarray:
    """
    Compute the local thickness field for a binary mask.

    This is done by calculating the distance transform and skeletonization, then combining these to create a sorted
    "distance ridge," which is an array of the distance transform values and indices of the skeletonization.
    Finally, a `numba`-jit-decorated function is called to efficiently use Hildebrand's sphere-fitting method for
    local thickness calculation. The local thickness field is scaled by the voxel width and multiplied by the
    binary mask to ensure local thickness values are not assigned to the background inadvertently.

    Parameters
    ----------
    mask : np.ndarray
        The mask for which to calculate the local thickness field.

    voxel_width : Union[Iterable[float], float]
        If an iterable of length 3, the voxel widths in each dimension. If a float, the isotropic voxel width.

    Returns
    -------
    np.ndarray
        The local thickness field.
    """
    if isinstance(voxel_width, float) or isinstance(voxel_width, int):
        voxel_width = np.array([float(voxel_width)] * 3)
    elif isinstance(voxel_width, Iterable):
        if len(voxel_width) != 3:
            raise ValueError(
                "`voxel_width must be a float, int, or iterable of length 3`"
            )
        else:
            voxel_width = np.array(voxel_width).astype(float)
    else:
        raise ValueError("`voxel_width must be a float, int, or iterable of length 3`")

    # binarize the mask if it wasn't already done
    mask = mask > 0
    if mask.sum() == 0:
        warnings.warn("given an empty mask, cannot proceed, returning zeros array")
        return np.zeros(mask.shape, dtype=float)

    mask_sitk = GetImageFromArray(
        (~np.pad(mask, 1, mode="constant", constant_values=0)).astype(int)
    )
    mask_sitk.SetSpacing(tuple(voxel_width))
    mask_dist = (
        mask
        * GetArrayFromImage(
            SignedMaurerDistanceMap(
                mask_sitk,
                useImageSpacing=True,
                insideIsPositive=False,
                squaredDistance=True,
            )
        )[1:-1, 1:-1, 1:-1]
    )
    sorted_dists = [(mask_dist[i, j, k], i, j, k) for (i, j, k) in zip(*mask.nonzero())]
    sorted_dists.sort()
    sorted_dists = np.asarray(sorted_dists)

    return mask * compute_local_thickness_from_sorted_distances(
        np.zeros(mask.shape, dtype=float),
        sorted_dists[:, 0].astype(float),
        sorted_dists[:, 1:].astype(int),
        voxel_width,
    )


def calc_structure_thickness_statistics(
    mask: np.ndarray,
    voxel_width: Union[float, Iterable],
    min_thickness: float,
    sub_mask: Optional[np.ndarray] = None,
):
    """
    Parameters
    ----------
    mask : numpy.ndarray
        3-dimensional numpy array containing a binary mask that is the segmentation of the structure you want
        to calculate the mean thickness of

    voxel_width : Union[float, Iterable]
        physical width of a voxel, for scaling distance. Either a single float value or length-3 iterable

    min_thickness : float
        the minimum thickness of the structure you want to calculate the mean thickness of

    sub_mask : Optional[np.ndarray]
        an optional sub mask. if given, we will calculate the local thickness field on `mask` but then sample
        local thickness values only from within `sub_mask` and calculate stats on these values only.

    Returns
    -------
    tuple
        the mean, standard deviation, minimum, and maximum of the local thickness of the structure defined by the mask,
        and the whole local thickness field of the entire image (0 outside the mask)
    """
    if (mask > 0).sum() > 0:
        mask = mask > 0  # binarize
        local_thickness = compute_local_thickness_from_mask(mask, voxel_width)
    else:
        warnings.warn(
            "cannot find structure thickness statistics for binary mask with no positive voxels"
        )
        return None, None, None, None, np.zeros(mask.shape, dtype=float)

    if sub_mask is not None:
        sub_mask = sub_mask > 0  # binarize
        if sub_mask.sum() == 0:
            warnings.warn(
                "cannot find structure thickness statistics for binary sub_mask with no positive voxels"
            )
            return None, None, None, None, np.zeros(mask.shape, dtype=float)
        if mask.shape != sub_mask.shape:
            raise ValueError(
                "`mask` and `sub_mask` must have same shape if `sub_mask` is given"
            )

    if sub_mask is not None:
        local_thickness_structure = local_thickness[sub_mask]
    else:
        local_thickness_structure = local_thickness[mask]

    local_thickness_structure = np.maximum(local_thickness_structure, min_thickness)

    return (
        local_thickness_structure.mean(),
        local_thickness_structure.std(),
        local_thickness_structure.min(),
        local_thickness_structure.max(),
        local_thickness,
    )
