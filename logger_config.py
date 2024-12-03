import logging

def configure_logger(app):
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)

    app.logger.addHandler(console_handler)
    app.logger.setLevel(logging.DEBUG)

