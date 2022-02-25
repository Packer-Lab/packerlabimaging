Installation instructions
=========================

Installation
------------
``packerlabimaging`` can be installed by downloading the source code or cloning the GitHub repository and running:

.. code-block:: python

    pip install -e packerlabimaging

**We recommend following the steps below:**

1. Clone this github repository using ``git clone https://github.com/Packer-Lab/packerlabimaging.git`` in the terminal.
2. Install the conda environment provided in this repository (``plitest.yml``) using::

    conda env create -f myenv.yml

from the terminal.

Note: The package is installable as a stand-alone python package. You can install the package into an existing conda environment, or you may choose to skip using conda environment all together.
3. Activate the conda environment::

    conda activate plitest

4. ``cd`` to the parent directory of where this repo was downloaded to.
5. From this parent directly, run::

    pip install -e packerlabimaging

from terminal to install ``packerlabimaging`` as a python package under developer settings (preferred for current release).


Test/Import Installation
------------------------
Test ``packerlabimaging`` is successfully installed by importing the package in python:

1. Ensure that the conda environment from which `packerlabimaging` was installed is activated.
2. start python from command line using::

    python

, or start python from the same conda environment in your preferred method (e.g. jupyter notebook or IDE).
3. Import the package::

    import packerlabimaging
    #or
    import packerlabimaging as pli

-- Ignore any warnings or printed messages :) --

Dependencies
------------
``packerlabimaging`` requires the use of multiple scientific python packages (e.g numpy, pandas, anndata, matplotlib).
These dependencies are automatically confirmed during the installation phase of ``packerlabimaging``.
However, if there are any non-trivial issues with dependencies during installation, please be sure to report this by raising an issue on Github.
