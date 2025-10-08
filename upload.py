import os
import sys
import subprocess
from dotenv import load_dotenv

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