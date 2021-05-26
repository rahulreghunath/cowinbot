import os
import logging
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update, ParseMode
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext, CallbackQueryHandler,
)
from districts import districts
import constants

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Loading env file
load_dotenv('.env')

API_KEY = os.getenv('API_KEY')

GENDER, PHOTO, LOCATION, BIO, SELECT_TYPE, PIN, DISTRICT_RESULT, PIN_RESULT, RESTART, DATE_INPUT, PIN_INPUT = range(11)
user_district = []
user_pin = ''
user_date = ''

dates = [
    [datetime.now().strftime('%d/%m/%Y'), (datetime.now() + timedelta(days=1)).strftime('%d/%m/%Y')],
    [(datetime.now() + timedelta(days=2)).strftime('%d/%m/%Y'),
     (datetime.now() + timedelta(days=3)).strftime('%d/%m/%Y')],
    [(datetime.now() + timedelta(days=4)).strftime('%d/%m/%Y'),
     (datetime.now() + timedelta(days=5)).strftime('%d/%m/%Y')]
]


def get_data(selected_district=None, date=None, pin=None):
    messages = []

    if selected_district:
        url = constants.FIND_BY_DIST.format(selected_district["district_id"], date)
    else:
        url = constants.FIND_BY_PIN.format(pin, date)

    headers = {
        'Accept-Language': 'IN',
        'Accept': 'application/json',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36',
    }
    # Getting data
    data = requests.get(
        url,
        headers=headers
    )
    if data.status_code == 200:
        results = data.json()['sessions']
        message = ''
        if len(results):
            number = 1
            for result in results:
                if result['available_capacity'] > 0:
                    text = f"{number}) <strong>{result['name']}</strong> \nAddress: <strong>{result['address']}</strong>\n" \
                           f"Block: <strong>{result['block_name']}</strong> | Pin: {result['pincode']}\n" \
                           f"Open from <strong>{result['from']} to {result['to']}</strong>\n" \
                           f"Vaccine: <strong>{result['vaccine']}</strong>\n" \
                           f"\n<strong>Availability</strong>\n" \
                           f"First Dose: {result['available_capacity_dose1']}\n" \
                           f"Second Dose: {result['available_capacity_dose2']}\n" \
                           f"<a href='https://www.google.com/maps/search/?api=1&query={result['lat']},{result['long']}'>Click to get directions</a> \n" \
                           f"------------------------\n"

                    if len(message + text) < 4096:
                        message += text
                    else:
                        messages.append(message)
                        message = ''
                    number += 1
            if message:
                messages.append(message)

    return data.status_code, messages


# Conversation Start
def start(update: Update, _: CallbackContext) -> int:
    reply_keyboard = [['District', 'Pin']]
    if os.getenv('API_KEY') == 'production':
        requests.get('https://api.countapi.xyz/hit/namespace/rahulreghunathmannady')
    user = update.message.from_user
    logger.info("User %s Started the conversation.", user.first_name)
    update.message.reply_text(
        'Hi☺️ \nMy name is CowinSlot Bot. Lets find a slot for vaccination.\n'
        'Type /stop anytime to end conversation',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
    )

    return SELECT_TYPE


def date_input_dialogue(update: Update, _: CallbackContext) -> int:
    """
    Read the district if success ask for date
    """
    if update.message.text.isnumeric():
        global user_pin
        user_pin = update.message.text
        return PIN_RESULT
    else:
        global user_district
        user_district = list(filter(lambda el: el['district_name'].upper() == update.message.text.upper(), districts))
        if len(user_district):
            update.message.reply_text(
                'Enter Date (DD/MM/YYYY)',
                reply_markup=ReplyKeyboardMarkup(dates, one_time_keyboard=True),
            )
            return DISTRICT_RESULT
        else:
            update.message.reply_text(
                'Check and re enter district name',
            )
            return DATE_INPUT


def pin_input(update: Update, _: CallbackContext) -> int:
    """
    Read the pin code and if success ask for date
    """
    global user_pin
    user_pin = update.message.text
    if len(user_pin) == 6:
        update.message.reply_text(
            'Enter Date (DD/MM/YYYY)',
            reply_markup=ReplyKeyboardMarkup(dates, one_time_keyboard=True),
        )
        return PIN_RESULT
    else:
        update.message.reply_text(
            'Check the pin and re enter',
        )
        return PIN_INPUT


