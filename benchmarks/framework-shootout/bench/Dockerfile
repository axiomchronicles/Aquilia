FROM python:3.11-alpine

# Install dependencies including wrk and hey from community/edge repos
RUN apk add --no-cache \
    curl \
    bash \
    wrk \
    hey \
    git \
    build-base \
    --repository=http://dl-cdn.alpinelinux.org/alpine/edge/community \
    --repository=http://dl-cdn.alpinelinux.org/alpine/edge/main

WORKDIR /bench
COPY bench/ /bench/

CMD ["./run_all.sh"]

