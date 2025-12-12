from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config.answers import WELCOME_TEXT, HELP_TEXT, MENU_TEXT, COMMAND_REQUIREMENTS, DEFAULT_ESSAY_TEMPLATE
from ai.agent import generate_text, check_essay, write_essay
from database.db_session import create_session
from database.models import User, Message, Essay, Template
from bott.bot import main_board
import html
import math

router = Router()


class HistoryStates(StatesGroup):
    browsing_history = State()


class TemplateStates(StatesGroup):
    waiting_for_template_name = State()
    waiting_for_template_content = State()
    waiting_for_essay_check = State()
    waiting_for_essay_topic = State()
    selecting_template = State()


def get_user(session, tg_id, name):
    user = session.query(User).filter_by(tg_id=tg_id).first()
    if not user:
        user = User(tg_id=tg_id, name=name)
        session.add(user)
        session.commit()
    return user


def clear_marks(text: str) -> str:
    text = html.escape(text)
    text = text.replace("*", "")
    text = text.replace("_", " ")
    text = text.replace("`", "'")
    text = text.replace("[", "(")
    text = text.replace("]", ")")
    return text


history_cache = {}


@router.message(Command("start"))
async def start(msg: types.Message):
    await msg.answer(
        WELCOME_TEXT,
        reply_markup=main_board()
    )


@router.message(Command("menu"))
@router.message(F.text == "Меню")
async def menu_command(msg: types.Message):
    await msg.answer(
        MENU_TEXT,
        reply_markup=main_board()
    )


@router.message(Command("help"))
@router.message(F.text == "Помощь")
async def help_command(msg: types.Message):
    await msg.answer(
        HELP_TEXT,
        reply_markup=main_board()
    )


@router.message(Command("write"))
async def write_essay_command(msg: types.Message, state: FSMContext):
    await msg.answer(
        COMMAND_REQUIREMENTS["write"],
        reply_markup=main_board()
    )
    await state.set_state(TemplateStates.waiting_for_essay_topic)


@router.message(TemplateStates.waiting_for_essay_topic)
async def process_essay(msg: types.Message, state: FSMContext):
    topic = msg.text
    session = create_session()
    user = get_user(session, msg.from_user.id, msg.from_user.full_name)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Использовать базовый шаблон", callback_data="use_default_template"),
                InlineKeyboardButton(text="Выбрать свой шаблон", callback_data="select_my_template")
            ]
        ]
    )

    await msg.answer(
        f"Тема сочинения: {topic}\n\n{DEFAULT_ESSAY_TEMPLATE}",
        reply_markup=keyboard
    )

    await state.update_data(topic=topic, user_id=user.id)
    session.close()


@router.callback_query(F.data == "use_default_template")
async def use_default_template(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    topic = data.get("topic")

    await callback.message.edit_text("Пишу сочинение...")

    ai_answer = clear_marks(await write_essay(topic, DEFAULT_ESSAY_TEMPLATE))

    session = create_session()
    essay = Essay(
        user_id=data.get("user_id"),
        topic=topic,
        content=ai_answer
    )
    session.add(essay)
    session.commit()

    await callback.message.edit_text(
        f"Сочинение на тему: {topic}\n\n{ai_answer}\n\nСочинение сохранено в историю!"
    )

    session.close()
    await state.clear()


@router.callback_query(F.data == "select_my_template")
async def select_my_template(callback: types.CallbackQuery, state: FSMContext):
    session = create_session()
    user = get_user(session, callback.from_user.id, callback.from_user.full_name)

    templates = session.query(Template).filter_by(user_id=user.id).all()

    if not templates:
        await callback.message.answer(
            "У вас пока нет своих шаблонов. Создайте новый через /templates",
            reply_markup=main_board()
        )
        session.close()
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for template in templates:
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text=template.name, callback_data=f"template_{template.id}")
        ])

    await callback.message.answer(
        "Выберите ваш шаблон:",
        reply_markup=keyboard
    )

    session.close()
    await state.set_state(TemplateStates.selecting_template)


