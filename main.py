import asyncio
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardRemove
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from dateutil.parser import parse
import datetime
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from db_orm import Users, Reminders, engine, Base
from kbs import get_kb, get_inline_kb
from config import TOKEN_API
from states import BotStatesForUser
from constants import HELP_COMMANDS
from utils import TZ

storage = MemoryStorage()

bot = Bot(TOKEN_API)
dp = Dispatcher(bot, storage=storage)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
tasks_of_scheduler = set()


async def on_startup(_):
    print("Start bot")
    ## !!! Full Erase and Recreate DB !!! ##
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.drop_all)
    #     await conn.run_sync(Base.metadata.create_all)


async def on_shutdown(_):
    print("Stop bot")
    await engine.dispose()
    await dp.storage.close()
    await dp.storage.wait_closed()


async def list_of_reminders(user_id):
    async with async_session() as session:
        stmt = (
            select(Reminders)
            .where(Reminders.user_id == user_id)
            .order_by(Reminders.reminder_time)
        )
        result = await session.execute(stmt)
    return [el for el in result.scalars()]


@dp.message_handler(commands=["start"], state="*")
async def comm_start(message: types.Message, state: FSMContext):
    print("Got command Start")
    current_user = message.from_user
    await state.update_data(current_user=current_user)
    async with async_session() as session:
        stmt = select(Users).where(Users.user_id == current_user.id)
        result = await session.execute(stmt)
    res = result.scalars().first()
    if res is not None:
        if res.user_tz is not None:  # known user
            print(
                f"Bot met known user {current_user.full_name} with time zone {res.user_tz}"
            )
            TZ_saved = True
            await state.update_data(current_TZ=res.user_tz)
            lr = await list_of_reminders(current_user.id)
            if len(lr) == 0:
                await message.answer(
                    text=f"<em><b>Welcome, {current_user.full_name}!</b> \n"
                    + "You don't have any reminders yet. But I'm here and ready to help! 😉</em>",
                    parse_mode="HTML",
                    reply_markup=get_inline_kb("add_remove"),
                )
            else:
                str_lr = "\n".join(
                    [
                        str(s.reminder_time)
                        + ": "
                        + s.reminder
                        + " ("
                        + s.type_of_reminder
                        + ")"
                        for s in lr
                    ]
                )
                quantity = str(len(lr)) + " reminder" if len(lr) == 1 else " reminders"
                await message.answer(
                    text=f"<em><b>Welcome, {current_user.full_name}!</b></em> \n"
                    + f"You have {quantity}:\n{str_lr}\n"
                    + "<em>And now, I'm here and ready to help! 😉</em>",
                    parse_mode="HTML",
                    reply_markup=get_inline_kb("add_remove"),
                )
            await BotStatesForUser.add_remove.set()
            await message.delete()
        else:
            print(f"Bot met known user {current_user.full_name} but without time zone")
            TZ_saved = False
    else:  # new user
        print(f"Bot met unknown user {current_user.full_name}")
        async with async_session() as session:
            async with session.begin():
                session.add_all(
                    [
                        Users(
                            user_id=current_user.id,
                            user_login=current_user.username,
                            user_name=current_user.full_name,
                        )
                    ]
                )
        print(
            f"Bot met unknown user {current_user.full_name}, add he to DB, and query time zone"
        )
        TZ_saved = False
    # if state.storage.data[str(message.from_id)][str(message.from_id)]['state'] == BotStatesForUser.unknown_TZ.state
    if TZ_saved == False:
        await message.answer(
            text=f"<em><b>Welcome, {current_user.full_name}!</b> I need to know your time zone! 😉</em>",
            parse_mode="HTML",
        )
        await message.delete()
        await message.answer(
            text="Current value UTC+03:00",
            reply_markup=get_inline_kb("set_TZ"),
        )
        await BotStatesForUser.unknown_TZ.set()
        await state.update_data(current_TZ="+03:00")
    else:
        copy_of_set = tasks_of_scheduler.copy()
        scheduler_not_started_for_current_user = True
        for task in copy_of_set:
            if task.get_name() == str(current_user.id):
                scheduler_not_started_for_current_user = False
        if scheduler_not_started_for_current_user:
            task_of_scheduler = asyncio.create_task(
                scheduler(message.chat, state), name=str(current_user.id)
            )  # start of scheduler
            tasks_of_scheduler.add(task_of_scheduler)


