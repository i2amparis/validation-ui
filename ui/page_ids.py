"""Page names, to be used for definitions, display and navigation.

This needs to be in a separate module from the page definitions themselves, to
avoid circular imports.
"""
from enum import StrEnum



class PageName(StrEnum):
    """Page names."""

    UPLOAD = 'Upload data'
    """The front page, for uploading data"""

    NAME_VALIDATION_SUMMARY = 'Run / summary'
    """Page for running name validation and displaying summary results"""

    NAME_VALIDATION_VARIABLE = 'Variable names'
    """Page for displaying name validation results for variable names"""
    
    NAME_VALIDATION_MODEL = 'Model names'
    """Page for displaying name validation results for model names"""
    
    SCENARIO_VALIDATION_SCENARIO = 'Scenario names'
    """Page for displaying name validation results for scenario names"""

    NAME_VALIDATION_REGION = 'Region names'
    """Page for displaying name validation results for region names"""

    NAME_VALIDATION_VARIABLE_UNIT_COMBO = 'Variable/unit combinations'
    """Page for displaying validation results for variable/unit combinations"""
    
    REGION_MAPPING = 'Run region mapping'
    """Page for running region aggregation and mapping of model-native names"""

    AR6_VETTING = 'IPCC AR6 vetting'
    """Page for running IPCC AR6 vetting checks"""

    GDP_POP_HARMONIZATION = 'GDP and population harmonization'

    MS16_HISTORICAL = 'Sectoral validation (MS16)'
    """Page for the TRANSIENCE MS16 historical-data diagnostic comparison"""

###END class PageName


PageKey = PageName
"""Enum for keys used for pages in the `pages` dict. For now the keys are 
the same as the page names.
"""