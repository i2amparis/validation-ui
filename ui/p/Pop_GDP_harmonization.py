from collections.abc import Mapping
from pathlib import Path

import pandas as pd
from pandas.io.formats.style import Styler as PandasStyler
import pyam
import streamlit as st

from iamcompact_vetting.output.timeseries import (
    CTCol,
    TimeseriesRefComparisonAndTargetOutput,
)
from iamcompact_vetting.output.iamcompact_outputs import \
    gdp_pop_harmonization_output

from common_elements import (
    check_data_is_uploaded,
    common_instructions,
    common_setup,
    download_excel_targetrange_output_button,
    make_passed_status_message,
)
from common_keys import (
    PAGE_RUN_NAME,
    SSKey,
    Ar6CriterionOutputKey,
)
from page_ids import PageName


DATAFRAME_PIXELS_HEIGHT: int = 480

# The functions below depend on a common iamcompact_vetting
# MultiCriterionTargetRangeOutput object to compute vetting checks and to
# produce output. It is set in the line below as a global variable (within this
# file). Change it here if needed, rather than inside the functions.
outputter: TimeseriesRefComparisonAndTargetOutput = gdp_pop_harmonization_output


def main():

    common_setup()

    st.header('GDP and population harmonization assessment')

    check_data_is_uploaded(stop=True, display_message=True)

    iam_df: pyam.IamDataFrame = st.session_state.get(SSKey.IAM_DF_REGIONMAPPED,
                                                     None)
    if iam_df is None:
        st.info(
            '**NB!** You have not run the region mapping step. If your results '
            'contain model-specific region names, and the file you uploaded '
            'has not already gone through region mapping, you will probably '
            'see unrecognized names or errors in the region name check. '
            'Model-specific regions will also not be checked for deviations, '
            'and you will likely **miss** any deviations in those regions. If '
            'the file you uploaded had not already been region-mapped, please '
            f'return to the page "{PageName.REGION_MAPPING}" and run '
            'region mapping.',
            icon='❗️',
        )
        iam_df = st.session_state[SSKey.IAM_DF_UPLOADED]
        st.session_state[SSKey.GDP_POP_RUN_WITH_NON_REGIONMAPPED] = True
    else:
        if st.session_state.get(SSKey.GDP_POP_RUN_WITH_NON_REGIONMAPPED, False):
            st.session_state[SSKey.GDP_POP_OUTPUT_DFS] = None
            st.session_state[SSKey.GDP_POP_RUN_WITH_NON_REGIONMAPPED] = False

    summary_df_key: str = get_summary_df_key()
    values_df_key: str = get_values_df_key()

    if st.session_state.get(SSKey.GDP_POP_OUTPUT_DFS, None) is None:
        with st.spinner('Computing GDP and population harmonization checks...'):
            _styled_dfs: Mapping[str, PandasStyler] = \
                compute_gdp_pop_harmonization_check(iam_df)
            _dfs: Mapping[str, pd.DataFrame] = {
                _key: _styled_df.data
                for _key, _styled_df in _styled_dfs.items()
            }
            st.session_state[SSKey.GDP_POP_ALL_PASSED] = \
                _dfs[summary_df_key].all(axis=None, skipna=True)
            st.session_state[SSKey.GDP_POP_ALL_INCLUDED] = \
                _dfs[summary_df_key].notna().all(axis=None)
            st.session_state[SSKey.GDP_POP_OUTPUT_DFS] = _styled_dfs
            del _dfs

    vetting_output_dfs: Mapping[str, PandasStyler] = \
        st.session_state[SSKey.GDP_POP_OUTPUT_DFS]
    vetting_tolerance_range: tuple[float, float] = get_tolerance_range()
    summary_df: PandasStyler = vetting_output_dfs[summary_df_key]
    values_df: PandasStyler = vetting_output_dfs[values_df_key]
    summary_df_in_range_col: str = get_summary_df_in_range_col()
    summary_df_values_col: str = get_summary_df_values_col()

    st.markdown(
        '\n\n'.join([
            make_passed_status_message(
                all_passed=st.session_state[SSKey.GDP_POP_ALL_PASSED],
                all_included=st.session_state[SSKey.GDP_POP_ALL_INCLUDED],
            ),
        ]),
        unsafe_allow_html=True,
    )

    st.markdown(
        'Values are considered to be within range if they are between '
        f'{-(vetting_tolerance_range[0]*100.0-100.0):.1f}% below and '
        f'{vetting_tolerance_range[1]*100.0-100.0:.1f}% above the '
        'harmonization values.'
    )

    summary_tab, values_tab, descriptions_tab = st.tabs(
        ['Summary', 'Deviations', 'Descriptions']
    )
    _tab_data: PandasStyler
    with summary_tab:
        st.markdown(
            'Status per model, scenario and region. Note that models not shown '
                'in the table below have <b>not</b> been assessed, most likely '
                'due to no matching region in the harmonization data.\n\n'
                '<span style="color: green"><b>✅</b></span> for all values in '
                'range, <span style="color: red"><b>❌</b></span> for some '
                'values out of range, blank or `None` with '
                '<span style="background-color: lightgrey">grey background'
                '</span> for missing data:',
            unsafe_allow_html=True,
        )
        _tab_data = summary_df
        _column_title_dict = {
            summary_df_in_range_col: summary_df_in_range_col,
            summary_df_values_col: 'Max deviation',
        }
        st.dataframe(
            _tab_data.format(
                {
                    summary_df_in_range_col: lambda x: 'missing' if pd.isna(x) \
                        else '✅' if x==True \
                        else '❌' if x==False else '',
                    summary_df_values_col: \
                        lambda x: f'{(float(x)-1.0)*100.0:+.2f}%'
                },
                na_rep='missing'
            ),
            column_config={
                _col: st.column_config.TextColumn(_column_title_dict[_col])
                for _col in _tab_data.data.columns
            },
            height=DATAFRAME_PIXELS_HEIGHT,
        )
    with values_tab:
        st.markdown(
            'Values calculated for the vetting criteria per model and '
            'scenario. <span style="color: violet"><b>Violet</b></span> for '
            'numbers below range, <span style="color: red"><b>red</b></span> '
            'for numbers above range, blank or `None` with '
            '<span style="background-color: lightgrey">grey background</span> for not assessed (required data not present):',
            unsafe_allow_html=True,
        )
        _tab_data = values_df
        st.dataframe(
            _tab_data.format(thousands=' '),
            # column_config={
            #     _col: st.column_config.TextColumn()
            #     for _col in _tab_data.data.columns}
            height=DATAFRAME_PIXELS_HEIGHT,
        )
    with descriptions_tab:
        st.markdown('Descriptions of each vetting criterion: ')
        st.info('Still to be added...', icon='🚧')

    download_excel_file_name: str = '_'.join(
        [
            str(Path(st.session_state[SSKey.FILE_CURRENT_NAME]).stem),
            'GDP_pop_harmonization_check.xlsx',
        ]
    )
    download_excel_targetrange_output_button(
        output_data=st.session_state[SSKey.GDP_POP_OUTPUT_DFS],
        outputter=outputter,
        download_path_key=SSKey.GDP_POP_EXCEL_DOWNLOAD_PATH,
        download_file_name=download_excel_file_name,
    )
    st.markdown(
        'Download full results as an Excel file.\n'
        'The file includes the "Statuses" and "Values" tabs shown here, as '
        'well as a separate tab with both status and values for each '
        'criterion. The file uses boolean TRUE/FALSE values rather than '
        'checkboxes.'
    )

