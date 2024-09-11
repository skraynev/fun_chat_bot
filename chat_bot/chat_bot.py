import logging
import os
import time

import eki_game
import telebot
from dotenv import load_dotenv
from parse_text_reactions import find_answer_on_text_msg, on_lar_command
from utils import validate_chats

logging.basicConfig(filename="bot.log", level=logging.INFO)

log = logging.getLogger(__name__)

load_dotenv()
token = os.environ.get("TELE_TOKEN")
log.info("Get token")
if not token:
    print("TELE_TOKEN env variable should be specified")
    exit(1)

log.info("Get allowed chats")
allowed_chats = set(map(int, os.environ.get("ALLOWED_CHATS", "").split(",")))

bot = telebot.TeleBot(token)


help_msg_main = (
    "Что я умею: \n"
    "- supported commands: /help, /lar \n"
    "- реагировать на сообщения с опреленными словами \n"
    "- показывать желтую карточку в некоторых случаях \n"
)

count_lar = 0
eki_games = {}
admin_ids = []

game_cls = eki_game.EkiGame()


@bot.message_handler(commands=["help"])
@validate_chats(allowed_chats)
def help_message(message):
    bot.send_message(message.chat.id, help_msg_main)


@bot.message_handler(commands=["lar"])
@validate_chats(allowed_chats)
def emulate_lar(message):
    global count_lar
    count_lar, answer = on_lar_command(count_lar)
    bot.send_message(message.chat.id, answer)


def game_is_run(message):
    chat_id = message.chat.id
    if chat_id not in eki_games:
        bot.send_message(chat_id, "Нет запущенной игры")
        return False
    return chat_id


def is_admin(message):
    if message.from_user.id not in admin_ids:
        chat_id = message.chat.id
        bot.send_message(chat_id, "У вас нет прав для этой команды!")
        return False
    return True


help_msg_game = """
Игра создана!

ВАЖНО:
- Для корректной работы необходимо один раз отправить сообщение любого
  содержания боту: @%s
- Для начала хода необходимо минимум 2-е участников
- Для начисления очков администратором укажите username в настройках аккаунта

Используя команды ниже, присоединяйтесь и играйте.
- Присоединится к игре, нажмите - /join
- Покинуть игру, нажмите - /drop_me
- Показать список игроков и результаты, нажмите - /top
- Показать, кто ходит следующий и какое задание - /whoisnext
- Получить задание текущему игроку и запустить таймер задания - /go

Только для администратора игры:
- Создание игры - /game
- Добавить очко игроку - /add_point
- Отнять очко игроку - /remove_point
- Пропустить текущий ход и перeйти к следующему игроку, нажмите - /cancel
- Засчитать вопрос отгаданным - /win
- Завершить игру и вывести результат, нажмите - /exit
"""


@bot.message_handler(commands=["game_help"])
@validate_chats(allowed_chats)
def help_eki_game(message):
    bot.send_message(message.chat.id, help_msg_game % bot.get_me().username)


@bot.message_handler(commands=["game"])
@validate_chats(allowed_chats)
def create_eki_game(message):
    if not is_admin(message):
        return
    global eki_games
    chat_id = message.chat.id
    if chat_id in eki_games:
        bot.send_message(chat_id, "Игра уже запущена")
        return
    game_cls = eki_game.EkiGame()
    eki_games = {chat_id: game_cls}
    bot.send_message(chat_id, help_msg_game % bot.get_me().username)


