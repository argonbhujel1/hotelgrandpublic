import os
from app import create_app, db
from app.models import *  # noqa: F401, F403

app = create_app()


@app.cli.command("init-db")
def init_db():
    """Create tables and seed demo public data (safe for local/dev)."""
    db.create_all()
    from seed import seed_demo
    seed_demo()
    print("Database initialized and seeded.")


@app.cli.command("create-tables")
def create_tables():
    """Create all tables on Aiven/Postgres without seeding."""
    db.create_all()
    print("Tables created.")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        if os.environ.get("SEED_DEMO", "1") == "1" and not os.environ.get("DATABASE_URL", "").startswith("postgres"):
            try:
                from seed import seed_demo
                seed_demo()
            except Exception as e:
                print(f"Seed note: {e}")
    port = int(os.environ.get("PORT", 8080))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(debug=debug, host="0.0.0.0", port=port)