@dp.message_handler(commands=["stop"], state="*")
async def comm_stop(message: types.Message, state: FSMContext):
    print("Got command Stop")
    user_data = await state.get_data()
    current_user = user_data["current_user"]
    await message.answer(
        text="<em><b>Good bye!</b> I will not bother you anymore! 🥹</em>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),
    )
    await message.delete()
    copy_of_set = tasks_of_scheduler.copy()
    for task in copy_of_set:
        if task.get_name() == str(current_user.id):
            task.cancel()
            tasks_of_scheduler.discard(task)


@dp.message_handler(commands=["help"], state="*")
async def comm_help(message: types.Message):
    print("Got Help")
    await message.answer(
        text=HELP_COMMANDS,
        reply_markup=get_kb(),
    )
    await message.delete()


@dp.callback_query_handler(text="Add_reminder", state=BotStatesForUser.add_remove)
# lambda callback_query: callback_query.data.startswith('Add')
async def action_callback_add(callback: types.CallbackQuery):
    print("Pressed Add reminder")
    await callback.message.edit_text(
        text="Let's choose type of reminder:\n"
        + "<b><u>Very important reminder</u></b> - bot will send a reminder message every minute until you confirm receipt\n"
        + "<b><u>Simple reminder</u></b> - bot will send a reminder message once",
        parse_mode="HTML",
        reply_markup=get_inline_kb("type_reminder"),
    )
    await BotStatesForUser.type_reminder.set()


@dp.callback_query_handler(text="VI_reminder", state=BotStatesForUser.type_reminder)
async def action_callback_add_VI_rem(callback: types.CallbackQuery):
    print("Pressed add VI reminder")
    await callback.message.edit_text(
        text="Good! Now send me text of very important reminder",
    )
    await BotStatesForUser.VI_reminder.set()


@dp.callback_query_handler(text="Simple_reminder", state=BotStatesForUser.type_reminder)
async def action_callback_add_simple_rem(callback: types.CallbackQuery):
    print("Pressed add simple reminder")
    await callback.message.edit_text(text="Good! Now send me text of simple reminder")
    await BotStatesForUser.simple_reminder.set()


@dp.message_handler(state=BotStatesForUser.simple_reminder)
async def simple_reminder(message: types.Message, state: FSMContext):
    print("Got text of simple reminder and saved to State")
    await state.update_data(simple_reminder_message=message)
    await message.answer(
        text=f"Got it! I saved text of reminder: \n'{message.text}'\n"
        + "Now send me date and time of simple reminder in format: \n"
        + "YYYY-MM-DD hh:mm \n"
    )
    await BotStatesForUser.simple_reminder_date.set()


@dp.message_handler(state=BotStatesForUser.VI_reminder)
async def VI_reminder(message: types.Message, state: FSMContext):
    print("Got text of VI reminder and saved to State")
    await state.update_data(vi_reminder_message=message)
    await message.answer(
        text=f"Got it! I saved text of reminder: \n'{message.text}'\n"
        + "Now send me date and time of very important reminder in format: \n"
        + "YYYY-MM-DD hh:mm \n"
    )
    await BotStatesForUser.VI_reminder_date.set()


@dp.message_handler(state=BotStatesForUser.simple_reminder_date)
async def simple_reminder_date(message: types.Message, state: FSMContext):
    print("Got date of simple reminder and creating simple reminder")
    user_data = await state.get_data()
    current_user = user_data["current_user"]
    date = parse(message.text)
    text = user_data["simple_reminder_message"].text
    await message.answer(
        text="Got it! I saved simple reminder: \n" + f"{str(date)}: '{text}'",
        reply_markup=get_inline_kb("add_remove"),
    )
    async with async_session() as session:
        async with session.begin():
            session.add_all(
                [
                    Reminders(
                        user_id=current_user.id,
                        type_of_reminder="simple",
                        reminder=text,
                        reminder_time=date,
                    )
                ]
            )
    await BotStatesForUser.add_remove.set()


@dp.message_handler(state=BotStatesForUser.VI_reminder_date)
async def VI_reminder_date(message: types.Message, state: FSMContext):
    print("Got date of VI reminder and creating VI reminder")
    user_data = await state.get_data()
    current_user = user_data["current_user"]
    date = parse(message.text)
    text = user_data["vi_reminder_message"].text
    await message.answer(
        text="Got it! I saved very important reminder: \n" + f"{str(date)}: '{text}'",
        reply_markup=get_inline_kb("add_remove"),
    )
    async with async_session() as session:
        async with session.begin():
            session.add_all(
                [
                    Reminders(
                        user_id=current_user.id,
                        type_of_reminder="VI",
                        reminder=text,
                        reminder_time=date,
                    )
                ]
            )
    await BotStatesForUser.add_remove.set()


