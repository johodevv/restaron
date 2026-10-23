import logging
import re


class RedactTokenFilter(logging.Filter):
    def filter(self, record):
        record.msg = re.sub(r'(token=)[^&\s\"\']+', r'\1[redacted]', record.getMessage())
        record.args = ()
        return True


def install_token_redaction():
    for name in ('uvicorn.error', 'uvicorn.access'):
        logger = logging.getLogger(name)
        if not any(isinstance(f, RedactTokenFilter) for f in logger.filters):
            logger.addFilter(RedactTokenFilter())
