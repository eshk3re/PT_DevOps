import logging
import re
import psycopg2
import paramiko
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackContext, CallbackQueryHandler
from dotenv import load_dotenv
import os
import subprocess

load_dotenv()

RM_HOST = os.getenv("RM_HOST")
PORT = int(os.getenv("RM_PORT"))
USER = os.getenv("RM_USER")
PASSWORD = os.getenv("RM_PASSWORD")

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DATABASE = os.getenv("DB_DATABASE")
DB_PORT = os.getenv("DB_PORT")

TOKEN = str(os.getenv("TOKEN"))

logging.basicConfig(
    filename='logfile.txt', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

def normalize_phone_number(number):
    number = re.sub(r'[^\d]', '', number)
    if number.startswith('7'):
        number = '8' + number[1:]
    return number

def is_valid_number_sequence(text):
    return not re.search(r'\d{11,}', text)

def start(update: Update, context: CallbackContext):
    user = update.effective_user
    update.message.reply_text(f'Привет {user.full_name}!')


def helpCommand(update: Update, context: CallbackContext):
    update.message.reply_text('Help!')


def findPhoneNumbersCommand(update: Update, context: CallbackContext):
    update.message.reply_text('Введите текст для поиска телефонных номеров: ')
    return 'find_phone_number'


def findPhoneNumbers (update: Update, context: CallbackContext):
    user_input = update.message.text 
  
    phoneNumRegex = re.compile(r'(?<!\d)(?:\+7|8)[ -]?\(?\d{3}\)?[ -]?\d{3}[ -]?\d{2}[ -]?\d{2}(?!\d)')
    raw_phone_numbers = phoneNumRegex.findall(user_input)
    normalized_phone_numbers = {normalize_phone_number(num) for num in raw_phone_numbers}

    if not normalized_phone_numbers: 
        update.message.reply_text('Телефонные номера не найдены')
        return ConversationHandler.END 

    phone_numbers = '\n'.join([f'{i+1}. {num}' for i, num in enumerate(normalized_phone_numbers)])
    context.user_data['phone_numbers'] = list(normalized_phone_numbers)
    update.message.reply_text(f'Найденные номера телефонов:\n{phone_numbers}\nСохранить в базу данных? (да/нет)')
    return 'confirm_savephone'
    
def save_phone_numbers(update: Update, context: CallbackContext):
    if update.message.text.lower() == 'да':
        phone_numbers = context.user_data.get('phone_numbers', [])
        save_result = save_to_db('phone_numbers', phone_numbers)
        if save_result:
            update.message.reply_text('Номера телефонов успешно сохранены')
        else:
            update.message.reply_text('Ошибка при сохранении номеров телефонов')
    else:
        update.message.reply_text('Сохранение номеров телефонов отменено')
    return ConversationHandler.END

def findEmailCommand(update: Update, context: CallbackContext):
    update.message.reply_text('Введите текст для поиска email-адресов: ')
    return 'find_email'


def findEmail(update: Update, context: CallbackContext):
    user_input = update.message.text
    email_regex = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    email_list = email_regex.findall(user_input)
    if not email_list:
        update.message.reply_text('Email-адреса не найдены')
        return ConversationHandler.END
    emails = '\n'.join([f'{i+1}. {email}' for i, email in enumerate(email_list)])
    context.user_data['emails'] = email_list
    update.message.reply_text(f'Найденные email-адреса:\n{emails}\nСохранить в базу данных? (да/нет)')
    return 'confirm_saveemail'

def save_emails(update: Update, context: CallbackContext):
    if update.message.text.lower() == 'да':
        emails = context.user_data.get('emails', [])
        save_result = save_to_db('emails', emails)
        if save_result:
            update.message.reply_text('Email-адреса успешно сохранены')
        else:
            update.message.reply_text('Ошибка при сохранении email-адресов')
    else:
        update.message.reply_text('Сохранение email-адресов отменено')
    return ConversationHandler.END

def save_to_db(table, data):
    try:
        conn = psycopg2.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
            host=DB_HOST,
            database=DATABASE
        )
        cursor = conn.cursor()
        if table == 'phone_numbers':
            for number in data:
                cursor.execute("INSERT INTO phone_numbers (phone_number) VALUES (%s);", (number,))
        elif table == 'emails':
            for email in data:
                cursor.execute("INSERT INTO emails (email) VALUES (%s);", (email,))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error saving to db: {e}")
        return False


