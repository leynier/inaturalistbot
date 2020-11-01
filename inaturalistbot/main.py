from logging import basicConfig, getLogger, INFO
from os import getenv
from pyinaturalist.node_api import get_taxa
from telegram import InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Updater, CommandHandler, InlineQueryHandler, MessageHandler, Filters


def start(update, context):
    chat_id = update.effective_chat.id
    text = 'Hello World!'
    context.bot.send_message(chat_id=chat_id, text=text)


def inline_search(update, context):
    query = update.inline_query.query
    if not query:
        return
    response = get_taxa(q=query)
    results = response['results']
    answers = [
        InlineQueryResultArticle(
            id=query.upper(),
            title=item['name'],
            input_message_content=InputTextMessageContent(item['preferred_common_name'])
        )
        for item in response['results']
    ]
    context.bot.answer_inline_query(update.inline_query.id, answers)


def error(update, context):
    logger.warning(f'Update {update} caused error {context.error}')


if __name__ == '__main__':
    TOKEN = getenv('TOKEN')
    NAME = getenv('NAME')
    PORT = getenv('PORT')

    basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=INFO)
    logger = getLogger(__name__)

    updater = Updater(TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(InlineQueryHandler(inline_search))
    dp.add_error_handler(error)

    updater.start_webhook(listen='0.0.0.0', port=int(PORT), url_path=TOKEN)
    updater.bot.setWebhook('https://{}.herokuapp.com/{}'.format(NAME, TOKEN))
    updater.idle()
