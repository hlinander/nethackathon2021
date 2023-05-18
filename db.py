import sqlalchemy
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, LargeBinary, Time, DateTime, JSON, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import datetime
import os
import numpy as np
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
    ticker = Column(String)

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
    item = Column(LargeBinary)

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
    item = Column(LargeBinary)

class EventHandler(Base):
    __tablename__ = "event_handler"
    id = Column(Integer, primary_key=True)
    last_handled_timestamp = Column(DateTime)
    state = Column(JSON)

class Event(Base):
    __tablename__ = "event"
    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey("players.id"))
    clan_id = Column(Integer, ForeignKey("clans.id"))
    session_start_time = Column(Integer)
    session_turn = Column(Integer)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    name = Column(String)
    previous_value = Column(Integer)
    value = Column(Integer)
    string_value = Column(String)
    extra = Column(JSON)


class Stonk(Base):
    __tablename__ = "stonk"
    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey("players.id"))
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    name = Column(String)
    value = Column(Integer)

class StonkHolding(Base):
    __tablename__ = "stonk_holding"
    id = Column(Integer, primary_key=True)
    fraction = Column(Float, default=1.0)
    clan_id = Column(Integer, ForeignKey("clans.id"))
    player_id = Column(Integer, ForeignKey("players.id"))
    stonk_name = Column(String)
    buy_event_id = Column(Integer, ForeignKey("event.id"))
    long = Column(Boolean)
    # stonk = relationship(Stonk)
    # clan = relationship(Clan)
    # buy_event = relationship(Event)
    expires_turn = Column(Integer)
    expires_delta = Column(Integer)
    session_start_time = Column(Integer)

class Transactions(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("event.id"))

    # sold =

def get_transaction(event):
    return session.query(Transactions).filter_by(event_id=event.id).first()


# class CertificateOwner(Base):
#     __tablename__ = "certificate_owner"
#     id = Column(Integer, primary_key=True)
#     certificate_id = Column(Integer, ForeignKey("certificate.id"))
#     player_id = Column(Integer, ForeignKey("player.id"))
#
# class Certificate(Base):
#     __tablename__ = "certificate"
#     id = Column(Integer, primary_key=True)
#     name = Column(String)
#     value = Column(Integer)

# NFTS:
# Global inv gold
# Global turns
# Global HP
# Per player
#   death
#   turns
#   hp
#
# class StonkStake(Base):
#     __tablename__ = "stonk_stake"
#     stake_player_id =  Column(Integer, ForeignKey("players.id"), primary_key=True)
#     holder_player_id =  Column(Integer, ForeignKey("players.id"), primary_key=True)

# HEEEEJ
# create table objectives(
# 	id int not null auto_increment,
# 	name varchar(32) not null,
# 	literal varchar(32) not null,
# 	score int,

# 	decrease_rate boolean,
# 	added timestamp,
# 	primary key(id));



def add_transaction(event_id):
    t = Transactions(event_id=event_id)
    session.add(t)
    session.flush()
    return t.id

def add_clan(name, power_gems):
    c = Clan(name=name, power_gems=power_gems)
    session.add(c)
    session.flush()
    b = Bag(clan=c.id)
    session.add(b)
    session.flush()
    return c.id


def open_db():
    global session
    psql = os.getenv('PSQL_TARGET')
    psql = psql if psql is not None else 'postgresql://postgres:vinst@localhost/nh'
    engine = create_engine(psql) #, echo=True)

    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    session.flush()

    return session




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
    o = session.query(Objective).filter_by(name=name).first()
    if o is None:
        session.add(Objective(
            name=name,
            literal=literal,
            score=score
            ))
        session.commit()

def add_clan_power(clan_id, power, level):
    power = ClanPowers(
        clan_id=clan_id,
        name=power,
        level=level
    )
    session.add(power)
    return power


def buy_stonk(event, stonk_player_session_time, stonk_player_id, stonk_name, spent_gems, expires, expires_delta, buy_long):
    p = session.query(Player).filter_by(id=event.player_id).first()
    # print(p.__dict__)
    stonk = get_stonk(stonk_player_id, stonk_name)
    if stonk is not None:
        if stonk.value > 0:
            fraction = spent_gems / stonk.value
            return insert_stonk_holding(p.clan, stonk_player_session_time, stonk_player_id, stonk.name, event.id, fraction, expires, expires_delta, buy_long)
        else:
            print("Stonk is free!")
    else:
        print(f"Tried to buy non-existent stonk {stonk_player_id}: {stonk_name}")


