from logging import basicConfig, getLogger, INFO
from os import getenv
from typing import Callable, List
from pyinaturalist.node_api import get_taxa
from telegram import InlineQueryResult, InlineQueryResultArticle, InputTextMessageContent, Update
from telegram.ext import Updater, CommandHandler, InlineQueryHandler, MessageHandler, Filters, CallbackContext


def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    text = 'Hello World!'
    context.bot.send_message(chat_id=chat_id, text=text)


def get_inline_callable_results(query: str, per_page: int = 5) -> Callable[[int], List[InlineQueryResult]]:
    def result(page: int) -> List[InlineQueryResult]:
        response = get_taxa(q=query, page=page+1, per_page=per_page)
        results = response['results']
        answers = [
            InlineQueryResultArticle(
                id=item['id'],
                title=item['name'],
                input_message_content=InputTextMessageContent(item['name'].title()),
                description=item['rank'].title(),
                thumb_url=item['default_photo']['url'] if 'default_photo' in item else None
            )
            for item in results
        ]
        return answers if answers else None
    return result


def inline_search(update: Update, context: CallbackContext):
    query = update.inline_query.query
    if not query:
        return
    context.bot.answer_inline_query(
        update.inline_query.id,
        get_inline_callable_results(query),
        auto_pagination=True,
        # current_offset=update.inline_query.offset,
        # next_offset=update.inline_query.offset + 1,
    )


def error(update: Update, context: CallbackContext):
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
