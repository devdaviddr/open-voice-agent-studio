FROM rust:1-slim AS build
WORKDIR /src
COPY Cargo.toml Cargo.lock* ./
COPY src ./src
RUN cargo build --release

FROM debian:bookworm-slim
COPY --from=build /src/target/release/audio /usr/local/bin/audio
EXPOSE 8001
CMD ["audio"]
