docker run \
  --name pgvecto-rs-demo \
  -e POSTGRES_PASSWORD=herdeherde \
  -p 5430:5432 \
  -d tensorchord/pgvecto-rs:pg16-v0.2.1
