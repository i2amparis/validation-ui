"""Utility functions to read/write Excel files."""
import io
from pathlib import Path
import tempfile
import typing as tp

import pandas as pd
from pandas.io.formats.style import Styler as PandasStyler

from vetting_adapter.core.output.base import (
    CriterionTargetRangeOutput,
    MultiCriterionTargetRangeOutput,
)
from vetting_adapter.core.output.excel import (
    DataFrameExcelWriter,
    ExcelFileSpec,
    MultiDataFrameExcelWriter,
)
from vetting_adapter.core.output.timeseries import \
    TimeseriesRefComparisonAndTargetOutput



ExcelWriterTypeVar = tp.TypeVar(
    'ExcelWriterTypeVar',
    bound=DataFrameExcelWriter|MultiDataFrameExcelWriter,
)

ExcelFileSpecTypeVar = tp.TypeVar(
    'ExcelFileSpecTypeVar',
    bound=ExcelFileSpec|pd.ExcelWriter,
)


@tp.overload
def get_excel_writer(
    file: tp.Optional[ExcelFileSpecTypeVar] = None,
    *,
    return_file: tp.Literal[False],
    excel_writer_class: tp.Type[ExcelWriterTypeVar] = MultiDataFrameExcelWriter,
    excel_writer_kwargs: tp.Optional[dict[str, tp.Any]] = None,
) -> ExcelWriterTypeVar:
    ...
@tp.overload
def get_excel_writer(
    file: tp.Optional[ExcelFileSpecTypeVar],
    *,
    return_file: tp.Literal[True],
    excel_writer_class: tp.Type[ExcelWriterTypeVar] = MultiDataFrameExcelWriter,
    excel_writer_kwargs: tp.Optional[dict[str, tp.Any]] = None,
) -> tuple[ExcelWriterTypeVar, ExcelFileSpecTypeVar]:
    ...
@tp.overload
def get_excel_writer(
    file: None,
    *,
    return_file: tp.Literal[True],
    excel_writer_class: tp.Type[ExcelWriterTypeVar] = MultiDataFrameExcelWriter,
    excel_writer_kwargs: tp.Optional[dict[str, tp.Any]] = None,
) -> tuple[ExcelWriterTypeVar, Path]:
    ...
def get_excel_writer(
    file: tp.Optional[ExcelFileSpecTypeVar] = None,
    *,
    excel_writer_class: tp.Type[ExcelWriterTypeVar] = MultiDataFrameExcelWriter,
    excel_writer_kwargs: tp.Optional[dict[str, tp.Any]] = None,
    return_file: bool = False,
) -> ExcelWriterTypeVar \
        | tuple[ExcelWriterTypeVar, ExcelFileSpecTypeVar|Path]:
    """Get an ExcelWriter instance.

    The function returns an instance of an
    `vetting_adapter.core.output.excel.DataFrameExcelWriter` or
    `MultiDataFrameExcelWriter` subclass which can be used to write output from
    `vetting_adapter` output objects to an Excel file or data stream.

    If no file or io buffer is specified, the function will by default return a
    writer instance that writes to a temporary file. The file will be deleted
    automatically when the file is closed. I.e., it is assumed that the stream
    will be read and downloaded before it is closed.

    It is the responsibility of the caller to call the `.close` method of the
    returned excel writer instance to ensure the stream or file is closed.

    Parameters
    ----------
    file : pathlib.Path, str, BytesIO, or pandas.ExcelWriter, optional
        The file or stream to write to, or an existing `pandas.ExcelWriter to
        use. If none is specified, a temporary file will be used, see notes
        above.
    excel_writer_class : type, optional
        The class to use for writing. If not specified, a
        `MultiDataFrameExcelWriter` will be used. That class requires the output
        to be a dictionary of dataframes (where one will be written to each
        worksheet, and the keys used as worksheet names).
    excel_writer_kwargs : dict, optional
        Keyword arguments to pass to the excel writer `__init__` method. If None
        and if `excel_writer_class` is not specified (in which case a
        `MultiDataFrameExcelWriter` class will be used), the
        `force_valid_sheet_name` parameter will be set to True (which is not the
        default for the class), to ensure that worksheet names are made valid
        without throwing any errors. Note that this may lead to silent
        unexpected renaming of worksheet names that are specified when you use
        the write instance to write data to Excel.
    

    Returns
    -------
    The type specified by `excel_writer_class`, or `MultiDataFrameExcelWriter`
    by default. If `return_file` is True, a tuple is returned, with `file` as
    the second element, or a Path object pointing to the created temporary file
    if the `file` parameter was None.
    """
    if excel_writer_class is None:
        excel_writer_class = MultiDataFrameExcelWriter
    elif excel_writer_kwargs is None:
        if excel_writer_kwargs is None:
            excel_writer_kwargs = {'force_valid_sheet_name': True}
    if file is None:
        _tmpfile = tempfile.NamedTemporaryFile(
            mode='wb',
            suffix='.xlsx',
            delete=False,
            delete_on_close=False,
        )
        tmp_file_path: Path = Path(_tmpfile.name)
    if isinstance(file, pd.ExcelWriter):
        pd_excel_writer: pd.ExcelWriter = file
    else:
        pd_excel_writer = pd.ExcelWriter(
            file if file is not None else tmp_file_path,
            engine='xlsxwriter'
        )
    writer: ExcelWriterTypeVar = excel_writer_class(
        pd_excel_writer,
        **excel_writer_kwargs
    )
    if return_file:
        if file is None:
            return (writer, tmp_file_path)
        else:
            return (writer, file)
    return writer
