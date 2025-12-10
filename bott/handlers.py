from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config.answers import WELCOME_TEXT, HELP_TEXT, MENU_TEXT, COMMAND_REQUIREMENTS, DEFAULT_ESSAY_TEMPLATE
from ai.agent import generate_text
from database.db_session import create_session
from database.models import User, Message, Essay, Template
from bott.bot import get_main_keyboard
import html

router = Router()


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


@router.message(Command("start"))
@router.message(F.text == "Старт")
async def start(msg: types.Message):
    await msg.answer(
        WELCOME_TEXT,
        reply_markup=get_main_keyboard()
    )


@router.message(Command("menu"))
@router.message(F.text == "Меню")
async def menu_cmd(msg: types.Message):
    await msg.answer(
        MENU_TEXT,
        reply_markup=get_main_keyboard()
    )


@router.message(Command("help"))
@router.message(F.text == "Помощь")
async def help_cmd(msg: types.Message):
    await msg.answer(
        HELP_TEXT,
        reply_markup=get_main_keyboard()
    )


@router.message(Command("write"))
async def write_essay(msg: types.Message, state: FSMContext):
    await msg.answer(
        COMMAND_REQUIREMENTS["write"],
        reply_markup=get_main_keyboard()
    )
    await state.set_state(TemplateStates.waiting_for_essay_topic)


@router.message(TemplateStates.waiting_for_essay_topic)
async def process_essay_topic(msg: types.Message, state: FSMContext):
    topic = msg.text
    session = create_session()
    user = get_user(session, msg.from_user.id, msg.from_user.full_name)

    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="Использовать базовый шаблон", callback_data="use_default_template"),
                types.InlineKeyboardButton(text="Выбрать свой шаблон", callback_data="select_my_template")
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

    prompt = f"Напиши сочинение на тему: '{topic}'. Используй стандартную структуру сочинения: введение, основная часть, заключение."

    await callback.message.edit_text("✍Пишу сочинение...")

    ai_answer = clear_marks(await generate_text(prompt))

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
            reply_markup=get_main_keyboard()
        )
        session.close()
        return

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[])
    for template in templates:
        keyboard.inline_keyboard.append([
            types.InlineKeyboardButton(text=template.name, callback_data=f"template_{template.id}")
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
        prompt = f"Напиши сочинение на тему: '{topic}'. Используй следующий шаблон:\n{template.content}"

        await callback.message.edit_text("✍Пишу сочинение по вашему шаблону...")

        ai_answer = clear_marks(await generate_text(prompt))

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
async def check_essay_cmd(msg: types.Message, state: FSMContext):
    await msg.answer(
        COMMAND_REQUIREMENTS["check"],
        reply_markup=get_main_keyboard()
    )
    await state.set_state(TemplateStates.waiting_for_essay_check)


@router.message(TemplateStates.waiting_for_essay_check)
async def process_essay_check(msg: types.Message, state: FSMContext):
    essay_text = msg.text
    session = create_session()
    user = get_user(session, msg.from_user.id, msg.from_user.full_name)

    await msg.answer("Проверяю сочинение на ошибки...")

    prompt = f"Проверь следующее сочинение на ошибки (орфографические, пунктуационные, стилистические, логические). Укажи конкретные ошибки и дай рекомендации по улучшению:\n\n{essay_text}"

    ai_answer = clear_marks(await generate_text(prompt))

    db_msg = Message(user_id=user.id, text=essay_text, answer=ai_answer)
    session.add(db_msg)
    session.commit()

    await msg.answer(
        f"Результат проверки:\n\n{ai_answer}"
    )

    session.close()
    await state.clear()


@router.message(Command("templates"))
async def templates_cmd(msg: types.Message):
    await msg.answer(
        COMMAND_REQUIREMENTS["templates"],
        reply_markup=get_main_keyboard()
    )

    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="Мои шаблоны", callback_data="show_templates"),
                types.InlineKeyboardButton(text="Новый шаблон", callback_data="create_template")
            ],
            [
                types.InlineKeyboardButton(text="Использовать шаблон", callback_data="use_template")
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
    await msg.answer("Теперь введите содержание шаблона (структуру сочинения):")
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
async def use_template_cmd(callback: types.CallbackQuery):
    await callback.message.answer("Для использования шаблона начните писать новое сочинение через команду /write")


@router.message(Command("history"))
async def history_cmd(msg: types.Message):
    session = create_session()
    user = get_user(session, msg.from_user.id, msg.from_user.full_name)

    essays = session.query(Essay).filter_by(user_id=user.id).order_by(Essay.created_at.desc()).limit(5).all()

    if not essays:
        await msg.answer("У вас пока нет сохраненных сочинений.")
    else:
        response = "Последние сочинения:\n\n"
        for essay in essays:
            response += f"• {essay.topic} ({essay.created_at.strftime('%d.%m.%Y %H:%M')})\n"
            preview = essay.content[:100] + "..." if len(essay.content) > 100 else essay.content
            response += f"  {preview}\n\n"

        await msg.answer(response)

    session.close()


@router.message()
async def other_messages(msg: types.Message):
    if msg.text not in ["Старт", "Меню", "Помощь"]:
        await msg.answer(
            "Пожалуйста, используйте команды из меню или нажмите /menu",
            reply_markup=get_main_keyboard()
        )