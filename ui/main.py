"""Main app runner."""

import streamlit as st
from streamlit.navigation.page import StreamlitPage

from common_elements import get_available_vetting_checks
from page_defs import (
    PageKey,
    pages,
    name_validation_dims,
    name_validation_dim_pagekeys,
    vetting_check_pagekeys,
)



# Only show a Vetting page if its check is actually available for the
# currently selected validation profile (some checks, e.g. GDP and
# population harmonization, are project-specific and not available for
# every profile). See `vetting_check_pagekeys` and
# `vetting_adapter.get_available_checks`.
_available_vetting_checks = get_available_vetting_checks(show_spinner=False)
_vetting_pages: list[StreamlitPage] = [
    pages[_pagekey]
    for _check_name, _pagekey in vetting_check_pagekeys.items()
    if _check_name in _available_vetting_checks
]

page: StreamlitPage = st.navigation(
    {
        '1. Start/upload': [
            pages[PageKey.UPLOAD],
        ],
        '2. Validation of names': [
            pages[PageKey.NAME_VALIDATION_SUMMARY],
        ] + [
            pages[name_validation_dim_pagekeys[_pagekey]]
            for _pagekey in name_validation_dims
        ] + [pages[PageKey.NAME_VALIDATION_VARIABLE_UNIT_COMBO]],
        '3. Region mapping': [
            pages[PageKey.REGION_MAPPING],
        ],
        '4. Validation of data': _vetting_pages,
    }
)
page.run()
