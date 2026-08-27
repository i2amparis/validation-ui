"""TRANSIENCE MS16 historical-data diagnostic comparison page.

Unlike the AR6 and GDP/population vetting pages, this check is purely
diagnostic (not pass/fail): for each variable/region covered by the
TRANSIENCE MS16 reference data, it shows the checked scenario's values next
to the historical reference values and the percent difference, for whichever
combinations the uploaded dataset actually has. Combinations the dataset
doesn't have are listed separately rather than silently dropped, and
combinations only available for a region broader than the checked dataset's
(e.g. EU27+UK vs. plain EU27) are shown with a caveat and no percent
difference, since the regions being compared aren't the same.
"""
import typing as tp

import pandas as pd
import pyam
import streamlit as st

from vetting_adapter.core.output.historical import MultiHistoricalComparisonOutput

from common_elements import (
    check_data_is_uploaded,
    common_setup,
    get_available_vetting_checks,
)
from common_keys import PAGE_RUN_NAME, SSKey
from page_ids import PageName


CHECK_NAME: tp.Final[str] = 'transience_ms16_historical'

CHECKED_VALUES_KEY: tp.Final[str] = 'checked_values'
HISTORICAL_VALUES_KEY: tp.Final[str] = 'historical_values'
PCT_DIFF_KEY: tp.Final[str] = 'pct_diff'

# The functions below depend on a common vetting_adapter
# MultiHistoricalComparisonOutput object. It is loaded from the currently
# selected validation profile's available checks. This is a
# project-specific check, so it may not be available for every profile --
# `outputter` may be None, which `main` checks for below.
outputter: MultiHistoricalComparisonOutput|None = \
    get_available_vetting_checks().get(CHECK_NAME)


def main():

    common_setup()

    st.header('Sectoral validation (MS16)')

    if outputter is None:
        st.info(
            'Sectoral validation (MS16) is not available for the '
            'currently selected validation profile.',
            icon='ℹ️',
        )
        st.stop()

    st.markdown(
        'This is a **diagnostic** comparison, not a pass/fail check: it '
        'shows how closely the historical years of the uploaded scenario '
        'follow the TRANSIENCE MS16 reference values, for whichever '
        'variable/region/year combinations the uploaded dataset actually '
        'has.'
    )

    check_data_is_uploaded(stop=True, display_message=True)

    iam_df: pyam.IamDataFrame|None = \
        st.session_state.get(SSKey.IAM_DF_REGIONMAPPED, None)
    if iam_df is None:
        st.info(
            '**NB!** You have not run the region mapping step. Since this '
            'comparison is region-specific, you will likely **miss** '
            'combinations that would otherwise match after region mapping. '
            'If the file you uploaded had not already been region-mapped, '
            f'please return to the page "{PageName.REGION_MAPPING}" and run '
            'region mapping.',
            icon='❗️',
        )
        iam_df = st.session_state[SSKey.IAM_DF_UPLOADED]
        st.session_state[SSKey.MS16_HISTORICAL_RUN_WITH_NON_REGIONMAPPED] = True
    elif st.session_state.get(
            SSKey.MS16_HISTORICAL_RUN_WITH_NON_REGIONMAPPED, False
    ):
        st.session_state[SSKey.MS16_HISTORICAL_RESULTS] = None
        st.session_state[SSKey.MS16_HISTORICAL_RUN_WITH_NON_REGIONMAPPED] = False

    if st.session_state.get(SSKey.MS16_HISTORICAL_RESULTS, None) is None:
        with st.spinner('Computing sectoral validation (MS16)...'):
            st.session_state[SSKey.MS16_HISTORICAL_RESULTS] = \
                compute_ms16_historical_results(iam_df)

    results: dict[str, dict[str, tp.Any]] = \
        st.session_state[SSKey.MS16_HISTORICAL_RESULTS]
    applicable_names = sorted(
        _name for _name, _r in results.items() if _r['status'] == 'applicable'
    )
    approximated_names = sorted(
        _name for _name, _r in results.items() if _r['status'] == 'approximated'
    )
    not_applicable_names = sorted(
        _name for _name, _r in results.items()
        if _r['status'] == 'not_applicable'
    )

    st.markdown(
        f'**{len(applicable_names)}** of **{len(results)}** reference '
        f'values match the uploaded dataset exactly, **'
        f'{len(approximated_names)}** more match with an approximated '
        f'region, and **{len(not_applicable_names)}** are not applicable to '
        'this dataset.'
    )

    applicable_tab, approximated_tab, not_applicable_tab = st.tabs([
        f'Applicable ({len(applicable_names)})',
        f'Applicable, region approximated ({len(approximated_names)})',
        f'Not applicable ({len(not_applicable_names)})',
    ])

    with applicable_tab:
        if not applicable_names:
            st.info('No exact-region matches for this dataset.', icon='ℹ️')
        for _name in applicable_names:
            _render_comparison(_name, results[_name], with_pct_diff=True)

    with approximated_tab:
        if not approximated_names:
            st.info(
                'No region-approximated matches for this dataset.', icon='ℹ️'
            )
        else:
            st.warning(
                'The historical reference for these variables covers a '
                'wider (or narrower) region than the one available in the '
                'uploaded dataset. Values are shown side by side for a '
                'visual check only -- **no percent difference is '
                'computed**, since the regions being compared are not the '
                'same.',
                icon='⚠️',
            )
        for _name in approximated_names:
            _render_comparison(_name, results[_name], with_pct_diff=False)

    with not_applicable_tab:
        if not not_applicable_names:
            st.info(
                'Every TRANSIENCE MS16 reference value applies to this '
                'dataset.', icon='ℹ️'
            )
        else:
            st.markdown(
                'These reference values could not be matched to the '
                'uploaded dataset (missing variable, region, or years):'
            )
            st.dataframe(
                pd.DataFrame([
                    {
                        'Variable': results[_name]['variable'],
                        'Region': results[_name]['region'],
                        'Unit': results[_name]['unit'],
                        'Source': results[_name]['source_name'] or '—',
                        'Source link': results[_name]['source_url'],
                    }
                    for _name in not_applicable_names
                ]),
                hide_index=True,
                column_config={
                    'Source link': st.column_config.LinkColumn(
                        display_text='Open',
                    ),
                },
            )

