import sqlalchemy
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Binary, Time, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
import re

#HEJ
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
    name = Column(String, unique=True)
    level = Column(Integer)
    power_gems = Column(Integer, default=0)

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
    name = Column(String, unique=True)
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

class ClanPowers(Base):
    __tablename__ = "clan_powers"
    clan_id = Column(Integer, ForeignKey("clans.id"), primary_key=True)
    name = Column(String, primary_key=True)
    level = Column(Integer)

class PlayerEquipment(Base):
    __tablename__ = "player_equipment"
    player_id = Column(Integer, ForeignKey("players.id"), primary_key=True)
    slot = Column(Integer, primary_key=True)
    item = Column(Binary)

# HEEEEJ
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
    engine = create_engine('postgresql://postgres:vinst@localhost/nh') #, echo=True)

    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    session.flush()




old_rewards = """
insert into objectives values(0, 'reach_minetn',	"Reach Minetown",		1000, 5, NOW());
insert into objectives values(0, 'reach_soko4',		"Reach Sokoban",		 500, 5, NOW());
insert into objectives values(0, 'reach_minend',	"Reach Mines' end",		 500, 5, NOW());
insert into objectives values(0, 'reach_knox',		"Reach Ludios",			1000, 5, NOW());
insert into objectives values(0, 'reach_strt',		"Reach Quest",			1000, 5, NOW());
insert into objectives values(0, 'reach_medusa',	"Reach Medusa",			1000, 5, NOW());
insert into objectives values(0, 'reach_castle',	"Reach Castle",			1000, 5, NOW());
insert into objectives values(0, 'reach_juiblex',	"Reach Juiblex",		1000, 5, NOW());
insert into objectives values(0, 'reach_orcus',		"Reach Orcus",			1000, 5, NOW());
insert into objectives values(0, 'reach_tower1',	"Reach Vlad's Tower",	1000, 5, NOW());
insert into objectives values(0, 'reach_sanctum',	"Reach Sanctum",		1000, 5, NOW());
insert into objectives values(0, 'reach_earth',		"Reach Earth Plane",	1000, 5, NOW());
insert into objectives values(0, 'reach_air',		"Reach Air Plane",		1000, 5, NOW());
insert into objectives values(0, 'reach_fire',		"Reach Fire Plane",		1000, 5, NOW());
insert into objectives values(0, 'reach_water',		"Reach Water Plane",	1000, 5, NOW());
insert into objectives values(0, 'reach_astral',	"Reach Astral Plane",	1000, 5, NOW());
insert into objectives values(0, 'reach_vinst1',	"Reach Oracle Quest 1",	1000, 5, NOW());
insert into objectives values(0, 'reach_vinst2',	"Reach Oracle Quest 2",	1000, 5, NOW());
insert into objectives values(0, 'reach_vinst3',	"Reach Oracle Quest 3",	1000, 5, NOW());
insert into objectives values(0, 'complete_soko',	"Complete Sokoban",		1000, 5, NOW());
insert into objectives values(0, 'curse_clan',		"Curse another clan",     4000, 0, NOW());
insert into objectives values(0, 'curse_kill',		"Kill with curse",         250, 0, NOW());
insert into objectives values(0, 'team_send', "Warp an item", 100, 0, NOW());
insert into objectives values(0, 'kill_woodchuck',			"Kill a Woodchuck",				500,	5, NOW());
insert into objectives values(0, 'kill_gridbug',			"Kill a Grid bug",				500,	5, NOW());
insert into objectives values(0, 'kill_floatingeye',		"Kill a Floating Eye",			500,	5, NOW());
insert into objectives values(0, 'kill_littledog',			"Kill a Little Dog",			500,	5, NOW());
insert into objectives values(0, 'kill_gnomelord',			"Kill a Gnome Lord",			500,	5, NOW());
insert into objectives values(0, 'kill_smallmimic',			"Kill a Small Mimic",			500,	5, NOW());
insert into objectives values(0, 'kill_largemimic',			"Kill a Large Mimic",			500,	5, NOW());
insert into objectives values(0, 'kill_giantmimic',			"Kill a Giant Mimic",			500,	5, NOW());
insert into objectives values(0, 'kill_wererat',			"Kill a Wererat",				500,	5, NOW());
insert into objectives values(0, 'kill_soldierant',			"Kill a Soldier Ant",			500,	5, NOW());
insert into objectives values(0, 'kill_mumak',				"Kill a Mumak",					500,	5, NOW());
insert into objectives values(0, 'kill_cockatrice',			"Kill a Cockatrice",			1000,	5, NOW());
insert into objectives values(0, 'kill_warhorse',			"Kill a Warhorse",				1000,	5, NOW());
insert into objectives values(0, 'kill_blackdragon',		"Kill a Black Dragon",			1500,	5, NOW());
insert into objectives values(0, 'kill_mastermindflayer',	"Kill a Master Mind Flayer",	1500,	5, NOW());
insert into objectives values(0, 'kill_archlich',			"Kill an Archlich",				1500,	5, NOW());
insert into objectives values(0, 'kill_archon',				"Kill an Archon",				1500,	5, NOW());
insert into objectives values(0, 'kill_oracle',				"Kill the evil Oracle",			7500,	10, NOW());
insert into objectives values(0, 'kill_nem',		"Kill Nemesis",			1000, 5, NOW());
insert into objectives values(0, 'kill_medusa',		"Kill Medusa",			1000, 5, NOW());
insert into objectives values(0, 'kill_juiblex',	"Kill Juiblex",			1000, 5, NOW());
insert into objectives values(0, 'kill_orcus',		"Kill Orcus",			1000, 5, NOW());
insert into objectives values(0, 'kill_vlad',		"Kill Vlad",			1000, 5, NOW());
insert into objectives values(0, 'kill_wizard',		"Kill Wizard",			1000, 5, NOW());
insert into objectives values(0, 'kill_demogorgon', "Kill Demogorgon",		1000, 5, NOW());
insert into objectives values(0, 'reach_3',		"Reach dlvl 3",		500,	5, NOW());
insert into objectives values(0, 'reach_5',		"Reach dlvl 5",		500,	5, NOW());
insert into objectives values(0, 'reach_10',	"Reach dlvl 10",	500,	5, NOW());
insert into objectives values(0, 'reach_15',	"Reach dlvl 15",	500,	5, NOW());
insert into objectives values(0, 'reach_20',	"Reach dlvl 20",	500,	5, NOW());
insert into objectives values(0, 'reach_25',	"Reach dlvl 25",	500,	5, NOW());
insert into objectives values(0, 'reach_30',	"Reach dlvl 30",	500,	5, NOW());
insert into objectives values(0, 'reach_35',	"Reach dlvl 35",	500,	5, NOW());
insert into objectives values(0, 'reach_40',	"Reach dlvl 40",	500,	5, NOW());
insert into objectives values(0, 'reach_45',	"Reach dlvl 45",	500,	5, NOW());
insert into objectives values(0, 'reach_50',	"Reach dlvl 50",	500,	5, NOW());
insert into objectives values(0, 'level_5',		"Get xlvl 5",	500,	5, NOW());
insert into objectives values(0, 'level_10',	"Get xlvl 10",	1000,	5, NOW());
insert into objectives values(0, 'level_14',	"Get xlvl 14",	1000,	5, NOW());
insert into objectives values(0, 'level_20',	"Get xlvl 20",	1000,	5, NOW());
insert into objectives values(0, 'level_30',	"Get xlvl 30",	2000,	5, NOW());
insert into objectives values(0, 'get_aoy',			"Get Amulet of Yendor",	1000, 5, NOW());
insert into objectives values(0, 'ascend',			"Ascend",				20000, 5, NOW());

insert into objectives values(0, 'curse_ascend',	"Ascend with curse item", 2000, 0, NOW());
"""

