FROM debian:trixie-slim
ARG DESK_UID=501
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    libreoffice-calc libreoffice-writer python3-uno python3-websockets python3-pil \
    chromium xvfb openbox dbus-x11 x11vnc novnc websockify x11-utils \
    poppler-utils fonts-dejavu-core fonts-liberation fonts-noto-cjk procps \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid ${DESK_UID} --shell /bin/sh desk
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends chromium-sandbox \
    && rm -rf /var/lib/apt/lists/* && mkdir -p /tmp/.X11-unix && chmod 1777 /tmp/.X11-unix
USER desk
WORKDIR /home/desk
ENV DISPLAY=:99 SAL_USE_VCLPLUGIN=gen NO_AT_BRIDGE=0
COPY start.sh /opt/start.sh
CMD ["/bin/sh", "/opt/start.sh"]
