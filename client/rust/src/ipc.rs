use crate::nh_proto;
use nh_proto::event::Msg;
use prost::Message;
use std::io::{Read, Result, Write};
use std::net::TcpStream;

pub struct Ipc {
    stream: TcpStream,
}
impl Ipc {
    pub fn new() -> Result<Self> {
        let stream = std::net::TcpStream::connect("192.168.1.148:8001")?;
        Ok(Self { stream })
    }

    pub fn auth(&mut self, id: i32) -> Result<bool> {
        let req = nh_proto::Login { player_id: id };
        self.send_event(Msg::Login(req))?;
        let read_response = self.read_message::<nh_proto::LoginStatus>()?;
        Ok(read_response.success)
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
        let read_response = self.read_message::<nh_proto::Clan>()?;
        Ok(read_response)
    }

    pub fn get_bag(&mut self) -> Result<Vec<(i32, nh_proto::ObjData)>> {
        let req = nh_proto::BagInventory {};
        self.send_event(Msg::BagInventory(req))?;
        let read_response = self.read_message::<nh_proto::Bag>()?;
        let mut items = Vec::new();
        for item in read_response.items {
            let obj_data = nh_proto::ObjData::decode(&*item.item)?;
            // println!("obj_data {:?}_____{:?}", item.item.iter().map(|i| format!("{:x}", i)),obj_data);
            items.push((item.id, obj_data));
        }
        // println!("items {:?}", items);
        Ok(items)
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
        let read_response = self.read_message::<nh_proto::RetrieveItemStatus>()?;
        Ok(read_response.success)
    }

    pub fn bag_remove(&mut self, item_id: i32) -> Result<bool> {
        let req = nh_proto::RetrieveItem {
            item: Some(nh_proto::BagItem {
                id: item_id,
                item: Vec::new(),
            }),
        };
        self.send_event(Msg::RetrieveItem(req))?;
        let read_response = self.read_message::<nh_proto::RetrieveItemStatus>()?;
        Ok(read_response.success)
    }
}
