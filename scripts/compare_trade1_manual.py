from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET

from operar_range.reference import reconstruct_reference_session
from operar_range.trade1 import reconstruct_trade1


MANUAL_FILE = Path("data/manual/candle18_manual.xlsx")

CASES = [
    (
        date(2026, 8, 18),
        Path(
            "data/normalized/"
            "winv26_ticks_20260818_enriched.parquet"
        ),
    ),
    (
        date(2026, 8, 19),
        Path(
            "data/normalized/"
            "winv26_ticks_20260819_enriched.parquet"
        ),
    ),
]


def excel_serial_to_date(value):
    if value in (None, ""):
        return None

    try:
        serial = int(float(value))
    except (TypeError, ValueError):
        return None

    return (
        datetime(1899, 12, 30)
        + timedelta(days=serial)
    ).date()


def column_letters(cell_ref):
    return "".join(
        char
        for char in cell_ref
        if char.isalpha()
    )


def read_manual_sheet(
    xlsx_path: Path,
    sheet_name: str,
):
    main_ns = (
        "http://schemas.openxmlformats.org/"
        "spreadsheetml/2006/main"
    )

    rel_ns = (
        "http://schemas.openxmlformats.org/"
        "officeDocument/2006/relationships"
    )

    package_rel_ns = (
        "http://schemas.openxmlformats.org/"
        "package/2006/relationships"
    )

    with ZipFile(xlsx_path) as archive:
        shared_strings = []

        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(
                archive.read(
                    "xl/sharedStrings.xml"
                )
            )

            for item in root.findall(
                f"{{{main_ns}}}si"
            ):
                text = "".join(
                    node.text or ""
                    for node in item.iter(
                        f"{{{main_ns}}}t"
                    )
                )
                shared_strings.append(text)

        workbook_root = ET.fromstring(
            archive.read("xl/workbook.xml")
        )

        relationship_id = None

        for sheet in workbook_root.findall(
            f".//{{{main_ns}}}sheet"
        ):
            if sheet.attrib.get("name") == sheet_name:
                relationship_id = sheet.attrib.get(
                    f"{{{rel_ns}}}id"
                )
                break

        if relationship_id is None:
            raise ValueError(
                f"Manual sheet not found: {sheet_name}"
            )

        rel_root = ET.fromstring(
            archive.read(
                "xl/_rels/workbook.xml.rels"
            )
        )

        target = None

        for relation in rel_root.findall(
            f"{{{package_rel_ns}}}Relationship"
        ):
            if (
                relation.attrib.get("Id")
                == relationship_id
            ):
                target = relation.attrib[
                    "Target"
                ]
                break

        if target is None:
            raise ValueError(
                "Unable to resolve manual worksheet."
            )

        if target.startswith("/"):
            sheet_path = target.lstrip("/")
        else:
            sheet_path = "xl/" + target

        sheet_root = ET.fromstring(
            archive.read(sheet_path)
        )

        rows = []

        for row_node in sheet_root.findall(
            f".//{{{main_ns}}}row"
        ):
            row_data = {}

            for cell in row_node.findall(
                f"{{{main_ns}}}c"
            ):
                ref = cell.attrib.get("r", "")
                column = column_letters(ref)

                cell_type = cell.attrib.get("t")

                value_node = cell.find(
                    f"{{{main_ns}}}v"
                )

                value = None

                if cell_type == "inlineStr":
                    inline = cell.find(
                        f"{{{main_ns}}}is"
                    )

                    if inline is not None:
                        value = "".join(
                            node.text or ""
                            for node in inline.iter(
                                f"{{{main_ns}}}t"
                            )
                        )

                elif value_node is not None:
                    raw = value_node.text

                    if cell_type == "s":
                        value = shared_strings[
                            int(raw)
                        ]
                    elif cell_type == "b":
                        value = raw == "1"
                    else:
                        try:
                            value = float(raw)
                        except (
                            TypeError,
                            ValueError,
                        ):
                            value = raw

                row_data[column] = value

            if row_data:
                rows.append(row_data)

        return rows


def load_manual_records():
    rows = read_manual_sheet(
        MANUAL_FILE,
        "Backtest Candle 18",
    )

    records = {}

    for row in rows:
        session_date = excel_serial_to_date(
            row.get("A")
        )

        if session_date is None:
            continue

        records[session_date] = {
            "date": session_date,
            "day": row.get("B"),
            "setup": row.get("C"),
            "direction_raw": row.get("D"),
            "went_against_before_pay": (
                row.get("E")
            ),
            "paid_favor": row.get("F"),
            "win_loss": row.get("G"),
            "reentry_note": row.get("H"),
            "extra_note": row.get("I"),
        }

    return records


def normalize_manual_direction(value):
    if value is None:
        return None

    value = str(value).strip().upper()

    if value == "COMPRA":
        return "LONG"

    if value == "VENDA":
        return "SHORT"

    return None


