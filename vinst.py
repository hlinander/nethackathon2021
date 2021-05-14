import select
import socket
import struct
import nh_pb2
import db
from sqlalchemy.sql import func
import argparse
import random
#from db import Player DBPlayer, Clan as DBClan, open_db

ep = select.epoll()

server_socket = socket.socket()
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind(("0.0.0.0", 8001))
server_socket.listen(1)

ep.register(server_socket.fileno(), select.EPOLLIN | select.EPOLLET)

connections = {}

db.open_db()

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset-db", action="store_true")
    return parser.parse_args()

def parse_complete_task(connection, complete_task):
    player = db.session.query(db.Player).filter_by(id=connection["player_id"]).first()
    print("Complete task: ", complete_task.objective_name)
    objective = db.session.query(db.Objective).filter_by(name=complete_task.objective_name).first()
    status = nh_pb2.Status()
    if objective is None:
        status.code = 1
        status.error_message = "No such objective"
        return [status]

    rewards = db.session.query(db.Reward).filter_by(
        objective=objective.id,
        player=player.id)
    decayed_reward = int(objective.score / (1 + rewards.count()))
    reward = db.Reward(player=player.id, 
                       objective=objective.id,
                       score=decayed_reward)
    total_reward = db.session.query(func.sum(db.Reward.score)).filter_by(
        player=player.id)

    status.code = 0

    pb_reward = nh_pb2.Reward()
    pb_reward.reward = decayed_reward
    pb_reward.total_reward = total_reward.scalar() if total_reward.scalar() is not None else 0
    pb_reward.objective = objective.name

    return [status, pb_reward]

def open_lootbox(connection, lootbox_req):
    lootbox_rarity = lootbox_req.rarity
    player = db.session.query(db.Player).filter_by(id=connection["player_id"]).first()
    status = nh_pb2.Status()
    if player is None:
        status.code = 1
        status.error_message = "Player does not exist"
        return [status]
    clan = db.session.query(db.Clan).filter_by(id=player.clan).first()
    if clan is None:
        status.code = 2
        status.error_message = "Clan does not exist"
        return [status]
    
    new_gems = 0
    if lootbox_rarity == 1:
        new_gems = random.randint(5, 10)
    elif lootbox_rarity == 2:
        new_gems = random.randint(11, 30)
    elif lootbox_rarity == 3:
        new_gems = random.randint(40, 60)

    clan.power_gems += new_gems
    db.session.commit()

    status = nh_pb2.Status()
    status.code = 0

    pb_reward = nh_pb2.Reward()
    pb_reward.reward = new_gems
    pb_reward.total_reward = clan.power_gems
    pb_reward.objective = "power gems"

    return [status, pb_reward]

def get_clan_powers(connection, req):
    player = db.session.query(db.Player).filter_by(id=connection["player_id"]).first()
    status = nh_pb2.Status()
    if player is None:
        status.code = 1
        status.error_message = "Player does not exist"
        return [status]
    clan_powers = db.session.query(db.ClanPowers).filter_by(clan_id=player.clan)
    
    status = nh_pb2.Status()
    status.code = 0

    pb_clan_powers = nh_pb2.ClanPowers()
    powers_list = []
    for power in clan_powers:
        power_item = nh_pb2.ClanPower()
        power_item.name = power.name
        power_item.num = power.level
        powers_list.append(power_item)
    pb_clan_powers.powers.extend(powers_list)

    return [status, pb_clan_powers]


def parse_insert_item(connection, insert_item):
    player = db.session.query(db.Player).filter_by(id=connection["player_id"]).first()
    bag = db.session.query(db.Bag).filter_by(clan=player.clan).first()
    item = db.BagItem(
        bag=bag.id,
        item=insert_item.item.item
        )
    db.session.add(item)
    db.session.commit()
    status = nh_pb2.RetrieveItemStatus()
    status.item.id = insert_item.item.id
    status.success = True
    return [status]
    

def parse_retrieve_item(connection, retrieve_item):
    item = db.session.query(db.BagItem).filter_by(id=retrieve_item.item.id).first()
    status = nh_pb2.RetrieveItemStatus()
    status.item.id = retrieve_item.item.id
    if item is not None:
        db.session.delete(item)
        db.session.commit()
        status.success = True
    else:
        status.success = False

    return [status]
    

def parse_bag_inventory(connection, bag_inventory):
    player = db.session.query(db.Player).filter_by(id=connection["player_id"]).first()
    bag_items = db.session.query(db.BagItem).join(db.Bag).filter(db.Bag.clan==player.clan)
    bag = nh_pb2.Bag()
    items = []
    for item in bag_items:
        bag_item = nh_pb2.BagItem()
        bag_item.item = item.item
        bag_item.id = item.id
        items.append(bag_item)
    bag.items.extend(items)
    print(bag)
    return [bag]