def verifyPasswordCommand(update: Update, context: CallbackContext):
    update.message.reply_text('Введите текст для проверки пароля: ')
    return 'verify_password'


def verifyPassword(update: Update, context: CallbackContext):
    user_input = update.message.text
    password_regex = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()])[A-Za-z\d!@#$%^&*()]{8,}$')
    if password_regex.match(user_input):
        update.message.reply_text('Пароль сложный')
    else:
        update.message.reply_text('Пароль простой')
    return ConversationHandler.END 


def execute_command_ssh(command):
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect(hostname=RM_HOST, port=PORT, username=USER, password=PASSWORD)
    stdin, stdout, stderr = ssh_client.exec_command(command)
    output = stdout.read().decode("utf-8")
    ssh_client.close()
    return output

def execute_sql_query(query):
    try:
        conn = psycopg2.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            database=DATABASE
        )
        cursor = conn.cursor()
        cursor.execute(query)
        result = cursor.fetchall()
        cursor.close()
        conn.close()
        return result
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        return None

def get_release(update: Update, context):
    release_info = execute_command_ssh("lsb_release -a")
    update.message.reply_text(release_info)


def get_uname(update: Update, context):
    uname_info = execute_command_ssh("uname -a")
    update.message.reply_text(uname_info)


def echo(update: Update, context):
    update.message.reply_text(update.message.text)


def get_uptime(update: Update, context):
    uptime_info = execute_command_ssh("uptime")
    update.message.reply_text(uptime_info)


def get_df(update: Update, context):
    df_info = execute_command_ssh("df -h")
    update.message.reply_text(df_info)


def get_free(update: Update, context):
    free_info = execute_command_ssh("free -m")
    update.message.reply_text(free_info)


def get_mpstat(update: Update, context):
    mpstat_info = execute_command_ssh("mpstat")
    update.message.reply_text(mpstat_info)


def get_w(update: Update, context):
    w_info = execute_command_ssh("w")
    update.message.reply_text(w_info)


def get_auths(update: Update, context):
    #auths_info = execute_command_ssh("tail /var/log/auth.log")
    auths_info = execute_command_ssh("last | head -n 10")
    update.message.reply_text(auths_info)


def get_critical(update: Update, context):
    critical_info = execute_command_ssh("journalctl -p crit -n 5")
    update.message.reply_text(critical_info)


def get_ps(update: Update, context):
    ps_info = execute_command_ssh("ps aux")
    ps_info_cut = ps_info[:4096]
    update.message.reply_text(ps_info_cut)


def get_ss(update: Update, context):
    ss_info = execute_command_ssh("ss -tuln")
    update.message.reply_text(ss_info)


