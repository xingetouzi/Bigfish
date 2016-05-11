import logging

logger = logging.getLogger("Backtesting.Singal")

def init():
    pass


def handle():
    if BarNum == 1:
        logger.info("李杀神 at bar:%s" % BarNum)
        return
    logger.info("老子赵日天来了 at bar:%s t:%s" % (BarNum, Datetime[0]))