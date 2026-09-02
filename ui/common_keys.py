"""Common strings and keys used throughout the app."""

from enum import StrEnum
import typing as tp

from vetting_adapter.core.output.base import CTCol
from vetting_adapter.general_checks.ar6_vetting import \
    ar6_vetting_target_range_output



class SSKey(StrEnum):
    """Keys used for the `streamlit.session_state` dictionary."""

    FILE_CURRENT_NAME = 'current_filename'
    """The name of the current uploaded file."""
    FILE_CURRENT_SIZE = 'current_file_size'
    """The size of the current uploaded file."""
    FILE_CURRENT_UPLOADED = 'uploaded_file'
    """The current uploaded file object."""

    IAM_DF_UPLOADED = 'uploaded_iam_df'
    """The IamDataFrame with data from the uploaded file."""
    IAM_DF_REGIONMAPPED = 'regionmapped_iam_df'
    """Resulting IamDataFrame after region mapping."""
    IAM_DF_REGIONMAPPED_EXCEL_DOWNLOAD_BYTES = \
        'regionmapped_iam_df_excel_download_bytes'
    """Prepared Excel for downloading region-mapped data, as a bytes object."""
    IAM_DF_TIMESERIES = 'uploaded_iam_df_timeseries'
    """A generated timeseries table of the uploaded IamDataFrame."""

    DO_INSPECT_DATA = 'inspect_data'
    """Whether to display a table with the uploaded data, on the upload page."""

    VALIDATION_DSD = 'validation_dsd'
    """Datastructure definition object to use for name validation."""
    VALIDATION_DSD_PROFILE = 'validation_dsd_profile'
    """Validation profile used to load the current datastructure definition."""

    VETTING_CHECKS = 'vetting_checks'
    """Dict of available vetting checks (name -> output object) for the
    currently selected validation profile.
    """
    VETTING_CHECKS_PROFILE = 'vetting_checks_profile'
    """Validation profile used to load `VETTING_CHECKS`."""
    VALIDATION_INVALID_NAMES_DICT = 'validation_invalid_names_dict'
    """Dictionary with invalid names per dimension.

    Contains the output from the name check if performed, or is unset or None
    if the name validation has not been run yet.
    """
    VALIDATION_INVALID_UNIT_COMBOS_DF = 'validation_invalid_unit_combos_df'
    """DataFrame with invalid unit combinations

    Contains a DataFrame with invalid variable/unit combinations and valid units
    for the same variables if the unit combo check has been run, or is unset or
    None otherwise.
    """

    VALIDATION_PROFILE = 'validation_profile'
    """The name of the selected validation profile to use."""

    REGION_MAPPING_EXCLUDE_INVALID_REGIONS = 'region_mapping_exclude_invalid_regions'
    """Whether to exclude invalid regions from the region-mapping step, and thus
    avoid letting the processing crash. This is the last state of the checkbox
    on the region-mapping page.
    """
    REGION_MAPPING_EXCLUDE_INVALID_VARIABLES = 'region_mapping_exclude_invalid_variables'
    """Whether to exclude invalid variables from the region-mapping step, and thus
    avoid letting the processing crash. This is the last state of the checkbox
    on the region-mapping page.
    """

    AR6_CRITERIA_OUTPUT_DFS = 'ar6_criteria_output_dfs'
    """Output DataFrame from `.prepare_output` method of the AR6 criteria."""
    AR6_CRITERIA_ALL_PASSED = 'ar6_criteria_all_passed'
    """Whether all assessed AR6 vetting checks passed for all assessed
    models/scenarios.
    """
    AR6_CRITERIA_ALL_INCLUDED = 'ar6_criteria_all_included'
    """Whether all models/scenarios were assessed for all AR6 vetting checks."""
    AR6_CRITERIA_ALL_INAPPLICABLE = 'ar6_criteria_all_inapplicable'
    """Whether none of the 12 AR6 vetting criteria had any matching data for
    any model/scenario in the uploaded dataset (as opposed to just some
    criteria/model/scenario combinations being unassessed). Distinct from
    `AR6_CRITERIA_ALL_INCLUDED` being False, since `.all()` on an empty
    DataFrame is vacuously True and would otherwise misreport this case as
    "all checks passed".
    """
    AR6_EXCEL_DOWNLOAD_PATH = 'ar6_excel_download_path'
    """Path to the Excel file to be downloaded with AR6 vetting results. None
    if no download file has been prepared yet.
    """

    GDP_POP_RUN_WITH_NON_REGIONMAPPED = 'gdp_pop_run_with_non_regionmapped'
    """Whether the GDP and population harmonization checks may previously have
    been run with non-region-mapped data. If True and region-mapped data is
    available, it means that previously saved GDP/population harmonization
    check data should be cleared.
    """
    GDP_POP_OUTPUT_DFS = 'gdp_pop_output_harmonization_dfs'
    """Output DataFrame from `.prepare_output` method of the GDP and population
    harmonization criteria.
    """
    GDP_POP_ALL_PASSED = 'gdp_pop_all_passed'
    """Whether all assessed GDP and population harmonization checks passed for
    all assessed models/scenarios.
    """
    GDP_POP_ALL_INCLUDED = 'gdp_pop_all_included'
    """Whether all models/scenarios were assessed for all GDP and population
    harmonization checks.
    """
    GDP_POP_EXCEL_DOWNLOAD_PATH = 'gdp_pop_excel_download_path'
    """Path to the Excel file to be downloaded with GDP and population
    harmonization results. None if no download file has been prepared yet.
    """

    MS16_HISTORICAL_RUN_WITH_NON_REGIONMAPPED = \
        'ms16_historical_run_with_non_regionmapped'
    """Whether the TRANSIENCE MS16 historical-comparison check may previously
    have been run with non-region-mapped data. If True and region-mapped data
    is available, it means that previously computed results should be
    cleared and recomputed.
    """
    MS16_HISTORICAL_RESULTS = 'ms16_historical_results'
    """Per-criterion results for the TRANSIENCE MS16 historical-comparison
    check: a dict mapping criterion name to a dict with keys `status`
    (`"applicable"`, `"approximated"` or `"not_applicable"`), `tables` (the
    dict returned by `HistoricalComparisonOutput.prepare_output`, or None if
    not applicable) and `unit` (the reference unit, for display in the "not
    applicable" listing).
    """

    DISMISSED_WARNING = 'dismissed_warning'
    """Whether the warning about not using browser navigation buttons has been
    dismissed.
    """

