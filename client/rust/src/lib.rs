pub mod ipc;
pub mod nh_api;
pub mod oracle;

pub mod nh_proto {
    include!(concat!(env!("OUT_DIR"), "/nh.rs"));
    include!(concat!(env!("OUT_DIR"), "/nh_obj.rs"));
}
