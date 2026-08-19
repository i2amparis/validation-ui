"""Elements and navigation functions used across multiple pages."""
from collections.abc import (
    Callable,
    Hashable,
    Iterable,
    Mapping,
    MutableMapping,
    Sequence,
)
import io
from pathlib import Path
import typing as tp
import warnings

import nomenclature_adapter as icnom
import vetting_adapter as ivet
from vetting_adapter.core.output.base import (
    CriterionTargetRangeOutput,
    MultiCriterionTargetRangeOutput,
)
from vetting_adapter.core.output.timeseries import \
    TimeseriesRefComparisonAndTargetOutput
from nomenclature import (
    CodeList,
    DataStructureDefinition,
)
import pandas as pd
from pandas.io.formats.style import Styler as PandasStyler
import streamlit as st
from streamlit.delta_generator import DeltaGenerator

from common_keys import SSKey
from excel import write_excel_targetrange_output
from page_ids import PageName



def check_data_is_uploaded(
        *,
        stop: bool = True,
        display_message: bool = True,
) -> bool:
    """Check whether data has been uploaded, and optionally stop if not.

    The function checks whether the session state `SSKey.IAM_DF_UPLOADED` has a
    exists and has a non-None value. If not, the function by default displays
    a message telling the user to go back to the upload page, and by deafult
    stops execution.

    Parameters
    ----------
    stop : bool, optional
        Whether to stop execution if `SSKey.IAM_DF_UPLOADED` does not exist.
        Note that the function will not return if `stop` is True and no uploaded
        data is found. Optional, by default True.
    display_message : bool, optional
        Whether to display a message telling the user to go back to the upload
        page. Optional, by default True.

    Returns
    -------
    bool
        Whether uploaded data was found.
    """
    if st.session_state.get(SSKey.IAM_DF_UPLOADED, None) is None:
        if display_message:
            st.info(
                'No data uploaded yet. Please go to the upload page '
                    f'("{PageName.UPLOAD}") and upload data first.',
                icon="⛔"
            )
        if stop:
            st.stop()
        return False
    return True
###END def check_data_is_uploaded


def common_setup() -> None:
    """Common setup for all pages."""
    pass
###END def common_setup

def common_instructions() -> None:
    """Display common instructions for all pages.

    Note that some content may be displayed in the sidebar, and some may be
    displayed directly in the page body. This may also change over time. For
    that reason, the function should always be called at a point in the page
    code where any calls to `st.write`, `st.info` or similar methods are
    appropriate.
    """
    @st.dialog(title='NB!', width='large')
    def _dismissable_warnings():
        st.info(
            'Do not use browser back/forward buttons, or reload the page '
                'unless you wish to reset the data and start over.',
            icon="⚠️",
        )
        st.session_state[SSKey.DISMISSED_WARNING] = st.checkbox(
            'Do not show again until next run',
            value=True,
        )
    if not st.session_state.get(SSKey.DISMISSED_WARNING, False):
        _dismissable_warnings()
###END def common_instructions


def make_passed_status_message(all_passed: bool, all_included: bool) -> str:
    """Make an HTML message to display whether all checks have passed.

    Also makes a message to display whether all models/scenarios have been
    assessed for all checks.
    """
    all_passed_message: str
    all_included_message: str
    if all_passed:
        all_passed_message = '<p style="font-weight: bold">Status: ' \
            '<span style="color: green">All checks passed</span></p>'
    else:
        all_passed_message = '<p style="font-weight: bold">Status: ' \
            '<span style="color: red">Some checks failed</span></p>'
    if all_included:
        all_included_message = '<p style="font-weight: bold">Coverage: ' \
            '<span style="color: green">All models/scenarios assessed for ' \
            'all checks</span></p>'
    else:
        all_included_message = '<p style="font-weight: bold">Coverage: ' \
            '<span style="color: red">Some models/scenarios not assessed ' \
            'for some or all checks</span></p>'
    return '\n'.join([all_passed_message, all_included_message])
###END def make_status_message