###END class SSKey

data_file_upload_clear_keys: tp.Final[tp.List[SSKey]] = [
    SSKey.IAM_DF_UPLOADED,
    SSKey.DO_INSPECT_DATA,
    SSKey.IAM_DF_TIMESERIES,
    SSKey.IAM_DF_REGIONMAPPED,
    SSKey.IAM_DF_REGIONMAPPED_EXCEL_DOWNLOAD_BYTES,
    SSKey.VALIDATION_INVALID_NAMES_DICT,
    SSKey.VALIDATION_INVALID_UNIT_COMBOS_DF,
    SSKey.AR6_CRITERIA_OUTPUT_DFS,
    SSKey.AR6_CRITERIA_ALL_PASSED,
    SSKey.AR6_CRITERIA_ALL_INCLUDED,
    SSKey.AR6_CRITERIA_ALL_INAPPLICABLE,
    SSKey.AR6_EXCEL_DOWNLOAD_PATH,
    SSKey.GDP_POP_OUTPUT_DFS,
    SSKey.GDP_POP_ALL_PASSED,
    SSKey.GDP_POP_ALL_INCLUDED,
    SSKey.MS16_HISTORICAL_RESULTS,
]


class CriterionColumn(StrEnum):
    """Column names used in output from criterion `.prepare_output` methods."""

    INRANGE = CTCol.INRANGE
    """Column name for in-range/not-in-range status, i.e., pass/fail."""

    VALUE = CTCol.VALUE
    """Column name for values returned by each criterion."""

###END class CriterionColumn

class Ar6CriterionOutputKey(StrEnum):
    """Keys used in output from AR6 criterion `.prepare_output` methods."""

    INRANGE = \
        ar6_vetting_target_range_output._default_summary_keys[CTCol.INRANGE]
    """Key for DataFrame with in-range/not-in-range status, i.e., pass/fail."""

    VALUE = \
        ar6_vetting_target_range_output._default_summary_keys[CTCol.VALUE]
    """Key for DataFrame with values returned by each criterion."""

###END class CriterionOutputKey


PAGE_RUN_NAME: tp.Final[str] = '__main__'
"""Value of the `__name__` attribute of a page being run."""
