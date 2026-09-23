from datetime import date

from operar_range.calendar import ny_regular_open_brt, reference_candle_window
from operar_range.entry import Side, entry_trigger


def main() -> None:
    session = date(2026, 3, 9)
    open_brt = ny_regular_open_brt(session)
    ref_start, ref_end = reference_candle_window(session)
    trigger = entry_trigger(
        side=Side.BUY,
        reference_high=130000,
        reference_low=129500,
        is_intraday_high=True,
        is_intraday_low=False,
    )

    print("OPERAR RANGE QUANT — ambiente OK")
    print(f"Abertura NY em BRT ({session}): {open_brt:%H:%M}")
    print(f"Candle de referência: {ref_start:%H:%M}–{ref_end:%H:%M}")
    print(f"Teste regra 20/40: compra em máxima intraday -> {trigger:.0f}")
    print("\nPróximo passo: importar 1 pregão completo de WIN em ticks.")


if __name__ == "__main__":
    main()
