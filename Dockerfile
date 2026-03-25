FROM odoo:19.0

USER root

# Dependencias Python de tus módulos
COPY ./config/requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages -r /tmp/requirements.txt

# Módulos custom
COPY ./addons /mnt/extra-addons

USER odoo