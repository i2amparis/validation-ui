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
        ['Status', 'Values', 'All checks']
    )
    with in_range_tab:
        st.markdown(
            'Pass status per check (rows) and model/scenario (columns).\n\n'
                '<span style="color: green"><b>✅</b></span> for passed, '
                '<span style="color: red"><b>❌</b></span> for not passed, '
                'blank or `None` with <span style="background-color: lightgrey">grey background</span> for not assessed (required data not present):',
            unsafe_allow_html=True,
        )
        st.dataframe(
            _transpose_inrange(
                ar6_vetting_output_dfs[Ar6CriterionOutputKey.INRANGE].data
            ),
            height=DATAFRAME_PIXELS_HEIGHT,
        )
    with values_tab:
        st.markdown(
            'Values calculated for the vetting criteria per check (rows) '
            'and model/scenario (columns). '
            '<span style="color: red"><b>Red</b></span> for numbers below '
            'range, <span style="color: violet"><b>violet</b></span> for '
            'numbers above range, blank or `None` with '
            '<span style="background-color: lightgrey">grey background</span> for not assessed (required data not present):',
            unsafe_allow_html=True,
        )
        st.dataframe(
            _transpose_values(
                outputter,
                ar6_vetting_output_dfs[Ar6CriterionOutputKey.VALUE].data,
            ),
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
        'The file includes the "Status" and "Values" tabs shown here (in '
        'their original, non-transposed orientation), as well as a '
        'separate tab with both status and values for each criterion. The '
        'file uses boolean TRUE/FALSE values rather than checkboxes.'
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


_COMMON_INDEX_STYLE: tp.Final[str] = 'font-weight: bold; text-align: left'
_COMMON_COLUMN_STYLE: tp.Final[str] = 'font-weight: bold'


def _bold_headers(styler: PandasStyler) -> PandasStyler:
    """Bold the row and column headers of a Styler, matching the header
    style vetting_adapter applies to its own (non-transposed) output.

    `Styler.map_index(..., axis=...)` followed by rendering raises a
    spurious pandas `KeyError` when the corresponding axis has zero
    entries (same underlying pandas bug worked around in vetting_adapter's
    `apply_common_styling` for the non-transposed axis=0 case) -- after
    transposing, either axis can end up empty (e.g. the "all criteria
    inapplicable" case has zero model/scenario columns), so both are
    guarded here.
    """
    if len(styler.data.index) > 0:
        styler = styler.map_index(lambda x: _COMMON_INDEX_STYLE, axis=0)
    if len(styler.data.columns) > 0:
        styler = styler.map_index(lambda x: _COMMON_COLUMN_STYLE, axis=1)
    return styler
###END def _bold_headers


def _transpose_inrange(inrange_df: pd.DataFrame) -> PandasStyler:
    """Transpose the pass/fail summary (checks as rows, model/scenario as
    columns) and reapply the same pass/fail styling vetting_adapter applies
    in the original (model/scenario as rows) orientation. The styling is a
    pure function of each cell's value, so it transposes safely without
    needing to touch vetting_adapter's own styling machinery.
    """
    styler: PandasStyler = inrange_df.T.style.format(
        lambda x: 'missing' if pd.isna(x) else '✅' if x == True else '❌' \
            if x == False else '',
        na_rep='missing',
    ).map(
        lambda x: 'color: black; background-color: lightgrey' if pd.isna(x)
            else 'color: green' if x == True
            else 'color: red; font-weight: bold',
    )
    return _bold_headers(styler)
###END def _transpose_inrange


def _transpose_values(
        multi_output: MultiCriterionTargetRangeOutput,
        values_df: pd.DataFrame,
) -> PandasStyler:
    """Transpose the values summary (checks as rows, model/scenario as
    columns) and reapply per-criterion below/above-range styling.

    Unlike `_transpose_inrange`, the styling here depends on which criterion
    a cell belongs to (each has its own target range), which after
    transposing means it depends on the cell's *row* rather than a fixed
    function of the value alone -- so each criterion's row is styled with
    its own `CriterionTargetRange.is_below_range`/`.is_above_range`, one
    `Styler.map` call per row (there are only 12 rows for AR6).
    """
    transposed: pd.DataFrame = values_df.T
    styler: PandasStyler = transposed.style.format(thousands=' ')
    for _name, _criterion in multi_output.criteria.items():
        if _name not in transposed.index or _criterion.range is None:
            continue
        def _style_row(x: tp.Any, _crit=_criterion) -> str | None:
            if pd.isna(x):
                return 'color: black; background-color: lightgrey'
            if _crit.is_in_range(x) == True:
                return ''
            if _crit.is_below_range(x) == True:
                return 'color: red; font-weight: bold'
            if _crit.is_above_range(x) == True:
                return 'color: violet; font-weight: bold'
            return None
        styler = styler.map(_style_row, subset=pd.IndexSlice[[_name], :])
    return _bold_headers(styler)
###END def _transpose_values


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
