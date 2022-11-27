import datetime
import logging

import aiogram.utils.markdown as md
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode
from aiogram.utils import executor

from config import API_TOKEN
from data import SECTIONS, EVENTS, SCHEDULE

# Включаем логирование, будем видетьчто происходит в консоли
logging.basicConfig(level=logging.INFO)

# Базовый объект, управляющий соединением с Telegram API
bot = Bot(token=API_TOKEN)

# Для примера храним данные в памяти.
# Подключение долговременнного хранилища: TODO
storage = MemoryStorage()

# Наш менеджер запросов к боту
dp = Dispatcher(bot, storage=storage)


# Состояния для конечного автомата
class Menu(StatesGroup):
    section = State()  # Будем постоянно спрашивать секцию


@dp.message_handler(commands='start')
async def cmd_start(message: types.Message):
    """
    Начало беседы
    """

    # Установим состояние section
    await Menu.section.set()
    # создаем клавиатуру
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    for section in SECTIONS:
        markup.add(section)

    await message.answer(f"Привет, {message.from_user.full_name}! "
                         f"\nЯ помогу тебе сориентироваться в расписании фестиваля!"
                         f"\nНа какое мероприятие хотелось бы попасть?", reply_markup=markup)


# Пометка состояния '*' поможет обработать любое сосотояние бота
@dp.message_handler(state='*', commands='cancel')
@dp.message_handler(state='*', regexp=r'(.*(с|С)пасибо.*|.*(о|О)тмена.*)')
async def cancel_handler(message: types.Message, state: FSMContext):
    """
    Разрешаем пользователю закончить общение в любой момент
    """
    current_state = await state.get_state()
    if current_state is None:
        return

    logging.info('Cancelling state %r', current_state)
    # Завершаем работу автомата
    await state.finish()

    # Сообщаем пользователю и удаляем клавиатуру
    await message.answer('Спасибо за использование!', reply_markup=types.ReplyKeyboardRemove())


@dp.message_handler(
    lambda message: message.text not in SECTIONS,
    state=Menu.section)
async def process_section_invalid(message: types.Message):
    """
    Можно выбирать только заданные секции
    """
    return await message.reply("У нас нет такой секции. Пожалуйста, выберите из списка.")


@dp.message_handler(state=Menu.section)
async def process_section(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['section'] = message.text

    reply_text = SECTIONS[message.text]

    if message.text == SCHEDULE:
        s_events = sorted(EVENTS)
        now = datetime.datetime.now().time()
        event = list(filter(lambda ev: ev[0].hour == now.hour and now.minute >= ev[0].minute, EVENTS))

        if len(event) > 0:
            reply_text = md.text('Отлично! Сейчас идёт:',
                                   md.italic(event[0][1]))
        else:
            reply_text = md.text('Кажется, фестиваль уже закончился!')
    else:
        reply_text = SECTIONS[message.text]

    await message.reply(reply_text, parse_mode=ParseMode.MARKDOWN)


@dp.message_handler(state='*', content_types=['document', 'photo', 'sticker'])
async def unknown_message(message: types.Message):
    message_text = md.text('Я не знаю, что с этим делать!')
    await message.reply(message_text, parse_mode=ParseMode.MARKDOWN)


if __name__ == '__main__':
    try:
        executor.start_polling(dp, skip_updates=True)
    except Exception as e:
        logging.error("Bot stopped! " + str(e))
