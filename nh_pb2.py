# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: nh.proto
"""Generated protocol buffer code."""
from google.protobuf.internal import builder as _builder
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x08nh.proto\x12\x02nh\"6\n\x05Login\x12\x11\n\tplayer_id\x18\x01 \x01(\x05\x12\x1a\n\x12session_start_time\x18\x02 \x01(\x05\"1\n\x0bLoginStatus\x12\x0f\n\x07success\x18\x01 \x01(\x08\x12\x11\n\tplayer_id\x18\x02 \x01(\x05\"\x1a\n\x06Player\x12\x10\n\x08username\x18\x01 \x01(\t\"\r\n\x0bRequestClan\"#\n\x04\x43lan\x12\x1b\n\x07players\x18\x01 \x03(\x0b\x32\n.nh.Player\"\x0e\n\x0c\x42\x61gInventory\"\'\n\nInsertItem\x12\x19\n\x04item\x18\x01 \x01(\x0b\x32\x0b.nh.BagItem\")\n\x0cRetrieveItem\x12\x19\n\x04item\x18\x01 \x01(\x0b\x32\x0b.nh.BagItem\"@\n\x12RetrieveItemStatus\x12\x19\n\x04item\x18\x01 \x01(\x0b\x32\x0b.nh.BagItem\x12\x0f\n\x07success\x18\x02 \x01(\x08\"1\n\rSaveEquipment\x12 \n\tequipment\x18\x01 \x01(\x0b\x32\r.nh.Equipment\"\'\n\tEquipment\x12\x0c\n\x04slot\x18\x01 \x01(\x05\x12\x0c\n\x04item\x18\x02 \x01(\x0c\"3\n\x0eSavedEquipment\x12!\n\nequipments\x18\x01 \x03(\x0b\x32\r.nh.Equipment\"\x18\n\x16RetrieveSavedEquipment\"#\n\x07\x42\x61gItem\x12\n\n\x02id\x18\x01 \x01(\x05\x12\x0c\n\x04item\x18\x02 \x01(\x0c\"!\n\x03\x42\x61g\x12\x1a\n\x05items\x18\x01 \x03(\x0b\x32\x0b.nh.BagItem\")\n\tObjective\x12\x0c\n\x04name\x18\x01 \x01(\t\x12\x0e\n\x06reward\x18\x02 \x01(\x05\"&\n\x0c\x43ompleteTask\x12\x16\n\x0eobjective_name\x18\x01 \x01(\t\"\x1d\n\x0bOpenLootbox\x12\x0e\n\x06rarity\x18\x01 \x01(\x05\"&\n\tClanPower\x12\x0c\n\x04name\x18\x01 \x01(\t\x12\x0b\n\x03num\x18\x02 \x01(\x05\"\x14\n\x12RetrieveClanPowers\"+\n\nClanPowers\x12\x1d\n\x06powers\x18\x01 \x03(\x0b\x32\r.nh.ClanPower\"A\n\x06Reward\x12\x0e\n\x06reward\x18\x01 \x01(\x05\x12\x11\n\tobjective\x18\x02 \x01(\t\x12\x14\n\x0ctotal_reward\x18\x03 \x01(\x05\"-\n\x06Status\x12\x0c\n\x04\x63ode\x18\x01 \x01(\x05\x12\x15\n\rerror_message\x18\x02 \x01(\t\"o\n\x0cSessionEvent\x12\x14\n\x0csession_turn\x18\x01 \x01(\x05\x12\x0c\n\x04name\x18\x02 \x01(\t\x12\x16\n\x0eprevious_value\x18\x03 \x01(\x05\x12\r\n\x05value\x18\x04 \x01(\x05\x12\x14\n\x0cstring_value\x18\x05 \x01(\t\"\x9f\x05\n\x05\x45vent\x12\'\n\x0crequest_clan\x18\x01 \x01(\x0b\x32\x0f.nh.RequestClanH\x00\x12\x18\n\x04\x63lan\x18\x02 \x01(\x0b\x32\x08.nh.ClanH\x00\x12\x1c\n\x06player\x18\x03 \x01(\x0b\x32\n.nh.PlayerH\x00\x12\x1a\n\x05login\x18\x04 \x01(\x0b\x32\t.nh.LoginH\x00\x12)\n\rbag_inventory\x18\x05 \x01(\x0b\x32\x10.nh.BagInventoryH\x00\x12\x1f\n\x08\x62\x61g_item\x18\x06 \x01(\x0b\x32\x0b.nh.BagItemH\x00\x12\x16\n\x03\x62\x61g\x18\x07 \x01(\x0b\x32\x07.nh.BagH\x00\x12%\n\x0binsert_item\x18\x08 \x01(\x0b\x32\x0e.nh.InsertItemH\x00\x12)\n\rretrieve_item\x18\t \x01(\x0b\x32\x10.nh.RetrieveItemH\x00\x12)\n\rcomplete_task\x18\n \x01(\x0b\x32\x10.nh.CompleteTaskH\x00\x12\x1c\n\x06reward\x18\x0b \x01(\x0b\x32\n.nh.RewardH\x00\x12\'\n\x0copen_lootbox\x18\x0c \x01(\x0b\x32\x0f.nh.OpenLootboxH\x00\x12-\n\x0b\x63lan_powers\x18\r \x01(\x0b\x32\x16.nh.RetrieveClanPowersH\x00\x12>\n\x18retrieve_saved_equipment\x18\x0e \x01(\x0b\x32\x1a.nh.RetrieveSavedEquipmentH\x00\x12+\n\x0esave_equipment\x18\x0f \x01(\x0b\x32\x11.nh.SaveEquipmentH\x00\x12)\n\rsession_event\x18\x10 \x01(\x0b\x32\x10.nh.SessionEventH\x00\x12#\n\nwealth_tax\x18\x11 \x01(\x0b\x32\r.nh.WealthTaxH\x00\x42\x05\n\x03msg\"\x0b\n\tWealthTaxb\x06proto3')