@st.fragment
def download_excel_targetrange_output_button(
    output_data: pd.DataFrame|PandasStyler \
        | dict[str, pd.DataFrame|PandasStyler],
    outputter: CriterionTargetRangeOutput | MultiCriterionTargetRangeOutput \
        | TimeseriesRefComparisonAndTargetOutput,
    download_path_key: SSKey,
    download_file_name: str = 'download.xlsx',
    use_prepare_button: bool = True,
    download_button_text: str = 'Download xlsx',
    prepare_button_text: str = 'Prepare download',
    download_data_text: tp.Optional[str] = None,
    prepare_download_text: tp.Optional[str] = 'Press the button to prepare ' \
        'an Excel file for download.',
) -> None:
    """Download the output data as an Excel file.

    Parameters
    ----------
    output_data : pandas DataFrame, pandas Styler, or dict
        The output data to be downloaded.
    outputter : CriterionTargetRangeOutput or MultiCriterionTargetRangeOutput
        The outputter object to be used to write the data. Should be the same
        object that was used to generate `output_data` using its
        `prepare_output` or `prepare_styled_output` method.
    download_path_key : SSKey
        The session state key to use to store the path of the downloaded file.
    download_file_name : str, optional
        The name of the file to be downloaded. Optional, 'download.xlsx' by
        default.
    use_prepare_button : bool, optional
        Whether to present the user with a button that needs to be clicked
        before the output data is prepared. If True, rather than presenting the
        user directly with a download button, there will first be a button that
        the user must press, which will write the Excel data to a temporary
        file, and then replace the prepare button with a download button. This
        avoids having to spend time and disk space to write a file that might
        not get downloaded at all. If False, the function will prepare an Excel
        file for download immediately, and present a download button directly.
        Optional, True by default.
    download_button_text : str, optional
        The text to use for the download button. Optional, 'Download' by
        default.
    prepare_button_text : str, optional
        The text to use for the prepare button. Optional, 'Prepare download' by
        default.
    download_data_text : str or None, optional
        Text to display below the download button (after having prepared the
        download data). If None, no text element is displayed. Optional, None by
        default.
    prepare_download_text : str or None, optional
        Text to display below the prepare data button. Will only be displayed if
        `prepare_button` is True. Afer the download has been prepared and the
        download button is displayed, this text will be hidden. If None, no text
        element is displayed. Optional, None by default.
    """
    button_element = st.empty()
    text_element = st.empty()
    download_file_path: Path|None \
        = st.session_state.get(download_path_key, None)
    if download_file_path is None or not download_file_path.exists():
        if use_prepare_button:
            prepare_button = button_element.button(prepare_button_text)
            if prepare_download_text is not None:
                text_element.markdown(prepare_download_text)
            if not prepare_button:
                return
        download_file_path = write_excel_targetrange_output(
            output_data=output_data,
            outputter=outputter,
            file=None,
        )
        st.session_state[download_path_key] = download_file_path
    with open (download_file_path, 'rb') as _f:
        download_button = button_element.download_button(
            label=download_button_text,
            data=_f,
            file_name=download_file_name,
        )
    if download_data_text is not None:
        text_element.markdown(download_data_text)
    else:
        text_element.empty()
###END def download_excel_output_button


@tp.overload
def get_validation_dsd(
    allow_load: tp.Literal[False],
    force_load: bool = False,
    show_spinner: bool = True,
) -> DataStructureDefinition|None:
    ...
@tp.overload
def get_validation_dsd(
    allow_load: bool = True,
    force_load: bool = False,
    show_spinner: bool = True,
) -> DataStructureDefinition:
    ...
