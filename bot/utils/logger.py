import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s.%(funcName)s:%(lineno)d - %(message)s'
)

logger = logging.getLogger(__name__)

logger.cstm_lvl = {
    "start_": 31,
    "consent_": 32,
    "subscribe_": 33,
    "check_": 34,
    "apply_": 35,
    "ask_": 36,
    "broadcast_": 37
}

logging.getLogger('aiogram.event').setLevel(logging.CRITICAL + 1)
