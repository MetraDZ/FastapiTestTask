from sqlalchemy import DateTime, ForeignKey, String, Table, create_engine, Column, Integer, func
from sqlalchemy.orm import relationship, sessionmaker, declarative_base

SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:root@172.17.0.2:3306/TestTaskDB" # TODO Insert url here <username>:<password>@<host>:<port>/<db_name>

engine = create_engine(SQLALCHEMY_DATABASE_URL)
Session = sessionmaker(bind=engine, autoflush=False)
Base = declarative_base()


user_post_likes_association = Table(
    'user_post_likes',
    Base.metadata,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('user.id')),
    Column('post_id', Integer, ForeignKey('post.id')),
    Column('date', DateTime(timezone=True), nullable=False, server_default=func.now())
)


class BaseWithJson(Base):
    __abstract__ = True

    def to_dict(self):
        return {field.name:getattr(self, field.name) for field in self.__table__.c if field.name != 'hashed_password'}


class User(BaseWithJson):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    username = Column(String(60), nullable=False)
    hashed_password = Column(String(60), nullable=False)
    email = Column(String(30), nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_request = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    likes = relationship('Post', secondary=user_post_likes_association, back_populates='liked_by')


class Post(BaseWithJson):
    __tablename__ = 'post'

    id = Column(Integer, primary_key=True)
    text = Column(String(255), nullable=False)
    number_of_likes = Column(Integer, nullable=False, server_default='0')
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by = Column(Integer, ForeignKey('user.id'), nullable=False)
    liked_by = relationship('User', secondary=user_post_likes_association, back_populates='likes')


Base.metadata.create_all(engine)