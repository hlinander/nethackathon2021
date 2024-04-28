use glob::glob;
use sqlx::Row;
use std::fs::{self, File};
use std::io::{self, BufRead, BufReader, Error, Read, Write};
use std::{env, path::Path};

use chrono::Local;

use std::process::{Command, Stdio};

use ptyprocess::PtyProcess;
use sqlx::PgPool;
use sqlx::{postgres::PgPoolOptions, Executor};
use tokio;

// async fn insert_rows(pool: &PgPool, rows: Vec<(Vec<f32>, String)>) -> Result<(), sqlx::Error> {
//     let mut transaction = pool.begin().await?;
//     for (row_idx, (row, row_str)) in rows.iter().enumerate() {
//         // Prepare an SQL INSERT statement
//         // Assuming table name is `data_table` and it has columns `col1, col2, ..., colN`
//         // let mut query = "INSERT INTO data_table VALUES (".to_owned();
//         let mut query =
//             format!("INSERT INTO items (embedding, text) VALUES ($1, $2) ON CONFLICT DO NOTHING",);

//         sqlx::query(&query)
//             .bind(&row as &[_])
//             .bind(row_str)
//             .execute(&mut *transaction)
//             .await
//             .inspect_err(|err| {
//                 println!("{}", err);
//             })
//             .unwrap();
//     }
//     transaction
//         .commit()
//         .await
//         .inspect_err(|err| println!("{}", err))
//         .unwrap();
//     Ok(())
// }

fn write_string_to_timestamped_file(data: &str, folder_name: &str) -> std::io::Result<()> {
    // Define the directory path where the file will be saved
    let dir_path = Path::new(folder_name);

    // Check if the directory exists, create it if it does not
    if !dir_path.exists() {
        fs::create_dir_all(dir_path)?;
    }

    // Get the current timestamp and format it
    let timestamp = Local::now().format("%Y-%m-%d_%H-%M-%S").to_string();

    // Create the file path
    let file_path = dir_path.join(format!("{}.txt", timestamp));

    // Create and open the file
    let mut file = File::create(&file_path)?;

    // Write the string to the file
    file.write_all(data.as_bytes())?;

    // println!("File written to {:?}", file_path);

    Ok(())
}

fn get_embedding(msg: &String) -> Option<Vec<f32>> {
    let output = Command::new("../oracle-worker/ggml_2024/result/bin/embedding")
        .arg("-m")
        .arg("../oracle-worker/ggml_2024/models/ggml-sfr-embedding-mistral-q4_k_m.gguf")
        .arg("-b")
        .arg("512")
        .arg("-ngl")
        .arg("0")
        .arg("-p")
        .arg(msg)
        .output() // Executes the command as a child process, waiting for it to finish
        .expect("failed to execute process");

    if output.status.success() {
        // Convert the stdout bytes to a string
        let stdout = String::from_utf8(output.stdout).expect("Not UTF-8");
        let s: Vec<_> = stdout.split(",").collect();
        let f: Vec<_> = s
            .iter()
            .take(s.len() - 1)
            .map(|x| x.trim().parse::<f32>().unwrap())
            .collect();
        Some(f)
        // println!("Command output:\n{:?}", f);
    } else {
        // If the command failed, handle it, for example, by printing stderr
        let stderr = String::from_utf8(output.stderr).expect("Not UTF-8");
        eprintln!("Command failed:\n{}", stderr);
        None
    }
}

