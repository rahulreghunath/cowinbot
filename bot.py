import logging
import requests
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
from dotenv import load_dotenv
import os

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

load_dotenv('.env')

logger = logging.getLogger(__name__)
API_KEY = os.getenv('API_KEY')

GENDER, PHOTO, LOCATION, BIO, SELECT_TYPE, PIN, DISTRICT_RESULT, PIN_RESULT, RESTART, DATE_INPUT, PIN_INPUT = range(11)
user_district = None
user_pin = None
user_date = None


def get_data(selected_district=None, date=None, pin=None):
    if selected_district:
        url = f'https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/findByDistrict?district_id={selected_district["district_id"]}&date={date}'
    else:
        url = f'https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/findByPin?pincode={pin}&date={date}'
    headers = {
        'Accept-Language': 'IN',
        'Accept': 'application/json',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36',
    }
    print(url)
    data = requests.get(
        url,
        headers=headers)
    if data.status_code == 200:
        results = data.json()['sessions']
        message = ''
        if len(results):
            for result in results:
                if result['available_capacity'] > 0:
                    message += f"<strong>{result['name']} - {result['address']}</strong>\n" \
                               f"Vaccine: <strong>{result['vaccine']}</strong>\n" \
                               f"Availability\n" \
                               f"First Dose: {result['available_capacity_dose1']}\n" \
                               f"Second Dose: {result['available_capacity_dose2']}\n" \
                               f"------------\n"
        if message == '':
            message = None
        else:
            message = f'<b>{date}</b>\n \n' + message
    else:
        message = 'All servers are busy, please try after some time'
    return message


def start(update: Update, _: CallbackContext) -> int:
    reply_keyboard = [['District', 'Pin']]
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text(
        'Hi! My name is CowinSlot Bot. Lets find a slot. '
        'Select an option',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
    )

    return SELECT_TYPE


def date_input_dialogue(update: Update, _: CallbackContext) -> int:
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
            )
            return DISTRICT_RESULT
        else:
            update.message.reply_text(
                'Check and re enter district name',
            )
            return DATE_INPUT


def pin_input(update: Update, _: CallbackContext) -> int:
    global user_pin
    user_pin = update.message.text
    if len(user_pin) == 6:
        update.message.reply_text(
            'Enter Date (DD/MM/YYYY)',
        )
        return PIN_RESULT
    else:
        update.message.reply_text(
            'Check the pin and re enter',
        )
        return PIN_INPUT


def district_pin_dialogue(update: Update, _: CallbackContext) -> int:
    if update.message.text.upper() == 'DISTRICT':
        update.message.reply_text(
            'Enter your district',
            reply_markup=ReplyKeyboardRemove(),
        )
        return DATE_INPUT
    elif update.message.text.upper() == 'PIN':
        update.message.reply_text(
            'Enter Pin Code',
            reply_markup=ReplyKeyboardRemove(),
        )
        return PIN_INPUT
    elif update.message.text.upper() == 'NEW DATE':
        update.message.reply_text(
            'Enter Date (DD/MM/YYYY)',
        )
        if bool(user_district):
            return DISTRICT_RESULT
        else:
            return PIN_RESULT


def district_result(update: Update, _: CallbackContext) -> int:
    reply_keyboard = [['District', 'Pin', 'New Date', '/stop']]
    global user_date
    user_date = update.message.text
    message = get_data(selected_district=user_district[0], date=update.message.text)
    update.message.reply_text(
        message if message is not None else 'No slot available in ' + user_district[0][
            'district_name'] + ' on ' + user_date,
        parse_mode=ParseMode.HTML,
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
    )
    return SELECT_TYPE


def pin_result(update: Update, _: CallbackContext) -> int:
    reply_keyboard = [['District', 'Pin', 'New Date', '/stop']]
    global user_date
    user_date = update.message.text
    message = get_data(date=update.message.text, pin=user_pin)
    update.message.reply_text(
        message if message is not None else 'No slot available in ' + user_pin + ' on ' + user_date,
        parse_mode=ParseMode.HTML,
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
    )
    return SELECT_TYPE


def cancel(update: Update, _: CallbackContext) -> int:
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text(
        'Bye! I hope we can talk again some day.', reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


def main() -> None:
    # Create the Updater and pass it your bot's token.
    updater = Updater(API_KEY)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Add conversation handler with the states GENDER, PHOTO, LOCATION and BIO
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SELECT_TYPE: [MessageHandler(Filters.regex('^(District|Pin|New Date)$'), district_pin_dialogue)],
            DATE_INPUT: [MessageHandler(Filters.regex('^[a-zA-Z ]+$'), date_input_dialogue)],
            PIN_INPUT: [MessageHandler(Filters.regex('^[0-9]+$'), pin_input)],
            DISTRICT_RESULT: [MessageHandler(Filters.regex(
                '^(0[1-9]|[12][0-9]|3[01])[- /.](0[1-9]|1[012])[- /.]((19|20)\\d\\d)$'),
                district_result)],
            PIN_RESULT: [MessageHandler(Filters.regex(
                '^(0[1-9]|[12][0-9]|3[01])[- /.](0[1-9]|1[012])[- /.]((19|20)\\d\\d)$'),
                pin_result)],
        },
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
