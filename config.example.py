from urllib.parse import urljoin

class HSPIAMConfig:
    #################
    #  HSP IAM      #
    #################
    HSP_IAM_URL = "https://iam-service.eu-west.philips-healthsuite.com"
    HSP_IAM_USERNAME = ""
    HSP_IAM_PASSWORD = ""       

class BaseConfig:
    OUTPUT_DIR = "c:\\tmp"
    
    
class HSPCDLConfig:
    #################
    #  HSP CDL      #
    #################
    HSP_CDL_URL = "https://research-cdl-prod-datalake.eu-west.philips-healthsuite.com/store/cdl/"
    HSP_CDL_CLIENT_ID = "public-client"
    CDL_ORGANIZATION_ID = ""
    DEFAULT_STUDY_ID = ""
    
    @classmethod
    def cdl_fhir_patient_url(self):
        return urljoin(HSPCDLConfig.HSP_CDL_URL, 
            f"{HSPCDLConfig.CDL_ORGANIZATION_ID}/Study/{HSPCDLConfig.DEFAULT_STUDY_ID}/Fhir/Patient")

    @classmethod
    def cdl_data_url(self):
        return urljoin(HSPCDLConfig.HSP_CDL_URL, 
            f"{HSPCDLConfig.CDL_ORGANIZATION_ID}/Study/{HSPCDLConfig.DEFAULT_STUDY_ID}/Data/")
    
    @classmethod
    def cdl_s3_download_credentials_url(self):
        return urljoin(HSPCDLConfig.HSP_CDL_URL, 
            f"{HSPCDLConfig.CDL_ORGANIZATION_ID}/Study/{HSPCDLConfig.DEFAULT_STUDY_ID}/DownloadCredential")
            