use crate::nh_proto::{self, SessionEvent};
use nh_proto::event::Msg;
use prost::Message;
use std::io::{Read, Write};
use std::net::TcpStream;

pub type Result<T> = std::result::Result<T, Error>;

#[derive(Debug)]
pub enum Error {
    IO(std::io::Error),
    Status(nh_proto::Status),
    EncodeError(prost::EncodeError),
    DecodeError(prost::DecodeError),
}

impl From<std::io::Error> for Error {
    fn from(e: std::io::Error) -> Self {
        Error::IO(e)
    }
}

impl From<prost::EncodeError> for Error {
    fn from(e: prost::EncodeError) -> Self {
        Error::EncodeError(e)
    }
}

impl From<prost::DecodeError> for Error {
    fn from(e: prost::DecodeError) -> Self {
        Error::DecodeError(e)
    }
}

pub struct Ipc {
    stream: TcpStream,
}
impl Ipc {
    pub fn new() -> Result<Self> {
        let stream = std::net::TcpStream::connect("192.168.1.148:8001")?;
        stream.set_read_timeout(Some(std::time::Duration::from_secs(3)));
        stream.set_write_timeout(Some(std::time::Duration::from_secs(3)));
        Ok(Self { stream })
    }

    pub fn auth(&mut self, id: i32, session_start_time: i32) -> Result<bool> {
        let req = nh_proto::Login {
            player_id: id,
            session_start_time,
        };
        self.send_event(Msg::Login(req))?;
        let response = self.read_message::<nh_proto::LoginStatus>()?;
        Ok(response.success)
    }

    fn read_msg_size(&mut self) -> Result<u32> {
        let mut msg_size = [0u8; 4];
        self.stream.read(&mut msg_size)?;
        Ok(u32::from_le_bytes(msg_size))
    }

    fn send_event(&mut self, evt: Msg) -> Result<()> {
        let mut evt_msg = nh_proto::Event::default();
        evt_msg.msg = Some(evt);
        let mut buf = Vec::new();
        evt_msg.encode(&mut buf)?;
        self.stream.write(&u32::to_le_bytes(buf.len() as u32))?;
        self.stream.write(&buf)?;
        Ok(())
    }

    fn read_message<T: Message + Default>(&mut self) -> Result<T> {
        let msg_size = self.read_msg_size()?;
        let mut buf = Vec::with_capacity(msg_size as usize);
        buf.resize(msg_size as usize, 0);
        self.stream.read_exact(&mut buf[0..msg_size as usize])?;
        Ok(T::decode(&*buf).expect("deserialize protobuf failed"))
    }
    pub fn get_clan(&mut self) -> Result<nh_proto::Clan> {
        let req = nh_proto::RequestClan {};
        self.send_event(Msg::RequestClan(req))?;
        let response = self.read_message::<nh_proto::Clan>()?;
        Ok(response)
    }

    pub fn get_bag(&mut self) -> Result<Vec<(i32, nh_proto::ObjData)>> {
        let req = nh_proto::BagInventory {};
        self.send_event(Msg::BagInventory(req))?;
        let response = self.read_message::<nh_proto::Bag>()?;
        let mut items = Vec::new();
        for item in response.items {
            let obj_data = nh_proto::ObjData::decode(&*item.item)?;
            items.push((item.id, obj_data));
        }
        Ok(items)
    }

    fn read_response<T: Message + Default>(&mut self) -> Result<T> {
        let status = self.read_message::<nh_proto::Status>()?;
        if status.code == 0 {
            let response = self.read_message::<T>()?;
            Ok(response)
        } else {
            Err(Error::Status(status))
        }
    }

    pub fn bag_add(&mut self, item: &nh_proto::ObjData) -> Result<bool> {
        let mut item_bytes = Vec::new();
        item.encode(&mut item_bytes)?;
        let req = nh_proto::InsertItem {
            item: Some(nh_proto::BagItem {
                id: 0,
                item: item_bytes,
            }),
        };
        self.send_event(Msg::InsertItem(req))?;
        let result = self.read_message::<nh_proto::RetrieveItemStatus>()?;
        Ok(result.success)
    }

    pub fn bag_remove(&mut self, item_id: i32) -> Result<bool> {
        let req = nh_proto::RetrieveItem {
            item: Some(nh_proto::BagItem {
                id: item_id,
                item: Vec::new(),
            }),
        };
        self.send_event(Msg::RetrieveItem(req))?;
        let response = self.read_message::<nh_proto::RetrieveItemStatus>()?;
        Ok(response.success)
    }

    pub fn task_complete(&mut self, objective_name: String) -> Result<nh_proto::Reward> {
        let req = nh_proto::CompleteTask { objective_name };
        self.send_event(Msg::CompleteTask(req))?;
        let response = self.read_response::<nh_proto::Reward>()?;
        Ok(response)
    }

    pub fn open_lootbox(&mut self, rarity: i32) -> Result<nh_proto::Reward> {
        let req = nh_proto::OpenLootbox { rarity };
        self.send_event(Msg::OpenLootbox(req))?;
        let response = self.read_response::<nh_proto::Reward>()?;
        Ok(response)
    }

    pub fn get_clan_powers(&mut self) -> Result<nh_proto::ClanPowers> {
        let req = nh_proto::RetrieveClanPowers {};
        self.send_event(Msg::ClanPowers(req))?;
        let response = self.read_response::<nh_proto::ClanPowers>()?;
        Ok(response)
    }

    pub fn save_equipment(&mut self, slot: i32, item: &nh_proto::ObjData) -> Result<()> {
        let mut item_bytes = Vec::new();
        item.encode(&mut item_bytes)?;
        let req = nh_proto::SaveEquipment {
            equipment: Some(nh_proto::Equipment {
                slot,
                item: item_bytes,
            }),
        };
        self.send_event(Msg::SaveEquipment(req))?;
        let status = self.read_message::<nh_proto::Status>()?;
        if status.code == 0 {
            Ok(())
        } else {
            Err(Error::Status(status))
        }
    }

    pub fn get_saved_equipment(&mut self) -> Result<Vec<(i32, nh_proto::ObjData)>> {
        let req = nh_proto::RetrieveSavedEquipment {};
        self.send_event(Msg::RetrieveSavedEquipment(req))?;
        let response = self.read_response::<nh_proto::SavedEquipment>()?;
        let mut items = Vec::new();
        for eq in response.equipments {
            let obj_data = nh_proto::ObjData::decode(&*eq.item)?;
            items.push((eq.slot, obj_data));
        }
        Ok(items)
    }

    pub fn send_session_event(&mut self, evt: SessionEvent) -> Result<()> {
        self.send_event(Msg::SessionEvent(evt))?;
        let status = self.read_message::<nh_proto::Status>()?;
        if status.code == 0 {
            Ok(())
        } else {
            Err(Error::Status(status))
        }
    }
}
