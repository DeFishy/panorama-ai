# syntax=docker/dockerfile:1
# Образ для миграций: dbmate поверх postgres той же основной версии, что и база.
# pg_dump должен совпадать с сервером по версии, иначе contracts/schema.sql
# будет отличаться между машинами.

ARG DBMATE_VERSION=2.36.0

FROM scratch AS dbmate-amd64
ARG DBMATE_VERSION
ADD --checksum=sha256:47e284b3d8cbad1ba5f090495aa05afd1bbd5f35e2ed5577aad06da74ce780ce \
    https://github.com/amacneil/dbmate/releases/download/v${DBMATE_VERSION}/dbmate-linux-amd64 /dbmate

FROM scratch AS dbmate-arm64
ARG DBMATE_VERSION
ADD --checksum=sha256:c7d49db4b54e487eddf8ce7d6e88f4035e1eb04c7edb16008f668cdfad2f29e8 \
    https://github.com/amacneil/dbmate/releases/download/v${DBMATE_VERSION}/dbmate-linux-arm64 /dbmate

FROM dbmate-${TARGETARCH} AS dbmate

FROM postgres:17
COPY --from=dbmate --chmod=755 /dbmate /usr/local/bin/dbmate
ENTRYPOINT ["dbmate"]
CMD ["--wait", "up"]