def insert_stonk_holding(clan_id, session_start_time, stonk_player_id, stonk_name, event_id, fraction, expires_turn, expires_delta, buy_long):
    stonk_holding = StonkHolding(
        clan_id=clan_id,
        player_id=stonk_player_id,
        stonk_name=stonk_name,
        buy_event_id=event_id,
        expires_turn=expires_turn,
        expires_delta=expires_delta,
        fraction=fraction,
        long=buy_long,
        session_start_time=session_start_time
    )
    session.add(stonk_holding)
    session.flush()
    session.commit()
    return stonk_holding

def delete_holding(holding_id):
    stonk_holding = session.query(StonkHolding).filter_by(id=holding_id).first()
    session.delete(stonk_holding)
    session.commit()

def add_buy_stonk_event(player_id, session_start_time, session_turn, stonk_player_id, stonk_name, spent_gems, expires, buy_long):
    p = session.query(Player).filter_by(id=player_id).first()
    clan = session.query(Clan).filter_by(id=p.clan).first()
    print(f"{clan.power_gems} <? {spent_gems}")
    if (clan.power_gems + 500) < spent_gems:
        return
    clan.power_gems -= spent_gems
    item = Event(
        player_id=player_id,
        clan_id=p.clan,
        session_start_time=session_start_time,
        session_turn=session_turn,
        name="buy_stonk",
        extra=dict(
            stonk_player_id=stonk_player_id,
            stonk_name=stonk_name,
            expires_delta=expires,
            spent_gems=spent_gems,
            buy_long=buy_long
        )
        )
    session.add(item)
    session.commit()

def add_clan_gems_for_clan(clan_id, gems):
    clan = session.query(Clan).filter_by(id=clan_id).first()
    clan.power_gems += gems
    session.commit()
    return clan.power_gems

def add_clan_gems_for_player(player_id, gems):
    p = session.query(Player).filter_by(id=player_id).first()
    add_clan_gems_for_clan(p.clan, gems)

def add_clan_power_for_player(player_id, name, level, cost):
    p = session.query(Player).filter_by(id=player_id).first()
    power = session.query(ClanPowers).filter_by(clan_id=p.clan, name=name).first()
    if power is None:
        power = add_clan_power(p.clan, name, 0)
    clan = session.query(Clan).filter_by(id=p.clan).first()
    if clan.power_gems >= cost:
        clan.power_gems -= cost
        #if power is None:
        #    add_clan_power(p.clan, name, level)
        #else:
        power.level = level

    session.commit()
    return power.level

def get_clan_by_id(clan_id):
    return session.query(Clan).filter_by(id=clan_id).first()

def get_clan(player_id):
    p = session.query(Player).filter_by(id=player_id).first()
    clan = session.query(Clan).filter_by(id=p.clan).first()
    return clan

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

def get_stonks(player_id):
    stonks = (session.query(Stonk)
              .filter_by(player_id=player_id))
    return list(set([stonk.name for stonk in stonks]))

def get_stonk(player_id, name):
    stonk = (session.query(Stonk)
              .filter_by(player_id=player_id, name=name).order_by(Stonk.timestamp.desc()).first())
    return stonk

def get_stonk_holdings():
    return session.query(StonkHolding).all()


# def get_stonk_holdings_():
#     stonk_holdings = get_stonk_holdings()
#     players = session.query(Player)
#     stonk_dict = dict()
#     for player in players:
#         print(".")
#         player_stonks = session.query(Stonk.name).filter_by(player_id=player.id).distinct()
#         all_long_holders = []
#         all_short_holders = []
#         for player_stonk in player_stonks:
#             print(";")
#             long_holders = session.query(StonkHolding).filter_by(
#                 stonk_id=player_stonk, long=True)
#             all_long_holders.extend([(holder.clan_id, holder.fraction * player_stonk.value) for holder in long_holders])
#             short_holders = session.query(StonkHolding).filter_by(
#                 stonk_id=player_stonk.id, long=False)
#             all_short_holders.extend([(holder.clan_id, holder.fraction * player_stonk.value) for holder in short_holders])
#         stonk_dict[player.id] = dict(long=all_long_holders, short=all_short_holders)
#     return stonk_dict



