def validate_chats(allowed_ips):
    def wrapper(func):
        def inner(*args, **kwargs):
            if args[0].chat.id in allowed_ips:
                return func(*args, **kwargs)
            else:
                pass

        return inner

    return wrapper