def get_validation_dsd(
    allow_load: bool = True,
    force_load: bool = False,
    show_spinner: bool = True,
) -> DataStructureDefinition|None:
    """Get the DataStructureDefinition object for the validation checks.

    Parameters
    ----------
    allow_load : bool, optional
        Whether to allow loading the DataStructureDefinition object from the
        source (the `nomenclature_adapter.get_dsd` method) if it has not
        already been loaded. If False and the DataStructureDefinition object
        has not already been loaded, the function will return None.
    force_load : bool, optional
        Whether to force loading of the DataStructureDefinition object, i.e.,
        don't obtain it from the session state even if it is available.
        Optional, by default False.
    show_spinner : bool, optional
        Whether to show a spinner while loading. Optional, by default True.

    Returns
    -------
    DataStructureDefinition or None
        The DataStructureDefinition object for the validation checks if already
        loaded into session state or if `allow_load` is True. None if it has
        not been loaded and `allow_load` is False.
    """

    # Get the selected profile from session state.
    selected_profile = st.session_state.get(
        SSKey.VALIDATION_PROFILE, icnom.DEFAULT_PROFILE
    )

    dsd: DataStructureDefinition|None = st.session_state.get(
        SSKey.VALIDATION_DSD, None)
    loaded_profile = st.session_state.get(SSKey.VALIDATION_DSD_PROFILE)
    if (
        (dsd is None and allow_load)
        or force_load
        or loaded_profile != selected_profile
    ):
        if show_spinner:
            with st.spinner('Loading datastructure definition...'):
                dsd = icnom.get_dsd(force_reload=force_load,
                profile_name=selected_profile)
        else:
            dsd = icnom.get_dsd(force_reload=force_load,
            profile_name=selected_profile)
        st.session_state[SSKey.VALIDATION_DSD] = dsd
        st.session_state[SSKey.VALIDATION_DSD_PROFILE] = selected_profile
    return dsd
###END def get_validation_dsd


def get_available_vetting_checks(
        force_load: bool = False,
        show_spinner: bool = True,
) -> dict[str, tp.Any]:
    """Get the vetting checks available for the currently selected profile.

    Cached in session state per profile, the same way `get_validation_dsd`
    caches the datastructure definition, so that this can be called on every
    script rerun (e.g. to decide which pages to show in the sidebar) without
    triggering a fresh profile resolution (and potential git fetch) each
    time.

    Parameters
    ----------
    force_load : bool, optional
        Whether to force reloading the available checks, i.e., don't use a
        cached result even if available. Optional, by default False.
    show_spinner : bool, optional
        Whether to show a spinner while loading. Optional, by default True.

    Returns
    -------
    dict[str, object]
        Mapping of check name to its output object, as returned by
        `vetting_adapter.get_available_checks`.
    """
    selected_profile = st.session_state.get(
        SSKey.VALIDATION_PROFILE, icnom.DEFAULT_PROFILE
    )

    checks: dict[str, tp.Any]|None = st.session_state.get(SSKey.VETTING_CHECKS)
    loaded_profile = st.session_state.get(SSKey.VETTING_CHECKS_PROFILE)
    if checks is None or force_load or loaded_profile != selected_profile:
        if show_spinner:
            with st.spinner('Loading available vetting checks...'):
                checks = ivet.get_available_checks(profile_name=selected_profile)
        else:
            checks = ivet.get_available_checks(profile_name=selected_profile)
        st.session_state[SSKey.VETTING_CHECKS] = checks
        st.session_state[SSKey.VETTING_CHECKS_PROFILE] = selected_profile
    return checks
###END def get_available_vetting_checks


def make_attribute_df(
        codelist: CodeList,
        attr_names: tp.Optional[Iterable[str]] = None,
        column_names: tp.Optional[Mapping[str, str]] = None,
        use_filler: bool|tp.Any = False,
) -> pd.DataFrame:
    """Make a DataFrame with the specified attributes of a CodeList.

    Parameters
    ----------
    codelist : CodeList
        The CodeList object to get the attributes from.
    attr_names : Iterable[str]
        The names of the attributes to include. Optional, by default
        `['name', 'description']`.
    column_names : Mapping[str, str]
        A mapping from attribute name to column name. Optional, by default uses
        the attribute names directly as column names.
    use_filler : bool or any
        Whether to use filler values for items that miss the given attributes
        (as opposed to raising an `AttributeError`). If `False` (bool literal),
        no filler will be used, and `AttributeError` will be most likely be
        raised if any of `attr_names` is missing for any of the code items. If
        any other value, that value will be used as for any attributes that are
        not found.

    Returns
    -------
    pd.DataFrame
        A DataFrame with the specified attributes listed in columns.
    """
    if attr_names is None:
        attr_names = ['name', 'description']
    if column_names is None:
        column_names = dict(zip(attr_names, attr_names))
    return_df: pd.DataFrame = pd.DataFrame(
        data=[
            [getattr(_code, _attr_name) for _attr_name in attr_names]
            if use_filler==False else
            [getattr(_code, attrname, use_filler) for attrname in attr_names]
            for _code in codelist.values()
        ],
        columns=list(column_names.values()),
        dtype=str,
    )
    if use_filler is not False:
        return_df = return_df.fillna(use_filler)
    return return_df
