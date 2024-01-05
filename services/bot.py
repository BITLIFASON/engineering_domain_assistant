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
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableParallel, RunnablePassthrough


with open('../credentials.json', 'r') as f:
    credentials = json.load(f)


OPENAI_API_KEY = credentials["OPENAI_API_KEY"]
TELEGRAM_TOKEN = credentials["TELEGRAM_TOKEN"]


embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY)
vectorstore = Chroma(collection_name='engineering_store',
                     embedding_function=embeddings,
                     persist_directory="../db")
collection = vectorstore.get()
retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 3})


setup_and_retrieval = RunnableParallel({"context": retriever, "question": RunnablePassthrough()})


llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0, api_key=OPENAI_API_KEY)


# шаблон для обычного ответа
template = """Контекст: {context}\n\n\
Используя контекст, ответь на вопрос: {question}. \
Если в данном контексте нет нужной информации, то отвечай:\n"\
Извините, не нашёл информации по этому вопросу"""
prompt = ChatPromptTemplate.from_template(template)


# системный шаблон для учёта контекста истории чата
contextualize_system_template = """Учитывая историю чата и последний вопрос пользователя, \
который может ссылаться на контекст в истории чата, сформулируй отдельный вопрос, \
который можно понять без истории чата. НЕ отвечай на этот вопрос, \
просто переформулируй его, если необходимо, и в противном случае верни как есть."""
contextualize_system_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", contextualize_system_template),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{question}"),
    ]
)
contextualize_chain = contextualize_system_prompt | llm | StrOutputParser()

# системный шаблон для ответа в режиме для начинающих
system_template = """Ты ассистент для ответов на вопросы. \
Используй следующие фрагменты извлеченного контекста, чтобы ответить на вопрос {context}\n\
Если в данном контексте нет нужной информации, то отвечай:\n\
Детализируйте свой вопрос"""
system_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_template),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{question}"),
    ]
)
def contextualized_question(input: dict):
    if input.get("chat_history"):
        return contextualize_chain
    else:
        return input["question"]
contextualized_retrieval = RunnablePassthrough.assign(context=contextualized_question | retriever)


output_parser = StrOutputParser()


logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

CHOOSING, DONE, ANSWER, BEGINNER, BEGINNER_CHOICE, OLD, SMART, ERROR = range(8)

reply_keyboard = [
    ["Получить ответ на вопрос"],
    ["Режим для начинающих"],
    ["Ответ по старым версиям"],
    ["Умный поиск"],
    ["Нахождение ошибок"],
    ["Закончить"],
]
markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
markup_begin = ReplyKeyboardMarkup([['Уточнить детали вопроса', 'Вернуться в меню']], one_time_keyboard=True)



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

    if text == "Получить ответ на вопрос":
        await update.message.reply_text("Введите вопрос:")
        return ANSWER

    if text == "Режим для начинающих":
        await update.message.reply_text("Введите вопрос:")
        return BEGINNER

    if text == "Ответ по старым версиям":
        return OLD

    if text == "Умный поиск":
        return SMART

    if text == "Нахождение ошибок":
        return ERROR

    if text == "Закончить":
        return DONE


async def answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """"Get answer"""

    global retriever
    global setup_and_retrieval
    global prompt
    global llm
    global output_parser

    user = update.message.from_user.username
    logger.info("User %s get answer.", user)

    text = update.message.text

    context = setup_and_retrieval.invoke(text)
    prompt_with_context = prompt.invoke(context)
    llm_answer = llm.invoke(prompt_with_context)
    llm_output = output_parser.invoke(llm_answer)

    await update.message.reply_text(llm_output)

    if 'Извините, не нашёл информации по этому вопросу' not in llm_output:

        relevant_documents = []
        for doc in context['context']:
            doc_name = doc.metadata["source"].split("\\")[-1][:-4]
            if doc_name not in relevant_documents:
                relevant_documents.append(doc_name)

        await update.message.reply_text("Список релевантных документов:\n"+"\n".join(relevant_documents))

    await update.message.reply_text("Возвращаю в меню.", reply_markup=markup)

    return CHOOSING


async def beginner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """"Beginner mode"""

    global contextualized_retrieval
    global llm

    user = update.message.from_user.username
    user_data = context.user_data
    logger.info("User %s call beginner.", user)

    if not user_data.get('chat_history', False):
        user_data['chat_history'] = []

    text = update.message.text

    context = contextualized_retrieval.invoke({"question": text,
                                               "chat_history": user_data['chat_history']})
    prompt_with_context = system_prompt.invoke(context)
    llm_answer = llm.invoke(prompt_with_context)
    llm_output = output_parser.invoke(llm_answer)
    user_data['chat_history'].extend([HumanMessage(content=text), llm_answer])

    await update.message.reply_text(llm_output)

    relevant_documents = []
    for doc in context['context']:
        doc_name = doc.metadata["source"].split("\\")[-1][:-4]
        if doc_name not in relevant_documents:
            relevant_documents.append(doc_name)
    await update.message.reply_text("Список возможно подходящих документов:\n"+"\n".join(relevant_documents))

    await update.message.reply_text("Сделайте выбор.", reply_markup=markup_begin)

    return BEGINNER_CHOICE


async def beginner_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """"Choice beginner"""

    user = update.message.from_user.username
    user_data = context.user_data
    logger.info("User %s call beginner choice.", user)

    text = update.message.text

    if text == "Уточнить детали вопроса":
        await update.message.reply_text("Введите детали:")
        return BEGINNER
    else:
        user_data['chat_history'] = []
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
            ANSWER: [MessageHandler(filters.TEXT & ~filters.Regex('^Закончить$'), answer)],
            BEGINNER: [MessageHandler(filters.TEXT & ~filters.Regex('^Закончить$'), beginner)],
            BEGINNER_CHOICE: [MessageHandler(filters.TEXT & ~filters.Regex('^Закончить$'), beginner_choice)],
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
