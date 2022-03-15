# pca-reimagine-cdl

## 🚨 Status: Pre-alpha 🚨

## Overview

This repo is to access the prostate cancer patient data from the 
[re-imagine](https://www.reimagine-pca.org/) consortium that is stored in the
HealthSuite Platform Clinical Data Lake.

Even though this doesnt directly use the [pycdal](https://github.com/philips-internal/pycdal) package 
it is heavily inspired by it and has shamelessly lifted code from it.

1. [CONTRIBUTING.md](./CONTRIBUTING.md)
2. [CHANGELOG.md](./CHANGELOG.md)
3. [CODE_OF_CONDUCT](./CODE_OF_CONDUCT.md)
4. [CODEOWNERS](./CODEOWNERS)
5. [LICENSE](./LICENSE)

## Getting Started

## Installation

### On Windows

1.	Create a virtual environment and activate it. See [here](https://medium.com/co-learning-lounge/create-virtual-environment-python-windows-2021-d947c3a3ca78) for more details.
2.	Install all the dependencies using the requirements.txt

    ```bash
    $> pip install -r requirements.txt
    ```

## Usage

1.	Copy the config.example.py file and rename it to config.py
2.	Edit the HSP_IAM_USERNAME attribute in the HSPIAMConfig class in the config.py
3.  Edit the CDL_ORGANIZATION_ID attribute in the HSPCDLConfig class in the config.py
3.	To change the study (default ReImagine/WS1) edit the DEFAULT_STUDY_ID attribute of HSPCDLConfig class in config.py
4.  Edit the OUTPUT_DIR attribute in the BaseConfig class in the config.py to change output directory.
5.	Download all patients MR identifiers associated with the study

    ```bash
    $> python download.py patients
    ```
    
    This will prompt you for HSP IAM PASSWORD and then create a file patients.txt in the OUTPUT_DIR with all patients MR identifiers from study
6.	Download metadata for all patients

    ```bash
    $> python download.py patient-metadata
    ```

    This will create a subfolder per patient in the OUTPUT_DIR and create a file metadata.json in it which will have information about the AWS S3 buckets where the patient information is available.
    This step can fail due to expiry of HSP Access Token. If so, please delete the last patient folder that was created (See error message on console) and restart this step. It will start downloading only for the remaining patients and patients for whom subfolder is already present will be skipped.

7.	Download actual patient data

    ```bash
    $> python download.py patient-data
    ```

    This step will download DICOM data and BIOSAMPLES data in the patient subfolder under OUTPUT_DIR. I haven’t executed the steps for all the patients in one shot, so let me know if this step throws any errors.

### Community

This project uses the [CODE_OF_CONDUCT](./CODE_OF_CONDUCT.md) to define expected conduct in our community. Instances of abusive, harassing, or otherwise unacceptable behavior may be reported by contacting a project [CODEOWNER](./CODEOWNERS)

## Changelog

See [CHANGELOG](./CHANGELOG.md) for more info on what's been changed.

## Development

## Licenses

See [LICENSE](./LICENSE)