###END def make_attribute_df


class GetOnReadBytesIO(io.BytesIO):
    """A BytesIO object that fetches data from a callable on first read.

    This class can be used to define an BytesIO object that calls a function to
    generate or fetch data the first time one of its read methods is called. The
    data must return a bytes object, which is cached and used on later calls to
    any of the read methods (caching can be disabled).

    Init parameters
    ----------
    on_read : Callable
        A callable that returns a bytes object when called. This callable is
        called on the first call to any of the following `BytesIO` methods:
        `getvalue()`, `getbuffer()`, `read()`, `read1()`, `readinto()`,
        `readinto1()`, `readline()`, and `readlines()`.
    initial_bytes : bytes, optional
        The initial bytes to store in the BytesIO object. Optional, by default
        `b''`.
    cache_data : bool, optional
        Whether to cache the data returned by `on_read`. Optional, by default
        `True`.

    Attributes
    ----------
    on_read : Callable
        The `on_read` attribute is set to the given `on_read` function.
    is_cached : bool
        Whether data has been read from `on_read` and is cached.

    Methods
    -------
    clear_cache()
        Clears cached data. `on_read` will be called again on the next read. If
        no data has been cached yet (or if `cache_data` is `False`), this method
        does nothing.
    """

    def __init__(
            self,
            on_read: tp.Callable[[], bytes],
            *,
            initial_bytes: bytes = b'',
            cache_data: bool = True,
    ) -> None:
        super().__init__(initial_bytes)
        self.on_read: tp.Callable[[], bytes] = on_read
        self.is_cached: bool = False
        self.cache_data: bool = cache_data
    ###END def GetOnReadBytesIO.__init__

    def _get_data(self) -> None:
        """Reads data from `on_read` or from cache."""
        if self.is_cached:
            return
        self.write(self.on_read())
        self.seek(0)
        if self.cache_data:
            self.is_cached = True
    ###END def _get_data

    def clear_cache(self) -> None:
        """Clears data. `on_read` will be called again on the next read."""
        self.seek(0)
        self.truncate(0)
        self.is_cached = False
    ###END def clear_cache

    def read(self, size: int = -1) -> bytes:
        """Reads data from `on_read` or from cache."""
        self._get_data()
        return super().read(size)
    ###END def read

    def read1(self, size: int = -1) -> bytes:
        """Reads data from `on_read` or from cache."""
        self._get_data()
        return super().read1(size)
    ###END def read1

    def readline(self, size: int = -1) -> bytes:
        """Reads data from `on_read` or from cache."""
        self._get_data()
        return super().readline(size)
    ###END def readline

    def readlines(self, size: int = -1) -> list[bytes]:
        """Reads data from `on_read` or from cache."""
        self._get_data()
        return super().readlines(size)
    ###END def readlines

    def getvalue(self) -> bytes:
        """Reads data from `on_read` or from cache."""
        self._get_data()
        return super().getvalue()
    ###END def getvalue

    def getbuffer(self) -> memoryview:
        """Reads data from `on_read` or from cache."""
        self._get_data()
        return super().getbuffer()
    ###END def getbuffer

    def readinto(self, b: bytes) -> int:
        """Reads data from `on_read` or from cache."""
        self._get_data()
        return super().readinto(b)
    ###END def readinto

    def readinto1(self, b: bytes) -> int:
        """Reads data from `on_read` or from cache."""
        self._get_data()
        return super().readinto1(b)
    ###END def readinto1

###END class GetOnReadBytesIO


class _NoCachedValue:
    """A class to represent absence of a cahced value for a CachingFunction."""
    def __init__(self, parent: 'CachingFunction') -> None:
        self.parent: 'CachingFunction' = parent
    def __repr__(self) -> str:
        return f'NoCachedValue for {repr(self.parent)}'
    def __str__(self) -> str:
        return f'NoCachedValue for {str(self.parent)}'
