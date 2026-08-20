from collections.abc import Mapping

import io
import pandas as pd
import pyam
import streamlit as st

import nomenclature_adapter as icnom
from nomenclature_adapter.validation import (
    get_invalid_model_regions,
    get_invalid_names,
    get_invalid_variable_units,
)
from nomenclature import DataStructureDefinition

from common_elements import (
    CachingFunction,
    check_data_is_uploaded,
    common_setup,
    deferred_download_button,
)
from common_keys import (
    PAGE_RUN_NAME,
    SSKey,
)
from p.name_validation_pages import get_validation_dsd
from page_ids import PageName



def make_dsd_excel_file() -> bytes:
    """Create an Excel file with the current data structure definition."""
    dsd: DataStructureDefinition = get_validation_dsd(force_load=True)
    output_bytes: io.BytesIO = io.BytesIO()
    dsd.to_excel(output_bytes)
    output_bytes.seek(0)
    return output_bytes.getvalue()
###END def make_dsd_excel_file


def main():

    common_setup()

    st.header('Run and summarize validation of names used in results')

    st.write(
        'This page runs validation checks for model, region, and variable names '
        'used in the uploaded results file, and variable/unit combinations. '
        'For each dimension, a red cross (❌) will be shown if any '
        'unrecognized names or variable/unit combinations were found, and a '
        'green checkmark (✅) otherwise.'
    )

    st.write(
        'If you want to view a full list of valid names offline, you can download '
        'an Excel file with the current data structure definition by pressing '
        'the button below to first prepare the file for download, and then again '
        'to download the file.'
    )

    selected_profile: str = st.session_state.get(
        SSKey.VALIDATION_PROFILE, icnom.DEFAULT_PROFILE
    )
    deferred_download_button(
        data_func=CachingFunction[bytes](make_dsd_excel_file),
        download_file_name=f'{selected_profile}_validation_dsd.xlsx',
        prepare_button_label='Prepare DSD download',
        download_button_label='Download DSD file',
    )

    check_data_is_uploaded(display_message=True, stop=True) 

    iam_df = st.session_state[SSKey.IAM_DF_UPLOADED]

    invalid_names_dict: Mapping[str, list[str]|pd.DataFrame]|None = \
        st.session_state.get(SSKey.VALIDATION_INVALID_NAMES_DICT, None)
    # Print an info message, with an "info" icon
    if invalid_names_dict is None:
        st.info(
            'Name validation has not been run yet. Press the button below to '
            'run.',
            icon='ℹ️',
        )
        button_field = st.empty()
        if button_field.button('Run name checks'):
            button_field.empty()
            dsd: DataStructureDefinition = \
                get_validation_dsd(force_load=True, allow_load=True,
                                   show_spinner=True)
            dsd_dims: list[str] = [str(_dim) for _dim in dsd.dimensions]
            non_region_dims: list[str] = [_dim for _dim in dsd_dims
                                           if _dim != 'region']
            with st.spinner(
                'Validating ' + ', '.join(non_region_dims) + ' names...'
            ):
                invalid_names_dict = \
                    get_invalid_names(iam_df, dsd, dimensions= non_region_dims)
            with st.spinner('Validating region names...'):
                invalid_region_and_model_names_dict: Mapping[str, list[str]] = \
                    get_invalid_model_regions(iam_df, dsd=dsd)
                invalid_region_and_model_names_df: pd.DataFrame = \
                    pd.DataFrame(
                        {
                            'Name': list(
                                invalid_region_and_model_names_dict.keys()
                            ),
                            'Unrecognized use by models': [
                                ', '.join(_models) for _models in
                                invalid_region_and_model_names_dict.values()
                            ]
                        },
                        dtype='string',
                    )
                invalid_names_dict['region'] = invalid_region_and_model_names_df
            st.session_state[SSKey.VALIDATION_INVALID_NAMES_DICT] = \
                invalid_names_dict
            with st.spinner('Validating variable/unit combinations...'):
                invalid_var_unit_combos = get_invalid_variable_units(iam_df, dsd)
                st.session_state[SSKey.VALIDATION_INVALID_UNIT_COMBOS_DF] = \
                    invalid_var_unit_combos
            st.rerun()
        else:
            st.stop()
        button_field.empty()
    else:
        invalid_var_unit_combos: pd.DataFrame|None = \
            st.session_state[SSKey.VALIDATION_INVALID_UNIT_COMBOS_DF]
        st.markdown('**Name validation summary**')
        st.markdown(
            '\n'.join(
                [
                    f'* **{_dim.capitalize()}**: ✅ No unrecognized names found'
                    if len(_invalid_names) == 0 else
                    f'* **{_dim.capitalize()}**: ❌ Unrecognized names found'
                    for _dim, _invalid_names in invalid_names_dict.items()
                ] + [
                    f'* **Variable/units**: ✅ No unrecognized combinations found'
                    if invalid_var_unit_combos is None else
                    f'* **Variable/units**: ❌ Unrecognized combinations found'
                ]
            )
        )

###END def main


if __name__ == PAGE_RUN_NAME:
    main()
