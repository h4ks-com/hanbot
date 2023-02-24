FROM mattfly/hanb:latest

WORKDIR /hanbbot
COPY . /hanbbot
RUN apt update && \
  apt-get install -y python3-pip && \
  pip3 install -r requirements.txt && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/*
ENV HANB_CMD=/hanb/hanb
ENTRYPOINT ["python3", "bot.py"]