###END class CachingFunction._NoCachedValue

class NoCachedValueError(RuntimeError):
    """Raised when a CachingFunction unexpectedly has no cached value."""
    ...
###END class NoCachedValueError

class CachingFunction[ReturnTypeVar]:
    """A class to cache results from a function.

    Instances of the class act as a wrapper around a single provided function,
    and will cache the result from that function the first time it is called, or
    if the cache is cleared with the `clear_cache` method. The return value can
    be stored either internally, or assigned to an externally provided dict
    under a specified key.

    The class is only intended to hold be used with functions that do not take
    any arguments, and is not intended as a replacement for `lru_cache` or any
    other general caching technique.

    Init parameters
    ---------------
    function : Callable
        The function to cache the return value from. Must take no arguments.
    cache_dict : dict, optional
        A dictionary to store the cached return values in. Optional, by default
        `None`, in which case the return value will be stored internally. Note
        that if `cache_dict` is not `None`, `cache_key` must also be provided.
        Also note that in the current implementation, `cache_dict[cache_key]` is
        immediately set to an object that represents no cached value if it does
        not already exist. If it does exist, the existing value will be assumed
        to be a previously cached return value from `function` and will be
        return when the instance is called. This ensures that a cached value,
        e.g., can be reused in cases new instances of `CachingFunction` are
        instantiated with the same `function` on different iterations of a loop
        or in different calls to another function.
    cache_key : str, optional
        The key under which to store the return value in `cache_dict`. This
        parameter is mandatory if `cache_dict` is not `None`, but ignored if it
        is `None`. *NB!* It is the responsibility of the caller to ensure that
        `cache_dict[cache_key]` either does not exist or is set to a value that
        is a valid cached value and that can be reused by the new
        `CachingFunction` instance.

    Properties
    ----------
    has_cached_value : bool
        Whether a return value is cached. If True, a return value from the
        cached function has been cached, and will be returned whenever the
        instance is called.

    Methods
    -------
    clear_cache()
        Clears the cache. The next time the instance is called, the cached
        function will be called again, and the resulting return value will be
        stored in the cache.
    """

    def __init__(
            self,
            function: tp.Callable[[], ReturnTypeVar],
            *,
            cache_dict: tp.Optional[MutableMapping] = None,
            cache_key: Hashable = None,
    ) -> None:
        self._function: tp.Callable[[], ReturnTypeVar] = function
        self._no_cached_value: tp.Final[_NoCachedValue] = _NoCachedValue(self)
        if cache_dict is None:
            self._cache_value: ReturnTypeVar|_NoCachedValue = \
                self._no_cached_value
        else:
            self._cache_dict: MutableMapping = cache_dict
            self._cache_key: Hashable = cache_key
            if self._cache_key not in self._cache_dict:
                self._cache_dict[cache_key] = self._no_cached_value
        self.cache_type: tp.Final[tp.Literal['internal', 'external_dict']] = \
            'internal' if hasattr(self, '_cache_value') else 'external_dict'
        if self.cache_type == 'external_dict' and not hasattr(self, '_cache_dict'):
            raise RuntimeError(
                '`self.cache_type == "external_dict"` but `self._cache_dict` '
                'is not set. This should not be possible.'
            )
    ###END def CachingFunction.__init__

    def _is_not_cached_value(self, value: ReturnTypeVar|_NoCachedValue) -> bool:
        """Whether a value indicates that no value has been cached.

        In the base implementation, this function returns True if the value is
        any instance of `_NoCachedValue`, and False otherwise. Subclasses may
        want to override this to require other conditions, such as the value
        being an instance of `_NoCachedValue` that was created by `self` or some
        other conditions.

        Parameters
        ----------
        value : object
            The value to check.

        Returns
        -------
        bool
            Whether the value is a `_NoCachedValue`.
        """
        return isinstance(value, _NoCachedValue)
    ###END def CachingFunction._is_not_cached_value

    def __repr__(self) -> str:
        return f'CachingFunction({repr(self._function)})'
    ###END def CachingFunction.__repr__
    def __str__(self) -> str:
        return f'CachingFunction({str(self._function)})'
    ###END def CachingFunction.__str__

    def _get_cached_value(self) -> ReturnTypeVar|_NoCachedValue:
        """Get the cached value, or `NoCachedValue` if not cached."""
        if self.cache_type == 'internal':
            return self._cache_value
        elif self.cache_type == 'external_dict':
            return self._cache_dict[self._cache_key]
        else:
            raise RuntimeError(
                f'Unknown `self.cache_type`: {self.cache_type}'
            )
    ###END def CachingFunction._get_cached_value

    def _require_cached_value(self) -> ReturnTypeVar:
        """Get the cached value, or raise an error if not cached."""
        cached_value: ReturnTypeVar|_NoCachedValue = self._get_cached_value()
        if self._is_not_cached_value(cached_value):
            raise NoCachedValueError(
                f'`CachingFunction` instance {repr(self)} was expected to have '
                'a cached value, but doesn\'t.'
            )
        cached_value = tp.cast(ReturnTypeVar, cached_value)
        return cached_value
    ###END def CachingFunction._require_cached_value

    def _set_cached_value(self, value: ReturnTypeVar) -> None:
        """Set the cached value."""
        if self.cache_type == 'internal':
            self._cache_value = value
        elif self.cache_type == 'external_dict':
            self._cache_dict[self._cache_key] = value
        else:
            raise RuntimeError(
                f'Unknown `self.cache_type`: {self.cache_type}'
            )
    ###END def CachingFunction._set_cached_value

    @property
    def has_cached_value(self) -> bool:
        """Whether a return value is cached."""
        return not self._is_not_cached_value(self._get_cached_value())
    ###END def CachingFunction.has_cached_value

    def __call__(self) -> ReturnTypeVar:
        """Get the cached value, or call the function."""
        if self.has_cached_value:
            return self._require_cached_value()
        func_value: ReturnTypeVar = self._function()
        self._set_cached_value(func_value)
        return func_value
    ###END def CachingFunction.__call__

    def clear_cache(self) -> None:
        """Clears the cache. The next time the instance is called, the cached
        function will be called again, and the resulting return value will be
        stored in the cache."""
        if self.cache_type == 'internal':
            self._cache_value = self._no_cached_value
        elif self.cache_type == 'external_dict':
            self._cache_dict[self._cache_key] = self._no_cached_value
        else:
            raise RuntimeError(
                f'Unknown `self.cache_type`: {self.cache_type}'
            )
    ###END def CachingFunction.clear_cache

