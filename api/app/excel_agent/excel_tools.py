from __future__ import annotations

from collections import OrderedDict
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType
from typing import Any
from zipfile import BadZipFile

import pandas as pd
from pandas.api.types import is_bool_dtype, is_datetime64_any_dtype, is_numeric_dtype

from app.excel_agent.constants import (
    DETECTED_TYPE_BOOLEAN,
    DETECTED_TYPE_DATETIME,
    DETECTED_TYPE_EMPTY,
    DETECTED_TYPE_NUMBER,
    DETECTED_TYPE_TEXT,
    SUPPORTED_EXCEL_SUFFIXES,
)
from app.excel_agent.domain import (
    ExcelColumnList,
    ExcelColumnProfile,
    ExcelFileReadError,
    ExcelSheetInfo,
    ExcelSheetList,
    ExcelSheetNotFoundError,
    ExcelSheetProfile,
    ExcelSheetRows,
    UnsafeExcelPathError,
    UnsupportedExcelFileError,
)


class ExcelAgentTools:
    def __init__(
        self,
        allowed_root: Path,
        allowed_roots: tuple[Path, ...] = (),
    ) -> None:
        self._allowed_roots = tuple(
            root.resolve() for root in (allowed_root, *allowed_roots)
        )
        self._sheet_rows_cache: OrderedDict[
            tuple[str, str, int, int],
            ExcelSheetRows,
        ] = OrderedDict()

    def list_sheets(self, file_path: Path) -> ExcelSheetList:
        resolved_path = self._resolve_source_path(file_path)
        with self._open_workbook(resolved_path) as excel_file:
            sheet_names = tuple(excel_file.sheet_names)
            sheets = tuple(
                ExcelSheetInfo(
                    name=worksheet.title,
                    visibility=worksheet.sheet_state,
                )
                for worksheet in excel_file.book.worksheets
            )
        return ExcelSheetList(
            file_path=resolved_path,
            sheet_names=sheet_names,
            sheets=sheets,
        )

    def get_columns(self, file_path: Path, sheet_name: str) -> ExcelColumnList:
        resolved_path = self._resolve_source_path(file_path)
        with self._open_workbook(resolved_path) as excel_file:
            _require_sheet(excel_file, sheet_name)
            columns = _workbook_columns(excel_file, sheet_name)
        return ExcelColumnList(
            file_path=resolved_path,
            sheet_name=sheet_name,
            columns=columns,
        )

    def profile_sheet(self, file_path: Path, sheet_name: str) -> ExcelSheetProfile:
        resolved_path = self._resolve_source_path(file_path)
        with self._open_workbook(resolved_path) as excel_file:
            _require_sheet(excel_file, sheet_name)
            _workbook_columns(excel_file, sheet_name)
        dataframe = pd.read_excel(
            resolved_path,
            sheet_name=sheet_name,
            engine="openpyxl",
        )
        columns = _normalize_columns(tuple(dataframe.columns))
        return ExcelSheetProfile(
            file_path=resolved_path,
            sheet_name=sheet_name,
            row_count=len(dataframe),
            column_count=len(columns),
            columns=tuple(
                _profile_column(dataframe.iloc[:, index], columns[index], index)
                for index in range(len(columns))
            ),
        )

    def read_sheet_rows(self, file_path: Path, sheet_name: str) -> ExcelSheetRows:
        """Load rows for deterministic backend services, never for direct output."""
        resolved_path = self._resolve_source_path(file_path)
        cache_key = _sheet_cache_key(resolved_path, sheet_name)
        cached = self._sheet_rows_cache.get(cache_key)
        if cached is not None:
            self._sheet_rows_cache.move_to_end(cache_key)
            return cached
        with self._open_workbook(resolved_path) as excel_file:
            _require_sheet(excel_file, sheet_name)
            _workbook_columns(excel_file, sheet_name)
        dataframe = pd.read_excel(
            resolved_path,
            sheet_name=sheet_name,
            engine="openpyxl",
            dtype=object,
        )
        columns = _normalize_columns(tuple(dataframe.columns))
        if len(set(columns)) != len(columns):
            raise ExcelFileReadError("duplicate normalized Excel columns")
        dataframe.columns = list(columns)
        clean_frame = dataframe.astype(object).where(dataframe.notna(), None)
        rows = tuple(
            MappingProxyType(dict(record))
            for record in clean_frame.to_dict(orient="records")
        )
        if _sheet_cache_key(resolved_path, sheet_name) != cache_key:
            raise ExcelFileReadError("Excel file changed while being read")
        result = ExcelSheetRows(
            file_path=resolved_path,
            content_sha256=_file_sha256(resolved_path),
            sheet_name=sheet_name,
            row_count=len(rows),
            columns=columns,
            rows=rows,
        )
        stale_keys = tuple(
            key
            for key in self._sheet_rows_cache
            if key[0] == str(resolved_path) and key[1] == sheet_name
        )
        for stale_key in stale_keys:
            self._sheet_rows_cache.pop(stale_key, None)
        self._sheet_rows_cache[cache_key] = result
        while len(self._sheet_rows_cache) > 4:
            self._sheet_rows_cache.popitem(last=False)
        return result

    def _resolve_source_path(self, file_path: Path) -> Path:
        resolved_path = file_path.resolve()
        if not any(
            _is_relative_to(resolved_path, allowed_root)
            for allowed_root in self._allowed_roots
        ):
            raise UnsafeExcelPathError(
                f"excel path is outside allowed root: {file_path}",
            )
        if resolved_path.suffix.lower() not in SUPPORTED_EXCEL_SUFFIXES:
            raise UnsupportedExcelFileError(
                f"unsupported Excel file extension: {resolved_path.suffix}",
            )
        if not resolved_path.is_file():
            raise ExcelFileReadError(f"excel file does not exist: {file_path}")
        return resolved_path

    def _open_workbook(self, file_path: Path) -> pd.ExcelFile:
        try:
            return pd.ExcelFile(file_path, engine="openpyxl")
        except (BadZipFile, OSError, ValueError) as exc:
            raise ExcelFileReadError(f"invalid Excel file: {file_path}") from exc


