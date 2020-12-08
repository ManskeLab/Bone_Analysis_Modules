cmake_minimum_required(VERSION 3.5)

project(ErosionAnalysis)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "http://slicer.org/slicerWiki/index.php/Documentation/Nightly/Extensions/ErosionAnalysis")
set(EXTENSION_CATEGORY "Radiology")
set(EXTENSION_CONTRIBUTORS "Mingjie Zhao (McCaig Institute)")
set(EXTENSION_DESCRIPTION "The extension is developed to detect and analyze cortical interruptions and erosions. ")
set(EXTENSION_ICONURL "http://www.example.com/Slicer/Extensions/ErosionAnalysis.png")
set(EXTENSION_SCREENSHOTURLS "http://www.example.com/Slicer/Extensions/ErosionAnalysis/Screenshots/1.png")
set(EXTENSION_DEPENDS "NA") # Specified as a space separated string, a list or 'NA' if any

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(LineIntensityProfile)
add_subdirectory(AutomaticContour)
add_subdirectory(ErosionDetection)

## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
