use crate::nh_proto::{self, CoconutSong, SessionEvent};
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

pub enum Ipc {
    Tcp(TcpIpc),
    Fake,
}
impl Ipc {
    pub fn new_fake() -> Result<Self> {
        Ok(Self::Fake)
    }
    pub fn new_tcp() -> Result<Self> {
        let stream = std::net::TcpStream::connect("127.0.0.1:8001")?;
        stream.set_nonblocking(false)?;
        stream.set_read_timeout(Some(std::time::Duration::from_secs(3)));
        stream.set_write_timeout(Some(std::time::Duration::from_secs(3)));
        Ok(Self::Tcp(TcpIpc { stream }))
    }

    pub fn auth(&mut self, id: i32, session_start_time: i32) -> Result<bool> {
        match self {
            Self::Tcp(ipc) => ipc.auth(id, session_start_time),
            Self::Fake => Ok(true),
        }
    }

    fn send_event(&mut self, evt: Msg) -> Result<()> {
        match self {
            Self::Tcp(ipc) => ipc.send_event(evt),
            Self::Fake => Ok(()),
        }
    }

    pub fn get_bag(&mut self) -> Result<Vec<(i32, nh_proto::ObjData)>> {
        match self {
            Self::Tcp(ipc) => ipc.get_bag(),
            Self::Fake => Ok(vec![]),
        }
    }

    pub fn bag_add(&mut self, item: &nh_proto::ObjData) -> Result<bool> {
        match self {
            Self::Tcp(ipc) => ipc.bag_add(item),
            Self::Fake => Ok(true),
        }
    }

    pub fn bag_remove(&mut self, item_id: i32) -> Result<bool> {
        match self {
            Self::Tcp(ipc) => ipc.bag_remove(item_id),
            Self::Fake => Ok(true),
        }
    }

    pub fn task_complete(&mut self, objective_name: String) -> Result<nh_proto::Reward> {
        match self {
            Self::Tcp(ipc) => ipc.task_complete(objective_name),
            Self::Fake => Ok(nh_proto::Reward {
                reward: 0,
                objective: "no".to_string(),
                total_reward: 0,
            }),
        }
    }

    pub fn open_lootbox(&mut self, rarity: i32) -> Result<nh_proto::Reward> {
        match self {
            Self::Tcp(ipc) => ipc.open_lootbox(rarity),
            Self::Fake => Ok(nh_proto::Reward {
                reward: 0,
                objective: "no".to_string(),
                total_reward: 0,
            }),
        }
    }

    pub fn get_clan_powers(&mut self) -> Result<nh_proto::ClanPowers> {
        match self {
            Self::Tcp(ipc) => ipc.get_clan_powers(),
            Self::Fake => Ok(nh_proto::ClanPowers { powers: vec![] }),
        }
    }

    pub fn save_equipment(&mut self, slot: i32, item: &nh_proto::ObjData) -> Result<()> {
        match self {
            Self::Tcp(ipc) => ipc.save_equipment(slot, item),
            Self::Fake => Ok(()),
        }
    }

    pub fn get_saved_equipment(&mut self) -> Result<Vec<(i32, nh_proto::ObjData)>> {
        match self {
            Self::Tcp(ipc) => ipc.get_saved_equipment(),
            Self::Fake => Ok(vec![]),
        }
    }

    pub fn send_session_event(&mut self, evt: SessionEvent) -> Result<()> {
        match self {
            Self::Tcp(ipc) => ipc.send_session_event(evt),
            Self::Fake => Ok(()),
        }
    }

    pub fn wealth_tax(&mut self) -> Result<()> {
        match self {
            Self::Tcp(ipc) => ipc.wealth_tax(),
            Self::Fake => Ok(()),
        }
    }

    pub fn coconut_song(&mut self, song: CoconutSong) -> Result<()> {
        match self {
            Self::Tcp(ipc) => ipc.coconut_song(song),
            Self::Fake => Ok(()),
        }
    }
}

pub struct TcpIpc {
    stream: TcpStream,
}
impl TcpIpc {
    pub fn new() -> Result<Self> {
        let stream = std::net::TcpStream::connect("192.168.1.11:8001")?;
        stream
            .set_read_timeout(Some(std::time::Duration::from_secs(3)))
            .unwrap();
        stream
            .set_write_timeout(Some(std::time::Duration::from_secs(3)))
            .unwrap();
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
        self.read_exact_with_retries(&mut msg_size)?;
        Ok(u32::from_le_bytes(msg_size))
    }

    fn debug_print_file(s: String) {
        let mut f = std::fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open("/tmp/nethackdebuglog")
            .unwrap();
        write!(f, "{}", s).unwrap();
    }
    fn read_exact_with_retries(&mut self, buf: &mut [u8]) -> Result<()> {
        let mut retries = 0;
        Ok(loop {
            let result = self.stream.read_exact(buf);
            if let Err(e) = &result {
                if e.kind() == std::io::ErrorKind::WouldBlock {
                    retries += 1;
                    // Self::debug_print_file(format!(
                    //     "would block when reading exact {} bytes, retry {}\n",
                    //     buf.len(),
                    //     retries
                    // ));
                    std::thread::sleep_ms(1);
                    if retries > 1000 {
                        break;
                    }
                    continue;
                } else {
                    result?
                }
            } else {
                break;
            }
        })
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
        self.read_exact_with_retries(&mut buf[0..msg_size as usize])?;
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

    pub fn wealth_tax(&mut self) -> Result<()> {
        let req = nh_proto::WealthTax {};
        self.send_event(Msg::WealthTax(req))?;
        let status = self.read_message::<nh_proto::Status>()?;
        if status.code == 0 {
            Ok(())
        } else {
            Err(Error::Status(status))
        }
    }

    pub fn coconut_song(&mut self, req: CoconutSong) -> Result<()> {
        self.send_event(Msg::CoconutSong(req))?;
        let status = self.read_message::<nh_proto::Status>()?;
        if status.code == 0 {
            Ok(())
        } else {
            Err(Error::Status(status))
        }
    }
}
