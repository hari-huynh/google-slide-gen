from googleapiclient.errors import HttpError

def call_api_decorator(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except HttpError as e:
            print(e)

    return wrapper