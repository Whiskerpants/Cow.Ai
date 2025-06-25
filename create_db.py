from app import app, db  # Change 'app' if your main file has a different name

with app.app_context():
    db.create_all()
    print("All database tables created!")