@router.callback_query(F.data.startswith("template_"), TemplateStates.selecting_template)
async def use_selected_template(callback: types.CallbackQuery, state: FSMContext):
    template_id = int(callback.data.split("_")[1])
    data = await state.get_data()
    topic = data.get("topic")

    session = create_session()
    template = session.query(Template).filter_by(id=template_id).first()

    if template:
        await callback.message.edit_text("Пишу сочинение по вашему шаблону...")

        ai_answer = clear_marks(await write_essay(topic, template.content))

        essay = Essay(
            user_id=data.get("user_id"),
            topic=topic,
            content=ai_answer
        )
        session.add(essay)
        session.commit()

        await callback.message.edit_text(
            f"Сочинение на тему: {topic}\n\n{ai_answer}\n\nСочинение сохранено в историю!"
        )

    session.close()
    await state.clear()


@router.message(Command("check"))
async def check_essay_command(msg: types.Message, state: FSMContext):
    await msg.answer(
        COMMAND_REQUIREMENTS["check"],
        reply_markup=main_board()
    )
    await state.set_state(TemplateStates.waiting_for_essay_check)


@router.message(TemplateStates.waiting_for_essay_check)
async def process_essay_check(msg: types.Message, state: FSMContext):
    essay_text = msg.text
    session = create_session()
    user = get_user(session, msg.from_user.id, msg.from_user.full_name)

    await msg.answer("Проверяю сочинение на ошибки...")

    ai_answer = clear_marks(await check_essay(essay_text))

    db_msg = Message(user_id=user.id, text=essay_text, answer=ai_answer)
    session.add(db_msg)
    session.commit()

    max_length = 4000
    if len(ai_answer) > max_length:
        parts = [ai_answer[i:i + max_length] for i in range(0, len(ai_answer), max_length)]
        for i, part in enumerate(parts, 1):
            await msg.answer(f"Часть {i}:\n\n{part}")
    else:
        await msg.answer(f"Результат проверки:\n\n{ai_answer}")

    session.close()
    await state.clear()


@router.message(Command("templates"))
async def templates_command(msg: types.Message):
    await msg.answer(
        COMMAND_REQUIREMENTS["templates"],
        reply_markup=main_board()
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Мои шаблоны", callback_data="show_templates"),
                InlineKeyboardButton(text="Новый шаблон", callback_data="create_template")
            ],
            [
                InlineKeyboardButton(text="Использовать шаблон", callback_data="use_template")
            ]
        ]
    )

    await msg.answer("Выберите действие:", reply_markup=keyboard)


@router.callback_query(F.data == "show_templates")
async def show_templates(callback: types.CallbackQuery):
    session = create_session()
    user = get_user(session, callback.from_user.id, callback.from_user.full_name)

    templates = session.query(Template).filter_by(user_id=user.id).all()

    if not templates:
        await callback.message.answer("У вас пока нет своих шаблонов. Создайте новый!")
    else:
        response = "Ваши шаблоны:\n\n"
        for template in templates:
            response += f"• {template.name} (создан: {template.created_at.strftime('%d.%m.%Y')})\n"

        await callback.message.answer(response)

    session.close()


@router.callback_query(F.data == "create_template")
async def create_template_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите название для нового шаблона:")
    await state.set_state(TemplateStates.waiting_for_template_name)


@router.message(TemplateStates.waiting_for_template_name)
async def process_template_name(msg: types.Message, state: FSMContext):
    await state.update_data(template_name=msg.text)
    await msg.answer("Теперь введите содержание шаблона (структуру сочинения по пунктам):")

    await state.set_state(TemplateStates.waiting_for_template_content)