_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, globals())
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'nh_pb2', globals())
if _descriptor._USE_C_DESCRIPTORS == False:

  DESCRIPTOR._options = None
  _LOGIN._serialized_start=16
  _LOGIN._serialized_end=70
  _LOGINSTATUS._serialized_start=72
  _LOGINSTATUS._serialized_end=121
  _PLAYER._serialized_start=123
  _PLAYER._serialized_end=149
  _REQUESTCLAN._serialized_start=151
  _REQUESTCLAN._serialized_end=164
  _CLAN._serialized_start=166
  _CLAN._serialized_end=201
  _BAGINVENTORY._serialized_start=203
  _BAGINVENTORY._serialized_end=217
  _INSERTITEM._serialized_start=219
  _INSERTITEM._serialized_end=258
  _RETRIEVEITEM._serialized_start=260
  _RETRIEVEITEM._serialized_end=301
  _RETRIEVEITEMSTATUS._serialized_start=303
  _RETRIEVEITEMSTATUS._serialized_end=367
  _SAVEEQUIPMENT._serialized_start=369
  _SAVEEQUIPMENT._serialized_end=418
  _EQUIPMENT._serialized_start=420
  _EQUIPMENT._serialized_end=459
  _SAVEDEQUIPMENT._serialized_start=461
  _SAVEDEQUIPMENT._serialized_end=512
  _RETRIEVESAVEDEQUIPMENT._serialized_start=514
  _RETRIEVESAVEDEQUIPMENT._serialized_end=538
  _BAGITEM._serialized_start=540
  _BAGITEM._serialized_end=575
  _BAG._serialized_start=577
  _BAG._serialized_end=610
  _OBJECTIVE._serialized_start=612
  _OBJECTIVE._serialized_end=653
  _COMPLETETASK._serialized_start=655
  _COMPLETETASK._serialized_end=693
  _OPENLOOTBOX._serialized_start=695
  _OPENLOOTBOX._serialized_end=724
  _CLANPOWER._serialized_start=726
  _CLANPOWER._serialized_end=764
  _RETRIEVECLANPOWERS._serialized_start=766
  _RETRIEVECLANPOWERS._serialized_end=786
  _CLANPOWERS._serialized_start=788
  _CLANPOWERS._serialized_end=831
  _REWARD._serialized_start=833
  _REWARD._serialized_end=898
  _STATUS._serialized_start=900
  _STATUS._serialized_end=945
  _SESSIONEVENT._serialized_start=947
  _SESSIONEVENT._serialized_end=1058
  _EVENT._serialized_start=1061
  _EVENT._serialized_end=1732
  _WEALTHTAX._serialized_start=1734
  _WEALTHTAX._serialized_end=1745
# @@protoc_insertion_point(module_scope)