fn rag_chat(context: &String, msg: String) -> String {
    // result/bin/llama -m models/mistral-7b-v0.1.Q4_K_M.gguf -p "Q: How old is the universe? A:" -c 1024
    // let context = "NONE".to_string();
    let context = format!(
        "
----- context start -----
{}
----- context end -----
----- instructions start -----
The agent gives players tips. It uses the context above to provide better tips.
The agent only uses general information from the context, not information that seems to be
specific for a particular user or game round.
The tips are formulated in a cheerful way, and are a maximum of 3 lines.
The tips are helpful, concrete, and formulated for a beginner player.
The agent only replies with human readably text, possibly including characters found
nethack from the ascii table.
----- instructions end -------
----- player request/sittuation/problem -----
{}
----- player end -----
----- agent tips start -----
",
        context, msg
    );
    // println!("CONTEXT LENGTH: {}", context.len());
    let mut output = Command::new("../oracle-worker/ggml_2024/result/bin/llama");
    // let output = PtyProcessBuilder::new("../oracle-worker/ggml_2024/result/bin/llama")
    output
        .arg("-m")
        .arg("../oracle-worker/ggml_2024/models/mistral-7b-v0.1.Q4_K_M.gguf")
        .arg("-c")
        .arg("8000")
        .arg("-ngl")
        .arg("0")
        .arg("--log-disable")
        .arg("-r")
        .arg("----- agent reply end -----")
        .arg("-r")
        .arg("----- agent reply end -----")
        .arg("-p")
        .arg(context);
    // let mut process = PtyProcess::spawn(output).expect("failed pty process");
    // let stream = process.get_raw_handle().expect("failed stream");
    let output = output.stdout(Stdio::piped()).stderr(Stdio::null()).spawn();

    let mut chars_out: Vec<char> = Vec::new();
    if let Ok(mut child) = output {
        let stdout = child.stdout.take().expect("Failed to take stdout");

        let mut reader = BufReader::new(stdout);
        // let mut reader = BufReader::new(stream);
        let mut buffer = [0; 1]; // A single byte buffer

        let mut reply_started = false;
        let mut reply_idx = 0;
        while let Ok(bytes_read) = reader.read(&mut buffer) {
            if bytes_read == 0 {
                // End of the stream
                break;
            }
            // Convert byte to char and print it
            chars_out.push(buffer[0] as char);
            if reply_started {
                print!("{}", buffer[0] as char);
                io::stdout().flush().unwrap();
            }
            let start_str = "----- agent tips start -----\n";
            let end_str = "----- agent reply start -----";
            if chars_out.len() > start_str.len() {
                let tail: String = chars_out[chars_out.len() - start_str.len()..]
                    .iter()
                    .collect();
                if tail == start_str {
                    reply_started = true;
                    reply_idx = chars_out.len() - 1;
                }
            }
            if reply_started
                && chars_out
                    .iter()
                    .skip(reply_idx)
                    .filter(|c| **c == '\n')
                    .count()
                    > 3
            {
                println!("[agent talked too much...]");
                break;
            }
        }
        // let reader = BufReader::new(stdout);
        // for line in reader.lines() {
        //     match line {
        //         Ok(line) => {
        //             println!("Line: {}", line);
        //             lines.push(line);
        //         }
        //         Err(e) => eprintln!("Error reading line: {}", e),
        //     }
        // }

        // Optionally, handle the case where you need to wait for the process to finish
        match child.kill() {
            _ => {} // Ok(()) => println!("Process exited"),
                    // Err(e) => eprintln!("Failed to wait on child: {}", e),
        };
        // match child.wait() {
        // Ok(status) => println!("Process exited with status: {}", status),
        // Err(e) => eprintln!("Failed to wait on child: {}", e),
        // };
    };
    // process.exit(true).expect("failed to quit");
    // } else {
    //     eprintln!("Failed to start process.");
    // }
    let full_result = chars_out.iter().collect::<String>();
    write_string_to_timestamped_file(full_result.as_str(), "chat_logs")
        .inspect_err(|err| println!("{}", err))
        .unwrap();
    full_result
    // lines.join("\n")

    // .output() // Executes the command as a child process, waiting for it to finish
    // .expect("failed to execute process");
}
async fn get_candidates(pool: &PgPool, msg: &String) -> Option<Vec<String>> {
    if let Some(embedding) = get_embedding(msg) {
        let query = "SELECT text FROM items ORDER BY embedding <-> $1 LIMIT 6".to_string();

        let candidates = sqlx::query(&query)
            .bind(&embedding as &[_])
            .fetch_all(pool)
            // .execute(&mut *transaction)
            .await
            .inspect_err(|err| {
                println!("{}", err);
            })
            .unwrap();

        Some(
            candidates
                .iter()
                .map(|row| row.get::<String, _>("text"))
                .collect(),
        )
    } else {
        None
    }
}

#[tokio::main]
async fn main() -> Result<(), sqlx::Error> {
    // println!("Hello, world!");

    let database_url = env::var("DATABASE_URL")
        .unwrap_or("postgres://postgres:herdeherde@localhost:5430".to_string());

    // println!("[db] connecting...");
    let pool = PgPoolOptions::new()
        .max_connections(5)
        .connect(&database_url)
        .await?;
    // .expect("Can't connect to database");
    // println!("[db] connected!");

    let msg = env::args().take(2).last().unwrap();
    let candidates = get_candidates(&pool, &msg).await;
    // println!("{:?}", candidates);
    if let Some(candidates) = candidates {
        let response = rag_chat(&candidates.join(";"), msg);
    }
    // pool.execute(
    //     format!(
    //         "
    //         CREATE TABLE items (
    //           id bigserial PRIMARY KEY,
    //           embedding vector({}) NOT NULL,
    //           text TEXT NOT NULL UNIQUE
    //         );
    //     ",
    //         n_embed
    //     )
    //     .as_str(),
    // )
    // .await
    // .inspect_err(|err| {
    //     println!("{}", err);
    // });
    Ok(())
}
