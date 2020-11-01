from logging import basicConfig, getLogger, INFO, Logger
from os import getenv
from typing import Callable, List
from pyinaturalist.node_api import get_taxa, get_taxa_by_id
from telegram import InlineQueryResult, InlineQueryResultArticle, InputTextMessageContent, Update
from telegram.ext import Updater, CommandHandler, InlineQueryHandler, CallbackContext, ChosenInlineResultHandler


def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    text = 'Hello World!'
    context.bot.send_message(chat_id=chat_id, text=text)


def inline_search(update: Update, context: CallbackContext):
    logger.info(f'inline_search - {update}')
    query = update.inline_query.query
    if not query:
        return
    def results(page: int) -> Callable[[int], List[InlineQueryResult]]:
        response = get_taxa(q=query, page=str(page + 1), per_page=10)
        results = response['results']
        if results:
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
        return None
    update.inline_query.answer(results, auto_pagination=True, cache_time=1)


def chosen_inline(update: Update, context: CallbackContext):
    logger.info(f'chosen_inline - {update}')
    identifier = update.chosen_inline_result.result_id
    if not identifier:
        logger.warning('identifier is None')
        return
    response = get_taxa_by_id(taxon_id=identifier)
    results = response.get('results')
    if not results:
        logger.warning('results is None')
        return
    item = results[0]
    name = item.get('name')
    rank = item.get('rank')
    photo = item['default_photo'].get('url') if 'default_photo' in item else None
    if name:
        context.bot.send_message(chat_id=update.effective_chat.id, text=name)
    else:
        logger.warning('name is None')
    if rank:
        context.bot.send_message(chat_id=update.effective_chat.id, text=rank)
    else:
        logger.warning('rank is None')
    if photo:
        context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo)
    else:
        logger.warning('photo is None')


# def error(update: Update, context: CallbackContext):
#     logger.warning(f'Update {update} caused error {context.error}')


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
    dp.add_handler(ChosenInlineResultHandler(chosen_inline))
    # dp.add_error_handler(error)

    updater.start_webhook(listen='0.0.0.0', port=int(PORT), url_path=TOKEN)
    updater.bot.setWebhook('https://{}.herokuapp.com/{}'.format(NAME, TOKEN))
    updater.idle()