###END class CachingFunction



@st.fragment
def deferred_download_button(
        data_func: tp.Callable[[], bytes] | CachingFunction[bytes],
        download_file_name: str,
        data_cache_key: tp.Optional[str] = None,
        *,
        prepare_button_label: str = 'Prepare download',
        download_button_label: str = 'Download',
        spinner_text: str = 'Preparing download',
        prepare_notice: tp.Optional[str|Callable[[DeltaGenerator], tp.Any]] \
            = None,
        download_notice: tp.Optional[str|Callable[[DeltaGenerator], tp.Any]] \
            = None,
        bypass_prepare: bool = False,
        prepare_button_kwargs: tp.Optional[dict] = None,
        download_button_kwargs: tp.Optional[dict] = None,
) -> bool:
    """Two-stage download button that prepares data on first press.

    The function creates a button that will prepare data using a function
    provided by the caller. When the button is pressed, the data preparation
    function is called, and once the function returns, a Streamlit download
    button is displayed for downloading the data.

    If a `CachingFunction` object is passed as the `data_func` argument, its
    `cached` property will be checked to see if it has cached data. If so, the
    prepare step will be skipped, and the download button will be displayed
    directly.

    The data returned by the `data_func` function will be cached, and on later
    reruns of the page, the prepare step will be skipped. To reset the cache
    and repeat the prepare step, clear the cache. This is done by calling
    `data_func.clear_cache()` if `data_func` is a `CachingFunction` object, or
    by removing the `data_cache_key` item from `st.session_state` if `data_func`
    is a regular function or other type of callable.

    Explanatory texts can be displayed belwow the prepare button and/or below
    the download button, using the `prepare_notice` and `download_notice`
    arguments respectively. These arguments can also be functions that render
    other elements than text. The rendering wll take place directly below the
    respective buttons.

    Parameters
    ----------
    data_func : Callable[[], bytes] or CachingFunction
        The function that prepares the data. Will be called when the prpare
        button is pressed. Must be callable without arguments, and return a
        `bytes` object with the data to be downloaded. If a `CachingFunction`
        object is passed, its `cached` property will be checked to see if it has
        cached data. If so, the prepare step will be skipped and the download
        button and `download_notice` will be displayed. *NB!* Note that the
        returned data or file contents are passed to
        `streamlit.download_button`, which may keep the data in memory for the
        duration of the user session, with no way of explicitly clearing it.
        This is a feature of `streamlit.download_button`, and unfortunately
        cannot be overridden.
    download_file_name : str
        The default name to give to the downloaded file (i.e., what is displayed
        in the browser download dialogue, not the name of a file on the server
        that is to be downloaded).
    data_cache_key : str, optional
        A key to be used to store the data in the `st.session_state`. This is
        mandatory if `data_func` is a function, but is ignored if `data_func`
        is a `CachingFunction` (in which case the cache dict and key in the
        `data_func` object will be used instead). Note that if
        `st.session_state` already contains the key, whatever data it contains
        will be used as the cached data, and `data_func` will not be called.
    prepare_button_label : str
        The label to display on the prepare button. Optional, by default
        'Prepare download'.
    download_button_label : str
        The label to display on the download button. Optional, by default
        'Download'.
    spinner_text : str
        Text to display in a spinner when preparing the data. Optional, by
        default 'Preparing download'.
    prepare_notice : str or callable, optional
        Text or a function that generates Streamlit elements that are displayed
        below the prepare button. If a function, it must take an `st.empty()`
        instance as its sole argument, and render the desired elements inside
        it.
    download_notice : str or Callable[[], None], optional
        Text or a function that generates Streamlit elements that are displayed
        below the download button. If a function, it must take an `st.empty()`
        instance as its sole argument, and render the desired elements inside
        it.
    bypass_prepare : bool, optional
        Whether to bypass the prepare step. If True, the prepare step is
        skipped, `data_func` is called (or its `cached` property is checked if
        a `CachingFunction` object) directly, and the download button is shown
        immediately once the data is ready. Optional, by default False.
    prepare_button_kwargs : dict, optional
        Additional keyword arguments to pass to the `st.button` function for
        the prepare button. *NB!* Note that the `label` argument is ignored
        if present (overridden by `prepare_button_label`)
    download_button_kwargs : dict, optional
        Additional keyword arguments to pass to the `st.download_button`
        function for the download button. *NB!* Note that the `label`, `data`
        and `file_name` arguments are ignored if present (overridden by other
        parameters to this function).


    Returns
    -------
    bool
        The return value of the `st.button` function during the peparation step,
        and the return value of the `st.download_button` function during the
        download step.
    """
    if prepare_button_kwargs is None:
        prepare_button_kwargs = {}
    if 'label' in prepare_button_kwargs:
        prepare_button_kwargs.pop('label')
        warnings.warn(
            'The `label` item in `prepare_button_kwargs` is ignored, use the '
            '`prepare_button_label` parameter instead.'
        )
    if download_button_kwargs is None:
        download_button_kwargs = {}
    if 'label' in download_button_kwargs:
        download_button_kwargs.pop('label')
        warnings.warn(
            'The `label` item in `download_button_kwargs` is ignored, use the '
            '`download_button_label` parameter instead.'
        )
    if 'file_name' in download_button_kwargs:
        download_button_kwargs.pop('file_name')
        warnings.warn(
            'The `file_name` item in `download_button_kwargs` is ignored, use '
            'the `download_file_name` parameter instead.'
        )
    if 'data' in download_button_kwargs:
        download_button_kwargs.pop('data')
        warnings.warn(
            'The `data` item in `download_button_kwargs` is ignored. the '
            'value returned by `data_func` will be used instead.'
        )
    if not isinstance(data_func, CachingFunction):
        if not callable(data_func):
            raise TypeError(
                'The `data_func` parameter must be a callable or a '
                f'`CachingFunction` object, not {type(data_func)}.'
            )
        if data_cache_key is None:
            raise ValueError(
                'The `data_cache_key` parameter must be provided if `data_func` '
                'is a function.'
            )
        data_func = CachingFunction(
            data_func,
            cache_dict=st.session_state,
            cache_key=data_cache_key
        )
    button_element = st.empty()
    notice_element = st.empty()
    download_data: bytes  # Variable to hold the data to download
    if not data_func.has_cached_value and not bypass_prepare:
        _prepare_button: bool = button_element.button(prepare_button_label,
                                                      **prepare_button_kwargs)
        if prepare_notice is not None:
            if isinstance(prepare_notice, str):
                notice_element.write(prepare_notice)
            else:
                prepare_notice(notice_element)
        if not _prepare_button:
            return False
    if not data_func.has_cached_value:  # Show a spinner if data is not cached
        button_element.empty()
        with button_element:
            with st.spinner(spinner_text):
                download_data = data_func()
    else:
        download_data = data_func()
    _download_button: bool = button_element.download_button(
        download_button_label,
        data=download_data,
        file_name=download_file_name,
        **download_button_kwargs
    )
    if download_notice is not None:
        if isinstance(download_notice, str):
            notice_element.write(download_notice)
        else:
            download_notice(notice_element)
    return _download_button