def format_value(value):
    if value is None:
        return "N/A"

    if isinstance(value, bool):
        return "True" if value else "False"

    return str(value)


def add_comparison(
    rows,
    field,
    automatic,
    manual=None,
    comparable=False,
):
    if comparable and manual is not None:
        match = automatic == manual
    else:
        match = "N/A"

    rows.append(
        (
            field,
            automatic,
            manual,
            match,
        )
    )


def target_reached(report, level):
    targets = report.get("targets")

    if targets is None:
        return None

    return bool(
        targets[str(level)]["reached"]
    )


def stop_hit(report, level):
    stops = report.get("stops")

    if stops is None:
        return None

    return bool(
        stops[str(level)]["hit"]
    )


def automatic_result(
    session_date,
    parquet_path,
):
    reference = reconstruct_reference_session(
        parquet_path=parquet_path,
        session_date=session_date,
    )

    trade = reconstruct_trade1(
        parquet_path=parquet_path,
        session_date=session_date,
    )

    candle_reference = (
        f"{reference['reference_candle_start']}"
        f" -> "
        f"{reference['reference_candle_end']}"
    )

    entry_found = bool(
        trade.get("entry_found")
    )

    result = {
        "Trade 1 existe?": entry_found,
        "direção": trade.get("direction"),
        "candle referência": candle_reference,
        "máxima do candle": reference["high"],
        "mínima do candle": reference["low"],
        "máxima intraday até NY Open": (
            reference[
                "intraday_high_until_open"
            ]
        ),
        "mínima intraday até NY Open": (
            reference[
                "intraday_low_until_open"
            ]
        ),
        "offset aplicado na compra": (
            reference["buy_offset"]
        ),
        "offset aplicado na venda": (
            reference["sell_offset"]
        ),
        "buy_level": reference["buy_level"],
        "sell_level": reference["sell_level"],
        "lado rompido primeiro": (
            trade.get("direction")
        ),
        "preço da entrada": (
            trade.get("entry_trigger_level")
        ),
        "timestamp da entrada": (
            trade.get("entry_timestamp")
        ),
        "MFE": trade.get("mfe_points"),
        "MAE": trade.get("mae_points"),
        "voltou ao 0x0?": (
            trade.get(
                "returned_to_zero_exact"
            )
        ),
        "primeira volta ao 0x0": (
            trade.get(
                "zero_return_timestamp"
            )
        ),
        (
            "máximo favorável antes "
            "da primeira volta"
        ): trade.get(
            "max_favorable_before_first_zero"
        ),
    }

    for level in (
        100,
        125,
        150,
        175,
        200,
        400,
        1000,
    ):
        result[
            f"atingiu +{level}?"
        ] = target_reached(
            trade,
            level,
        )

    for level in (
        100,
        125,
        150,
        170,
        175,
        200,
    ):
        result[
            f"stop {level} atingido?"
        ] = stop_hit(
            trade,
            level,
        )

    return reference, trade, result


def print_automatic(result):
    print("\nPARTE 1 — RESULTADO AUTOMÁTICO")

    if result["Trade 1 existe?"] is False:
        print("Trade 1 existe?: False")
        print("status: SEM TRADE 1")
        print(
            "motivo: não houve rompimento "
            "no candle imediatamente seguinte "
            "ao candle de referência."
        )

    for field, value in result.items():
        if (
            result["Trade 1 existe?"] is False
            and field == "Trade 1 existe?"
        ):
            continue

        print(
            f"{field}: "
            f"{format_value(value)}"
        )


def print_manual_context(manual):
    print("\nDADOS BRUTOS DO ESTUDO MANUAL")

    if manual is None:
        print("registro_manual: N/A")
        return

    print(
        "direção_manual:",
        format_value(
            manual[
                "direction_raw"
            ]
        ),
    )

    print(
        "foi_contra_antes_de_pagar:",
        format_value(
            manual[
                "went_against_before_pay"
            ]
        ),
    )

    print(
        "quanto_pagou_a_favor:",
        format_value(
            manual[
                "paid_favor"
            ]
        ),
    )

    print(
        "win_loss:",
        format_value(
            manual[
                "win_loss"
            ]
        ),
    )

    print(
        "observacao:",
        format_value(
            manual[
                "reentry_note"
            ]
        ),
    )

    print(
        "observacao_extra:",
        format_value(
            manual[
                "extra_note"
            ]
        ),
    )


def manual_trade1_exists(manual):
    if manual is None:
        return None

    texts = [
        manual.get("reentry_note"),
        manual.get("extra_note"),
    ]

    for value in texts:
        if value is None:
            continue

        text = str(value).strip().lower()

        if (
            "nao rompeu no candle seguinte"
            in text
            or
            "não rompeu no candle seguinte"
            in text
        ):
            return False

    direction = normalize_manual_direction(
        manual.get("direction_raw")
    )

    if direction is not None:
        return True

    return None


