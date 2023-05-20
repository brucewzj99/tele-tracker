import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
import bot.firebase as db
import bot.google_sheet as gs
from bot.common import EntryType
import re
import pytz
import datetime as dt
import bot.logger as lg
from warnings import filterwarnings
from telegram.warnings import PTBUserWarning

filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)

BOT_TOKEN = os.getenv("TRACKER_TELEGRAM_TOKEN")
GOOGLE_API_EMAIL = os.getenv("GOOGLE_API_EMAIL")
logger = lg.setup_logger()

# Local Timezone
timezone = pytz.timezone('Asia/Singapore')

# States
SET_UP, RESET_UP, CONFIG__HANDLER, START_DESTINATION, ENTRY, PRICE, REMARKS, CATEGORY, SUBCATEGORY, PAYMENT, SUBPAYMENT, QUICK_ADD, CONFIG_SETUP, CONFIG_CATEGORY, CONFIG_SUBCATEGORY, CONFIG_PAYMENT, CONFIG_SUBPAYMENT = range(17)

# Create inline markup based on list of strings
def create_inline_markup(list):
    keyboard_markup_list = []
    for reply in list:
        keyboard_markup_list.append([InlineKeyboardButton(reply, callback_data=reply)])
    
    return InlineKeyboardMarkup(keyboard_markup_list)

# Check price is valid
def is_valid_price(price):
    # the regex pattern
    pattern = r"^\d{0,10}(\.\d{0,2})?$"
    return bool(re.match(pattern, price))

# Set up text
async def setup_text():
    text = ('Please set up your Google sheet by following the steps below.\n\n'+
            '1. Go over to https://docs.google.com/spreadsheets/d/1dJgJk7YUoR0nYjNa_lgrMxpz-MehOo4SyfRitlasQo8/\n'+
            '2. Go to File > Make a copy\n'+
            '3. Go to File > Share > Share with others\n'+
            '4. Add '+str(GOOGLE_API_EMAIL)+' as an editor\n'+
            '5. Copy your Google Sheet URL and send it over\n'+
            'Example: https://docs.google.com/spreadsheets/d/abcd1234/edit\n'+
            '6. Edit the Dropdown sheet accordingly\n')
    return text

# Send category text
async def get_category_text(sheet_id,entry_type):
    msg = ""
    markup_list = []
    if entry_type == EntryType.TRANSPORT:
        msg = "What type of transport is this?"
        markup_list = gs.get_main_dropdown_value(sheet_id, EntryType.TRANSPORT)
    elif entry_type == EntryType.OTHERS:
        msg = "What category is this?"
        markup_list = gs.get_main_dropdown_value(sheet_id, EntryType.OTHERS)
    return msg, markup_list
    
async def get_payment_text(sheet_id):
    payment_list = gs.get_main_dropdown_value(sheet_id, "Payment")
    return payment_list

# Start bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    telegram_id = update.effective_user.id
    try:
        user_exists = db.check_if_user_exists(telegram_id)
        if user_exists:
            context.user_data["sheet_id"]=db.get_user_sheet_id(telegram_id)
            link = f"https://docs.google.com/spreadsheets/d/{context.user_data['sheet_id']}/edit"
            await update.message.reply_text(f"Seems like you have already linked a Google sheet with us, do you want to link a different Google sheet with us?\n\n{link}", reply_markup=create_inline_markup(["Yes", "No"]))
            return RESET_UP
        else:
            await update.message.reply_text(await setup_text())
            return SET_UP
    except Exception as e:
            logger.error(f'function start:{e}')
            print(e)
            await update.message.reply_text('There seems to be an error, please try again later.')
            return ConversationHandler.END

