#! /bin/sh
#
# build_module.sh
# Copyright (C) 2026 TU Dresden
#
# Distributed under terms of the MIT license.
#


./configure --add-module="/usr/local/src/${NGINX_VER}/${MODULE_SRC}" --with-ld-opt="-lpython3.12" \
    --prefix=/usr/share/nginx --conf-path=/etc/nginx/nginx.conf \
    --http-log-path=/var/log/nginx/access.log --error-log-path=stderr \
    --lock-path=/var/lock/nginx.lock --pid-path=/run/nginx.pid \
    --modules-path=/usr/lib/nginx/modules --http-client-body-temp-path=/var/lib/nginx/body \
    --http-fastcgi-temp-path=/var/lib/nginx/fastcgi --http-proxy-temp-path=/var/lib/nginx/proxy \
    --http-scgi-temp-path=/var/lib/nginx/scgi --http-uwsgi-temp-path=/var/lib/nginx/uwsgi \
    --with-pcre-jit --with-http_ssl_module --with-http_stub_status_module \
    --with-http_realip_module --with-http_auth_request_module --with-http_v2_module \
    --with-http_v3_module --with-http_dav_module --with-http_slice_module --with-threads \
    --with-http_addition_module --with-http_flv_module --with-http_gunzip_module \
    --with-http_gzip_static_module --with-http_mp4_module --with-http_random_index_module \
    --with-http_secure_link_module --with-http_sub_module --with-mail_ssl_module \
    --with-stream_ssl_module --with-stream_ssl_preread_module --with-stream_realip_module \
    --with-compat --with-debug \
    && make -j && make install && ln -s /usr/share/nginx/sbin/nginx /usr/local/sbin/nginx \
    && mkdir -p /var/lib/nginx
# --with-http_image_filter_module=dynamic \
# --with-http_perl_module=dynamic --with-mail=dynamic \
# --with-stream=dynamic \
 # --with-http_xslt_module=dynamic --with-http_geoip_module=dynamic --with-stream_geoip_module=dynamic \
