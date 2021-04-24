import sqlalchemy
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Binary, Time, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

Base = declarative_base()

session = None

class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True)
    clan = Column(Integer, ForeignKey("clans.id"))
    username = Column(String, unique=True)
    password = Column(String)

class Clan(Base):
    __tablename__ = "clans"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    level = Column(Integer)

class Bag(Base):
    __tablename__ = "bags"
    id = Column(Integer, primary_key=True)
    clan = Column(Integer, ForeignKey("clans.id"))

class BagItem(Base):
    __tablename__ = "bagitems"
    id = Column(Integer, primary_key=True)
    bag = Column(Integer, ForeignKey("bags.id"))
    item = Column(Binary)

class Objective(Base):
    __tablename__ = "objectives"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    literal = Column(String)
    score = Column(Integer)
    decay_rate = Column(Integer)

class Reward(Base):
    __tablename__ = "rewards"
    id = Column(Integer, primary_key=True)
    player = Column(Integer, ForeignKey("players.id"))
    objective = Column(Integer, ForeignKey("objectives.id"))
    score = Column(Integer)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

# create table objectives(
# 	id int not null auto_increment,
# 	name varchar(32) not null,
# 	literal varchar(32) not null,
# 	score int,
# 	decrease_rate boolean,
# 	added timestamp,
# 	primary key(id));



def add_clan(name):
    c = Clan(name=name)
    session.add(c)
    session.flush()
    b = Bag(clan=c.id)
    session.add(b)
    session.flush()
    return c.id


def open_db():
    global session
    engine = create_engine('postgresql://postgres:vinst@localhost/nh', echo=True)

    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    session.flush()

def init_db():
    cid = add_clan("vinst")
    p = Player(username="hej", password="sko", clan=cid)
    session.add(p)
    session.commit()

    session.add(Objective(
        name="killed_gridbug", 
        literal="Killed gridbug",
        score=10
        ))
    session.add(Objective(
        name="killed_medusa", 
        literal="Killed Medusa",
        score=100
        ))
    session.commit()