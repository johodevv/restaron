import logging

from uvicorn.logging import AccessFormatter
from app.core.logging import RedactTokenFilter


def test_access_formatter_keeps_positional_arguments_and_redacts_request_token():
    record = logging.LogRecord('uvicorn.access', logging.INFO, '', 0,
        '%s - "%s %s HTTP/%s" %d',
        ('127.0.0.1:1234', 'GET', '/api/v1/ws/1?token=secret&table_id=2', '1.1', 200), None)
    assert RedactTokenFilter().filter(record)
    output = AccessFormatter('%(client_addr)s %(request_line)s %(status_code)s', use_colors=False).format(record)
    assert 'secret' not in output
    assert 'token=[redacted]&table_id=2' in output
    assert '200' in output and len(record.args) == 5


def test_error_messages_and_mapping_arguments_still_redact_tokens():
    records = [
        logging.LogRecord('uvicorn.error', logging.INFO, '', 0, 'socket token=secret', (), None),
        logging.LogRecord('uvicorn.error', logging.INFO, '', 0, 'request %(url)s',
            ({'url': '/ws?token=other-secret&x=1'},), None),
        logging.LogRecord('uvicorn.error', logging.INFO, '', 0, 'socket token=%s', ('secret',), None),
    ]
    for record in records:
        assert RedactTokenFilter().filter(record)
        output = logging.Formatter('%(message)s').format(record)
        assert 'secret' not in output and '[redacted]' in output
