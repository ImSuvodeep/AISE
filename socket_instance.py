from flask_socketio import SocketIO
from src.logger import Logger

socketio = SocketIO(cors_allowed_origins="*", async_mode="gevent")
logger = Logger()


def emit_agent(channel, content, log=True):
    """
    Emits a message to the specified channel using SocketIO.

    Args:
        channel (str): The name of the channel to emit the message to.
        content (dict): The content to be emitted.
        log (bool): Whether to log the emit action (default: True).

    Returns:
        bool: True if the message was emitted successfully, False otherwise.
    """
    try:
        socketio.emit(channel, content)
        if log:
            logger.info(f"SOCKET {channel} MESSAGE: {content}")
        return True
    except Exception as e:
        logger.error(f"Error emitting message on SOCKET {channel}: {e}")
        return False