###END def main


# Index levels dropped for display: constant across a table (region and
# variable match the expander's title; unit is shown alongside it), unlike
# `model`/`scenario`, which are kept since a checked dataset may have more
# than one. NB: this must not be a bare string literal (i.e. not a
# docstring-style comment) -- Streamlit's "magic commands" auto-render any
# bare string expression at module scope.
_REDUNDANT_INDEX_LEVELS: tp.Final[list[str]] = ['region', 'variable', 'unit']


def _drop_redundant_levels(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    return df.droplevel(_REDUNDANT_INDEX_LEVELS, axis=0)
###END def _drop_redundant_levels


def _source_caption(
        source_name: tp.Optional[str],
        source_url: tp.Optional[str],
) -> str:
    """Markdown snippet citing a reference value's source, for display next
    to the comparison. Falls back to a plain "not available" note if the
    checkset didn't supply a citation for this variable."""
    if not source_name:
        return '_not available_'
    if source_url:
        return f'[{source_name}]({source_url})'
    return source_name
###END def _source_caption


def _render_comparison(
        name: str,
        result: dict[str, tp.Any],
        *,
        with_pct_diff: bool,
) -> None:
    with st.expander(name):
        st.markdown(
            f"**Variable:** `{result['variable']}`  \n"
            f"**Region:** `{result['region']}`  \n"
            f"**Unit:** {result['unit']}  \n"
            f"**Source:** {_source_caption(result['source_name'], result['source_url'])}"
        )
        tables: dict[str, pd.DataFrame] = result['tables']
        st.markdown('**Checked data**')
        st.dataframe(_drop_redundant_levels(tables[CHECKED_VALUES_KEY]))
        st.markdown('**TRANSIENCE MS16 historical reference**')
        st.dataframe(_drop_redundant_levels(tables[HISTORICAL_VALUES_KEY]))
        if with_pct_diff and PCT_DIFF_KEY in tables:
            st.markdown('**Percent difference (checked vs. historical)**')
            _pct_df: pd.DataFrame = _drop_redundant_levels(tables[PCT_DIFF_KEY])
            st.dataframe(
                _pct_df.style.format('{:+.2f}%') if not _pct_df.empty
                    else _pct_df
            )
###END def _render_comparison


def compute_ms16_historical_results(
        iamdf: pyam.IamDataFrame,
) -> dict[str, dict[str, tp.Any]]:
    """Compute applicability and comparison tables for every named check.

    Returns a dict mapping each criterion name to a dict with `status`
    (`"applicable"`, `"approximated"` or `"not_applicable"`), `tables` (the
    dict returned by `HistoricalComparisonOutput.prepare_output`, or None),
    and `unit` (the reference unit, for the "not applicable" listing).
    """
    results: dict[str, dict[str, tp.Any]] = {}
    for _name, _candidates in outputter.criteria.items():
        _template = _candidates[0]
        _common: dict[str, tp.Any] = {
            'variable': _template.variable,
            'region': _template.region,
            'unit': str(_template.reference.unit[0]),
            'source_name': _template.source_name,
            'source_url': _template.source_url,
        }
        _output = outputter.get_applicable_output(_name, iamdf)
        if _output is None:
            results[_name] = {
                'status': 'not_applicable', 'tables': None, **_common,
            }
            continue
        results[_name] = {
            'status': 'applicable' if _output.include_pct_diff
                else 'approximated',
            'tables': _output.prepare_output(iamdf),
            **_common,
        }
    return results
###END def compute_ms16_historical_results


if __name__ == PAGE_RUN_NAME:
    main()
