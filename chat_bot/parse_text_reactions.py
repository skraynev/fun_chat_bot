import random

banned_words = [
    "бля",
    "сука",
    "пиздец",
]


def find_answer_on_text_msg(msg, owner):
    if any(banned_word in msg for banned_word in banned_words):
        return "Желтую карточку тебе!!!"
    if "чернобыль" in msg:
        return "Все норм у нас..."


lar_words = [
    "Искренние маршруты каждый день!",
    "Хочу бегать на улице",
    "А давайте в Героев",
    "Прям ностальгия...",
    "Нет времени - проект делаю",
    "Тимич, что скажешь об этом?",
    "Главное: чтобы душа - в душу",
]

too_much_lar = [
    "Хорош баловаться!",
    "Это попахивает желтой карточкой!",
]


def on_lar_command(count):
    count += 1
    answer = ""
    if count > 5:
        count = 0
        answer = random.choice(too_much_lar)
    else:
        answer = random.choice(lar_words)
    return count, answer
