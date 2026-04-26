import io
import math
from contextlib import asynccontextmanager
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Жизненный цикл приложения.
    Выводит кликабельную ссылку в консоль при старте сервера.
    """
    print("\n" + "=" * 60)
    print("🚀 Сервер табличного RAG-чанкинга успешно запущен!")
    print("👉 Откройте веб-интерфейс по ссылке: http://localhost:8000/docs")
    print("=" * 60 + "\n")
    yield


app = FastAPI(
    title="Table to RAG Chunker PRO",
    description="Продвинутый модуль обработки табличных файлов с профилированием",
    version="2.0.0",
    lifespan=lifespan,
)


def col_to_letter(col_idx: int) -> str:
    """Преобразует индекс колонки (от 0) в буквенный формат Excel (A, B, C...)."""
    string = ""
    col_idx += 1
    while col_idx > 0:
        col_idx, remainder = divmod(col_idx - 1, 26)
        string = chr(65 + remainder) + string
    return string


def map_dtype(series: pd.Series) -> str:
    """Определяет унифицированный тип данных колонки."""
    if series.isna().all() or series.dropna().astype(str).str.strip().eq("").all():
        return "empty"
    if pd.api.types.is_numeric_dtype(series):
        return "number"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "date/datetime"
    if pd.api.types.is_bool_dtype(series):
        return "bool"
    if pd.api.types.is_string_dtype(series):
        return "string"
    return "mixed"


def profile_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    """Формирует профиль таблицы (статистика, типы, пропуски)."""
    columns_profile = []
    warnings = []
    total_rows = len(df)
    empty_rows = int(df.isna().all(axis=1).sum())

    if empty_rows > total_rows * 0.1:
        warnings.append(f"Много пустых строк ({empty_rows} из {total_rows})")

    for i, col_name in enumerate(df.columns):
        series = df[col_name]
        col_type = map_dtype(series)
        null_count = int(series.isna().sum())
        null_pct = round((null_count / total_rows * 100) if total_rows else 0, 2)

        col_info = {
            "index": i,
            "name_raw": str(col_name),
            "type": col_type,
            "null_percentage": null_pct,
        }

        # Базовые статистики в зависимости от типа
        valid_series = series.dropna()
        if col_type == "number" and not valid_series.empty:
            col_info["stats"] = {
                "min": float(valid_series.min()),
                "max": float(valid_series.max()),
                "avg": float(valid_series.mean()),
            }
        elif col_type in ("string", "mixed") and not valid_series.empty:
            top_vals = valid_series.value_counts().head(3).to_dict()
            col_info["stats"] = {"top_values": {str(k): v for k, v in top_vals.items()}}

        columns_profile.append(col_info)

    mixed_cols = [c["name_raw"] for c in columns_profile if c["type"] == "mixed"]
    if mixed_cols:
        warnings.append(f"Смешанные типы в колонках: {', '.join(mixed_cols)}")

    return {
        "dimensions": {"row_count": total_rows, "column_count": len(df.columns)},
        "header_rows": 1,
        "warnings": warnings,
        "columns": columns_profile,
    }


def process_dataframe(
        df: pd.DataFrame,
        filename: str,
        sheet_name: str,
        max_rows_per_chunk: int,
        max_cells_per_chunk: int,
) -> Dict[str, Any]:
    """
    Анализирует таблицу, профилирует её и нарезает на чанки.
    """
    # Собираем профиль до того, как заполним NaN-ы строками
    table_profile = profile_dataframe(df)

    # Подготовка данных для текста (чтобы JSON не ломался на NaN и Infinity)
    df_clean = df.replace({np.nan: "[ПУСТО]", np.inf: "[INF]", -np.inf: "[-INF]"})
    total_rows = len(df_clean)
    num_cols = len(df_clean.columns)

    if num_cols == 0 or total_rows == 0:
        return {"profile": table_profile, "chunks": []}

    # Рассчитываем реальный размер чанка, чтобы не превысить лимит ячеек
    effective_chunk_size = min(
        max_rows_per_chunk, max(1, max_cells_per_chunk // num_cols)
    )

    chunks = []
    end_col_let = col_to_letter(num_cols - 1)

    for start_idx in range(0, total_rows, effective_chunk_size):
        end_idx = min(start_idx + effective_chunk_size, total_rows)
        sub_df = df_clean.iloc[start_idx:end_idx]

        # Excel координаты (считаем, что строка 1 — это заголовок)
        start_row_excel = start_idx + 2
        end_row_excel = end_idx + 1
        source_ref = f"{sheet_name}!A{start_row_excel}:{end_col_let}{end_row_excel}"

        # Текстовая проекция
        text_projection = (
            f"Файл: {filename} | Лист: {sheet_name}\n"
            f"Колонки: {', '.join(df_clean.columns.astype(str))}\n"
            f"Диапазон строк: {start_row_excel}-{end_row_excel}\n"
            f"Данные:\n{sub_df.to_markdown(index=False)}"
        )

        chunks.append(
            {
                "chunk_id": f"{sheet_name}_rows_{start_row_excel}_{end_row_excel}",
                "context": {
                    "source_file": filename,
                    "sheet_name": sheet_name,
                    "header_rows": 1,
                    "row_start": start_row_excel,
                    "row_end": end_row_excel,
                    "source_ref": source_ref,
                },
                "text_projection": text_projection,
            }
        )

    return {"profile": table_profile, "chunks": chunks}


@app.post("/upload-table/", summary="Продвинутая обработка CSV/XLSX")
async def upload_table(
        file: UploadFile = File(..., description="Файл .csv или .xlsx"),
        max_rows_per_chunk: int = Form(50, ge=1, description="Максимум строк в чанке"),
        max_cells_per_chunk: int = Form(1000, ge=1, description="Защита от широких таблиц"),
):
    """
    Загружает файл, извлекает листы, профилирует схему и формирует чанки по логике таблицы.
    """
    filename = file.filename
    content = await file.read()

    result_payload = {
        "metadata": {"filename": filename, "total_sheets": 0},
        "sheets": {},
        "all_chunks": [],
    }

    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content))
            sheet_name = "CSV_Data"
            result_payload["metadata"]["total_sheets"] = 1

            processed_data = process_dataframe(
                df, filename, sheet_name, max_rows_per_chunk, max_cells_per_chunk
            )
            result_payload["sheets"][sheet_name] = processed_data["profile"]
            result_payload["all_chunks"].extend(processed_data["chunks"])

        elif filename.endswith((".xlsx", ".xls")):
            engine = "openpyxl" if filename.endswith(".xlsx") else "xlrd"
            excel_data = pd.read_excel(
                io.BytesIO(content), sheet_name=None, engine=engine
            )

            result_payload["metadata"]["total_sheets"] = len(excel_data)

            for sheet_name, df in excel_data.items():
                if df.empty:
                    continue
                processed_data = process_dataframe(
                    df, filename, sheet_name, max_rows_per_chunk, max_cells_per_chunk
                )
                result_payload["sheets"][sheet_name] = processed_data["profile"]
                result_payload["all_chunks"].extend(processed_data["chunks"])
        else:
            raise HTTPException(
                status_code=400,
                detail="Поддерживаются только форматы .csv, .xlsx, .xls",
            )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Ошибка обработки файла: {str(e)}"
        )

    return JSONResponse(content=result_payload)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)