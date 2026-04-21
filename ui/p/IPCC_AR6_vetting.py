from collections.abc import Mapping
from pathlib import Path

import pandas as pd
from pandas.io.formats.style import Styler as PandasStyler
import pyam
import streamlit as st

from iamcompact_vetting.output.base import MultiCriterionTargetRangeOutput
from iamcompact_vetting.output.iamcompact_outputs import \
    ar6_vetting_target_range_output

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


DATAFRAME_PIXELS_HEIGHT: int = 480

# The functions below depend on a common iamcompact_vetting
# MultiCriterionTargetRangeOutput object to compute vetting checks and to
# produce output. It is set in the line below as a global variable (within this
# file). Change it here if needed, rather than inside the functions.
outputter: MultiCriterionTargetRangeOutput = ar6_vetting_target_range_output


def main():

    common_setup()

    st.header('Vetting checks for IPCC AR6')

    check_data_is_uploaded(stop=True, display_message=True)
    uploaded_iamdf: pyam.IamDataFrame = st.session_state[SSKey.IAM_DF_UPLOADED]

    if st.session_state.get(SSKey.AR6_CRITERIA_OUTPUT_DFS, None) is None:
        with st.spinner('Computing IPCC AR6 vetting checks...'):
            _styled_dfs: Mapping[str, PandasStyler] = \
                compute_ar6_vetting_checks(uploaded_iamdf)
            _dfs: Mapping[str, pd.DataFrame] = {
                _key: _styled_df.data for _key, _styled_df in _styled_dfs.items()
            }
            st.session_state[SSKey.AR6_CRITERIA_ALL_PASSED] = \
                _dfs[Ar6CriterionOutputKey.INRANGE].all(axis=None, skipna=True)
            st.session_state[SSKey.AR6_CRITERIA_ALL_INCLUDED] = \
                _dfs[Ar6CriterionOutputKey.INRANGE].notna().all(axis=None)
            st.session_state[SSKey.AR6_CRITERIA_OUTPUT_DFS] = _styled_dfs
            del _dfs

    ar6_vetting_output_dfs: Mapping[str, PandasStyler] = \
        st.session_state[SSKey.AR6_CRITERIA_OUTPUT_DFS]

    st.markdown(
        '\n\n'.join([
            make_passed_status_message(
                all_passed=st.session_state[SSKey.AR6_CRITERIA_ALL_PASSED],
                all_included=st.session_state[SSKey.AR6_CRITERIA_ALL_INCLUDED],
            ),
            'Note: In AR6, only the checks on historical values were grounds '
            'for exclusion. The checks on future values (post-2020) were only '
            'a flag for possible issues.',
        ]),
        unsafe_allow_html=True,
    )

    in_range_tab, values_tab, descriptions_tab = st.tabs(
        ['Statuses', 'Values', 'Descriptions']
    )
    _tab_data: PandasStyler
    with in_range_tab:
        st.markdown(
            'Pass status per model and scenario.\n\n'
                '<span style="color: green"><b>✅</b></span> for passed, '
                '<span style="color: red"><b>❌</b></span> for not passed, '
                'blank or `None` with <span style="background-color: lightgrey">grey background</span> for not assessed (required data not present):',
            unsafe_allow_html=True,
        )
        _tab_data = ar6_vetting_output_dfs[Ar6CriterionOutputKey.INRANGE]
        # _tab_data = ar6_vetting_output_dfs[CriterionOutputKey.INRANGE].format(lambda x: 'missing' if pd.isna(x) else '✅' if x==True else '❌' if x==False else '')
        # st.write(_tab_data.to_html(), unsafe_allow_html=True)
        st.dataframe(
            # _tab_data.data.map(lambda x: 'missing' if pd.isna(x) else '✅' if x==True else '❌' if x==False else 'unknown'),
            _tab_data.format(lambda x: 'missing' if pd.isna(x) else '✅' if x==True else '❌' if x==False else '', na_rep='missing'),
            column_config={_col: st.column_config.TextColumn()
                           for _col in _tab_data.data.columns},
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
        _tab_data = ar6_vetting_output_dfs[Ar6CriterionOutputKey.VALUE]
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
            'AR6_vetting.xlsx',
        ]
    )
    download_excel_targetrange_output_button(
        output_data=st.session_state[SSKey.AR6_CRITERIA_OUTPUT_DFS],
        outputter=outputter,
        download_path_key=SSKey.AR6_EXCEL_DOWNLOAD_PATH,
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



def compute_ar6_vetting_checks(
    iamdf: pyam.IamDataFrame
) -> Mapping[str, PandasStyler]:
    """Compute vetting checks on the IAM DataFrame."""
    try:
        return outputter.prepare_styled_output(
            iamdf,
            prepare_output_kwargs=dict(add_summary_output=True),
            style_output_kwargs=dict(include_summary=True),
        )

    except ValueError as err:
        msg = str(err)

        # Catches missing-variable / missing-slice errors from AR6 vetting
        if "is/are not available in the provided pyam.IamDataFrame" in msg:
            st.warning(
                """
                **AR6 vetting could not be performed**

                The uploaded dataset does not contain all variables required
                for IPCC AR6 vetting (e.g. global CO₂ emissions for 2020).

                This is expected for regional-only datasets or datasets
                without AFOLU-inclusive global totals.
                """
            )
            st.stop()

        # Any other ValueError should still surface (real bug)
        raise


if __name__ == PAGE_RUN_NAME:
    main()