@dp.callback_query_handler(text="Remove_reminder", state=BotStatesForUser.add_remove)
async def action_callback_remove(callback: types.CallbackQuery, state: FSMContext):
    print("Pressed Remove reminder")
    await callback.answer()
    user_data = await state.get_data()
    current_user = user_data["current_user"]
    lr = await list_of_reminders(current_user.id)
    if len(lr) == 0:
        await callback.message.answer(
            text=f"<em><b>{current_user.full_name}!</b>\n"
            + "You don't have any reminders yet. But I'm here and ready to help! 😉</em>",
            parse_mode="HTML",
            reply_markup=get_inline_kb("add_remove"),
        )
    else:
        str_lr = "\n".join(
            [
                str(i)
                + ": "
                + str(s.reminder_time)
                + ": "
                + s.reminder
                + " ("
                + s.type_of_reminder
                + ")"
                for i, s in enumerate(lr, start=1)
            ]
        )
        quantity = str(len(lr)) + " reminder" if len(lr) == 1 else " reminders"
        await callback.message.answer(
            text=f"<em><b>{current_user.full_name}!</b></em> \n"
            + f"You have {quantity}: \n{str_lr} \n"
            + "<em>And now, you can send me number of reminder, that to be deleted (for example 1)😉</em>\n"
            + "(if you change your mind - press 'Back'",
            parse_mode="HTML",
            reply_markup=get_inline_kb("back"),
        )
    await BotStatesForUser.remove_reminder_num.set()


@dp.message_handler(state=BotStatesForUser.remove_reminder_num)
async def remove_reminder_num(message: types.Message, state: FSMContext):
    print("Got number of reminder to be removed")
    user_data = await state.get_data()
    current_user = user_data["current_user"]
    if message.text.strip().isdigit():
        reminder_number = int(message.text.strip())
        async with async_session() as session:
            stmt = (
                select(Reminders)
                .where(Reminders.user_id == current_user.id)
                .order_by(Reminders.reminder_time)
            )
            result = await session.execute(stmt)
            for i, rem in enumerate(result.scalars(), start=1):
                if i == reminder_number:
                    await session.delete(rem)
                    await session.commit()
    lr = await list_of_reminders(current_user.id)
    if len(lr) == 0:
        await message.answer(
            text=f"<em><b>{current_user.full_name}!</b> \n"
            + "You don't have any reminders now. But I'm here and ready to help! 😉</em>",
            parse_mode="HTML",
            reply_markup=get_inline_kb("add_remove"),
        )
    else:
        str_lr = "\n".join(
            [
                str(s.reminder_time)
                + ": "
                + s.reminder
                + " ("
                + s.type_of_reminder
                + ")"
                for s in lr
            ]
        )
        quantity = str(len(lr)) + " reminder" if len(lr) == 1 else " reminders"
        await message.answer(
            text=f"<em><b>{current_user.full_name}!</b></em> \n"
            + f"You have {quantity}: \n{str_lr}\n"
            + "<em>And now, I'm here and ready to help! 😉</em>",
            parse_mode="HTML",
            reply_markup=get_inline_kb("add_remove"),
        )
    await BotStatesForUser.add_remove.set()


@dp.callback_query_handler(text="Change_TZ", state=BotStatesForUser.add_remove)
async def action_callback_change_TZ(callback: types.CallbackQuery, state: FSMContext):
    print("Pressed Change time zone")
    await callback.answer()
    user_data = await state.get_data()
    current_user = user_data["current_user"]
    async with async_session() as session:
        stmt = select(Users).where(Users.user_id == current_user.id)
        result = await session.execute(stmt)
        res = result.scalars().first()
    await callback.message.answer(
        text=f"Let's change your time zone. Current value UTC{res.user_tz}",
        reply_markup=get_inline_kb("set_TZ"),
    )
    await state.update_data(current_TZ=res.user_tz)
    await BotStatesForUser.unknown_TZ.set()


