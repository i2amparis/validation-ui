"""Page to run reigon mapping and add it to session state before vetting."""
from io import BytesIO
from pathlib import Path

import pyam
import streamlit as st
from streamlit.delta_generator import DeltaGenerator

from nomenclature_adapter.mapping import map_regions

from common_elements import (
    check_data_is_uploaded,
    common_setup,
    deferred_download_button,
    stateful_checkbox,
)
from common_keys import (
    PAGE_RUN_NAME,
    SSKey,
)
from page_ids import PageName



def main() -> None:

    common_setup()

    st.header('Map/rename and aggregate regions')

    st.write(
        'This page maps/renames and aggregates model-specific regions to '
        'common regions with recognized region names.'
    )
    st.write(
        'Multi-country regions that are specific to a given model will in most '
        'cases be renamed by adding the model name as a prefix '
        '(`"Model|region"`), and aggregating to common regions.'
    )
    st.write(
        'Single-country regions or multi-country regions that are identical '
        'to a common region will in most cases be unchanged if they use the '
        'recognized common name, or otherwise renamed.'
    )
    st.write(
        'When completed, the region-mapped data will be used in the vetting '
        'steps.'
    )

    check_data_is_uploaded(display_message=True, stop=True)

    iam_df: pyam.IamDataFrame = st.session_state[SSKey.IAM_DF_UPLOADED]

    if st.session_state.get(SSKey.IAM_DF_REGIONMAPPED, None) is not None:
        st.info(
            'You have already performed the region-mapping step. You only need '
            'to run it again if you want to change the exclusion options.',
            icon='✅'
        )

    invalid_names_dict = \
        st.session_state.get(SSKey.VALIDATION_INVALID_NAMES_DICT, None)
    if invalid_names_dict is None:
        st.info(
            'You have not yet run the name validation step. You must first go '
            f'to the page {PageName.NAME_VALIDATION_SUMMARY} and run the '
            'name validation step before proceeding.',
            icon='⛔',
        )
        st.stop()

    if len(invalid_names_dict['model']) > 0:
        st.info(
            '**Invalid model names were found in the data.**\n\n'
            'You can in principle proceed with region-mapping, but the '
            'model-specific regions for the unrecognized model names will not '
            'be region-mapped. This means that any deviations from '
            'harmonization data in those regions will **not** be detected '
            'during the vetting steps. It is recommended that you correct the '
            'unrecognized model names and rerun before proceeding.',
            icon='⚠️',
        )

    if (len(invalid_names_dict['region']) > 0) or \
            (len(invalid_names_dict['variable']) > 0):
        st.info(
            '**Invalid region and/or variable names were found in the data.**\n\n'
            'Only recognized variable and region names can be included in the '
            'region mapping. Unrecognized  names will cause the mapping function '
            'to fail. Please make sure that you have performed the name validation '
            'step and fixed or removed any unrecognized variable and region names '
            'before proceeding.\n\n'
            'If you want to run the region despite having unrecognized region or '
            'variable names in the data, you can check the boxes below to perform '
            'region mapping on only the valid parts of the data. The data after '
            'this step will then be a mix of region-mapped fully valid data and '
            'non-mapped data that contains unrecognized region and/or variable '
            'names.\n\n'
            '**NB!** Note that this can lead to unexpected results in the '
            'vetting checks, including false fails or passes, or data being '
            'silently excluded from harmonization checks because region names do '
            'not match the harmonization data. It should only be done as a '
            'temporary quick-fix to proceed with vetting checks. You should later '
            'correct the issues by either fixing the model variable/region names '
            'or having the missing names added to the project variable/region name '
            'definitions.',
            icon='⚠️',
        )

        st.write(
            'Yes, I want to silently accept unrecognized names in the following '
            'dimensions, and apply region mapping to only parts of the data with '
            'recognized names:'
        )
        exclude_invalid_regions: bool = stateful_checkbox(
            label='Regions',
            state_key=SSKey.REGION_MAPPING_EXCLUDE_INVALID_REGIONS
        )
        exclude_invalid_variables: bool = stateful_checkbox(
            label='Variables',
            state_key=SSKey.REGION_MAPPING_EXCLUDE_INVALID_VARIABLES,
        )
        
        iam_df_excluded_vars: pyam.IamDataFrame|None = None
        if exclude_invalid_variables:
            invalid_names_dict = \
                st.session_state.get(SSKey.VALIDATION_INVALID_NAMES_DICT, None)
            if invalid_names_dict is None:
                st.info(
                    'You must run the name validation step before you can proceed '
                    'with invalid variable names. Please uncheck the box or go to '
                    f'the page "{PageName.NAME_VALIDATION_SUMMARY}',
                    icon='⛔',
                )
                st.stop()
            else:
                invalid_var_names: list[str] = invalid_names_dict['variable']
                iam_df_excluded_vars = iam_df.filter(variable=invalid_var_names)
                iam_df = iam_df.filter(variable=invalid_var_names, keep=False)
                if iam_df is None or len(iam_df) == 0:
                    st.info(
                        'The data contains no valid variable names, cannot proceed '
                        'with region mapping.',
                        icon='⚠️',
                    )
    else:
        exclude_invalid_regions = False
        iam_df_excluded_vars = None

    run_mapping_button_area = st.empty()
    result_iam_df: pyam.IamDataFrame

    def _run_mapping(
            _iam_df: pyam.IamDataFrame = iam_df,
            _button_area: DeltaGenerator = run_mapping_button_area,
            _exclude_invalid_regions: bool = exclude_invalid_regions,
            _iam_df_excluded_vars: pyam.IamDataFrame|None \
                = iam_df_excluded_vars,
    ) -> pyam.IamDataFrame:
        _button_area.empty()
        _regmapped_iam_df: pyam.IamDataFrame
        _regmap_excluded_iam_df: pyam.IamDataFrame|None = None
        with st.spinner('Performing region mapping...'):
            if _exclude_invalid_regions:
                _regmapped_iam_df, _regmap_excluded_iam_df = map_regions(
                    _iam_df,
                    return_excluded=True,
                )
            else:
                _regmapped_iam_df = map_regions(_iam_df, return_excluded=False)

        if _exclude_invalid_regions:
            with st.spinner('Combining results with excluded regions...'):
                _result_iam_df = pyam.concat(
                    [_regmapped_iam_df, _regmap_excluded_iam_df]
                )
        else:
            _result_iam_df = _regmapped_iam_df
        if _iam_df_excluded_vars is not None:
            with st.spinner('Combining results with excluded variables...'):
                _result_iam_df = pyam.concat(
                    [_result_iam_df, _iam_df_excluded_vars]
                )
        return _result_iam_df
    ###END def main._run_mapping

    if st.session_state.get(SSKey.IAM_DF_REGIONMAPPED, None) is None:
        if not run_mapping_button_area.button('Perform region mapping'):
            st.stop()
        result_iam_df = _run_mapping()
        st.session_state[SSKey.IAM_DF_REGIONMAPPED] = result_iam_df
    else:
        if run_mapping_button_area.button('Rerun region mapping'):
            result_iam_df = _run_mapping()
            st.session_state[SSKey.IAM_DF_REGIONMAPPED] = result_iam_df
        else:
            result_iam_df = st.session_state[SSKey.IAM_DF_REGIONMAPPED]

    st.info(
        'Region mapping complete. You can proceed with the vetting steps.',
        icon='✅',
    )

    def _prepare_download_data() -> bytes:
        download_io: BytesIO = BytesIO()
        result_iam_df.to_excel(download_io)
        return download_io.getvalue()
    ##END def main._prepare_download_data

    download_info_text: str = \
        'You can download the region-mapped data as an Excel file. If you ' \
        'need to rerun the vetting checks later with the same data, you can ' \
        'then upload the region-mapped file instead of the original data and ' \
        'skip the region-mapping step to save time.'

    prepare_download_extra_text: str = \
        'Click the button above to prepare the data for download, and again ' \
        'to start the download when it is ready. Note that peparing the ' \
        'Excel file can take some time, typically close to the time required ' \
        'for the region-mapping itself.'

    deferred_download_button(
        _prepare_download_data,
        download_file_name=Path(st.session_state[SSKey.FILE_CURRENT_NAME]).stem \
            + 'regionmapped.xlsx',
        data_cache_key=SSKey.IAM_DF_REGIONMAPPED_EXCEL_DOWNLOAD_BYTES,
        prepare_notice=lambda _element: _element.write(
            '\n'.join([download_info_text, prepare_download_extra_text]),
        ),
        download_notice=lambda _element: _element.write(download_info_text)
    )
    
###END def mail


if __name__ == PAGE_RUN_NAME:
    main()
