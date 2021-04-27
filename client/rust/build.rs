fn main() -> std::io::Result<()> {
    prost_build::compile_protos(&["nh.proto", "nh_obj.proto"], &["../../nhvinst/", "proto"])?;
    Ok(())
}