def _require_sheet(excel_file: pd.ExcelFile, sheet_name: str) -> None:
    if sheet_name not in excel_file.sheet_names:
        raise ExcelSheetNotFoundError(f"unknown Excel sheet: {sheet_name}")


def _normalize_columns(columns: tuple[Any, ...]) -> tuple[str, ...]:
    normalized_columns: list[str] = []
    for index, column in enumerate(columns):
        column_name = str(column).strip() if column is not None else ""
        if not column_name or column_name.startswith("Unnamed:"):
            column_name = f"column_{index + 1}"
        normalized_columns.append(column_name)
    return tuple(normalized_columns)


def _workbook_columns(
    excel_file: pd.ExcelFile,
    sheet_name: str,
) -> tuple[str, ...]:
    worksheet = excel_file.book[sheet_name]
    first_row = next(
        worksheet.iter_rows(min_row=1, max_row=1, values_only=True),
        (),
    )
    columns = _normalize_columns(tuple(first_row))
    if len(set(columns)) != len(columns):
        raise ExcelFileReadError("duplicate normalized Excel columns")
    return columns


def _profile_column(
    series: pd.Series[Any],
    column_name: str,
    position: int,
) -> ExcelColumnProfile:
    missing_count = int(series.isna().sum())
    non_empty_count = int(series.notna().sum())
    row_count = int(len(series))
    missing_ratio = missing_count / row_count if row_count else 0.0
    return ExcelColumnProfile(
        name=column_name,
        position=position,
        detected_type=_detect_type(series),
        non_empty_count=non_empty_count,
        missing_count=missing_count,
        missing_ratio=missing_ratio,
    )


def _detect_type(series: pd.Series[Any]) -> str:
    non_empty_series = series.dropna()
    if non_empty_series.empty:
        return DETECTED_TYPE_EMPTY
    if is_bool_dtype(non_empty_series):
        return DETECTED_TYPE_BOOLEAN
    if is_datetime64_any_dtype(non_empty_series):
        return DETECTED_TYPE_DATETIME
    if is_numeric_dtype(non_empty_series):
        return DETECTED_TYPE_NUMBER
    return DETECTED_TYPE_TEXT


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sheet_cache_key(path: Path, sheet_name: str) -> tuple[str, str, int, int]:
    stat = path.stat()
    return str(path), sheet_name, stat.st_size, stat.st_mtime_ns
