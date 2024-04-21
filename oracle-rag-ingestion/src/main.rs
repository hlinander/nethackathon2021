use glob::glob;
use std::fs::File;
use std::io::{self, BufReader, Error, Read};
use std::{env, path::Path};

use sqlx::PgPool;
use sqlx::{postgres::PgPoolOptions, Executor};
use tokio;

fn read_binary_file<P: AsRef<Path>>(path: P) -> io::Result<(i32, Vec<(Vec<f32>, String)>)> {
    let file = File::open(path)?;
    let mut reader = BufReader::new(file);

    // Read the number of columns as i32
    let mut n_cols_bytes = [0u8; 4];
    reader.read_exact(&mut n_cols_bytes)?;
    let n_cols = i32::from_le_bytes(n_cols_bytes);

    if n_cols <= 0 {
        return Err(Error::new(
            io::ErrorKind::InvalidData,
            "Number of columns must be positive",
        ));
    }

    let mut rows = Vec::new();
    let mut float_bytes = [0u8; 4];
    let mut text_length_bytes = [0u8; 4];

    while let Ok(_) = reader.read_exact(&mut float_bytes) {
        let mut float_row = Vec::with_capacity(n_cols as usize);
        float_row.push(f32::from_le_bytes(float_bytes));

        // Read the rest of the floats for this row
        for _ in 1..n_cols {
            reader.read_exact(&mut float_bytes)?;
            float_row.push(f32::from_le_bytes(float_bytes));
        }

        // Read the length of the following string
        reader.read_exact(&mut text_length_bytes)?;
        let text_length = u32::from_le_bytes(text_length_bytes) as usize;

        // Read the string of the given length
        let mut string_bytes = vec![0u8; text_length];
        reader.read_exact(&mut string_bytes)?;
        let text = String::from_utf8(string_bytes)
            .map_err(|_| Error::new(io::ErrorKind::InvalidData, "Invalid UTF-8 sequence"))?;

        // Store the tuple of floats and string
        rows.push((float_row, text));
    }

    Ok((n_cols, rows))
}

async fn insert_rows(pool: &PgPool, rows: Vec<(Vec<f32>, String)>) -> Result<(), sqlx::Error> {
    let mut transaction = pool.begin().await?;
    for (row_idx, (row, row_str)) in rows.iter().enumerate() {
        // Prepare an SQL INSERT statement
        // Assuming table name is `data_table` and it has columns `col1, col2, ..., colN`
        // let mut query = "INSERT INTO data_table VALUES (".to_owned();
        let mut query =
            format!("INSERT INTO items (embedding, text) VALUES ($1, $2) ON CONFLICT DO NOTHING",);

        sqlx::query(&query)
            .bind(&row as &[_])
            .bind(row_str)
            .execute(&mut *transaction)
            .await
            .inspect_err(|err| {
                println!("{}", err);
            })
            .unwrap();
    }
    transaction
        .commit()
        .await
        .inspect_err(|err| println!("{}", err))
        .unwrap();
    Ok(())
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
    let (n_embed, embeddings) =
        read_binary_file("../oracle-worker/ggml_2024/nhwiki/chunked_wiki_00.txt_00000.bin")
            .unwrap();

    // Execute the SQL command
    pool.execute("CREATE DATABASE embeddings").await;
    pool.execute(
        "
        DROP EXTENSION IF EXISTS vectors;
        CREATE EXTENSION vectors;
        ",
    )
    .await
    .inspect_err(|err| {
        println!("{}", err);
    });
    pool.execute(
        "
            DROP TABLE items; 
        ",
    )
    .await
    .inspect_err(|err| {
        println!("{}", err);
    });

    pool.execute(
        format!(
            "
            CREATE TABLE items (
              id bigserial PRIMARY KEY,
              embedding vector({}) NOT NULL,
              text TEXT NOT NULL UNIQUE
            );
        ",
            n_embed
        )
        .as_str(),
    )
    .await
    .inspect_err(|err| {
        println!("{}", err);
    });
    for entry in
        glob("../oracle-worker/ggml_2024/nhwiki/*.bin").expect("Failed to read glob pattern")
    {
        match entry {
            Ok(path) => {
                let (n_embed, embeddings) = read_binary_file(&path).unwrap();
                println!("{:?}", embeddings.last().unwrap().1);
                insert_rows(&pool, embeddings)
                    .await
                    .inspect_err(|err| {
                        println!("{}", err);
                    })
                    .unwrap();
                println!("ingested {:?}", path);
            }
            Err(e) => println!("{:?}", e),
        }
    }
    Ok(())
}