def add_objective(name, literal, score):
    session.add(Objective(
        name=name,
        literal=literal,
        score=score
        ))
    session.commit()

def add_clan_power(clan_id, power, level):
    session.add(ClanPowers(
        clan_id=clan_id,
        name=power,
        level=level
    ))

def add_clan_power_for_player(player_id, name, level, cost):
    p = session.query(Player).filter_by(id=player_id).first()
    power = session.query(ClanPowers).filter_by(clan_id=p.clan, name=name).first()
    clan = session.query(Clan).filter_by(id=p.clan).first()
    if clan.power_gems >= cost:
        clan.power_gems -= cost
        if power is None:
            add_clan_power(p.clan, name, level)
        else:
            power.level = level

    session.commit()
    return power.level

def get_power_gems_for_player(player_id):
    p = session.query(Player).filter_by(id=player_id).first()
    clan = session.query(Clan).filter_by(id=p.clan).first()
    return clan.power_gems

def get_clan_powers_for_player(player_id):
    p = session.query(Player).filter_by(id=player_id).first()
    powers = session.query(ClanPowers).filter_by(clan_id=p.clan)
    ret = dict()
    for power in powers:
       ret[power.name] = power.level
    return ret

def login(username, password):
    player = session.query(Player).filter_by(username=username).first()
    if player is None:
        return dict(logged_in=False, status="Username doesn't exist")
    if player.password != password:
        return dict(logged_in=False, status=f"Wrong password! Your password is {player.password}")
    return dict(logged_in=True, status="Success", player_id=player.id)


def insert_rewards():
    reward_lines = old_rewards.strip().split("\n")
    old_reg = r".*('.*').*(\".*\"),\s*(\d*),\s*(\d*).*"
    patt = re.compile(old_reg)
    for line in reward_lines:
        m = patt.match(line)
        code = m.group(1)
        desc = m.group(2)
        points = m.group(3)
        add_objective(code, desc, points)
        print("Added {code} {desc} with reward {points}".format(code=code, desc=desc,points=points))


def init_db():
    cid = add_clan("vinst")
    add_clan_power(cid, "hp", 200)
    p = Player(username="hej", password="sko", clan=cid)
    session.add(p)
    session.commit()

    session.add(Objective(
        name="kill_gridbug",
        literal="Killed gridbug",
        score=10
        ))

    session.add(Objective(
        name="kill_medusa",
        literal="Killed Medusa",
        score=100
        ))
    session.commit()
