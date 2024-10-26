FROM rust:1.82 as bot

WORKDIR /hanbbot
COPY . /hanbbot
RUN apt update && \
  apt-get install -y python3-pip && \
  pip3 install -r requirements.txt --break-system-packages && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/*

from bot as hanb
WORKDIR /
RUN git clone https://github.com/handyc/hanb.git hanb_master && \
    mv /hanb_master/rust /hanb && \
    cd /hanb && \
    cargo build --release && \
    cp target/release/hanb /hanb && \
    cargo clean --release #redo

WORKDIR /hanbbot
ENV HANB_CMD=/hanb/hanb
ENTRYPOINT ["python3", "bot.py"]