def get_apt_list_command(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("Все пакеты", callback_data='all_packages')],
        [InlineKeyboardButton("Определённый пакет", callback_data='specific_package')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Выберите опцию:', reply_markup=reply_markup)
    return 'apt_list_option'


def get_apt_list_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    if query.data == 'all_packages':
        apt_list = execute_command_ssh("apt list --installed")
        apt_list_cut = apt_list[:4096]
        query.edit_message_text(apt_list_cut if apt_list else "Не удалось получить список установленных пакетов.")
        return ConversationHandler.END
    elif query.data == 'specific_package':
        query.edit_message_text('Введите название пакета:')
        return 'apt_list_package_name'
    
    
def get_apt_list_package_name(update: Update, context: CallbackContext):
    package_name = update.message.text
    apt_info = execute_command_ssh(f"apt-cache show {package_name}")
    apt_info_cut = apt_info[:4096]
    update.message.reply_text(apt_info_cut if apt_info else f"Пакет '{package_name}' не найден.")
    return ConversationHandler.END


def get_services(update: Update, context):
    services_info = execute_command_ssh("service --status-all")
    update.message.reply_text(services_info)

def get_repl_logs(update: Update, context):
    repl_logs_info = execute_ssh_command("sudo cat /var/log/postgresql/postgresql-14-main.log | grep repl")
    update.message.reply_text(repl_logs_info[:4090])


def get_emails(update: Update, context):
    emails = execute_sql_query("SELECT * FROM emails;")
    if emails:
        emails_str = '\n'.join(['. '.join(map(str, email)) for email in emails])
        update.message.reply_text(emails_str)
    else:
        update.message.reply_text('Не удалось получить email-адреса из базы данных (Таблица пустая).')

def get_phone_numbers(update: Update, context):
    phone_numbers = execute_sql_query("SELECT * FROM phone_numbers;")
    if phone_numbers:
        phone_numbers_str = '\n'.join(['. '.join(map(str, number)) for number in phone_numbers])
        update.message.reply_text(phone_numbers_str)
    else:
        update.message.reply_text('Не удалось получить номера телефонов из базы данных (Таблица пустая).')


def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    convHandlerGetAptList = ConversationHandler(
    entry_points=[CommandHandler('get_apt_list', get_apt_list_command)],
    states={
        'apt_list_option': [CallbackQueryHandler(get_apt_list_callback)],
        'apt_list_package_name': [MessageHandler(Filters.text & ~Filters.command, get_apt_list_package_name)],
    },
    fallbacks=[]
)

    convHandlerFindPhoneNumbers = ConversationHandler(
        entry_points=[CommandHandler('find_phone_number', findPhoneNumbersCommand)],
        states={
            'find_phone_number': [MessageHandler(Filters.text & ~Filters.command, findPhoneNumbers)],
            'confirm_savephone': [MessageHandler(Filters.text & ~Filters.command, save_phone_numbers)],
        },
        fallbacks=[]
    )

    convHandlerFindEmail = ConversationHandler(
        entry_points=[CommandHandler('find_email', findEmailCommand)],
        states={
            'find_email': [MessageHandler(Filters.text & ~Filters.command, findEmail)],
            'confirm_saveemail': [MessageHandler(Filters.text & ~Filters.command, save_emails)],
        },
        fallbacks=[]
    )

    convHandlerVerifyPassword = ConversationHandler(
        entry_points=[CommandHandler('verify_password', verifyPasswordCommand)],
        states={
            'verify_password': [MessageHandler(Filters.text & ~Filters.command, verifyPassword)],
        },
        fallbacks=[]
    )

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", helpCommand))
    dp.add_handler(convHandlerFindPhoneNumbers)
    dp.add_handler(convHandlerFindEmail)
    dp.add_handler(convHandlerVerifyPassword)

    dp.add_handler(CommandHandler("get_release", get_release))
    dp.add_handler(CommandHandler("get_uname", get_uname))
    dp.add_handler(CommandHandler("get_uptime", get_uptime))
    dp.add_handler(CommandHandler("get_df", get_df))
    dp.add_handler(CommandHandler("get_free", get_free))
    dp.add_handler(CommandHandler("get_mpstat", get_mpstat))
    dp.add_handler(CommandHandler("get_w", get_w))
    dp.add_handler(CommandHandler("get_auths", get_auths))
    dp.add_handler(CommandHandler("get_critical", get_critical))
    dp.add_handler(CommandHandler("get_ps", get_ps))
    dp.add_handler(CommandHandler("get_ss", get_ss))
    dp.add_handler(CommandHandler("get_services", get_services))
    dp.add_handler(CommandHandler("get_repl_logs", get_repl_logs))
    dp.add_handler(CommandHandler("get_emails", get_emails))
    dp.add_handler(CommandHandler("get_phone_numbers", get_phone_numbers))

    dp.add_handler(convHandlerGetAptList)
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
