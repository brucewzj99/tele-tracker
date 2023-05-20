import logging

def setup_logger():
    # Create a logger instance
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.WARNING)

    # Create a file handler
    file_handler = logging.FileHandler('app.log', mode='a')
    file_handler.setLevel(logging.WARNING)

    # Create a formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Set the formatter for the handlers
    file_handler.setFormatter(formatter)

    # Add the handlers to the logger
    logger.addHandler(file_handler)
    return logger