def get_stonk_series(player_id, name, nsteps, time_start, time_end):
    stonks = (session.query(Stonk)
              .filter_by(player_id=player_id, name=name)
              .filter(Stonk.timestamp > time_start)
              .filter(Stonk.timestamp < time_end)
              .order_by(Stonk.timestamp))
    if stonks.first() is None:
        stonk = (session.query(Stonk)
                  .filter_by(player_id=player_id, name=name)
                  .filter(Stonk.timestamp < time_end)
                  .order_by(Stonk.timestamp)
                  .first())
        if stonk is None:
            return [0] * nsteps

        xp = [time_start.timestamp(), time_end.timestamp()]
        fp = [stonk.value, stonk.value]
    else:
        stonker = list(stonks)
        xp = np.array([stonk.timestamp.timestamp() for stonk in stonker])
        fp = np.array([stonk.value for stonk in stonker])

    timestamp_start = time_start.timestamp()
    timestamp_stop = time_end.timestamp()
    time_steps = np.linspace(timestamp_start, timestamp_stop, nsteps)
    return np.interp(time_steps, xp, fp)

def insert_stonk(player_id, name, value, timestamp):
    session.add(Stonk(
        player_id=player_id,
        value=value,
        name=name,
        timestamp=timestamp
        ))

        # db.insert_stonk_holding(player_id, stonk.id, expires)

def reset_stonks():
    session.query(StonkHolding).delete()
    session.query(Stonk).delete()
    session.commit()


def get_player(player_id):
    return session.query(Player).filter_by(id=player_id).first()

def login(username, password):
    player = session.query(Player).filter_by(username=username).first()
    if player is None:
        return dict(logged_in=False, status="Username doesn't exist")
    if player.password != password:
        return dict(logged_in=False, status=f"Wrong password! Your password is {player.password}")
    return dict(logged_in=True, status="Success", player_id=player.id)


def insert_rewards():
    reward_lines = old_rewards.strip().split("\n")
    old_reg = r".*'(.*)'.*\"(.*)\",\s*(\d*),\s*(\d*).*"
    patt = re.compile(old_reg)
    for line in reward_lines:
        try:
            m = patt.match(line)
            code = m.group(1)
            desc = m.group(2)
            points = m.group(3)
            add_objective(code, desc, points)
        except Exception as e:
            breakpoint()
            print(line)
            print(str(e))
        #print("Added {code} {desc} with reward {points}".format(code=code, desc=desc,points=points))


def init_db():
    pissduktiga = add_clan("erikocherik", 200)
    hquit = add_clan("#quit", 200)
    vinst = add_clan("vinst", 200)
    boisen = add_clan("boisen", 200)
    #testarna = add_clan("test")
    #ctest = session.query(Clan).filter_by(id=testarna).first()
    #ctest.power_gems = 50000
    # add_clan_power(cid, "hp", 0)
    session.add(Player(username="menvafan", ticker="MVF", password="sko", clan=boisen))
    # session.add(Player(username="erik2", ticker="ER2", password="sko", clan=boisen))
    session.add(Player(username="myfz", ticker="VAL", password="sko", clan=boisen))
    session.add(Player(username="Aransentin", ticker="ARS", password="sko", clan=boisen))
    session.add(Player(username="bJazz", ticker="BJZ", password="sko", clan=boisen))

    session.add(Player(username="pellsson", ticker="PLS", password="sko", clan=hquit))
    session.add(Player(username="CeleryMan", ticker="CEL", password="sko", clan=hquit))
    session.add(Player(username="eracce", ticker="ERC", password="sko", clan=hquit))
    session.add(Player(username="kwahkai", ticker="KWA", password="sko", clan=hquit))

    session.add(Player(username="kae", ticker="KAE", password="sko", clan=vinst))
    session.add(Player(username="chokladboll", ticker="CHO", password="sko", clan=vinst))
    session.add(Player(username="dregg", ticker="DRE", password="sko", clan=vinst))
    session.add(Player(username="drgiffel", ticker="DRG", password="sko", clan=vinst))
    session.add(Player(username="macroman", ticker="MCR", password="sko", clan=vinst))

    session.add(Player(username="breggan", ticker="BRG", password="sko", clan=vinst))

    session.commit()

    insert_rewards()
