use glob::glob;
use sqlx::Row;
use std::fs::File;
use std::io::{self, BufRead, BufReader, Error, Read};
use std::{env, path::Path};

use std::process::{Command, Stdio};

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

fn get_embedding(msg: &String) -> Option<Vec<f32>> {
    let output = Command::new("../oracle-worker/ggml_2024/result/bin/embedding")
        .arg("-m")
        .arg("../oracle-worker/ggml_2024/models/ggml-sfr-embedding-mistral-q4_k_m.gguf")
        .arg("-b")
        .arg("512")
        .arg("-ngl")
        .arg("40")
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
    let context = format!(
        "
Context information:
----------
{}
----------
You are a helpful automatic agent that gives players tips on what they could have done better. The above context might be used to provide tips.
The tips are always formulated in a cheerful but condescending tone.
Sittuation: {}
Agent tips:",
        context, msg
    );
    println!("CONTEXT LENGTH: {}", context.len());
    let output = Command::new("../oracle-worker/ggml_2024/result/bin/llama")
        .arg("-m")
        .arg("../oracle-worker/ggml_2024/models/mistral-7b-v0.1.Q4_K_M.gguf")
        .arg("-c")
        .arg("8000")
        .arg("-ngl")
        .arg("20")
        .arg("--log-disable")
        .arg("-p")
        .arg(context)
        .stdout(Stdio::piped())
        // .stderr(Stdio::null())
        .spawn();

    let mut lines: Vec<String> = Vec::new();
    if let Ok(mut child) = output {
        let stdout = child.stdout.take().expect("Failed to take stdout");

        let reader = BufReader::new(stdout);
        for line in reader.lines() {
            match line {
                Ok(line) => {
                    println!("Line: {}", line);
                    lines.push(line);
                }
                Err(e) => eprintln!("Error reading line: {}", e),
            }
        }

        // Optionally, handle the case where you need to wait for the process to finish
        match child.wait() {
            Ok(status) => println!("Process exited with status: {}", status),
            Err(e) => eprintln!("Failed to wait on child: {}", e),
        };
    } else {
        eprintln!("Failed to start process.");
    }
    lines.join("\n")

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
    println!("Hello, world!");

    let database_url = env::var("DATABASE_URL")
        .unwrap_or("postgres://postgres:herdeherde@localhost:5430".to_string());

    println!("[db] connecting...");
    let pool = PgPoolOptions::new()
        .max_connections(5)
        .connect(&database_url)
        .await?;
    // .expect("Can't connect to database");
    println!("[db] connected!");

    let msg = env::args().take(2).last().unwrap();
    let candidates = get_candidates(&pool, &msg).await;
    println!("{:?}", candidates);
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
