import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from flask import g

from config.settings import settings
from data.database import Base
from api import create_app

USE_SQLITE = os.getenv("USE_SQLITE", "0") == "1"

@pytest.fixture(scope="session")
def engine():
    db_url = "sqlite:///:memory:" if USE_SQLITE else settings.DATABASE_URL
    connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
    return create_engine(db_url, connect_args=connect_args)

@pytest.fixture(scope="session")
def tables(engine):
    Base.metadata.create_all(bind=engine)
    yield
    # Keep schema intact in PostgreSQL session

@pytest.fixture
def db_session(engine, tables):
    """Returns a sqlalchemy session, rolling back after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def app(db_session):
    """Create and configure a new app instance for each test."""
    app = create_app()
    app.config.update({
        "TESTING": True,
    })
    
    # Override the before_request to use our test db_session
    @app.before_request
    def override_db():
        g.db = db_session
        
    yield app

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()
