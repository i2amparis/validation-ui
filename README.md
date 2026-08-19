# Results validation and vetting app

## Introduction

This app is used for performing name-validation and region-mapping on the
modelling results of Integrated Assessment Models (IAMs), as well as vetting
using the vetting criteria from IPCC AR6, and comparison with harmonization
data (at the moment only population and GDP). The app supports multiple
projects via a validation profile selector (e.g. IAM COMPACT, TRANSIENCE),
each with its own set of valid model/region/variable/scenario names and
region mappings; see [`nomenclature-adapter`](https://github.com/i2amparis/nomenclature-adapter)
and [`vetting-adapter`](https://github.com/i2amparis/vetting-adapter) for how
profiles and checks are defined.
Specification of the vetting criteria for IPCC AR6 vetting rules can be found
in the IPCC AR6 Working Group III report, Annex III, Table 11
([link](https://www.ipcc.ch/report/ar6/wg3/downloads/report/IPCC_AR6_WGIII_Annex-III.pdf)).

The app is built in Python and Streamlit and will be eventually integrated in
I2AM PARIS, an open-access, data exchange platform for modelling results
([link](https://i2am-paris.eu)).
It is based on a fork from the [I2AM Paris validation app](https://github.com/i2amparis/validation).

This app itself started as [CICERO's `iamcompact-validation-ui`](https://github.com/ciceroOslo/iamcompact-validation-ui),
built specifically for the HORIZON EUROPE project IAM COMPACT, and has since
been generalized to support multiple projects through the validation profile
selector described above (see also
[`nomenclature-adapter`](https://github.com/i2amparis/nomenclature-adapter)
and [`vetting-adapter`](https://github.com/i2amparis/vetting-adapter), which
underwent the same generalization from their own CICERO IAM COMPACT-specific
origins).

## Installation

To run the app locally, follow these steps (ask the developer if you are not
familiar with setting up Python environments):

* Clone the repository to your computer, and cd to it: Go to where you want to
  download the repo, type `git clone https://github.com/i2amparis/validation-ui.git`
  then `cd validation-ui`.
* Create a Python virtual environment based on Python 3.11 or 3.12, using any
  any Python environment/package management tool that lets you select a Python
  version (unless your system already has Python 3.11 or 3.12 installed).
* Activate the virtual environment.
* Install the repo using your favorite Python package manager (`pip install .`
  or equivalent in the repo directory). This will install all the required
  dependencies.

You can then run the app as follows:
* In the repo directory, type `streamlit run ui/main.py`
* Go to `http://localhost:8501` in your browser.

To run the app in a production server, build and run a docker image from
`ui/Dockerfile`. This can also be done locally on your computer if you are
familiar with using Docker and don't want to create a separate Python
environment. The commands are (assuming you want to name your image
`validation_ui`:

* While in the `ui/` directory: `docker build -t validation_ui .`
  (make sure to include the final `.` period!)
* Run the image: `docker run -p 8501:8501 validation_ui`. The `-p`
  option is needed to connect to the required network port.


## Documentation

Instructions are given directly in the app. More detailed documentation will follow.

## License

GPL-3.0-or-later
