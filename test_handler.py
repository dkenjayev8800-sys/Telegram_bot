from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import (
    create_test, get_tests, get_test, add_test_response,
    get_test_responses, delete_test
)
from config import ADMIN_USER_ID
import logging

logger = logging.getLogger(__name__)

async def show_tests_menu(query, context: ContextTypes.DEFAULT_TYPE):
    """Testlarni ko'rsatish menyu (admin uchun)"""
    tests = get_tests()
    text = "📝 Testlar\n\n"

    keyboard = []

    if tests:
        for i, test in enumerate(tests, 1):
            response_count = len(test.get("responses", []))
            text += f"{i}. {test['title']}\n   Javoblar: {response_count}\n\n"
            keyboard.append([
                InlineKeyboardButton(f"👁️ {test['title']}", callback_data=f"view_test_{test['id']}"),
                InlineKeyboardButton("📊", callback_data=f"test_stats_{test['id']}"),
                InlineKeyboardButton("🗑️", callback_data=f"del_test_{test['id']}")
            ])
    else:
        text += "Testlar yo'q\n\n"

    keyboard.append([InlineKeyboardButton("➕ Test yaratish", callback_data="create_test")])
    keyboard.append([InlineKeyboardButton("🏠 Orqaga", callback_data="back")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def show_test_for_user(query, context: ContextTypes.DEFAULT_TYPE, test_id: int):
    """Foydalanuvchi uchun test ko'rsatish - birinchi savol"""
    test = get_test(test_id)
    if not test:
        await query.answer("❌ Test topilmadi", show_alert=True)
        return

    questions = test.get("questions", [])
    if not questions:
        await query.answer("❌ Savolarsiz test", show_alert=True)
        return

    first_question = questions[0]
    text = f"📝 {test['title']}\n\n"
    text += f"1/{len(questions)}: {first_question['text']}\n\n"

    keyboard = []
    for i, answer in enumerate(first_question.get("answers", []), 1):
        keyboard.append([
            InlineKeyboardButton(
                f"{i}. {answer}",
                callback_data=f"test_answer_{test_id}_0_{i-1}"
            )
        ])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_test_answer(query, context: ContextTypes.DEFAULT_TYPE, test_id: int, q_idx: int, a_idx: int):
    """Testga javob berish"""
    user_id = query.from_user.id
    test = get_test(test_id)

    if not test:
        await query.answer("❌ Test topilmadi", show_alert=True)
        return

    questions = test.get("questions", [])
    if q_idx >= len(questions):
        await query.answer("❌ Savol topilmadi", show_alert=True)
        return

    question = questions[q_idx]
    answers = question.get("answers", [])

    if a_idx >= len(answers):
        await query.answer("❌ Javob topilmadi", show_alert=True)
        return

    selected_answer = answers[a_idx]
    add_test_response(test_id, user_id, q_idx, selected_answer)

    next_q_idx = q_idx + 1

    if next_q_idx < len(questions):
        next_question = questions[next_q_idx]
        text = f"📝 {test['title']}\n\n"
        text += f"{next_q_idx + 1}/{len(questions)}: {next_question['text']}\n\n"

        keyboard = []
        for i, answer in enumerate(next_question.get("answers", []), 1):
            keyboard.append([
                InlineKeyboardButton(
                    f"{i}. {answer}",
                    callback_data=f"test_answer_{test_id}_{next_q_idx}_{i-1}"
                )
            ])

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await query.edit_message_text(
            f"✅ Test tugatildi!\n\n"
            f"Barcha savollarga javob berdingiz."
        )

async def show_test_stats(query, context: ContextTypes.DEFAULT_TYPE, test_id: int):
    """Test statistikasini ko'rsatish (admin uchun)"""
    if query.from_user.id != ADMIN_USER_ID:
        await query.answer("❌ Faqat admin ko'rishi mumkin", show_alert=True)
        return

    test = get_test(test_id)
    if not test:
        await query.answer("❌ Test topilmadi", show_alert=True)
        return

    responses = get_test_responses(test_id)
    questions = test.get("questions", [])

    text = f"📊 {test['title']} - Statistika\n\n"
    text += f"Jami javoblar: {len(responses)}\n\n"

    for q_idx, question in enumerate(questions, 1):
        text += f"{q_idx}. {question['text']}\n"
        answers = question.get("answers", [])

        answer_counts = {i: 0 for i in range(len(answers))}

        for response in responses:
            if response["question_index"] == q_idx - 1:
                answer_text = response["answer"]
                try:
                    a_idx = answers.index(answer_text)
                    answer_counts[a_idx] += 1
                except ValueError:
                    pass

        for a_idx, answer in enumerate(answers, 1):
            count = answer_counts.get(a_idx - 1, 0)
            text += f"   {a_idx}. {answer} - {count} ta\n"

        text += "\n"

    keyboard = [[InlineKeyboardButton("🏠 Orqaga", callback_data="back")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
