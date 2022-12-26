from aiogram.dispatcher.filters.state import StatesGroup, State


class BotStatesForUser(StatesGroup):

    unknown_TZ = State()
    add_remove = State()
    type_reminder = State()
    remove_reminder = State()
    remove_reminder_num = State()
    VI_reminder = State()
    simple_reminder = State()
    VI_reminder_date = State()
    simple_reminder_date = State()
