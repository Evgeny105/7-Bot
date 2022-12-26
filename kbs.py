from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)


def get_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)  # , one_time_keyboard=True)
    b_help = KeyboardButton("/help")
    b_stop = KeyboardButton("/stop")
    kb.add(b_help).insert(b_stop)
    return kb


def get_inline_kb(type_of_inl_kb: str) -> InlineKeyboardMarkup:

    inline_butt_add = InlineKeyboardButton(
        text="Add reminder", callback_data="Add_reminder"
    )
    inline_butt_del = InlineKeyboardButton(
        text="Remove reminder", callback_data="Remove_reminder"
    )
    inline_butt_ch_TZ = InlineKeyboardButton(
        text="Change time zone", callback_data="Change_TZ"
    )
    inline_butt_vi = InlineKeyboardButton(
        text="Very important reminder", callback_data="VI_reminder"
    )
    inline_butt_set_time = InlineKeyboardButton(
        text="Lock text and set time", callback_data="set_time"
    )
    inline_butt_create_reminder = InlineKeyboardButton(
        text="Create reminder", callback_data="create_reminder"
    )
    inline_butt_simple = InlineKeyboardButton(
        text="Simple reminder", callback_data="Simple_reminder"
    )
    inline_butt_back = InlineKeyboardButton(text="Back", callback_data="Back")
    inline_plus_TZ = InlineKeyboardButton(text=">>", callback_data="TZ_to_West")
    inline_minus_TZ = InlineKeyboardButton(text="<<", callback_data="TZ_to_East")
    inline_set_TZ = InlineKeyboardButton(
        text="Set current value", callback_data="TZ_set"
    )
    inline_butt_got_it = InlineKeyboardButton(text="Got it!", callback_data="got_it")

    if type_of_inl_kb == "add_remove":
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(inline_butt_add, inline_butt_del, inline_butt_ch_TZ)

    if type_of_inl_kb == "remove":
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(inline_butt_del)

    if type_of_inl_kb == "type_reminder":
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(inline_butt_vi, inline_butt_simple, inline_butt_back)

    if type_of_inl_kb == "set_time_reminder":
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(inline_butt_set_time)

    if type_of_inl_kb == "reminder_create":
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(inline_butt_create_reminder)

    if type_of_inl_kb == "set_TZ":
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(inline_minus_TZ, inline_plus_TZ, inline_set_TZ)

    if type_of_inl_kb == "got_it":
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(inline_butt_got_it)

    if type_of_inl_kb == "back":
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(inline_butt_back)

    return kb