@bot.message_handler(commands=["join"])
@validate_chats(allowed_chats)
def join_to_game(message):
    chat_id = game_is_run(message)
    if not chat_id:
        return
    game_cls = eki_games[chat_id]
    user = message.from_user
    bot.send_message(
        chat_id, game_cls.add_player(user.id, user.username, user.first_name)
    )
    try:
        bot.send_message(
            user.id,
            (
                "Вы присоединились к игре. В этот чат будут "
                "присылаться слова для заданий."
            ),
        )
        if 1 < len(game_cls.players) < 3:
            run_msg = (
                "Когда игрок будет готов получите задание выполнив команду - " "/go"
            )
            bot.send_message(
                chat_id,
                "%s\n\n%s" % (game_cls.next_turn, run_msg),
                parse_mode="Markdown",
            )
    except telebot.apihelper.ApiException as exc:
        json_res = exc.result.json()
        if (
            json_res["error_code"] == 403
            and json_res["description"]
            == "Forbidden: bot can't initiate conversation with a user"
        ):
            bot.send_message(
                chat_id,
                (
                    "Отправьте любое сообщение боту @%s. "
                    "Затем выполните /drop_me и /join команды."
                )
                % bot.get_me().username,
            )
        else:
            bot.send_message(chat_id, "SERVER TELEGRAM ERROR: %s" % json_res)


@bot.message_handler(commands=["drop_me"])
@validate_chats(allowed_chats)
def leave_game(message):
    chat_id = game_is_run(message)
    if not chat_id:
        return
    game_cls = eki_games[chat_id]
    bot.send_message(
        chat_id, game_cls.del_player(message.from_user.id), parse_mode="Markdown"
    )


@bot.message_handler(commands=["top"])
@validate_chats(allowed_chats)
def show_top(message):
    chat_id = game_is_run(message)
    if not chat_id:
        return
    game_cls = eki_games[chat_id]
    bot.send_message(chat_id, game_cls.show_top)


@bot.message_handler(commands=["go"])
@validate_chats(allowed_chats)
def send_question(message):
    chat_id = game_is_run(message)
    if not chat_id:
        return
    game_cls = eki_games[chat_id]
    if len(game_cls.players) < 2:
        bot.send_message(
            chat_id,
            "Недостаточно игроков для игры. Минимально разрешенное количество - 2.",
        )
        return

    err_msg, player_id, word, task_time = game_cls.get_task()

    if err_msg is None:
        try:
            bot.send_message(player_id, word)
            bot.send_message(
                chat_id, "Задание отправлено игроку: %s" % game_cls.context["player"]
            )
        except Exception as exc:
            bot.send_message(chat_id, "Sheet happens: %s" % str(exc))
            ret_status, msg = game_cls.cancel_question()
            bot.send_message(chat_id, msg)
            if ret_status:
                run_msg = (
                    "Когда игрок будет готов получите задание выполнив команду - /go"
                )
                bot.send_message(
                    chat_id,
                    "%s\n\n%s" % (game_cls.next_turn, run_msg),
                    parse_mode="Markdown",
                )
            return
    else:
        bot.send_message(chat_id, err_msg)
        return
    # ЗАПУСТИТЬ ТАЙМЕР!!!!
    bot.send_message(
        chat_id, "Таймер запущен!\nПри победе нажмите /win\nДля пропуска - /cancel"
    )
    for _ in range(10 * task_time):
        time.sleep(0.1)
        # check, may be it was skipped manually
        if game_cls.status == eki_game.WAIT_START:
            bot.send_message(chat_id, "Таймер сброшен.")
            break
    else:
        # ОКОНЧАНИЕ таймера и вопроса
        bot.send_message(chat_id, "Время вышло. %s" % game_cls.cancel_question()[1])
        run_msg = "Когда игрок будет готов получите задание выполнив команду - /go"
        bot.send_message(
            chat_id, "%s\n\n%s" % (game_cls.next_turn, run_msg), parse_mode="Markdown"
        )


@bot.message_handler(commands=["whoisnext"])
@validate_chats(allowed_chats)
def who_is_next(message):
    chat_id = game_is_run(message)
    if not chat_id:
        return
    game_cls = eki_games[chat_id]
    run_msg = (
        "Когда игрок будет готов запустите таймер и получите задание выполнив "
        "команду - /go"
    )
    bot.send_message(
        chat_id, "%s\n\n%s" % (game_cls.current_turn, run_msg), parse_mode="Markdown"
    )


