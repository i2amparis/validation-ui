from collections.abc import Mapping
import typing as tp
from pathlib import Path

import pandas as pd
from pandas.io.formats.style import Styler as PandasStyler
import pyam
import streamlit as st

from vetting_adapter.core.output.base import MultiCriterionTargetRangeOutput

from common_elements import (
    check_data_is_uploaded,
    common_instructions,
    common_setup,
    download_excel_targetrange_output_button,
    get_available_vetting_checks,
    make_passed_status_message,
)
from common_keys import (
    PAGE_RUN_NAME,
    SSKey,
    Ar6CriterionOutputKey,
)


DATAFRAME_PIXELS_HEIGHT: int = 480

# The functions below depend on a common vetting_adapter
# MultiCriterionTargetRangeOutput object to compute vetting checks and to
# produce output. It is loaded from the currently selected validation
# profile's available checks (AR6 vetting is a built-in check, available for
# every profile, so this should never be None in practice).
outputter: MultiCriterionTargetRangeOutput|None = \
    get_available_vetting_checks().get('ar6_vetting')


def main():

    common_setup()

    st.header('Vetting checks for IPCC AR6')

    if outputter is None:
        st.info(
            'IPCC AR6 vetting is not available for the currently selected '
            'validation profile.',
            icon='ℹ️',
        )
        st.stop()

    check_data_is_uploaded(stop=True, display_message=True)
    uploaded_iamdf: pyam.IamDataFrame = st.session_state[SSKey.IAM_DF_UPLOADED]

    if st.session_state.get(SSKey.AR6_CRITERIA_OUTPUT_DFS, None) is None:
        with st.spinner('Computing IPCC AR6 vetting checks...'):
            _styled_dfs: Mapping[str, PandasStyler] = \
                compute_ar6_vetting_checks(uploaded_iamdf)
            _dfs: Mapping[str, pd.DataFrame] = {
                _key: _styled_df.data for _key, _styled_df in _styled_dfs.items()
            }
            # `len(...) == 0` (as opposed to `.all(...)`, which is vacuously
            # True on an empty DataFrame) is the correct check for "not one
            # single model/scenario had data for any of the 12 criteria" --
            # otherwise that case would be reported as "all checks passed".
            st.session_state[SSKey.AR6_CRITERIA_ALL_INAPPLICABLE] = \
                len(_dfs[Ar6CriterionOutputKey.INRANGE]) == 0
            st.session_state[SSKey.AR6_CRITERIA_ALL_PASSED] = \
                _dfs[Ar6CriterionOutputKey.INRANGE].all(axis=None, skipna=True)
            st.session_state[SSKey.AR6_CRITERIA_ALL_INCLUDED] = \
                _dfs[Ar6CriterionOutputKey.INRANGE].notna().all(axis=None)
            st.session_state[SSKey.AR6_CRITERIA_OUTPUT_DFS] = _styled_dfs
            del _dfs

    ar6_vetting_output_dfs: Mapping[str, PandasStyler] = \
        st.session_state[SSKey.AR6_CRITERIA_OUTPUT_DFS]

    if st.session_state[SSKey.AR6_CRITERIA_ALL_INAPPLICABLE]:
        st.warning(
            '**None of the 12 AR6 vetting criteria could be assessed for '
            'this dataset.** None of the required variable/region/year '
            'combinations were found for any model/scenario -- see the '
            '"All checks" tab below for exactly what each criterion '
            'requires. This is commonly a **region** naming issue: every '
            'AR6 criterion requires the exact region name `World` '
            '(case-sensitive, e.g. `WORLD` or `Global` will not match).',
            icon='⚠️',
        )
    else:
        st.markdown(
            '\n\n'.join([
                make_passed_status_message(
                    all_passed=st.session_state[SSKey.AR6_CRITERIA_ALL_PASSED],
                    all_included=st.session_state[SSKey.AR6_CRITERIA_ALL_INCLUDED],
                ),
                'Note: In AR6, only the checks on historical values were '
                'grounds for exclusion. The checks on future values '
                '(post-2020) were only a flag for possible issues.',
            ]),
            unsafe_allow_html=True,
        )

    in_range_tab, values_tab, descriptions_tab = st.tabs(
        ['Statuses', 'Values', 'All checks']
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
        st.markdown(
            'All 12 AR6 vetting criteria, the exact variable/region/year '
            'combination each one requires, and whether that combination '
            'was found for at least one model/scenario in the uploaded '
            'dataset:'
        )
        _found_columns: pd.DataFrame = \
            ar6_vetting_output_dfs[Ar6CriterionOutputKey.VALUE].data
        st.dataframe(
            _describe_all_criteria(outputter, found_columns=_found_columns),
            hide_index=True,
        )

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
    """Compute vetting checks on the IAM DataFrame.

    Individual criteria that have no matching variable/region/year data at
    all are handled gracefully by `CriterionTargetRange.get_values` (they
    show up as "not assessed" -- NaN/grey -- for every model/scenario,
    exactly like a criterion that only lacks data for *some* model/scenario
    pairs), so this should not normally raise for that reason any more. The
    `except` block below is kept only as a defensive fallback in case some
    other, currently-unanticipated path still produces that error message.
    """
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


_REQUIREMENT_COLUMN_TITLES: tp.Final[dict[str, str]] = {
    'name': 'Name',
    'variable': 'Variable',
    'region': 'Region',
    'year': 'Year',
    'reference_year': 'Reference year',
    'unit': 'Unit',
    'target': 'Target',
    'range': 'Range',
}


def _describe_all_criteria(
        multi_output: MultiCriterionTargetRangeOutput,
        *,
        found_columns: pd.DataFrame,
) -> pd.DataFrame:
    """Build an overview table of every AR6 criterion's requirements.

    One row per criterion in `multi_output.criteria`, with columns for
    whatever `CriterionTargetRange.describe_requirements` returns (variable,
    region, year, unit, target, range, ...), plus a "Found in data" column
    derived from `found_columns` (the "Values" summary DataFrame -- a
    criterion counts as found if it has a non-NaN value for at least one
    model/scenario in the uploaded dataset).
    """
    rows: list[dict[str, tp.Any]] = []
    for _name, _criterion in multi_output.criteria.items():
        _row: dict[str, tp.Any] = dict(_criterion.describe_requirements())
        if 'range' in _row and _row['range'] is not None:
            _row['range'] = f'[{_row["range"][0]:g}, {_row["range"][1]:g}]'
        _found: bool = _name in found_columns.columns \
            and found_columns[_name].notna().any()
        _row['found'] = '✅' if _found else '❌'
        rows.append(_row)
    df: pd.DataFrame = pd.DataFrame(rows)
    df = df.rename(columns=_REQUIREMENT_COLUMN_TITLES | {'found': 'Found in data'})
    _column_order: list[str] = [
        _col for _col in
        list(_REQUIREMENT_COLUMN_TITLES.values()) + ['Found in data']
        if _col in df.columns
    ]
    return df[_column_order]
###END def _describe_all_criteria


if __name__ == PAGE_RUN_NAME:
    main()
