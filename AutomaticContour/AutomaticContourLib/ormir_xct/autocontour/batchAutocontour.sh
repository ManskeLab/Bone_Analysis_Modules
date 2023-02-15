#!/bin/bash -u
AUTOCONTOUR_SCRIPT="/Users/mkuczyns/Projects/HandOA/autocontour.py"
IMG_DIR="/Volumes/LaCie/HandOA/"

cd $IMG_DIR

# HANDOA_001
CMC="/Volumes/LaCie/HandOA/HANDOA_001/stackRegistrationOutput/FULL_IMAGE.nii"
cmd="python \"${AUTOCONTOUR_SCRIPT}\" \"${CMC}\""
eval $cmd

# HANDOA_002
CMC="/Volumes/LaCie/HandOA/HANDOA_002/stackRegistrationOutput/FULL_IMAGE.nii"
cmd="python \"${AUTOCONTOUR_SCRIPT}\" \"${CMC}\""
eval $cmd

# HANDOA_003
CMC="/Volumes/LaCie/HandOA/HANDOA_003/stackRegistrationOutput/FULL_IMAGE.nii"
cmd="python \"${AUTOCONTOUR_SCRIPT}\" \"${CMC}\""
eval $cmd

# HANDOA_007
CMC="/Volumes/LaCie/HandOA/HANDOA_007/stackRegistrationOutput/FULL_IMAGE.nii"
cmd="python \"${AUTOCONTOUR_SCRIPT}\" \"${CMC}\""
eval $cmd

# HANDOA_009
CMC="/Volumes/LaCie/HandOA/HANDOA_009/stackRegistrationOutput/FULL_IMAGE.nii"
cmd="python \"${AUTOCONTOUR_SCRIPT}\" \"${CMC}\""
eval $cmd

# HANDOA_010
CMC="/Volumes/LaCie/HandOA/HANDOA_010/stackRegistrationOutput/FULL_IMAGE.nii"
cmd="python \"${AUTOCONTOUR_SCRIPT}\" \"${CMC}\""
eval $cmd

# HANDOA_012
CMC="/Volumes/LaCie/HandOA/HANDOA_012/stackRegistrationOutput/FULL_IMAGE.nii"
cmd="python \"${AUTOCONTOUR_SCRIPT}\" \"${CMC}\""
eval $cmd

# HANDOA_101
CMC="/Volumes/LaCie/HandOA/HANDOA_101/stackRegistrationOutput/FULL_IMAGE.nii"
cmd="python \"${AUTOCONTOUR_SCRIPT}\" \"${CMC}\""
eval $cmd

# HANDOA_103
CMC="/Volumes/LaCie/HandOA/HANDOA_103/stackRegistrationOutput/FULL_IMAGE.nii"
cmd="python \"${AUTOCONTOUR_SCRIPT}\" \"${CMC}\""
eval $cmd

# HANDOA_104
CMC="/Volumes/LaCie/HandOA/HANDOA_104/stackRegistrationOutput/FULL_IMAGE.nii"
cmd="python \"${AUTOCONTOUR_SCRIPT}\" \"${CMC}\""
eval $cmd

# HANDOA_106
CMC="/Volumes/LaCie/HandOA/HANDOA_106/stackRegistrationOutput/FULL_IMAGE.nii"
cmd="python \"${AUTOCONTOUR_SCRIPT}\" \"${CMC}\""
eval $cmd

# HANDOA_107
CMC="/Volumes/LaCie/HandOA/HANDOA_107/stackRegistrationOutput/FULL_IMAGE.nii"
cmd="python \"${AUTOCONTOUR_SCRIPT}\" \"${CMC}\""
eval $cmd

# HANDOA_109
CMC="/Volumes/LaCie/HandOA/HANDOA_109/stackRegistrationOutput/FULL_IMAGE.nii"
cmd="python \"${AUTOCONTOUR_SCRIPT}\" \"${CMC}\""
eval $cmd

# HANDOA_112
CMC="/Volumes/LaCie/HandOA/HANDOA_112/stackRegistrationOutput/FULL_IMAGE.nii"
cmd="python \"${AUTOCONTOUR_SCRIPT}\" \"${CMC}\""
eval $cmd

# HANDOA_113
CMC="/Volumes/LaCie/HandOA/HANDOA_113/stackRegistrationOutput/FULL_IMAGE.nii"
cmd="python \"${AUTOCONTOUR_SCRIPT}\" \"${CMC}\""
eval $cmd