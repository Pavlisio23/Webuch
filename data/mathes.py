import datetime
import sqlalchemy
from .db_session import SqlAlchemyBase
from sqlalchemy_serializer import SerializerMixin


class Match(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'matches'
    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    team1 = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    team2 = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    map = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    category = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    date = sqlalchemy.Column(sqlalchemy.DateTime,
                                      default=datetime.datetime.now)
    event = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    country = sqlalchemy.Column(sqlalchemy.String, nullable=True)
