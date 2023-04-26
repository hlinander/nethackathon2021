use nh2021::ipc::Result;
use nh2021::nh_proto;

fn test_get_clan() -> Result<nh_proto::Clan> {
    todo!()
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
