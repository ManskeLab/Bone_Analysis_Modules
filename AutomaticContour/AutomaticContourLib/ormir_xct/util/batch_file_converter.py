import os
import sys
import glob
import argparse

from ormir_xct.util.file_converter import file_converter

# Dictionary for valid file extensions
file_extensions = ["aim", "nii", "mha"]


def extension_check(input_dir, input_ext, output_ext):
    """
    Returns the input image converted to the specified file type.

    Parameters
    ----------
    input_dir : string
        The input directory containing the images to be converted.

    input_ext : string
        The input extension of files to convert.

    output_ext : string
        The output image file extension to convert images to.

    Returns
    -------
    bool
        True if the extension is valid, False otherwise.
    """

    # Check if we have a valid directory
    if not os.path.isdir(input_dir):
        print(f"Error: Invalid directory {input_dir}")
        return False

    # Check if input and output file extension are valid
    if input_ext not in file_extensions:
        print(f"Error: Invalid file extension {input_ext} for output.")
        return False
    elif output_ext not in file_extensions:
        print(f"Error: Invalid file extension {output_ext} for output.")
        return False

    # Check if any files exist in the directory with the given file extension
    if "aim" in input_ext:
        if (
            len(glob.glob(os.path.join(input_dir, "*." + input_ext))) == 0
            and len(glob.glob(os.path.join(input_dir, "*." + input_ext + ";*"))) == 0
            and len(glob.glob(os.path.join(input_dir, "*." + input_ext.upper()))) == 0
            and len(glob.glob(os.path.join(input_dir, "*." + input_ext.upper() + ";*")))
            == 0
        ):
            print("No files of type " + input_ext + " in provided directory.")
            return False
    elif len(glob.glob(os.path.join(input_dir, "*." + input_ext))) == 0:
        print("No files of type " + input_ext + " in provided directory.")
        return False

    return True


# Parse input arguments
parser = argparse.ArgumentParser()
parser.add_argument("inpout_dir", type=str, help="The input image directory")
parser.add_argument(
    "input_ext", type=str, help="The input image file type (e.g. AIM, NII, MHA, etc.)"
)
parser.add_argument(
    "output_ext",
    type=str,
    default="",
    help="The output image file type (e.g. AIM, NII, MHA, etc.)",
)
args = parser.parse_args()

input_dir = args.inpout_dir
input_ext = (args.input_ext).lower()
output_ext = (args.output_ext).lower()

if not extension_check(input_dir, input_ext, output_ext):
    sys.exit(1)

# Loop through all files in the directory
for file in os.listdir(input_dir):
    # Get the next file
    filename = os.fsdecode(file)

    old_file = os.path.join(input_dir, filename)
    base_name, extension = os.path.splitext(filename)
    extension = extension.lower()

    # Skip files that are not the type we want to convert
    if input_ext not in extension:
        continue

    # Convert the file
    new_file = os.path.join(input_dir, base_name + "." + output_ext)

    if file_extensions[0] in extension:
        # Convert from AIM
        log_file = os.path.join(input_dir, base_name + ".txt")
        file_converter(old_file, new_file)
    elif file_extensions[1] in extension or file_extensions[2] in extension:
        # Assume log files have the same name as the input file when converting
        if file_extensions[0] in output_ext:
            log_file = os.path.join(input_dir, base_name + ".txt")
        else:
            log_file = None

        file_converter(old_file, new_file)
    else:
        continue