@router.message(TemplateStates.waiting_for_template_content)
async def process_template_content(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    template_name = data.get("template_name")
    template_content = msg.text

    session = create_session()
    user = get_user(session, msg.from_user.id, msg.from_user.full_name)

    template = Template(
        user_id=user.id,
        name=template_name,
        content=template_content
    )

    session.add(template)
    session.commit()

    await msg.answer(f"Шаблон '{template_name}' успешно сохранен!")

    session.close()
    await state.clear()


@router.callback_query(F.data == "use_template")
async def use_template_command(callback: types.CallbackQuery):
    await callback.message.answer("Для использования шаблона начните писать новое сочинение через команду /write")


@router.message(Command("history"))
async def history_command(msg: types.Message, state: FSMContext):
    session = create_session()
    user = get_user(session, msg.from_user.id, msg.from_user.full_name)

    essays = session.query(Essay).filter_by(user_id=user.id).order_by(Essay.created_at.desc()).all()

    if not essays:
        await msg.answer("У вас пока нет сохраненных сочинений.")
        session.close()
        return

    history_cache[msg.from_user.id] = {
        'essays': essays,
        'current_page': 0,
        'total_pages': math.ceil(len(essays) / 5)
    }

    await show_history_page(msg, msg.from_user.id)

    session.close()
    await state.set_state(HistoryStates.browsing_history)


async def show_history_page(msg: types.Message, user_id: int, page: int = 0):
    if user_id not in history_cache:
        return

    data = history_cache[user_id]
    essays = data['essays']
    total_pages = data['total_pages']

    if page >= total_pages:
        page = 0
    if page < 0:
        page = total_pages - 1

    start_idx = page * 5
    end_idx = start_idx + 5
    page_essays = essays[start_idx:end_idx]

    response = f"История сочинений (стр. {page + 1}/{total_pages}):\n\n"

    keyboard_buttons = []

    for i, essay in enumerate(page_essays, start=1):
        essay_num = start_idx + i
        response += f"{essay_num}. {essay.topic} ({essay.created_at.strftime('%d.%m.%Y %H:%M')})\n"

        keyboard_buttons.append([
            InlineKeyboardButton(
                text=f"{essay_num}. {essay.topic[:30]}...",
                callback_data=f"view_essay_{essay.id}"
            )
        ])

    nav_buttons = []
    if total_pages > 1:
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(text="Назад", callback_data=f"history_prev_{page}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(text="Вперед", callback_data=f"history_next_{page}"))

    if nav_buttons:
        keyboard_buttons.append(nav_buttons)

    keyboard_buttons.append([InlineKeyboardButton(text="Закрыть историю", callback_data="close_history")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    try:
        await msg.edit_text(response, reply_markup=keyboard)
    except:
        await msg.answer(response, reply_markup=keyboard)

    history_cache[user_id]['current_page'] = page


@router.callback_query(F.data.startswith("history_"))
async def history_navigation(callback: types.CallbackQuery, state: FSMContext):
    if callback.data.startswith("history_prev_"):
        page = int(callback.data.split("_")[2])
        await show_history_page(callback.message, callback.from_user.id, page - 1)
    elif callback.data.startswith("history_next_"):
        page = int(callback.data.split("_")[2])
        await show_history_page(callback.message, callback.from_user.id, page + 1)
    await callback.answer()


@router.callback_query(F.data.startswith("view_essay_"))
async def view_essay(callback: types.CallbackQuery):
    essay_id = int(callback.data.split("_")[2])

    session = create_session()
    essay = session.query(Essay).filter_by(id=essay_id).first()

    if essay:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Назад к списку", callback_data="back_to_history")]
            ]
        )

        max_length = 4000
        essay_text = essay.content

        if len(essay_text) > max_length:
            parts = [essay_text[i:i + max_length] for i in range(0, len(essay_text), max_length)]
            for i, part in enumerate(parts, 1):
                if i == 1:
                    await callback.message.edit_text(
                        f"Сочинение: {essay.topic}\n"
                        f"Дата: {essay.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
                        f"Часть {i}:\n{part}",
                        reply_markup=keyboard
                    )
                else:
                    await callback.message.answer(f"Часть {i}:\n{part}")
        else:
            await callback.message.edit_text(
                f"Сочинение: {essay.topic}\n"
                f"Дата: {essay.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
                f"{essay_text}",
                reply_markup=keyboard
            )

    session.close()
    await callback.answer()


@router.callback_query(F.data == "back_to_history")
async def back_to_history(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if user_id in history_cache:
        current_page = history_cache[user_id]['current_page']
        await show_history_page(callback.message, user_id, current_page)
    await callback.answer()


@router.callback_query(F.data == "close_history")
async def close_history(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if user_id in history_cache:
        del history_cache[user_id]

    await callback.message.delete()
    await callback.answer("История закрыта")
    await state.clear()


@router.message(HistoryStates.browsing_history)
async def history_state(msg: types.Message):
    await msg.answer("Для выхода из режима истории нажмите 'Закрыть историю' или используйте команды бота")


@router.message()
async def other_messages(msg: types.Message):
    if msg.text not in ["Меню", "Помощь"]:
        await msg.answer(
            "Пожалуйста, используйте команды из меню или нажмите /menu",
            reply_markup=main_board()
        )