###END def get_excel_writer


@tp.overload
def write_excel_targetrange_output(
        output_data: pd.DataFrame|PandasStyler \
            | dict[str, pd.DataFrame|PandasStyler],
        outputter: CriterionTargetRangeOutput|MultiCriterionTargetRangeOutput,
        file: ExcelFileSpecTypeVar,
        *,
        use_existing_writer: tp.Literal[False],
        excel_writer_class: tp.Optional[
            tp.Type[DataFrameExcelWriter] | tp.Type[MultiDataFrameExcelWriter]
        ] = None,
) -> ExcelFileSpecTypeVar:
    ...
@tp.overload
def write_excel_targetrange_output(
        output_data: pd.DataFrame|PandasStyler \
            | dict[str, pd.DataFrame|PandasStyler],
        outputter: CriterionTargetRangeOutput|MultiCriterionTargetRangeOutput,
        file: None = None,
        *,
        use_existing_writer: tp.Literal[False],
        excel_writer_class: tp.Optional[
            tp.Type[DataFrameExcelWriter] | tp.Type[MultiDataFrameExcelWriter]
        ] = None,
) -> Path:
    ...
@tp.overload
def write_excel_targetrange_output(
        output_data: pd.DataFrame|PandasStyler \
            | dict[str, pd.DataFrame|PandasStyler],
        outputter: CriterionTargetRangeOutput|MultiCriterionTargetRangeOutput,
        file: tp.Optional[ExcelFileSpecTypeVar] = None,
        *,
        use_existing_writer: tp.Literal[True],
        excel_writer_class: tp.Optional[
            tp.Type[DataFrameExcelWriter] | tp.Type[MultiDataFrameExcelWriter]
        ] = None,
) -> tp.Any:
    ...
