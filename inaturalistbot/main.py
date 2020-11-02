from logging import basicConfig, getLogger, INFO
from os import getenv
from typing import Callable, List, Optional
from pydantic import BaseModel
from pyinaturalist.node_api import get_taxa, get_taxa_by_id
from pymongo import MongoClient
from telegram import (
    InlineQueryResult,
    InlineQueryResultArticle,
    InputTextMessageContent,
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    Updater,
    CommandHandler,
    InlineQueryHandler,
    CallbackContext,
    CallbackQueryHandler,
)


global logger
global db

class User(BaseModel):
    id: int
    is_bot: bool
    first_name: str
    last_name: str
    username: Optional[str] = None
    language_code: Optional[str] = None
    can_join_groups: Optional[bool] = None
    can_read_all_group_messages: Optional[bool] = None
    supports_inline_queries: Optional[bool] = None

    class Config:
        orm_mode = True


class Log(BaseModel):
    method: str
    user: User


def start_help(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    text = 'To search a taxon use the inline mode, for this enter @inaturalistbot followed by the search and you will see the list of results for that search.'
    context.bot.send_message(chat_id=chat_id, text=text)


def inline_search(update: Update, context: CallbackContext):
    logger.info(f'Inline Search: {update}')

    # Loggin to Database
    user = update.inline_query.from_user
    user_model = User.from_orm(user)
    log = Log(method='inline_search', user=user_model)
    db.logs.insert_one(log.dict())

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
                    input_message_content=InputTextMessageContent(
                        f'*{item["name"].title()}*',
                        parse_mode='MarkdownV2'
                    ),
                    description=item['rank'].title(),
                    thumb_url=item['default_photo']['url'] if 'default_photo' in item else None,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text='See more', callback_data=item['id'])]])
                )
                for item in results
            ]
            return answers if answers else None
        return None
    update.inline_query.answer(results, auto_pagination=True, cache_time=1)


def callback_query(update: Update, context: CallbackContext):
    logger.info(f'Callback Query: {update}')
    
    # Loggin to Database
    user = update.callback_query.from_user
    user_model = User.from_orm(user)
    log = Log(method='callback_query', user=user_model)
    db.logs.insert_one(log.dict())

    query = update.callback_query
    if not query or not query.data:
        logger.warning('query or query.data is None')
        return
    identifier = query.data
    response = get_taxa_by_id(taxon_id=identifier)
    results = response.get('results')
    if not results:
        logger.warning('results is None')
        return
    item = results[0]
    name = item.get('name')
    rank = item.get('rank')
    photo_url = item['default_photo'].get('url') if 'default_photo' in item else None
    wikipedia_url = item.get('wikipedia_url')
    wikipedia_summary = item.get('wikipedia_summary')
    if name:
        text = f'<strong>{name}</strong>\n\n'
        if rank:
            text += f'<strong>Rank:</strong> {rank}\n\n'
        if wikipedia_summary:
            text += f'{wikipedia_summary}\n\n'
        if photo_url:
            text += f'Photo: <a href="{photo_url}">Link</a>\n'
        if wikipedia_url:
            text += f'Wikipedia: <a href="{wikipedia_url}">Link</a>'
        query.edit_message_text(text=text, parse_mode='HTML')


def error(update: Update, context: CallbackContext):
    logger.error(f'Update {update} caused error {context.error}')


if __name__ == '__main__':
    TOKEN = getenv('TOKEN')
    NAME = getenv('NAME')
    PORT = getenv('PORT')

    basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=INFO)
    logger = getLogger(__name__)

    client = MongoClient(getenv('DATABASE'))
    db = client[getenv('NAME')]

    updater = Updater(TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', start_help))
    dp.add_handler(CommandHandler('help', start_help))
    dp.add_handler(InlineQueryHandler(inline_search))
    dp.add_handler(CallbackQueryHandler(callback_query))
    # dp.add_error_handler(error)

    updater.start_webhook(listen='0.0.0.0', port=int(PORT), url_path=TOKEN)
    updater.bot.setWebhook('https://{}.herokuapp.com/{}'.format(NAME, TOKEN))
    updater.idle()