@dp.callback_query_handler(text="TZ_set", state=BotStatesForUser.unknown_TZ)
async def action_callback_set_TZ(callback: types.CallbackQuery, state: FSMContext):
    print("Set TZ")
    user_data = await state.get_data()
    current_user = user_data["current_user"]
    async with async_session() as session:
        stmt = select(Users).where(Users.user_id == current_user.id)
        result = await session.execute(stmt)
        res = result.scalars().first()
        res.user_tz = user_data["current_TZ"]
        await session.commit()

    lr = await list_of_reminders(current_user.id)
    if len(lr) == 0:
        await callback.message.answer(
            text=f"<em><b>Very good, {current_user.full_name}!</b>\n"
            + "You don't have any reminders now. But I'm here and ready to help! 😉</em>",
            parse_mode="HTML",
            reply_markup=get_inline_kb("add_remove"),
        )
    else:
        str_lr = "\n".join(
            [
                str(s.reminder_time)
                + ": "
                + s.reminder
                + " ("
                + s.type_of_reminder
                + ")"
                for s in lr
            ]
        )
        quantity = str(len(lr)) + " reminder" if len(lr) == 1 else " reminders"
        await callback.message.answer(
            text=f"<em><b>Very good, {current_user.full_name}!</b></em>\n"
            + f"You have {quantity}:\n{str_lr}\n"
            + "<em>And now, I'm here and ready to help! 😉</em>",
            parse_mode="HTML",
            reply_markup=get_inline_kb("add_remove"),
        )

    await BotStatesForUser.add_remove.set()
    await callback.message.delete()
    copy_of_set = tasks_of_scheduler.copy()
    scheduler_not_started_for_current_user = True
    for task in copy_of_set:
        if task.get_name() == str(current_user.id):
            scheduler_not_started_for_current_user = False
    if scheduler_not_started_for_current_user:
        task_of_scheduler = asyncio.create_task(
            scheduler(callback.message.chat, state), name=str(current_user.id)
        )  # start of scheduler
        tasks_of_scheduler.add(task_of_scheduler)


@dp.callback_query_handler(state=BotStatesForUser.unknown_TZ)
async def action_callback_ch_TZ(callback: types.CallbackQuery, state: FSMContext):
    print("Change TZ")
    user_data = await state.get_data()
    if callback.data == "TZ_to_West":
        curr_TZ = TZ(user_data["current_TZ"], plus_hour=True)
        await state.update_data(current_TZ=curr_TZ[0])
    elif callback.data == "TZ_to_East":
        curr_TZ = TZ(user_data["current_TZ"], plus_hour=False)
    await state.update_data(current_TZ=curr_TZ[0])
    await callback.message.edit_text(
        text=f"Current value UTC{curr_TZ[0]}",
        reply_markup=get_inline_kb("set_TZ"),
    )
    await BotStatesForUser.unknown_TZ.set()


@dp.callback_query_handler(text="Back", state="*")
async def action_callback_back(callback: types.CallbackQuery):
    print("Pressed Back")
    await callback.answer()  # show_alert=True,
    await callback.message.answer(
        text="<em><b>Ok!</b> I'm here and ready to help! 😉</em>",
        parse_mode="HTML",
        reply_markup=get_inline_kb("add_remove"),
    )
    await BotStatesForUser.add_remove.set()


@dp.callback_query_handler(text="got_it", state="*")
async def action_callback_got_it(callback: types.CallbackQuery, state: FSMContext):
    print("Got it!")
    await callback.answer()
    user_data = await state.get_data()
    async with async_session() as session:
        stmt = select(Reminders).where(Reminders.id == user_data["last_VI_rem"])
        result = await session.execute(stmt)
        rem = result.scalars().first()
        rem.type_of_reminder = "done"
        await session.commit()
    await callback.message.answer(text="Ok, I got it too!")


@dp.message_handler(state="*")
async def echo(message: types.Message, state: FSMContext):
    print("Got some text and saved to State")
    await state.update_data(last_message=message)
    await message.answer(text=f"Got it! I saved: '{message.text}'")


async def scheduler(chat, state):
    pass
    while True:
        await asyncio.sleep(60)
        print(f"Check schedule for user with id {chat.id}")
        user_data = await state.get_data()
        async with async_session() as session:
            stmt = select(Reminders).where(Reminders.user_id == chat.id)
            result = await session.execute(stmt)
            for rem in result.scalars():
                reminder_time_utc = rem.reminder_time - datetime.timedelta(
                    hours=TZ(user_data["current_TZ"])[1]
                )
                if reminder_time_utc <= datetime.datetime.utcnow():
                    if rem.type_of_reminder == "simple":
                        await chat.bot.send_message(text=rem.reminder, chat_id=chat.id)
                        rem.type_of_reminder = "done"
                        await session.commit()
                    if rem.type_of_reminder == "VI":
                        await chat.bot.send_message(
                            text=rem.reminder,
                            chat_id=chat.id,
                            reply_markup=get_inline_kb("got_it"),
                        )
                        await state.update_data(last_VI_rem=rem.id)


if __name__ == "__main__":
    executor.start_polling(
        dp,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True,  # ignoring offline messages
    )
