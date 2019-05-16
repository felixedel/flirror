from flask import render_template


def make_error_handler(template="error.html"):
    def _handler(e):
        return (
            render_template(template, error_code=e.code, error_message=e.description),
            e.code,
        )

    return _handler
