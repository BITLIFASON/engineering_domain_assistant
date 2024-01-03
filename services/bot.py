import logging
import json

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from langchain.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings

with open('../credentials.json', 'r') as f:
    credentials = json.load(f)

OPENAI_API_KEY = credentials["OPENAI_API_KEY"]
TELEGRAM_TOKEN = credentials["TELEGRAM_TOKEN"]

embeddings=OpenAIEmbeddings(api_key=OPENAI_API_KEY)
vectorstore = Chroma(collection_name='engineering_store',
                     embedding_function=embeddings,
                     persist_directory="../db")
collection = vectorstore.get()
retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 3})

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

CHOOSING, DONE, RELEVANCE, BEGINNER, OLD, SMART, ERROR = range(7)

reply_keyboard = [
    ["Выдача релевантных документов"],
    ["Режим для начинающих"],
    ["Ответ по старым версиям"],
    ["Умный поиск"],
    ["Нахождение ошибок"],
    ["Закончить"],
]
markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start bot"""

    user = update.message.from_user.username
    logger.info("User %s start bot.", user)

    await update.message.reply_text(
        "Привет! Это ассистент инженера. Выберите пункт меню.",
        reply_markup=markup
    )

    return CHOOSING


async def choosing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """"Choice command"""

    user = update.message.from_user.username
    text = update.message.text

    logger.info("User %s choice command.", user)

    if text == "Выдача релевантных документов":
        await update.message.reply_text("Введите вопрос:")
        return RELEVANCE

    if text == "Режим для начинающих":
        return BEGINNER

    if text == "Ответ по старым версиям":
        return OLD

    if text == "Умный поиск":
        return SMART

    if text == "Нахождение ошибок":
        return ERROR

    if text == "Закончить":
        return DONE


async def relevance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """"Get relevance"""

    global retriever

    user = update.message.from_user.username
    logger.info("User %s call relevance.", user)

    text = update.message.text

    relevant_documents = []
    retrieve_documents = retriever.get_relevant_documents(text)
    for doc in retrieve_documents:
        doc_name = doc.metadata["source"].split("\\")[1][:-4]
        if doc_name not in relevant_documents:
            relevant_documents.append(doc_name)

    await update.message.reply_text("Список релевантных документов:\n"+"\n".join(relevant_documents))

    await update.message.reply_text("Возвращаю в меню.", reply_markup=markup)

    return CHOOSING


async def beginner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """"Beginner mode"""

    user = update.message.from_user.username
    logger.info("User %s call beginner.", user)

    await update.message.reply_text(
        "Функция не реализована. Выберите пункт меню.",
        reply_markup=markup
    )

    return CHOOSING


async def old(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """"Get old versions"""

    user = update.message.from_user.username
    logger.info("User %s call old.", user)

    await update.message.reply_text(
        "Функция не реализована. Выберите пункт меню.",
        reply_markup=markup
    )

    return CHOOSING


async def smart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """"Smart search"""

    user = update.message.from_user.username
    logger.info("User %s call smart.", user)

    await update.message.reply_text(
        "Функция не реализована. Выберите пункт меню.",
        reply_markup=markup
    )

    return CHOOSING


async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """"Find error"""

    user = update.message.from_user.username
    logger.info("User %s call error.", user)

    await update.message.reply_text(
        "Функция не реализована. Выберите пункт меню.",
        reply_markup=markup
    )

    return CHOOSING


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stop bot"""

    user = update.message.from_user.username
    logger.info("User %s stop bot.", user)
    await update.message.reply_text(
        "До встречи!", reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


def main() -> None:
    """Run bot"""

    global TELEGRAM_TOKEN

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING: [MessageHandler(filters.TEXT & ~filters.Regex('^Закончить$'), choosing)],
            RELEVANCE: [MessageHandler(filters.TEXT & ~filters.Regex('^Закончить$'), relevance)],
            BEGINNER: [MessageHandler(filters.TEXT & ~filters.Regex('^Закончить$'), beginner)],
            OLD: [MessageHandler(filters.TEXT & ~filters.Regex('^Закончить$'), old)],
            SMART: [MessageHandler(filters.TEXT & ~filters.Regex('^Закончить$'), smart)],
            ERROR: [MessageHandler(filters.TEXT & ~filters.Regex('^Закончить$'), error)]
        },
        fallbacks=[MessageHandler(filters.Regex('^Закончить$'), stop)],
    )

    application.add_handler(conv_handler)

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