def build_comparison(
    automatic,
    manual,
):
    rows = []

    manual_exists = (
        manual_trade1_exists(manual)
    )

    add_comparison(
        rows,
        "Trade 1 existe?",
        automatic["Trade 1 existe?"],
        manual_exists,
        comparable=(
            manual_exists is not None
        ),
    )

    manual_direction = None

    if (
        manual is not None
        and manual_exists is not False
    ):
        manual_direction = (
            normalize_manual_direction(
                manual["direction_raw"]
            )
        )

    add_comparison(
        rows,
        "direção",
        automatic["direção"],
        manual_direction,
        comparable=(
            automatic["Trade 1 existe?"]
            and manual_exists is True
            and manual_direction is not None
        ),
    )

    add_comparison(
        rows,
        "lado rompido primeiro",
        automatic[
            "lado rompido primeiro"
        ],
        manual_direction,
        comparable=(
            automatic["Trade 1 existe?"]
            and manual_exists is True
            and manual_direction is not None
        ),
    )

    fields_without_direct_manual_equivalent = [
        "candle referência",
        "máxima do candle",
        "mínima do candle",
        "máxima intraday até NY Open",
        "mínima intraday até NY Open",
        "offset aplicado na compra",
        "offset aplicado na venda",
        "buy_level",
        "sell_level",
        "preço da entrada",
        "timestamp da entrada",
        "MFE",
        "MAE",
        "voltou ao 0x0?",
        "primeira volta ao 0x0",
        (
            "máximo favorável antes "
            "da primeira volta"
        ),
        "atingiu +100?",
        "atingiu +125?",
        "atingiu +150?",
        "atingiu +175?",
        "atingiu +200?",
        "atingiu +400?",
        "atingiu +1000?",
        "stop 100 atingido?",
        "stop 125 atingido?",
        "stop 150 atingido?",
        "stop 170 atingido?",
        "stop 175 atingido?",
        "stop 200 atingido?",
    ]

    for field in (
        fields_without_direct_manual_equivalent
    ):
        add_comparison(
            rows,
            field,
            automatic[field],
            None,
            comparable=False,
        )

    return rows


def print_comparison(rows):
    print(
        "\nPARTE 2 — COMPARAÇÃO "
        "AUTOMÁTICO × MANUAL"
    )

    print(
        "CAMPO | AUTOMÁTICO | "
        "MANUAL | MATCH"
    )

    for (
        field,
        automatic,
        manual,
        match,
    ) in rows:
        print(
            f"{field} | "
            f"{format_value(automatic)} | "
            f"{format_value(manual)} | "
            f"{format_value(match)}"
        )


def divergence_records(
    session_date,
    trade,
    manual,
    comparison_rows,
):
    divergences = []

    for (
        field,
        automatic,
        manual_value,
        match,
    ) in comparison_rows:
        if match is False:
            divergences.append(
                {
                    "campo": field,
                    "automatico": automatic,
                    "manual": manual_value,
                    "evidencia": (
                        "Comparação direta entre "
                        "campo equivalente."
                    ),
                    "causa": (
                        "Divergência objetiva "
                        "detectada."
                    ),
                }
            )

    return divergences


def print_divergences(divergences):
    print("\nPARTE 3 — DIVERGÊNCIAS")

    if not divergences:
        print("nenhuma_divergencia_comparavel")
        return

    for index, item in enumerate(
        divergences,
        start=1,
    ):
        print(
            f"\nDIVERGÊNCIA {index}"
        )
        print(
            "campo divergente:",
            item["campo"],
        )
        print(
            "valor automático:",
            format_value(
                item["automatico"]
            ),
        )
        print(
            "valor manual:",
            format_value(
                item["manual"]
            ),
        )
        print(
            "evidência disponível:",
            item["evidencia"],
        )
        print(
            "causa:",
            item["causa"],
        )


def main():
    if not MANUAL_FILE.exists():
        raise FileNotFoundError(
            MANUAL_FILE
        )

    manual_records = (
        load_manual_records()
    )

    for (
        session_date,
        parquet_path,
    ) in CASES:
        print(
            "\n"
            + "=" * 90
        )

        print(
            "ETAPA 6 —",
            session_date.isoformat(),
        )

        print(
            "=" * 90
        )

        (
            reference,
            trade,
            automatic,
        ) = automatic_result(
            session_date,
            parquet_path,
        )

        manual = manual_records.get(
            session_date
        )

        print_automatic(
            automatic
        )

        print_manual_context(
            manual
        )

        comparison_rows = (
            build_comparison(
                automatic,
                manual,
            )
        )

        print_comparison(
            comparison_rows
        )

        divergences = (
            divergence_records(
                session_date,
                trade,
                manual,
                comparison_rows,
            )
        )

        print_divergences(
            divergences
        )


if __name__ == "__main__":
    main()