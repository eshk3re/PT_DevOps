FROM postgres:14

ARG DB_REPL_USER
ARG DB_REPL_PASSWORD
ARG DB_HOST
ARG DB_USER
ARG DB_PORT

COPY init.sql /docker-entrypoint-initdb.d/

RUN sed -i \
    -e "s/\${DB_REPL_USER}/${DB_REPL_USER}/g" \
    -e "s/\${DB_REPL_PASSWORD}/${DB_REPL_PASSWORD}/g" \
    -e "s/\${DB_DATABASE}/${DB_DATABASE}/g" \
    /docker-entrypoint-initdb.d/init.sql


RUN echo "wal_level = replica\nmax_wal_senders = 10 \
\nwal_log_hints = on\narchive_mode = on\nlog_replication_commands = on \
\narchive_command = 'cp %p /oracle/pg_data/archive/%f' \
\nhba_file = '/etc/postgresql/pg_hba.conf'\nlisten_addresses = '*' \
\nlog_destination = 'stderr'\nlogging_collector = on \
\nlog_directory = '/var/log/postgresql/'\nlog_filename = 'postgresql-14-main.log'" \
>> /etc/postgresql/postgresql.conf \
&& echo "local all $DB_USER peer \
\nhost all all 0.0.0.0/0 password \
\nhost replication $DB_REPL_USER all scram-sha-256" >> /etc/postgresql/pg_hba.conf

CMD ["postgres", "-c", "config_file=/etc/postgresql/postgresql.conf", "-c", "hba_file=/etc/postgresql/pg_hba.conf"]
