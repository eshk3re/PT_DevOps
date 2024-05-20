FROM postgres:14

ARG DB_USER
ARG DB_REPL_USER
ARG DB_REPL_PASSWORD
ARG DB_HOST

RUN echo "#!/bin/bash \
\nset -eux \nsleep 10 \
\nrm -rf /var/lib/postgresql/data/* \
\nPGPASSWORD=$DB_REPL_PASSWORD pg_basebackup -h $DB_HOST -U ${DB_REPL_USER} \
-D /var/lib/postgresql/data --wal-method=stream --write-recovery-conf \
\nchown -R $DB_USER:$DB_USER /var/lib/postgresql/data \
\nchmod 700 /var/lib/postgresql/data \
\nexec postgres" > /usr/local/bin/script.sh \
&& chmod +x /usr/local/bin/script.sh

USER postgres

CMD ["/usr/local/bin/script.sh"]
