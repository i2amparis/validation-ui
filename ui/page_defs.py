"""Common functions to be used for defining pages."""
from collections.abc import Callable
import functools
from pathlib import Path
import typing as tp

import streamlit as st
from streamlit.navigation.page import StreamlitPage

from nomenclature_adapter import dimensions as name_validation_dims

from p.name_validation_pages import (
    make_name_validation_dim_page,
    make_variable_unit_combo_validation_page,
)
from page_ids import (
    PageKey,
    PageName,
)



name_validation_dim_pagekeys: tp.Final[dict[str, PageKey]] = {
    'variable': PageKey.NAME_VALIDATION_VARIABLE,
    'model': PageKey.NAME_VALIDATION_MODEL,
    'scenario': PageKey.SCENARIO_VALIDATION_SCENARIO,
    'region': PageKey.NAME_VALIDATION_REGION,
}
name_validation_dim_pagenames: tp.Final[dict[str, PageName]] = {
    'variable': PageName.NAME_VALIDATION_VARIABLE,
    'model': PageName.NAME_VALIDATION_MODEL,
    'scenario': PageName.SCENARIO_VALIDATION_SCENARIO,
    'region': PageName.NAME_VALIDATION_REGION,
}

page_folder: tp.Final[Path] = Path(__file__).parent / 'p'

def _variable_func() -> None:
    return make_name_validation_dim_page(dim_name='variable')
def _model_func() -> None:
    return make_name_validation_dim_page(dim_name='model')
def _scenario_func() -> None:
    return make_name_validation_dim_page(dim_name='scenario')
def _region_func() -> None:
    return make_name_validation_dim_page(dim_name='region')

page_funcs: dict[str, Callable[[], None]] = {
    'variable': _variable_func,
    'model': _model_func,
    'scenario': _scenario_func,
    'region': _region_func,
}

pages: tp.Final[dict[PageKey, StreamlitPage]] = {
    PageKey.UPLOAD: st.Page(
        page_folder / 'Upload_data.py',
        title=PageName.UPLOAD,
        default=True,
    ),
    PageKey.NAME_VALIDATION_SUMMARY: st.Page(
        page_folder / 'Validation_run_and_summary.py',
        title=PageName.NAME_VALIDATION_SUMMARY,
    ),
    **{
        name_validation_dim_pagekeys[_dim]: st.Page(
            page_funcs[_dim],
            title=name_validation_dim_pagenames[_dim],
        )
        for _dim in name_validation_dims
    },
    PageKey.NAME_VALIDATION_VARIABLE_UNIT_COMBO: st.Page(
        make_variable_unit_combo_validation_page,
        title=PageName.NAME_VALIDATION_VARIABLE_UNIT_COMBO,
    ),
    PageKey.REGION_MAPPING: st.Page(
        page_folder / 'Region_mapping.py',
        title=PageName.REGION_MAPPING,
    ),
    PageKey.AR6_VETTING: st.Page(
        page_folder / 'IPCC_AR6_vetting.py',
        title=PageName.AR6_VETTING,
    ),
    PageKey.GDP_POP_HARMONIZATION: st.Page(
        page_folder / 'Pop_GDP_harmonization.py',
        title=PageName.GDP_POP_HARMONIZATION,
    ),
}