# Set up google sheet ID
async def set_up(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    telegram_id = update.effective_user.id
    url = update.message.text
    
    pattern = r"/d/([a-zA-Z0-9-_]+)"
    match = re.search(pattern, url)
    if match:
        sheet_id = match.group(1)
        try:
            db.new_user_setup(telegram_id, sheet_id)    
            current_datetime = dt.datetime.now(timezone)
            day = current_datetime.day
            gs.update_rows(sheet_id, day, 4, 5) #New users start from row 5
            await update.message.reply_text('Google sheet successfully linked!')
            return ConversationHandler.END
        except Exception as e:
            logger.error(f'function set_up:{e}')
            print(e)
            await update.message.reply_text('There seems to be an error linking your google sheet, please try again later.')
            return ConversationHandler.END
    else:
        await update.message.reply_text('That doesn\'t seem like a Google sheet link, are you sure? Try sending again.')
        return SET_UP

# Reset up google sheet ID
async def reset_up(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply = update.callback_query.data
    await update.callback_query.answer()
    if reply == "Yes":
        await update.callback_query.message.reply_text(await setup_text())
        return SET_UP
    else:
        await update.callback_query.edit_message_text('Okay, no worries!', reply_markup=None)
        return ConversationHandler.END

# Configuration
async def config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    telegram_id = update.effective_user.id
    context.user_data["sheet_id"]=db.get_user_sheet_id(telegram_id)
    list = ["Change Google Sheet", "Configure Quick Transport", "Configure Quick Others", "Cancel"]
    await update.message.reply_text("How can i help you today?", reply_markup=create_inline_markup(list))
    return CONFIG__HANDLER

# Configuration handler
async def config_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply = update.callback_query.data
    await update.callback_query.answer()
    if reply == "Cancel":
        await update.callback_query.edit_message_text('Okay!', reply_markup=None)
        return ConversationHandler.END
    
    await update.callback_query.edit_message_text(reply, reply_markup=None)
    if reply == "Change Google Sheet":
        await update.callback_query.message.reply_text(await setup_text())
        return SET_UP
    else:
        try:
            context.user_data['config'] = EntryType.OTHERS
            if reply == "Configure Quick Transport":
                context.user_data['config'] = EntryType.TRANSPORT
            msg = f'This is your current {context.user_data["config"].value} settings.\n'
            # Retrieve current settings
            setting_list = gs.get_quick_add_settings(context.user_data['sheet_id'], context.user_data['config'])
            if setting_list == None:
                msg = f'{msg}Default Payment: None\nDefault Type: None\n'
            else:
                msg = f'{msg}Default Payment: {setting_list[0]}\nDefault Type: {setting_list[1]}\n'
            msg = f'{msg}Do you want to update it?'
            await update.callback_query.message.reply_text(msg, reply_markup=create_inline_markup(["Yes", "No"]))
            return CONFIG_SETUP
        except Exception as e:
            logger.error(f'function config_handler:{e}')
            await update.callback_query.message.reply_text('There seems to be an error setting your configuration, please try again later.')
            return ConversationHandler.END


# Quick add set up
async def config_setup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply = update.callback_query.data
    await update.callback_query.answer()
    config = context.user_data['config']
    try:
        if reply == "Yes":
            markup_list = gs.get_main_dropdown_value(context.user_data["sheet_id"], config)
            await update.callback_query.message.edit_text(f'Choose your default {config.value} type.', reply_markup=create_inline_markup(markup_list))
            return CONFIG_CATEGORY
    except Exception as e:
        logger.error(f'function config_setup:{e}')
        await update.callback_query.message.reply_text("Something seems to be a problem, please try again later.")
        return ConversationHandler.END
    await update.callback_query.edit_message_text('Okay, no worries!', reply_markup=None)
    return ConversationHandler.END

# Quick category setup
async def config_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply = update.callback_query.data
    await update.callback_query.answer()
    config = context.user_data['config']
    context.user_data['config-category'] = reply
    try:
        sheet_id = context.user_data["sheet_id"]
        await update.callback_query.answer()
        if config == EntryType.TRANSPORT:
            await update.callback_query.edit_message_text(f'Default transport type: {reply}', reply_markup=None)
            payment_list = gs.get_main_dropdown_value(sheet_id, "Payment")
            
            await update.callback_query.message.reply_text('What is your default mode of payment?', reply_markup=create_inline_markup(payment_list))
            return CONFIG_PAYMENT
        elif config == EntryType.OTHERS:
            sub_markup_list = gs.get_sub_dropdown_value(sheet_id, reply, config)
            if len(sub_markup_list) > 1:
                sub_markup_list.pop(0)
                msg = "What subcategory is this?"
                await update.callback_query.message.edit_text(msg, reply_markup=create_inline_markup(sub_markup_list))
                return CONFIG_SUBCATEGORY
    except Exception as e:
        logger.error(f'function config_category:{e}')
        await update.callback_query.reply_text("Something seems to be a problem, please try again later.")
        return ConversationHandler.END

# Quick subcategory setup
async def config_subcategory(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply = update.callback_query.data
    context.user_data['config-category'] = f'{context.user_data["config-category"]} - {reply}'
    try:
        sheet_id = context.user_data["sheet_id"]
        payment_list = gs.get_main_dropdown_value(sheet_id, "Payment")
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(f'Default category type: {context.user_data["config-category"]}', reply_markup=None)
        await update.callback_query.message.reply_text('What is your default mode of payment?', reply_markup=create_inline_markup(payment_list))
        return CONFIG_PAYMENT
    except Exception as e:
        logger.error(f'function config_subcategory:{e}')
        await update.callback_query.message.reply_text("Something seems to be a problem, please try again later.")
        return ConversationHandler.END

# Quick payment setup
async def config_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply = update.callback_query.data
    try:
        sheet_id = context.user_data["sheet_id"]
        await update.callback_query.answer()
        context.user_data['config-payment'] = reply
        sub_markup_list = gs.get_sub_dropdown_value(sheet_id, reply, "Payment")
        if len(sub_markup_list) > 1:
            sub_markup_list.pop(0)
            msg = "What is your default mode of payment?"
            await update.callback_query.message.edit_text(msg, reply_markup=create_inline_markup(sub_markup_list))
            return CONFIG_SUBPAYMENT
    except Exception as e:
        logger.error(f'function config_payment:{e}')
        await update.callback_query.message.reply_text("Something seems to be a problem, please try again later.")
        return ConversationHandler.END

# Get subpayment
async def config_subpayment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply = update.callback_query.data
    context.user_data['config-payment'] = f'{context.user_data["config-payment"]} - {reply}'
    try:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(f'Payment type: {context.user_data["config-payment"]}', reply_markup=None)
        gs.update_quick_add_settings(context.user_data['sheet_id'], context.user_data['config'], context.user_data['config-payment'], context.user_data['config-category'])
        await update.callback_query.message.reply_text(f'Default {context.user_data["config"].value} settings updated.')
        return ConversationHandler.END
    except Exception as e:
        logger.error(f'function config_payment:{e}')
        await update.callback_query.message.reply_text("Something seems to be a problem, please try again later.")
        return ConversationHandler.END

# Add new entry
async def add_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    telegram_id = update.effective_user.id
    context.user_data["sheet_id"]=db.get_user_sheet_id(telegram_id)
    await update.message.reply_text("What type of entry is this?", reply_markup=create_inline_markup([entry_type.value for entry_type in EntryType]))
    return ENTRY

# Get entry
async def entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply = update.callback_query.data
    context.user_data['entry_type'] = EntryType[reply.upper()]
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(f'Entry type: {reply}', reply_markup=None)
    await update.callback_query.message.reply_text("How much is the price? e.g. 1.50")
    return PRICE

# Get price
async def price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply = update.message.text
    if is_valid_price(reply):
        context.user_data['price'] = reply
        entry_type = context.user_data['entry_type']
        if entry_type == EntryType.TRANSPORT:
            await update.message.reply_text('Please enter the start and end destination seperated by comma.\ne.g. Home, School')
        elif entry_type == EntryType.OTHERS:
            await update.message.reply_text('Please enter the remarks.\ne.g. Bought a new shirt')
        return REMARKS
    else:
        await update.message.reply_text('Please enter a valid price.')
        return PRICE

# Get remarks
async def remarks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply = update.message.text
    context.user_data['remarks'] = reply
    entry_type = context.user_data['entry_type']        
    sheet_id = context.user_data["sheet_id"]

    #Check if is there is only one comma for start and end destination
    if entry_type == EntryType.TRANSPORT:
        if reply.count(',') != 1:
            await update.message.reply_text('Please enter the start and end destination seperated by comma.\ne.g. Home, School')
            return REMARKS

    msg, markup_list = await get_category_text(sheet_id, entry_type)
    try:        
        await update.message.reply_text(msg, reply_markup=create_inline_markup(markup_list))
        return CATEGORY
    except Exception as e:
        logger.error(f'function remarks:{e}')
        await update.message.reply_text("Something seems to be a problem, please try again later.")
        return ConversationHandler.END

# Get category, check if have sub
async def category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply = update.callback_query.data
    entry_type = context.user_data['entry_type']
    try:
        sheet_id = context.user_data["sheet_id"]
        await update.callback_query.answer()
        if entry_type == EntryType.TRANSPORT:
            await update.callback_query.edit_message_text(f'Transport type: {reply}', reply_markup=None)
            context.user_data['category'] = f'{reply}'
            payment_list = await get_payment_text(sheet_id)
            await update.callback_query.message.reply_text('What is your mode of payment?', reply_markup=create_inline_markup(payment_list))
            return PAYMENT
        elif entry_type == EntryType.OTHERS:
            context.user_data['category'] = reply
            sub_markup_list = gs.get_sub_dropdown_value(sheet_id, reply, entry_type)
            if len(sub_markup_list) > 1:
                sub_markup_list.pop(0)
                sub_markup_list.append(" << Back")
                msg = "What subcategory is this?"
                await update.callback_query.message.edit_text(msg, reply_markup=create_inline_markup(sub_markup_list))
                return SUBCATEGORY
            # This won't be called as there will always be a subcategory, but just in case
            else:
                await update.callback_query.edit_message_text(f'Category type: {reply}', reply_markup=None)
                return PAYMENT
    except Exception as e:
        logger.error(f'function category:{e}')
        await update.callback_query.reply_text("Something seems to be a problem, please try again later.")
        return ConversationHandler.END
        
# Get subcategory
async def subcategory(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply = update.callback_query.data
    sheet_id = context.user_data["sheet_id"]
    entry_type = context.user_data["entry_type"]
    await update.callback_query.answer()
    if reply == " << Back":
        msg, markup_list = await get_category_text(sheet_id, entry_type)
        await update.callback_query.edit_message_text(msg, reply_markup=create_inline_markup(markup_list))
        return CATEGORY
    try:
        context.user_data['category'] = f'{context.user_data["category"]} - {reply}'
        await update.callback_query.edit_message_text(f'Category type: {context.user_data["category"]}', reply_markup=None)
        payment_list = await get_payment_text(sheet_id)
        await update.callback_query.message.reply_text('What is your mode of payment?', reply_markup=create_inline_markup(payment_list))
        return PAYMENT
    except Exception as e:
        logger.error(f'function subcategory:{e}')
        await update.callback_query.message.reply_text("Something seems to be a problem, please try again later.")
        return ConversationHandler.END

# Get payment
async def payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply = update.callback_query.data
    try:
        sheet_id = context.user_data["sheet_id"]
        await update.callback_query.answer()
        context.user_data['payment'] = reply
        sub_markup_list = gs.get_sub_dropdown_value(sheet_id, reply, "Payment")
        if len(sub_markup_list) > 1:
            sub_markup_list.pop(0)
            sub_markup_list.append(" << Back")
            msg = "What is your mode of payment?"
            await update.callback_query.message.edit_text(msg, reply_markup=create_inline_markup(sub_markup_list))
            return SUBPAYMENT
    except Exception as e:
        logger.error(f'function payment:{e}')
        await update.callback_query.message.reply_text("Something seems to be a problem, please try again later.")
        return ConversationHandler.END

# Get subpayment
async def subpayment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply = update.callback_query.data
    await update.callback_query.answer()
    sheet_id = context.user_data["sheet_id"]
    if reply == " << Back":
        payment_list = await get_payment_text(sheet_id)
        await update.callback_query.edit_message_text('What is your mode of payment?', reply_markup=create_inline_markup(payment_list))
        return PAYMENT
    try:
        context.user_data['payment'] = f'{context.user_data["payment"]} - {reply}'
        await update.callback_query.edit_message_text(f'Payment type: {context.user_data["payment"]}', reply_markup=None)
        await log_transaction(context.user_data, update)
        await update.callback_query.message.reply_text("Transaction logged.")
        return ConversationHandler.END

    except Exception as e:
        logger.error(f'function subpayment:{e}')
        await update.callback_query.message.reply_text("Something seems to be a problem, please try again later.")
        return ConversationHandler.END
    
# logging transaction
async def log_transaction(user_data, update):
    sheet_id = user_data["sheet_id"]
    trackers = gs.get_trackers(sheet_id)

    # datatime data
    current_datetime = dt.datetime.now(timezone)
    day = current_datetime.day
    month = current_datetime.strftime('%B')

    # tracker data
    day_tracker = int(trackers[0])
    other_row_tracker = int(trackers[1])
    transport_row_tracker = int(trackers[2])
    first_row = int(trackers[3])

    # user input data
    entry_type = user_data['entry_type']
    payment = user_data["payment"]
    price = user_data['price']
    category = user_data['category']
    remarks = user_data['remarks']
    row_data = [entry_type, price, remarks, category, payment]

    msg = ""

    # start new date if date elapsed
    if day_tracker < day or day == 1:
        msg = (f'New entry for {day} {month}')
        if day == 1:
            month = (current_datetime - dt.timedelta(days=1)).strftime("%B")
        # update prev day
        msg = f'{msg}\nCreating sum for day {day_tracker}'
        gs.update_prev_day(sheet_id, month, first_row)
        if day == 1:
            new_row = 5
            first_row = 6
            gs.update_rows(sheet_id, 1, new_row, first_row)
        else:
            new_row = gs.get_new_row(sheet_id, month)
            first_row = new_row + 1
            gs.update_rows(sheet_id, day, new_row, first_row) 
        if update.callback_query and update.callback_query.message:
            await update.callback_query.message.reply_text(msg)
        elif update.message:
            await update.message.reply_text(msg)

        transport_row_tracker = new_row
        first_row = new_row + 1
        other_row_tracker = new_row
        
        # enter date into cell
        gs.create_date(sheet_id, day, month, first_row)

    # update row + 1
    gs.row_incremental(sheet_id, entry_type)
    if entry_type == EntryType.TRANSPORT:
        transport_row_tracker += 1
    else:
        other_row_tracker += 1

    # create entry
    if entry_type == EntryType.TRANSPORT:
        gs.create_entry(sheet_id, month, transport_row_tracker, row_data)
    else:
        gs.create_entry(sheet_id, month, other_row_tracker, row_data)

# cancel
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Conversation cancelled. Good bye.', reply_markup=None)
    return ConversationHandler.END

# add transport quickly
async def add_transport(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    telegram_id = update.effective_user.id
    try:
        context.user_data["sheet_id"]=db.get_user_sheet_id(telegram_id)
        context.user_data['entry_type'] = EntryType.TRANSPORT
        setting_list = gs.get_quick_add_settings(context.user_data["sheet_id"], EntryType.TRANSPORT)
    except Exception as e:
        logger.error(f'function add_transport:{e}')
        await update.callback_query.message.reply_text("Can't seem to retrieve transport information, please try again later.")
        return ConversationHandler.END
    if setting_list is None or setting_list[0] is None:
        await update.message.reply_text('You have not set up your quick add settings for transport yet, please do so by typing /config')
        return ConversationHandler.END
    else:
        context.user_data['payment'] = setting_list[0]      
        context.user_data['category'] = setting_list[1]
        await update.message.reply_text(f'Quick Add Transport\nDefault Payment: {setting_list[0]}\nDefault Type: {setting_list[1]}'+
                                    '\n\nPlease enter as follow: [price],[start],[end]\n e.g. 2.11, Home, Work')
    return QUICK_ADD

# add others quickly
async def add_others(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    telegram_id = update.effective_user.id
    try:
        context.user_data["sheet_id"]=db.get_user_sheet_id(telegram_id)
        context.user_data['entry_type'] = EntryType.OTHERS
        setting_list = gs.get_quick_add_settings(context.user_data["sheet_id"], EntryType.OTHERS)
    except Exception as e:
        logger.error(f'function add_others:{e}')
        await update.callback_query.message.reply_text("Can't seem to retrieve others information, please try again later.")
        return ConversationHandler.END
    if setting_list is None or setting_list[0] is None:
        await update.message.reply_text('You have not set up your quick add settings for others yet, please do so by typing /config')
        return ConversationHandler.END
    else: 
        context.user_data['payment'] = setting_list[0]      
        context.user_data['category'] = setting_list[1]
        await update.message.reply_text(f'Quick Add Others\nDefault Payment: {setting_list[0]}\nDefault Type: {setting_list[1]}'+
                                    '\n\nPlease enter as follow: [price],[remarks]\n e.g. 19.99, New shirt')
    return QUICK_ADD

# add in entry
async def quick_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply = update.message.text
    try:
        context.user_data['price'], context.user_data['remarks'] = reply.split(",", 1)
        try:
            await log_transaction(context.user_data, update)
            await update.message.reply_text("Transaction logged.")
            return ConversationHandler.END
        except Exception as e:
            logger.error(f'function quick_add:{e}')
            await update.message.reply_text("Something seems to be a problem, please try again later.")
            return ConversationHandler.END
    except Exception as e:
        logger.error(f'function quick_add:{e}')
        await update.message.reply_text("Please follow the format and try again.")
        return QUICK_ADD

# help messaghe
async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = ("To get started, please type /start\n" + "Remember to configure your Dropdown sheet to get started on this bot.\n\n" + "To configure, type /config\n" + 
    "To add entry, type /addentry\n" + "To add transport quickly, type /addtransport\n" + "To add others quickly, type /addothers\n")
    await update.message.reply_text(msg)


def run_telegram_bot():
    print ("Starting telegram bot...")
    application = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start),
                      CommandHandler('config', config),
                      CommandHandler('addentry', add_entry),
                      CommandHandler('addtransport', add_transport),
                      CommandHandler('addothers', add_others)],
        
        states={
            SET_UP: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_up)],
            RESET_UP: [CallbackQueryHandler(reset_up)],
            # Config stuff
            CONFIG__HANDLER: [CallbackQueryHandler(config_handler),],
            CONFIG_SETUP: [CallbackQueryHandler(config_setup),],
            CONFIG_CATEGORY: [CallbackQueryHandler(config_category)],
            CONFIG_SUBCATEGORY: [CallbackQueryHandler(config_subcategory)],
            CONFIG_PAYMENT: [CallbackQueryHandler(config_payment)],
            CONFIG_SUBPAYMENT: [CallbackQueryHandler(config_subpayment)],
            # Add entry stuff
            ENTRY: [CallbackQueryHandler(entry)],
            PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, price)],
            REMARKS: [MessageHandler(filters.TEXT & ~filters.COMMAND, remarks)],
            CATEGORY: [CallbackQueryHandler(category)],
            SUBCATEGORY: [CallbackQueryHandler(subcategory)],
            PAYMENT: [CallbackQueryHandler(payment)],
            SUBPAYMENT: [CallbackQueryHandler(subpayment)],
            # Quick add stuff
            QUICK_ADD: [MessageHandler(filters.TEXT & ~filters.COMMAND, quick_add)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(conv_handler)

    help_handler = CommandHandler('help', help)
    application.add_handler(help_handler)

    # Run the bot until the user presses Ctrl-C
    application.run_polling()