###END def main



def compute_gdp_pop_harmonization_check(
    iamdf: pyam.IamDataFrame
) -> Mapping[str, PandasStyler]:
    try:
        return gdp_pop_harmonization_output.prepare_styled_output(iamdf)

    except IndexError:
        st.warning(
            """
            **GDP & population harmonization could not be performed**

            The uploaded dataset does not contain the GDP and/or population
            variables required for harmonization checks, or no matching
            regions were found after region mapping.

            This commonly happens when:
            - GDP or population variables are missing
            - The data only contains a subset of regions
            - Region mapping has not been applied or does not match
            """
        )
        st.stop()

    except ValueError as err:
        # Catch other expected vetting failures
        st.warning(
            f"""
            **GDP & population harmonization could not be performed**

            {err}
            """
        )
        st.stop()
###END def compute_gdp_pop_harmonization_check

def get_tolerance_range() -> tuple[float, float]:
    """Gets the relative 1.0-based tolerance range for the vetting check.

    Returns
    -------
    tuple[float, float]
        The relative 1.0-based tolerance range for the vetting check. The first
        element is the lower range and the second element is the upper range.
    """
    target_range: tuple[float, float] | None \
        = gdp_pop_harmonization_output.target_range.range
    if target_range is None:
        raise RuntimeError(
            'The target range for '
            f'{gdp_pop_harmonization_output.target_range.name} is not set. '
            'This should not happen.'
        )
    return target_range
###END def get_tolerance_range

def get_summary_df_key() -> str:
    return gdp_pop_harmonization_output.summary_key
###END def get_summary_df_key

def get_values_df_key() -> str:
    return gdp_pop_harmonization_output.full_comparison_key
###END def get_values_df_key

def get_summary_df_in_range_col() -> str:
    return gdp_pop_harmonization_output.summary_column_titles[CTCol.INRANGE]
###END def get_summary_df_in_range_key

def get_summary_df_values_col() -> str:
    return gdp_pop_harmonization_output.summary_column_titles[CTCol.VALUE]
###END def get_summary_df_value_col


if __name__ == PAGE_RUN_NAME:
    main()
