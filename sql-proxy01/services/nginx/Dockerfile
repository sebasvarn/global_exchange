# basado en bullseye-slim
FROM nginx:1.22  
ENV TZ="America/Asuncion"

# install dependencies: htpasswd fancyindex
RUN apt-get update && apt-get install -y --no-install-recommends apache2-utils \
    && apt-get install -y --no-install-recommends nginx-extras 

RUN rm /etc/nginx/conf.d/default.conf
RUN rm /etc/nginx/sites-enabled/default
COPY nginx.conf /etc/nginx/conf.d

WORKDIR /usr/src/nginx-home

# copy entrypoint-test.sh
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# run entrypoint.sh
ENTRYPOINT ["/usr/src/nginx-home/entrypoint.sh"]