def write_excel_targetrange_output(
        output_data: pd.DataFrame|PandasStyler \
            | dict[str, pd.DataFrame|PandasStyler],
        outputter: CriterionTargetRangeOutput \
            | MultiCriterionTargetRangeOutput \
            | TimeseriesRefComparisonAndTargetOutput,
        file: tp.Optional[ExcelFileSpecTypeVar] = None,
        *,
        use_existing_writer: bool = False,
        excel_writer_class: tp.Optional[
            tp.Type[DataFrameExcelWriter] | tp.Type[MultiDataFrameExcelWriter]
        ] = None,
        close_after_write: tp.Optional[bool] = None,
) -> ExcelFileSpecTypeVar|Path|tp.Any:
    """Writes an output object to Excel file.
    
    Parameters
    ----------
    output_data : pandas DataFrame, pandas Styler, or dict
        The data to write. Should have been prepared with 
        `outputter.prepare_output` or `outputter.prepare_styled_output`. If
        `outputter` is a `CriterionTargetRangeOutput`, `output_data` must be a
        single DataFrame or pandas Styler. If `outputter` is a
        `MultiCriterionTargetRangeOutput`, `output_data` must be a dictionary
        mapping criterion names to DataFrames or pandas Stylers.
    outputter : CriterionTargetRangeOutput or MultiCriterionTargetRangeOutput
        The output object to use for writing. Should be the same object that was
        used to produce `output_data`, or one with compatible attributes and
        state.
    file, optional
        A file, stream or `pandas.ExcelWriter` to write to. Any argument that
        is accepted by `vetting_adapter.core.output.excel.ExcelWriterBase`.
        Optional. If None, a temporary file will be used, and a `pathlib.Path`
        object pointing to that file will be returned.
    use_existing_writer : bool, optional
        Whether to use the existing `writer` attribute of `outputter`. If True,
        `file` will be ignored, and the function returns whatever value is
        returned by `outputter.write_output` (which will often be `None`).
    excel_writer_class : DataFrameExcelWriter or MultiDataFrameExcelWriter, optional
        The class to use for the `ExcelWriter` that will be used with
        `outputter` to write the Excel output. Only used if
        `use_existing_writer` is False. Optional. Defaults to
        `MultiDataFrameExcelWriter` if `outputter` is an instance of
        `MultiCriterionTargetRangeOutput` or a subclass, and
        `DataFrameExcelWriter` if `outputter` is an instance of
        `CriterionTargetRangeOutput` or a subclass.
    close_after_write : bool, optional
        Whether to close the Excel writer object after writing. Note that if
        this is not done, the file may not actually get written to disk by the
        time you want to read it again. Optional. If not specified, it will be
        set to True if `file` is unspecified or None or a str or Path object,
        and False if it is a `pandas.ExcelWriter` or BytesIO object (in which
        case it is assumed that the caller may want to keep using the object).

    Returns
    -------
    One of the following, in order of priority:
      * If `use_existing_writer` is True: The return value from
        `outputter.write_output`.
      * If `file` is specified and not None: `file`.
      * If `file` is None: A `pathlib.Path` object pointing to the temporary
        file that was created.
    """
    if close_after_write is None:
        close_after_write = file is None or isinstance(file, (str, Path))
    if isinstance(outputter, CriterionTargetRangeOutput):
        if not isinstance(output_data, (pd.DataFrame, PandasStyler)):
            raise TypeError(
                'When outputter is a CriterionTargetRangeOutput, `output_data` '
                'must be a single pandas DataFrame.'
            )
        output_data = tp.cast(pd.DataFrame|PandasStyler, output_data)
        if excel_writer_class is None:
            excel_writer_class = DataFrameExcelWriter
    elif isinstance(
            outputter,
            (MultiCriterionTargetRangeOutput,
             TimeseriesRefComparisonAndTargetOutput)
    ):
        if not isinstance(output_data, dict):
            raise TypeError(
                'When outputter is a MultiCriterionTargetRangeOutput, '
                '`output_data` must be a dictionary of pandas DataFrames.'
            )
        if excel_writer_class is None:
            excel_writer_class = MultiDataFrameExcelWriter
        output_data = tp.cast(dict[str, pd.DataFrame|PandasStyler], output_data)
    else:
        print(outputter)
        raise TypeError(
            'outputter must be a CriterionTargetRangeOutput or '
            'MultiCriterionTargetRangeOutput.'
        )
    if use_existing_writer:
        return outputter.write_output(output_data)
    writer: DataFrameExcelWriter|MultiDataFrameExcelWriter
    if file is None:
        writer, file = get_excel_writer(
            file=None,
            excel_writer_class=excel_writer_class,
            return_file=True,
        )
    else:
        writer = get_excel_writer(
            file=file,
            excel_writer_class=excel_writer_class,
            return_file=False,
        )
    outputter.with_writer(writer).write_output(output_data)
    if close_after_write:
        writer.close()
    return file
###END def write_excel_output