def district_pin_dialogue(update: Update, _: CallbackContext) -> int:
    """
    Select the input option
    """
    if update.message.text.upper() in ['DISTRICT', '/DISTRICT']:
        update.message.reply_text(
            'Enter your district',
            reply_markup=ReplyKeyboardRemove(),
        )
        return DATE_INPUT
    elif update.message.text.upper() in ['PIN', '/PIN']:
        update.message.reply_text(
            'Enter Pin Code',
            reply_markup=ReplyKeyboardRemove(),
        )
        return PIN_INPUT
    elif update.message.text.upper() in ['NEW DATE', '/PIN']:
        update.message.reply_text(
            'Enter Date (DD/MM/YYYY)',
        )
        if bool(user_district):
            return DISTRICT_RESULT
        else:
            return PIN_RESULT


def district_result(update: Update, _: CallbackContext) -> int:
    """
    Send result message from a specific district
    """
    reply_keyboard = [['District', 'Pin'], ['New Date', '/stop']]
    global user_date
    user_date = update.message.text
    status, messages = get_data(selected_district=user_district[0], date=update.message.text)
    if status == 200 and len(messages):
        for message in messages:
            update.message.reply_text(
                f'<b>{user_date}</b>\n\n{message}',
                parse_mode=ParseMode.HTML,
                reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
            )
    elif status != 200:
        update.message.reply_text(
            constants.SERVER_ERROR,
            parse_mode=ParseMode.HTML,
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
        )
    elif not len(messages):
        update.message.reply_text(
            'No slot available in ' + user_district[0][
                'district_name'] + ' on ' + user_date + '😢',
            parse_mode=ParseMode.HTML,
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
        )
    update.message.reply_text(
        '/district     /pin     /newdate     /restart',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
    )
    return SELECT_TYPE


def pin_result(update: Update, _: CallbackContext) -> int:
    """
    Send result message from a specific pin code
    """
    reply_keyboard = [['District', 'Pin'], ['New Date', '/stop']]
    global user_date
    user_date = update.message.text
    status, messages = get_data(date=update.message.text, pin=user_pin)

    if status == 200 and len(messages):
        for message in messages:
            update.message.reply_text(
                f'<b>{user_date}</b>\n\n{message}',
                parse_mode=ParseMode.HTML,
                reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
            )
    elif status != 200:
        update.message.reply_text(
            constants.SERVER_ERROR,
            parse_mode=ParseMode.HTML,
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
        )
    elif not len(messages):
        update.message.reply_text(
            'No slot available in ' + user_pin + ' on ' + user_date + '😢',
            parse_mode=ParseMode.HTML,
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
        )
    update.message.reply_text(
        '/district     /pin     /newdate     /restart',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
    )
    return SELECT_TYPE


def cancel(update: Update, _: CallbackContext) -> int:
    """
    End the conversation
    """
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text(
        'Bye! I hope we can talk again some day. Stay safe 😁', reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


def main() -> None:
    # Create the Updater and pass it your bot's token.
    updater = Updater(API_KEY)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Add conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start), CommandHandler('restart', start)],
        states={
            SELECT_TYPE: [MessageHandler(
                Filters.regex('^(District|Pin|New Date|/district|/pin|/newdate)$'),
                district_pin_dialogue
            )],
            DATE_INPUT: [MessageHandler(Filters.regex('^[a-zA-Z ]+$'), date_input_dialogue)],
            PIN_INPUT: [MessageHandler(Filters.regex('^[0-9]+$'), pin_input)],
            DISTRICT_RESULT: [MessageHandler(Filters.regex(
                '^(0[1-9]|[12][0-9]|3[01])[- /.](0[1-9]|1[012])[- /.]((19|20)\\d\\d)$'),
                district_result)],
            PIN_RESULT: [MessageHandler(Filters.regex(
                '^(0[1-9]|[12][0-9]|3[01])[- /.](0[1-9]|1[012])[- /.]((19|20)\\d\\d)$'),
                pin_result)],
        },
        allow_reentry=True,
        fallbacks=[CommandHandler('stop', cancel)],
    )

    dispatcher.add_handler(conv_handler)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