@bot.message_handler(commands=["cancel"])
@validate_chats(allowed_chats)
def cancel_question(message):
    chat_id = game_is_run(message)
    if not chat_id:
        return
    game_cls = eki_games[chat_id]
    if not is_admin(message) or message.from_user.id != game_cls.context["player_id"]:
        return
    ret_status, msg = game_cls.cancel_question()
    bot.send_message(chat_id, msg)
    if ret_status:
        run_msg = "Когда игрок будет готов получите задание выполнив команду - /go"
        bot.send_message(
            chat_id, "%s\n\n%s" % (game_cls.next_turn, run_msg), parse_mode="Markdown"
        )


@bot.message_handler(commands=["win"])
@validate_chats(allowed_chats)
def win_question(message):
    chat_id = game_is_run(message)
    if not chat_id:
        return
    game_cls = eki_games[chat_id]
    if not is_admin(message) or message.from_user.id != game_cls.context["player_id"]:
        return
    bot.send_message(chat_id, game_cls.question_is_answered())
    run_msg = "Когда игрок будет готов получите задание выполнив команду - /go"
    bot.send_message(
        chat_id, "%s\n\n%s" % (game_cls.next_turn, run_msg), parse_mode="Markdown"
    )


@bot.message_handler(commands=["exit"])
@validate_chats(allowed_chats)
def del_eki_game(message):
    chat_id = game_is_run(message)
    if not chat_id:
        return
    if not is_admin(message):
        return
    game_cls = eki_games.pop(chat_id, None)
    bot.send_message(chat_id, "Игра Закончена! \n%s" % game_cls.show_top)
    del game_cls


@bot.message_handler(commands=["add_point"])
@validate_chats(allowed_chats)
def add_point(message):
    chat_id = game_is_run(message)
    if not chat_id:
        return
    if not is_admin(message):
        return

    game_cls = eki_games[chat_id]
    command_and_username = message.text.split("@")
    if len(command_and_username) != 2:
        bot.send_message(chat_id, "Не указан username игрока")
        return
    username = command_and_username[1]
    result = game_cls.add_point(username, by_username=True)
    if result:
        bot.send_message(chat_id, "%s" % game_cls.show_top)
    else:
        bot.send_message(chat_id, "Не удалось найти игрока с таким username")


@bot.message_handler(commands=["remove_point"])
@validate_chats(allowed_chats)
def remove_point(message):
    chat_id = game_is_run(message)
    if not chat_id:
        return
    if not is_admin(message):
        return

    game_cls = eki_games[chat_id]
    command_and_username = message.text.split("@")
    if len(command_and_username) != 2:
        bot.send_message(chat_id, "Не указан username игрока")
        return
    username = command_and_username[1]
    result = game_cls.remove_point(username, by_username=True)
    if result:
        bot.send_message(chat_id, "%s" % game_cls.show_top)
    else:
        bot.send_message(chat_id, "Не удалось найти игрока с таким username")


# @bot.message_handler(commands=['admin'])
# def show_top(message):
#    chat_id = game_is_run(message)
#    if not chat_id:
#        return
#    if not is_admin(message):
#        return
#    global admin_ids
#    admin_ids.append()
#    bot.send_message(chat_id, game_cls.show_top)


@bot.message_handler(content_types=["text"])
@validate_chats(allowed_chats)
def send_text(message):
    chat_id = message.chat.id
    msg_text = message.text.lower()

    if chat_id in eki_games:
        pass
        # TODO: add parsing of answers
        # game_cls = eki_games[chat_id]
        # if game_cls.status == eki_game.IN_PROGRESS:
        #    game_cls.parse_answer(msg_text)
    else:
        answer = find_answer_on_text_msg(msg_text, message.from_user.username)
        if answer:
            bot.send_message(chat_id, answer)


if __name__ == "__main__":
    log.info("Running polling")
    bot.infinity_polling()
    log.info("Poll is in progress")

# TODO:
# - доп задание - слова
# - доп темы
# - добавить командную игру
