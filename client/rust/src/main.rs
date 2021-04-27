use nh2021::nh_proto;
use prost::Message;
use std::io::{Read, Result, Write};
use std::net::TcpStream;

fn test_get_clan() -> Result<nh_proto::Clan> {
    let mut ipc = nh2021::ipc::Ipc::new()?;
    ipc.get_clan()
}

fn main() {
    loop {
        match test_get_clan() {
            Ok(clan) => {
                println!("success {:?}", clan);
            }
            Err(e) => {
                eprintln!("get_clan error: {:?}", e)
            }
        }
        std::thread::sleep_ms(1000);
    }
}