###END def download_excel_output_button


@st.fragment
def stateful_checkbox(
        label: str,
        state_key: str,
        value: bool = False,
        key: tp.Optional[str] = None,
        help: tp.Optional[str] = None,
        on_change: tp.Optional[Callable[[], None]] = None,
        args: tp.Optional[Sequence] = None,
        kwargs: tp.Optional[dict] = None,
        *,
        disabled: bool = False,
        label_visibility: tp.Literal['visible', 'hidden', 'collapsed'] \
            = 'visible',
) -> bool:
    """Checkbox with persistent state.

    Creates a checkbox that will remember its state across Streamlite reruns and
    page switches, and that does not trigger a rerun when toggled.

    The checkbox stores its state in `st.session_state` when toggled, and reads
    it from there when re-rendered.

    Note that toggling the checkbox does not trigger a rerun of the entire app.
    To get the updated state of the checkbox after the `stateful_checkbox`
    function has been called, read the value from `st.session_state[state_key]`.
    If you do wish every toggling to trigger an app rerun, set `on_change` equal
    to `st.rerun` or a function that calls it.

    Parameters
    ----------
    state_key : str
        The key used to store the checkbox state in `st.session_state`. If an
        item already exists for this key when the function is called, it will be
        used to set the checkbox state. It is the responsibility of the caller
        to ensure that the item contains a bool value if it exists. Any other
        type of value will raise a `TypeError`.
    value : bool, optional
        The initial value of the checkbox. NB! This value is only used if
        `streamlit.session_state[state_key]` does not exist. Optional, by
        default False.
    on_change : callable, optional
        Function to call when the checkbox is toggled. Note that
        `streamlit.session_state[state_key]` will be toggled before
        `on_change` is called, i.e., it will have the new value of the checkbox
        when `on_change` is called. Optional, by default None.

    The function additionally accepts all other parameters accepted by
    `stremlit.checkbox`, with the same behavior.
    """
    if not isinstance(value, bool):
        raise TypeError(f'`value` must be a bool, not {type(value)}.')
    use_value: bool|None = st.session_state.get(state_key, None)
    if not (isinstance(use_value, bool) or use_value is None):
        raise TypeError(
            f'`streamlit.session_state["{state_key}"]` must be a bool.'
        )
    if use_value is None:
        use_value = value
        st.session_state[state_key] = use_value

    def _toggle_value() -> None:
        if on_change is not None:
            on_change()
        st.session_state[state_key] = not st.session_state[state_key]

    st.checkbox(
        label,
        value=use_value,
        key=key,
        help=help,
        on_change=_toggle_value,
        args=args,
        kwargs=kwargs,
        disabled=disabled,
        label_visibility=label_visibility
    )

    return use_value
###END def stateful_checkbox
