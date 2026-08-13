from app import create_app

app = create_app()

with app.app_context():
    from app.utils.helpers import init_default_settings
    init_default_settings()


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000, use_reloader=False)