import logging

log = logging.getLogger(__name__)


def validate_chats(allowed_ips):
    def wrapper(func):
        def inner(*args, **kwargs):
            if args[0].chat.id in allowed_ips:
                return func(*args, **kwargs)
            else:
                chat = args[0].chat
                info = {
                    "id": chat.id,
                    "firstname": chat.first_name,
                    "secondname": chat.last_name,
                    "chat": str(chat),
                }
                log.warning("Get unallowed request from: %s", info)

        return inner

    return wrapper
