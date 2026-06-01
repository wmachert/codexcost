from codexcost import __version__ as version
import logging
from pathlib import Path
import shutil
import subprocess
import sys


def bundle(app=version.__title__, version=version.__version__,
        extras="[all]", main=f"{version.__title__}.cli:main",
        base_path=Path(__file__).parents[1], build_name=".bundle"):
    """Create a pyz bundle containing the application and all dependencies."""
    build_path = base_path / build_name
    bundle_name = f"{app}-{version}.pyz"
    
    logging.info("Bundling application into: %s", bundle_name)

    build_path.mkdir(exist_ok=True)
    # install all dependencies
    subprocess.run(["uv", "tool", "run", "pip", "install", f".{extras}", "--target", str(build_path), "--no-compile"], cwd=base_path)
    
    # remove native binaries
    if (build_path / "bin").exists():
       shutil.rmtree(build_path / "bin")
    
    # bundle package with dependencies
    subprocess.run(["uv", "run", "python", "-m", "zipapp", "-co", bundle_name, "-p", "/usr/bin/env python3", "-m", main, str(build_path)], cwd=base_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stderr,
        format='%(asctime)s %(filename)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    bundle()
