import os
import sys
import subprocess
from dotenv import load_dotenv
import shutil

def clean_build_folders():
    """Removes the dist, build, and .egg-info directories."""
    print("🧹 Cleaning old build artifacts...")
    folders_to_remove = ["dist", "build"]
    # Find any .egg-info folders to remove as well
    for item in os.listdir('.'):
        if item.endswith('.egg-info'):
            folders_to_remove.append(item)

    for folder in folders_to_remove:
        if os.path.exists(folder):
            shutil.rmtree(folder)
            print(f"   - Removed '{folder}'")

# Clean old build and then build the package
try:
    clean_build_folders()
    print("\n📦 Building the package...")
    # This runs 'python -m build' and checks if it was successful
    build_command = [sys.executable, "-m", "build"]
    subprocess.run(build_command, check=True)
    print("✅ Build successful!")
except subprocess.CalledProcessError as e:
    print(f"❌ Build failed with error: {e}")
    sys.exit(1) # Exit the script if the build fails
except FileNotFoundError:
    print("❌ Error: 'build' command not found. Is it installed? (pip install build)")
    sys.exit(1)

# Load variables from .env file into the environment
load_dotenv()
print("✅ Loaded environment variables from .env file.")

# Get the target repository from the command-line argument
# Default to the real PyPI if no argument is given
target = "pypi"
if len(sys.argv) > 1 and sys.argv[1] == "test":
    target = "testpypi"

# Construct the twine upload command
if target == "testpypi":
    print("🚀 Preparing to upload to TestPyPI...")
    command = [
        "python", "-m", "twine", "upload",
        "--repository", "testpypi",
        "dist/*"
    ]
else:
    print("🚀 Preparing to upload to the REAL PyPI...")
    command = [
        "python", "-m", "twine", "upload",
        "dist/*"
    ]

# Run the command. The TWINE_USERNAME and TWINE_PASSWORD are now in the environment
# and twine will pick them up automatically.
try:
    subprocess.run(command, check=True)
    print(f"✅ Successfully uploaded to {target}!")
except subprocess.CalledProcessError as e:
    print(f"❌ Upload failed: {e}")
    sys.exit(1)
except FileNotFoundError:
    print("❌ Error: 'twine' command not found. Is it installed?")
    sys.exit(1)