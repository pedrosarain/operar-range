from operar_range.entry import Side, entry_trigger


def test_buy_normal_offset_20():
    assert entry_trigger(
        side=Side.BUY,
        reference_high=130000,
        reference_low=129500,
        is_intraday_high=False,
        is_intraday_low=False,
    ) == 130020


def test_sell_normal_offset_20():
    assert entry_trigger(
        side=Side.SELL,
        reference_high=130000,
        reference_low=129500,
        is_intraday_high=False,
        is_intraday_low=False,
    ) == 129480


def test_buy_intraday_high_offset_40():
    assert entry_trigger(
        side=Side.BUY,
        reference_high=130000,
        reference_low=129500,
        is_intraday_high=True,
        is_intraday_low=False,
    ) == 130040


def test_sell_intraday_low_offset_40():
    assert entry_trigger(
        side=Side.SELL,
        reference_high=130000,
        reference_low=129500,
        is_intraday_high=False,
        is_intraday_low=True,
    ) == 129460