def parse_request_clan(connection, request_clan):
    player = db.session.query(db.Player).filter_by(id=connection["player_id"]).first()
    clan_players = db.session.query(db.Player).filter_by(clan=player.clan)
    clan = nh_pb2.Clan()
    players = []
    for p in clan_players:
        np = nh_pb2.Player()
        np.username = p.username
        players.append(np)
    clan.players.extend(players)
    return [clan]

def parse_login(connection, login):
    connection["player_id"] = login.player_id
    status = nh_pb2.LoginStatus()
    status.success = True
    status.player_id = login.player_id
    return [status]

def parse_save_equipment(connection, save_eq):
    equipment_row = db.session.query(db.PlayerEquipment).filter_by(
            player_id=connection["player_id"],
            slot = save_eq.equipment.slot
        ).first()
    if equipment_row is None:
        equipment_row = db.PlayerEquipment(
            player_id=connection["player_id"],
            slot = save_eq.equipment.slot,
            item = save_eq.equipment.item
        )

        db.session.add(equipment_row)
    else:
        equipment_row.item = save_eq.equipment.item

    db.session.commit()

    status = nh_pb2.Status()
    status.code = 0
    return [status]

def parse_retrieve_saved_equipment(connection, req):
    equipment_rows = db.session.query(db.PlayerEquipment).filter_by(player_id=connection["player_id"]).first()
    pb_items_list = []
    for eq_row in equipment_rows:
        pb_eq = nh_pb2.Equipment(
            slot = eq_row.slot,
            item = eq.item
        )
        pb_items_list.append(pb_eq)
    response = nh_pb2.SavedEquipment()
    response.equipments.extend(pb_items_list)

    status = nh_pb2.Status()
    status.code = 0
    return [status, response]

dispatch = {
    "request_clan": parse_request_clan,
    "bag_inventory": parse_bag_inventory,
    "insert_item": parse_insert_item,
    "retrieve_item": parse_retrieve_item,
    "complete_task": parse_complete_task,
    "login": parse_login,
    "open_lootbox": open_lootbox,
    "clan_powers": get_clan_powers,
    "save_equipment": parse_save_equipment,
    "retrieve_saved_equipment": parse_retrieve_saved_equipment,
}

def parse_packet(connection, data):
    print(data)
    e = nh_pb2.Event()
    e.ParseFromString(data)
    e_type = e.WhichOneof("msg")
    return dispatch[e_type](connection, getattr(e, e_type))

    #dispatch[event_type](reader)

#parse_packet(b'\n\x07\n\x05\n\x03hej')
#bi = nh_pb2.BagInventory()
# e = nh_pb2.Event()
# #bi.player.username = "hej"
# e.insert_item.item.item = b"daaaaata"
# e.insert_item.item.id = 0
# 
# parse_packet(e.SerializeToString())
# 
# e = nh_pb2.Event()
# #bi.player.username = "hej"
# e.bag_inventory.player.username = "hej"
# parse_packet(e.SerializeToString())
# 
# e = nh_pb2.Event()
# e.retrieve_item.item.id = 1324321
# parse_packet(e.SerializeToString())
# 
# e = nh_pb2.Event()
# e.complete_task.player.username = "hej"
# e.complete_task.objective_name = "killed_gridbug"
# parse_packet(e.SerializeToString())

# e = nh_pb2.Event()
# e.clan_powers.SetInParent()
# print(parse_packet(dict(player_id=1), e.SerializeToString()))

e = nh_pb2.Event()
e.open_lootbox.rarity = 1
ret = parse_packet(dict(player_id=1), e.SerializeToString())
print(ret)

# e = nh_pb2.Event()
# e.login.player_id = 1
# parse_packet(dict(player_id=1), e.SerializeToString())
# e = nh_pb2.Event()
# e.complete_task.objective_name = "killed_gridbug"
# print(parse_packet(dict(player_id=1), e.SerializeToString()))

args = parse_args()
if args.reset_db:
    db.init_db()

while True:
    events = ep.poll(1)

    for fileno, event in events:
        if fileno == server_socket.fileno():
            connection, address = server_socket.accept()
            connection.setblocking(0)
            print(address)
            ep.register(connection.fileno(), select.EPOLLIN | select.EPOLLET)
            connections[connection.fileno()] = dict(conn=connection, buffer=b"", player_id=None)
        elif event & select.EPOLLIN:
            try:
                connections[fileno]["buffer"] += (
                    connections[fileno]["conn"].recv(512))
            except:
                del connections[fileno]


            if len(connections[fileno]["buffer"]) > 4:
                size = struct.unpack("<I", connections[fileno]["buffer"][:4])[0]
                if len(connections[fileno]["buffer"][4:]) >= size:
                    responses = parse_packet(connections[fileno], connections[fileno]["buffer"][4:(4 + size)])
                    db.session.commit()
                    for response in responses:
                        response_data = response.SerializeToString()
                        connections[fileno]["conn"].send(struct.pack("<I", len(response_data)))
                        connections[fileno]["conn"].send(response_data)
                    connections[fileno]["buffer"] = connections[fileno]["buffer"][4 + size:]
