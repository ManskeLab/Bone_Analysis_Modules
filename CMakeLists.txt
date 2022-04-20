cmake_minimum_required(VERSION 3.5)

project(Bone Analysis Modules (BAM))

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://github.com/ManskeLab/Bone_Analysis_Modules/wiki")
set(EXTENSION_CATEGORY "Bone Analysis Modules (BAM)")
set(EXTENSION_CONTRIBUTORS "Mingjie Zhao (McCaig Institute, University of Calgary), Ryan Yan (McCaig Institute, University of Calgary)")
set(EXTENSION_DESCRIPTION "This extensions provides algorithms for semi-automated detection of cortical breaks and bone erosions in HR-pQCT images. Also, it includes supporting image analysis tools such as automatic contouring and image registration.")
set(EXTENSION_ICONURL "https://raw.githubusercontent.com/ManskeLab/Bone_Analysis_Modules/main/Logos/BAM_Logo.png")
set(EXTENSION_SCREENSHOTURLS "https://raw.githubusercontent.com/ManskeLab/Bone_Analysis_Modules/main/Screenshot.png")
set(EXTENSION_DEPENDS "NA") # Specified as a space separated string, a list or 'NA' if any

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(AutomaticContour)
add_subdirectory(ErosionVolume)
add_subdirectory(CorticalBreakDetection)
add_subdirectory(FileConverter)
add_subdirectory(ImageRegistration)
add_subdirectory(ErosionComparison)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
